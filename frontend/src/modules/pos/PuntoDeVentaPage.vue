<script setup>
/**
 * Punto de venta (US1). Orquesta el flujo completo: abrir venta → agregar
 * líneas → cobrar (efectivo / tarjeta simulada) → confirmar → abrir el
 * comprobante para imprimir/guardar (FR-004, SC-011).
 *
 * Toda regla vive en el backend; esta página sólo llama a `ventasApi`.
 */
import { computed, reactive, ref } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import BuscadorProducto from './components/BuscadorProducto.vue'
import TicketVenta from './components/TicketVenta.vue'
import SimuladorDatafono from './components/SimuladorDatafono.vue'

// Datos de sesión — provisorios hasta la feature 008 (login real).
const sesion = reactive({
  tiendaId: Number(localStorage.getItem('sira_tienda_id')) || 1,
  cajeroId: Number(localStorage.getItem('sira_empleado_id')) || 1,
})

const venta = ref(null)
const medioPagoId = ref(null)
const mediosPago = [
  { id: 1, nombre: 'Efectivo', tarjeta: false },
  { id: 2, nombre: 'Tarjeta', tarjeta: true },
  { id: 3, nombre: 'Transferencia', tarjeta: false },
  { id: 4, nombre: 'Billetera Digital', tarjeta: false },
]
const tipoComprobante = ref('nota_venta')
const identificacion = ref('')
const razonSocial = ref('')

const cargando = ref(false)
const procesandoPago = ref(false)
const error = ref('')
const pagoTarjetaAprobado = ref(false)

const medioSeleccionado = computed(() => mediosPago.find((m) => m.id === medioPagoId.value) || null)
const requiereTarjeta = computed(() => medioSeleccionado.value?.tarjeta === true)
const puedeConfirmar = computed(
  () =>
    venta.value?.estado === 'en_curso' &&
    venta.value.lineas.length > 0 &&
    medioPagoId.value != null &&
    (!requiereTarjeta.value || pagoTarjetaAprobado.value) &&
    (tipoComprobante.value !== 'factura' || identificacion.value.trim().length > 0)
)

async function conError(fn) {
  error.value = ''
  cargando.value = true
  try {
    return await fn()
  } catch (e) {
    error.value = e.message
    throw e
  } finally {
    cargando.value = false
  }
}

async function nuevaVenta() {
  pagoTarjetaAprobado.value = false
  medioPagoId.value = null
  venta.value = await conError(() =>
    ventasApi.iniciar({ tiendaId: sesion.tiendaId, cajeroId: sesion.cajeroId })
  )
}

async function agregar({ productId, codigoBarras, cantidad }) {
  if (!venta.value) await nuevaVenta()
  venta.value = await conError(() =>
    ventasApi.agregarLinea(venta.value.venta_id, { productId, codigoBarras, cantidad })
  )
}

async function remover({ lineaId, autorizaEmpleadoId, motivo }) {
  venta.value = await conError(() =>
    ventasApi.removerLinea(venta.value.venta_id, lineaId, { autorizaEmpleadoId, motivo })
  )
}

async function cobrarTarjeta({ escenario, onResultado }) {
  procesandoPago.value = true
  try {
    const res = await conError(() =>
      ventasApi.pagoTarjeta(venta.value.venta_id, { monto: venta.value.total, escenario })
    )
    onResultado(res.resultado)
    pagoTarjetaAprobado.value = res.resultado === 'aprobado'
  } finally {
    procesandoPago.value = false
  }
}

async function confirmar() {
  const confirmada = await conError(() =>
    ventasApi.confirmar(venta.value.venta_id, {
      medioPagoId: medioPagoId.value,
      tipoComprobante: tipoComprobante.value,
      identificacion: identificacion.value,
      razonSocial: razonSocial.value,
    })
  )
  venta.value = confirmada
  // SC-011: abrir el comprobante de inmediato para imprimir/guardar.
  window.open(ventasApi.comprobanteUrl(confirmada.venta_id), '_blank', 'noopener')
}
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <header class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Punto de Venta</h1>
      <button
        type="button"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
        @click="nuevaVenta"
      >
        Nueva venta
      </button>
    </header>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div
      v-if="!venta"
      class="rounded-xl border border-dashed border-outline-variant p-10 text-center text-on-surface-variant"
    >
      Pulsa «Nueva venta» para empezar a escanear.
    </div>

    <div v-else class="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <section class="space-y-4">
        <BuscadorProducto v-if="venta.estado === 'en_curso'" @agregar="agregar" />
        <TicketVenta :venta="venta" :removible="venta.estado === 'en_curso'" @remover="remover" />
      </section>

      <aside class="space-y-4">
        <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
          <h2 class="mb-3 text-sm font-semibold text-on-surface">Cobro</h2>

          <label class="mb-2 block text-xs font-medium text-on-surface-variant"
            >Medio de pago</label
          >
          <select
            v-model.number="medioPagoId"
            :disabled="venta.estado !== 'en_curso'"
            class="mb-3 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
          >
            <option :value="null">Selecciona…</option>
            <option v-for="m in mediosPago" :key="m.id" :value="m.id">{{ m.nombre }}</option>
          </select>

          <label class="mb-2 block text-xs font-medium text-on-surface-variant">Comprobante</label>
          <select
            v-model="tipoComprobante"
            class="mb-3 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
          >
            <option value="nota_venta">Nota de venta</option>
            <option value="factura">Factura</option>
          </select>

          <template v-if="tipoComprobante === 'factura'">
            <input
              v-model="identificacion"
              placeholder="Identificación del comprador"
              class="mb-2 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
            />
            <input
              v-model="razonSocial"
              placeholder="Razón social"
              class="mb-3 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
            />
          </template>

          <button
            type="button"
            :disabled="!puedeConfirmar || cargando"
            class="w-full rounded-lg bg-primary-container px-4 py-2.5 text-sm font-bold text-on-primary-container disabled:opacity-40"
            @click="confirmar"
          >
            Confirmar venta
          </button>
          <p
            v-if="venta.estado === 'confirmada'"
            class="mt-2 text-center text-sm font-semibold text-on-tertiary-container"
          >
            Venta #{{ venta.venta_id }} confirmada
          </p>
        </div>

        <SimuladorDatafono
          v-if="requiereTarjeta && venta.estado === 'en_curso' && venta.lineas.length"
          :monto="venta.total"
          :procesando="procesandoPago"
          @cobrar="cobrarTarjeta"
        />
      </aside>
    </div>
  </main>
</template>
