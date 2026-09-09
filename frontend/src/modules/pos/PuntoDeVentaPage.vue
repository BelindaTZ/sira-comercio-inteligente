<script setup>
/**
 * Punto de Venta & Registro Rápido (001, US1). Orquesta el flujo completo:
 * abrir venta → agregar líneas (escáner / manual) → cobrar (efectivo / tarjeta
 * simulada) → confirmar → abrir el comprobante (FR-004, SC-011). Toda regla vive
 * en el backend; esta página sólo llama a `ventasApi`.
 *
 * Rediseño feature 013 sobre `docs/diseno-ui/.../sira_punto_de_venta_y_registro_r_pido…`:
 * cockpit de dos columnas con el kit del design-system. El grid de productos con
 * foto del mockup necesita un endpoint de catálogo para el Cajero (hoy no tiene
 * lectura de `productos`/`inventario`); mientras tanto el registro es por escáner
 * o código, que es el flujo real.
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import { useSesion } from '@/stores/sesion'
import { money as moneyUsd } from '@/shared/currency'
import Icon from '@/shared/ui/Icon.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import BuscadorProducto from './components/BuscadorProducto.vue'
import BuscadorCliente from './components/BuscadorCliente.vue'
import TicketVenta from './components/TicketVenta.vue'
import SimuladorDatafono from './components/SimuladorDatafono.vue'

const sesionStore = useSesion()
const sesion = reactive({
  tiendaId: sesionStore.tiendaId ?? (Number(localStorage.getItem('sira_tienda_id')) || 1),
  cajeroId: sesionStore.empleadoId ?? (Number(localStorage.getItem('sira_empleado_id')) || 1),
  cajaId: Number(localStorage.getItem('sira_caja_id')) || null,
})

const venta = ref(null)
const clienteId = ref(null)
const medioPagoId = ref(null)
const mediosPago = ref([])
const tipoComprobante = ref('nota_venta')
const identificacion = ref('')
const razonSocial = ref('')
const efectivoRecibido = ref('')

const cargando = ref(false)
const procesandoPago = ref(false)
const error = ref('')
const pagoTarjetaAprobado = ref(false)
const datafonoAviso = ref('')

const money = (v) => moneyUsd(v, { showCode: false })
const tiendaNombre = computed(() => sesionStore.tiendaNombre || `Tienda ${sesion.tiendaId}`)
const cajeroNombre = computed(() => sesionStore.nombre || `Cajero ${sesion.cajeroId}`)

const medioSeleccionado = computed(
  () => mediosPago.value.find((m) => m.medio_pago_id === medioPagoId.value) || null,
)
const requiereTarjeta = computed(() => medioSeleccionado.value?.nombre === 'Tarjeta')
const esEfectivo = computed(() => medioSeleccionado.value?.nombre === 'Efectivo')
const vuelto = computed(() => {
  const r = Number(efectivoRecibido.value)
  const t = Number(venta.value?.total || 0)
  return r > t ? r - t : 0
})
const quickCash = computed(() => {
  const t = Number(venta.value?.total || 0)
  if (t <= 0) return []
  const opts = new Set([Math.ceil(t * 100) / 100])
  for (const base of [1, 5, 10, 20, 50, 100]) {
    opts.add(Math.ceil(t / base) * base)
  }
  return [...opts].filter((n) => n >= t).sort((a, b) => a - b).slice(0, 4)
})

const ICONO_MEDIO = { Efectivo: 'bank', Tarjeta: 'key', 'Transferencia Bancaria': 'bank', 'Billetera Digital': 'wifi' }

async function cargarMediosPago() {
  try {
    mediosPago.value = await ventasApi.mediosPagoDisponibles()
  } catch (e) {
    error.value = e.message
  }
}

watch(requiereTarjeta, async (necesita) => {
  datafonoAviso.value = ''
  if (!necesita || !sesion.cajaId) return
  try {
    const { disponible, estado } = await ventasApi.datafonoDisponible(sesion.cajaId)
    if (!disponible) {
      datafonoAviso.value = `El datáfono de esta caja está ${estado || 'no disponible'}. Puedes cobrar con otro medio de pago.`
    }
  } catch {
    /* la advertencia es best-effort, nunca bloquea el cobro */
  }
})

onMounted(cargarMediosPago)

const puedeConfirmar = computed(
  () =>
    venta.value?.estado === 'en_curso' &&
    venta.value.lineas.length > 0 &&
    medioPagoId.value != null &&
    (!requiereTarjeta.value || pagoTarjetaAprobado.value) &&
    (tipoComprobante.value !== 'factura' || identificacion.value.trim().length > 0),
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
  clienteId.value = null
  efectivoRecibido.value = ''
  venta.value = await conError(() =>
    ventasApi.iniciar({ tiendaId: sesion.tiendaId, cajeroId: sesion.cajeroId }),
  )
}

async function vincularCliente(c) {
  clienteId.value = c.household_id
  if (venta.value && venta.value.estado === 'en_curso' && !venta.value.lineas.length) {
    venta.value = await conError(() =>
      ventasApi.iniciar({
        tiendaId: sesion.tiendaId,
        cajeroId: sesion.cajeroId,
        householdId: c.household_id,
      }),
    )
  }
}

async function agregar({ productId, codigoBarras, cantidad }) {
  if (!venta.value) {
    venta.value = await conError(() =>
      ventasApi.iniciar({
        tiendaId: sesion.tiendaId,
        cajeroId: sesion.cajeroId,
        householdId: clienteId.value,
      }),
    )
  }
  venta.value = await conError(() =>
    ventasApi.agregarLinea(venta.value.venta_id, { productId, codigoBarras, cantidad }),
  )
}

async function remover({ lineaId, autorizaEmpleadoId, autorizaPin, motivo }) {
  venta.value = await conError(() =>
    ventasApi.removerLinea(venta.value.venta_id, lineaId, {
      autorizaEmpleadoId,
      autorizaPin,
      motivo,
    }),
  )
}

async function aplicarDescuento({ lineaId, tipo, valor, motivo, empleadoAutorizaId, autorizaPin }) {
  venta.value = await conError(() =>
    ventasApi.aplicarDescuento(venta.value.venta_id, lineaId, {
      tipo,
      valor,
      motivo,
      empleadoAplicaId: sesion.cajeroId,
      empleadoAutorizaId,
      autorizaPin,
    }),
  )
}

async function cobrarTarjeta({ escenario, onResultado }) {
  procesandoPago.value = true
  try {
    const res = await conError(() =>
      ventasApi.pagoTarjeta(venta.value.venta_id, { monto: venta.value.total, escenario }),
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
    }),
  )
  venta.value = confirmada
  window.open(ventasApi.comprobanteUrl(confirmada.venta_id), '_blank', 'noopener')
}

// --- atajos de teclado del mockup ([F2] buscar · [F4] descuento · [F12] cobrar) ---
const buscador = ref(null)
function atajos(e) {
  if (e.key === 'F2') {
    e.preventDefault()
    if (!venta.value) return nuevaVenta()
    buscador.value?.focar?.()
  } else if (e.key === 'F12') {
    e.preventDefault()
    if (puedeConfirmar.value && !cargando.value) confirmar()
  }
}
onMounted(() => window.addEventListener('keydown', atajos))
onBeforeUnmount(() => window.removeEventListener('keydown', atajos))
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-6 lg:px-8">
    <header class="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-center">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="font-display text-2xl font-extrabold tracking-tight text-brand-950">
            Punto de Venta
          </h1>
          <SemanticChip v-if="venta?.estado === 'en_curso'" tipo="ok">Venta abierta</SemanticChip>
          <SemanticChip v-else-if="venta?.estado === 'confirmada'" tipo="neutral">Confirmada</SemanticChip>
        </div>
        <p class="mt-0.5 text-[13px] font-medium text-slate-600">
          {{ tiendaNombre }}<template v-if="sesion.cajaId"> · Caja {{ sesion.cajaId }}</template>
          · {{ cajeroNombre }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <span
          class="hidden items-center gap-2 rounded-lg border border-brand-200 bg-white px-2.5 py-1.5 font-mono text-[11px] font-semibold text-slate-500 sm:flex"
        >
          <span><b class="text-brand-700">F2</b> Buscar</span>
          <span class="text-slate-300">·</span>
          <span><b class="text-brand-700">F12</b> Cobrar</span>
        </span>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl bg-brand-800 px-4 py-2.5 text-[13px] font-bold text-white shadow-md hover:bg-brand-700"
          @click="nuevaVenta"
        >
          <Icon name="plus" :size="17" /> Nueva venta
        </button>
      </div>
    </header>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">{{ error }}</p>

    <div
      v-if="!venta"
      class="satin-card grid place-items-center rounded-2xl p-16 text-center shadow-card-subtle"
    >
      <div>
        <Icon name="cart" :size="30" class="mx-auto mb-3 text-brand-300" />
        <p class="text-[14px] font-bold text-slate-800">Sin venta en curso</p>
        <p class="mt-1 text-[12px] text-slate-500">Pulsá «Nueva venta» para empezar a escanear.</p>
      </div>
    </div>

    <div v-else class="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <!-- Columna izquierda: registro + ticket -->
      <section class="space-y-4">
        <BuscadorProducto
          v-if="venta.estado === 'en_curso'"
          ref="buscador"
          :tienda-id="sesion.tiendaId"
          @agregar="agregar"
        />
        <TicketVenta
          :venta="venta"
          :removible="venta.estado === 'en_curso'"
          @remover="remover"
          @descuento="aplicarDescuento"
          @incrementar="agregar({ productId: $event, cantidad: 1 })"
        />
      </section>

      <!-- Columna derecha: cliente + cobro -->
      <aside class="space-y-4">
        <BuscadorCliente
          v-if="venta.estado === 'en_curso'"
          :seleccionado-id="clienteId"
          @seleccionar="vincularCliente"
          @quitar="clienteId = null"
        />

        <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
          <h2 class="mb-3 font-display text-[13px] font-bold text-brand-950">Cobro</h2>

          <div class="mb-1.5 flex items-baseline justify-between">
            <span class="text-[11px] font-bold uppercase tracking-wide text-slate-500">Total a pagar</span>
            <span class="font-display text-2xl font-extrabold tabular-nums text-brand-900">
              {{ money(venta.total) }}
            </span>
          </div>

          <label class="mb-1 mt-3 block text-[11px] font-bold uppercase tracking-wide text-slate-500">
            Medio de pago
          </label>
          <div class="mb-3 grid grid-cols-2 gap-1.5">
            <button
              v-for="m in mediosPago"
              :key="m.medio_pago_id"
              type="button"
              :disabled="venta.estado !== 'en_curso'"
              class="flex items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-[12px] font-semibold transition disabled:opacity-40"
              :class="
                medioPagoId === m.medio_pago_id
                  ? 'border-brand-600 bg-brand-50 text-brand-900'
                  : 'border-brand-200 bg-white text-slate-600 hover:border-brand-400'
              "
              @click="((medioPagoId = m.medio_pago_id), (pagoTarjetaAprobado = false))"
            >
              <Icon :name="ICONO_MEDIO[m.nombre] || 'bank'" :size="14" /> {{ m.nombre }}
            </button>
          </div>

          <p
            v-if="datafonoAviso"
            class="mb-3 flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-[11px] text-amber-800"
          >
            <Icon name="alert" :size="13" class="mt-px shrink-0" /> {{ datafonoAviso }}
          </p>

          <!-- Efectivo: recibido + vuelto -->
          <template v-if="esEfectivo">
            <label class="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-500">
              Pago con efectivo
            </label>
            <input
              v-model="efectivoRecibido"
              type="number"
              min="0"
              placeholder="Monto recibido"
              class="mb-1.5 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            />
            <div class="mb-2 flex flex-wrap gap-1.5">
              <button
                v-for="q in quickCash"
                :key="q"
                type="button"
                class="rounded-lg border border-brand-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-brand-400"
                @click="efectivoRecibido = String(q)"
              >
                {{ money(q) }}
              </button>
            </div>
            <p v-if="vuelto > 0" class="mb-3 text-right text-[12px] font-bold text-emerald-700">
              Vuelto: {{ money(vuelto) }}
            </p>
          </template>

          <label class="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-500">
            Comprobante
          </label>
          <select
            v-model="tipoComprobante"
            class="mb-3 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option value="nota_venta">Nota de venta</option>
            <option value="factura">Factura</option>
          </select>

          <template v-if="tipoComprobante === 'factura'">
            <input
              v-model="identificacion"
              placeholder="Identificación del comprador"
              class="mb-2 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            />
            <input
              v-model="razonSocial"
              placeholder="Razón social"
              class="mb-3 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            />
          </template>

          <button
            type="button"
            :disabled="!puedeConfirmar || cargando"
            class="w-full rounded-xl bg-brand-800 px-4 py-3 text-sm font-bold text-white shadow-md hover:bg-brand-700 disabled:opacity-40"
            @click="confirmar"
          >
            {{ cargando ? 'Procesando…' : `Cobrar ${money(venta.total)} — Imprimir boleta` }}
          </button>
          <p
            v-if="venta.estado === 'confirmada'"
            class="mt-2 text-center text-[13px] font-bold text-emerald-700"
          >
            Venta #{{ venta.venta_id }} confirmada
          </p>
        </div>

        <SimuladorDatafono
          v-if="requiereTarjeta && venta.estado === 'en_curso' && venta.lineas.length"
          :monto="money(venta.total)"
          :procesando="procesandoPago"
          @cobrar="cobrarTarjeta"
        />
      </aside>
    </div>
  </div>
</template>
