<script setup>
/**
 * Punto de Venta & Registro Rápido (001 US1). Cockpit de dos columnas según
 * `docs/diseno-ui/.../Punto d eventa/`: barra de acciones (Pausar · Anular ·
 * Cuadre de Caja · Nueva Venta), buscador unificado + grid de productos a la
 * izquierda, "Ticket Activo" con cliente, totales, medios de pago y cobro a la
 * derecha. Toda regla vive en el backend.
 *
 * El turno de la caja (apertura / cierre) se abre y cierra desde aquí: una caja
 * es el manejo de efectivo de un cajero durante su turno, no la caja física.
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import { cajaApi } from '@/services/cajaApi'
import { clientesApi } from '@/services/clientesApi'
import { useSesion } from '@/stores/sesion'
import { money as moneyUsd } from '@/shared/currency'
import { confirm, prompt } from '@/shared/ui/dialogs'
import Icon from '@/shared/ui/Icon.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Modal from '@/shared/ui/Modal.vue'
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

const money = (v) => moneyUsd(v, { showCode: false })
const tiendaNombre = computed(() => sesionStore.tiendaNombre || `Tienda ${sesion.tiendaId}`)
const cajeroNombre = computed(() => sesionStore.nombre || `Cajero ${sesion.cajeroId}`)

const venta = ref(null)
const cliente = ref(null)
const medioPagoId = ref(null)
const mediosPago = ref([])
const tipoComprobante = ref('nota_venta')
const identificacion = ref('')
const razonSocial = ref('')
const efectivoRecibido = ref('')

const cargando = ref(false)
const procesandoPago = ref(false)
const error = ref('')
const aviso = ref('')
const pagoTarjetaAprobado = ref(false)
const datafonoAviso = ref('')
const ticketsPausados = ref([])
const nivelesFidel = ref([])
const ventaCobrada = ref(null)
const emailEnviando = ref(false)
const emailResultado = ref('')

// alta rápida de cliente desde el POS
const modalNuevoCliente = ref(false)
const formCliente = reactive({ nombre: '', email: '', documento: '', consentimiento: true })
const guardandoCliente = ref(false)

// ---- turno de caja -------------------------------------------------------
const cajas = ref([])
const turno = ref(null)
const modalCaja = ref(null) // 'abrir' | 'cerrar' | null
const formCaja = reactive({ cajaId: null, fondoInicial: '', totalContado: '' })
const guardandoCaja = ref(false)
const cajaAbierta = computed(() => turno.value?.abierta === true)

async function cargarCajas() {
  try {
    cajas.value = await ventasApi.cajas(sesion.tiendaId)
    if (!sesion.cajaId && cajas.value.length) sesion.cajaId = cajas.value[0].caja_id
  } catch {
    /* sin lista de cajas: se opera igual con la del localStorage */
  }
}

async function cargarTurno() {
  if (!sesion.cajaId) return
  try {
    turno.value = await cajaApi.turno(sesion.cajaId)
  } catch (e) {
    error.value = msg(e)
  }
}

async function abrirModalCaja() {
  Object.assign(formCaja, {
    cajaId: sesion.cajaId ?? cajas.value[0]?.caja_id ?? null,
    fondoInicial: '',
    totalContado: '',
  })
  error.value = ''
  // refresca el turno para que el "total esperado" del cuadre no salga viejo
  await cargarTurno()
  modalCaja.value = cajaAbierta.value ? 'cerrar' : 'abrir'
}

async function abrirCaja() {
  guardandoCaja.value = true
  error.value = ''
  try {
    await cajaApi.registrarApertura({
      cajaId: formCaja.cajaId,
      fondoInicial: Number(formCaja.fondoInicial || 0),
    })
    sesion.cajaId = formCaja.cajaId
    try {
      localStorage.setItem('sira_caja_id', String(formCaja.cajaId))
    } catch {
      /* almacenamiento no disponible */
    }
    modalCaja.value = null
    aviso.value = 'Caja abierta. Ya puedes registrar ventas.'
    await cargarTurno()
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardandoCaja.value = false
  }
}

async function cerrarCaja() {
  guardandoCaja.value = true
  error.value = ''
  try {
    const r = await cajaApi.registrarCierre({
      cajaId: sesion.cajaId,
      totalRegistrado: Number(formCaja.totalContado || 0),
    })
    modalCaja.value = null
    aviso.value =
      Number(r.diferencia) === 0
        ? 'Cuadre registrado: la caja cuadra.'
        : `Cuadre registrado con una diferencia de ${money(r.diferencia)}. Queda marcado para revisión.`
    await cargarTurno()
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardandoCaja.value = false
  }
}

// ---- medios de pago -----------------------------------------------------
const medioSeleccionado = computed(
  () => mediosPago.value.find((m) => m.medio_pago_id === medioPagoId.value) || null,
)
const requiereTarjeta = computed(() =>
  /tarjeta/i.test(medioSeleccionado.value?.nombre || ''),
)
const esEfectivo = computed(() => /efectivo/i.test(medioSeleccionado.value?.nombre || ''))
const esDigital = computed(() =>
  /digital|qr|billetera|transfer/i.test(medioSeleccionado.value?.nombre || ''),
)

const vuelto = computed(() => {
  const r = Number(efectivoRecibido.value)
  const t = Number(venta.value?.total || 0)
  return r > t ? r - t : 0
})
const quickCash = computed(() => {
  const t = Number(venta.value?.total || 0)
  if (t <= 0) return []
  const opts = new Set([Math.ceil(t * 100) / 100])
  for (const base of [1, 5, 10, 20, 50, 100]) opts.add(Math.ceil(t / base) * base)
  return [...opts].filter((n) => n >= t).sort((a, b) => a - b).slice(0, 4)
})

const ICONO_MEDIO = (n) =>
  /efectivo/i.test(n) ? 'bank' : /tarjeta/i.test(n) ? 'key' : /digital|qr/i.test(n) ? 'wifi' : 'tag'

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo completar la operación.'
}

async function cargarMediosPago() {
  try {
    mediosPago.value = await ventasApi.mediosPagoDisponibles()
  } catch (e) {
    error.value = msg(e)
  }
}

watch(requiereTarjeta, async (necesita) => {
  datafonoAviso.value = ''
  if (!necesita || !sesion.cajaId) return
  try {
    const { disponible, estado } = await ventasApi.datafonoDisponible(sesion.cajaId)
    if (!disponible) {
      datafonoAviso.value = `El datáfono de esta caja está ${estado || 'no disponible'}. Puedes cobrar con otro medio.`
    }
  } catch {
    /* la advertencia es best-effort */
  }
})

onMounted(() => {
  cargarMediosPago()
  cargarCajas().then(cargarTurno)
  clientesApi.niveles().then((n) => (nivelesFidel.value = n)).catch(() => {})
  window.addEventListener('keydown', atajos)
})
onBeforeUnmount(() => window.removeEventListener('keydown', atajos))

// ---- venta ------------------------------------------------------------
const artsCount = computed(() =>
  (venta.value?.lineas || []).reduce((s, l) => s + (l.cantidad || 0), 0),
)
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
    error.value = msg(e)
    throw e
  } finally {
    cargando.value = false
  }
}

function resetPago() {
  // el medio de pago se conserva entre ventas (casi siempre efectivo): un paso menos
  pagoTarjetaAprobado.value = false
  efectivoRecibido.value = ''
  tipoComprobante.value = 'nota_venta'
  identificacion.value = ''
  razonSocial.value = ''
  ventaCobrada.value = null
  emailResultado.value = ''
}

async function nuevaVenta() {
  resetPago()
  cliente.value = null
  venta.value = await conError(() =>
    ventasApi.iniciar({ tiendaId: sesion.tiendaId, cajeroId: sesion.cajeroId }),
  )
  buscador.value?.focar?.()
}

async function vincularCliente(c) {
  const nivel = nivelesFidel.value.find((n) => n.nivel_id === c.nivel_fidelizacion_id)
  cliente.value = { ...c, nivel_nombre: nivel?.nombre || null, puntos: null, valor_canje_usd: null }
  clientesApi
    .ficha360(c.household_id)
    .then((f) => {
      if (cliente.value?.household_id === c.household_id) {
        cliente.value = { ...cliente.value, puntos: f.puntos, valor_canje_usd: f.valor_canje_usd }
      }
    })
    .catch(() => {})
  // asocia el cliente a la venta actual (sirve incluso con líneas ya registradas)
  if (venta.value?.estado === 'en_curso') {
    venta.value = await conError(() =>
      ventasApi.vincularCliente(venta.value.venta_id, c.household_id),
    )
  }
}

async function quitarCliente() {
  cliente.value = null
  if (venta.value?.estado === 'en_curso' && venta.value.household_id) {
    venta.value = await conError(() => ventasApi.vincularCliente(venta.value.venta_id, null))
  }
}

async function agregar({ productId, codigoBarras, cantidad }) {
  if (!venta.value) {
    venta.value = await conError(() =>
      ventasApi.iniciar({
        tiendaId: sesion.tiendaId,
        cajeroId: sesion.cajeroId,
        householdId: cliente.value?.household_id,
      }),
    )
  }
  venta.value = await conError(() =>
    ventasApi.agregarLinea(venta.value.venta_id, { productId, codigoBarras, cantidad }),
  )
}

async function remover({ lineaId, autorizaEmpleadoId, autorizaPin, motivo }) {
  venta.value = await conError(() =>
    ventasApi.removerLinea(venta.value.venta_id, lineaId, { autorizaEmpleadoId, autorizaPin, motivo }),
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
  if (!puedeConfirmar.value || cargando.value) return
  const confirmada = await conError(() =>
    ventasApi.confirmar(venta.value.venta_id, {
      medioPagoId: medioPagoId.value,
      tipoComprobante: tipoComprobante.value,
      identificacion: identificacion.value,
      razonSocial: razonSocial.value,
    }),
  )
  venta.value = confirmada
  ventaCobrada.value = confirmada
  emailResultado.value = ''
  aviso.value = ''
  await cargarTurno()
}

function imprimirComprobante() {
  if (!ventaCobrada.value) return
  window.open(ventasApi.comprobanteUrl(ventaCobrada.value.venta_id), '_blank', 'noopener')
}

async function enviarComprobantePorCorreo() {
  if (!ventaCobrada.value) return
  emailEnviando.value = true
  emailResultado.value = ''
  try {
    const r = await ventasApi.enviarComprobanteEmail(ventaCobrada.value.venta_id)
    emailResultado.value = r.enviado
      ? `Comprobante enviado a ${r.email}.`
      : `No se pudo enviar por correo: ${r.motivo || 'servicio no disponible'}.`
  } catch (e) {
    emailResultado.value = msg(e)
  } finally {
    emailEnviando.value = false
  }
}

async function crearCliente() {
  if (!formCliente.nombre.trim() || !formCliente.email.trim()) {
    error.value = 'El nombre y el correo del cliente son obligatorios.'
    return
  }
  guardandoCliente.value = true
  error.value = ''
  try {
    const c = await clientesApi.crear({
      nombre: formCliente.nombre.trim(),
      email: formCliente.email.trim(),
      documentoIdentidad: formCliente.documento.trim() || null,
      consentimientoDatos: formCliente.consentimiento,
    })
    modalNuevoCliente.value = false
    Object.assign(formCliente, { nombre: '', email: '', documento: '', consentimiento: true })
    await vincularCliente(c)
    aviso.value = `Cliente ${c.nombre} registrado y vinculado a la venta.`
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardandoCliente.value = false
  }
}

// ---- pausar / anular --------------------------------------------------
function pausarTicket() {
  if (!venta.value || venta.value.estado !== 'en_curso' || !venta.value.lineas.length) return
  ticketsPausados.value.push({ venta: venta.value, cliente: cliente.value })
  venta.value = null
  cliente.value = null
  resetPago()
  aviso.value = 'Ticket pausado. Retómalo desde «Tickets pausados».'
}

function retomarTicket(i) {
  const t = ticketsPausados.value.splice(i, 1)[0]
  venta.value = t.venta
  cliente.value = t.cliente
  resetPago()
}

async function anularVenta() {
  if (!venta.value) return
  if (venta.value.estado === 'en_curso') {
    if (venta.value.lineas.length) {
      const ok = await confirm({
        title: 'Descartar el ticket en curso',
        message: 'Se pierden las líneas registradas. Esta acción no queda en el historial.',
        confirmText: 'Descartar',
        tone: 'danger',
      })
      if (!ok) return
    }
    venta.value = null
    cliente.value = null
    resetPago()
    aviso.value = 'Ticket descartado.'
    return
  }
  if (venta.value.estado === 'confirmada') {
    const motivo = await prompt({
      title: `Anular venta #${venta.value.venta_id}`,
      message: 'La anulación repone el stock y sólo puede hacerse durante la misma jornada (FR-007).',
      label: 'Motivo de la anulación',
      required: true,
      tone: 'danger',
      confirmText: 'Anular venta',
    })
    if (!motivo) return
    await conError(() =>
      ventasApi.anular(venta.value.venta_id, { empleadoId: sesion.cajeroId, motivo }),
    )
    aviso.value = `Venta #${venta.value.venta_id} anulada.`
    venta.value = null
    cliente.value = null
    resetPago()
    await cargarTurno()
  }
}

// ---- atajos de teclado ----------------------------------------------
const buscador = ref(null)
function atajos(e) {
  if (e.key === 'F2') {
    e.preventDefault()
    if (!venta.value || ventaCobrada.value) return nuevaVenta()
    buscador.value?.focar?.()
  } else if (e.key === 'F6') {
    e.preventDefault()
    pausarTicket()
  } else if (e.key === 'F12') {
    e.preventDefault()
    // tras cobrar, F12 arranca la venta siguiente — bucle rápido sin tocar el mouse
    if (ventaCobrada.value) nuevaVenta()
    else if (puedeConfirmar.value && !cargando.value) confirmar()
  }
}
</script>

<template>
  <div class="mx-auto max-w-[1720px] px-4 py-5 sm:px-6 lg:px-8">
    <!-- Barra de acciones del POS -->
    <header
      class="mb-4 flex flex-col justify-between gap-3 rounded-2xl border border-brand-200 bg-shell-bar px-4 py-3 text-white lg:flex-row lg:items-center"
    >
      <div class="flex items-center gap-3">
        <span class="grid h-9 w-9 place-items-center rounded-xl bg-brand-700">
          <Icon name="cart" :size="18" />
        </span>
        <div class="leading-tight">
          <p class="font-display text-[15px] font-extrabold">Punto de Venta</p>
          <p class="text-[11px] text-brand-200">
            {{ tiendaNombre }} · {{ cajeroNombre }}
            <template v-if="sesion.cajaId"> · Caja {{ sesion.cajaId }}</template>
          </p>
        </div>
        <SemanticChip :tipo="cajaAbierta ? 'ok' : 'quiebre'" class="ml-1">
          {{ cajaAbierta ? 'Caja abierta' : 'Caja cerrada' }}
        </SemanticChip>
      </div>

      <div class="flex flex-wrap items-center gap-1.5">
        <button
          v-if="ticketsPausados.length"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl border border-amber-400/40 bg-[#0e3f3a] px-2.5 py-1.5 text-[12px] font-semibold text-amber-200 hover:bg-[#134f49]"
          @click="retomarTicket(ticketsPausados.length - 1)"
        >
          <Icon name="clock" :size="14" /> Tickets pausados ({{ ticketsPausados.length }})
        </button>
        <button
          type="button"
          :disabled="!venta || venta.estado !== 'en_curso' || !venta.lineas.length"
          class="inline-flex items-center gap-1.5 rounded-xl border border-amber-400/40 bg-[#0e3f3a] px-2.5 py-1.5 text-[12px] font-semibold text-amber-200 hover:bg-[#134f49] disabled:opacity-40"
          @click="pausarTicket"
        >
          <Icon name="clock" :size="14" /> Pausar
          <span class="font-mono text-amber-400">F6</span>
        </button>
        <button
          type="button"
          :disabled="!venta"
          class="inline-flex items-center gap-1.5 rounded-xl border border-rose-400/40 bg-[#0e3f3a] px-2.5 py-1.5 text-[12px] font-semibold text-rose-200 hover:bg-rose-950/40 disabled:opacity-40"
          @click="anularVenta"
        >
          <Icon name="trash" :size="14" /> Anular
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl border border-[#1d635a] bg-[#0e3f3a] px-2.5 py-1.5 text-[12px] font-semibold text-brand-100 hover:bg-[#14534c]"
          @click="abrirModalCaja"
        >
          <Icon name="bank" :size="14" /> Cuadre de Caja
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl bg-emerald-400 px-3 py-1.5 text-[12px] font-bold text-brand-950 hover:bg-emerald-300"
          @click="nuevaVenta"
        >
          <Icon name="plus" :size="15" /> Nueva Venta
        </button>
      </div>
    </header>

    <p
      v-if="error"
      class="mb-3 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby"
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-3 flex items-center justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      <span>{{ aviso }}</span>
      <button class="text-brand-600 hover:text-brand-900" @click="aviso = ''">
        <Icon name="x" :size="14" />
      </button>
    </p>

    <!-- Caja cerrada: bloquea la venta -->
    <div
      v-if="!cajaAbierta"
      class="satin-card grid place-items-center rounded-2xl p-14 text-center shadow-card-subtle"
    >
      <div class="max-w-sm">
        <Icon name="bank" :size="30" class="mx-auto mb-3 text-brand-300" />
        <p class="text-[14px] font-bold text-slate-800">La caja está cerrada</p>
        <p class="mt-1 text-[12px] text-slate-500">
          Abre tu caja declarando el fondo inicial para empezar a registrar ventas.
        </p>
        <button
          type="button"
          class="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-brand-800 px-4 py-2.5 text-[13px] font-bold text-white hover:bg-brand-700"
          @click="abrirModalCaja"
        >
          <Icon name="bank" :size="16" /> Abrir caja
        </button>
      </div>
    </div>

    <!-- Sin venta -->
    <div
      v-else-if="!venta"
      class="satin-card grid place-items-center rounded-2xl p-14 text-center shadow-card-subtle"
    >
      <div>
        <Icon name="cart" :size="30" class="mx-auto mb-3 text-brand-300" />
        <p class="text-[14px] font-bold text-slate-800">Sin venta en curso</p>
        <p class="mt-1 text-[12px] text-slate-500">
          Pulsa «Nueva Venta» (o F2) para empezar a escanear.
        </p>
      </div>
    </div>

    <!-- Cockpit -->
    <div v-else class="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_380px] xl:grid-cols-[minmax(0,1fr)_420px]">
      <section>
        <BuscadorProducto
          v-if="venta.estado === 'en_curso'"
          ref="buscador"
          :tienda-id="sesion.tiendaId"
          :en-ticket="Object.fromEntries((venta.lineas || []).map((l) => [l.product_id, l.cantidad]))"
          @agregar="agregar"
        />
      </section>

      <aside class="space-y-4">
        <!-- Ticket -->
        <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
          <div class="flex items-center justify-between border-b border-brand-200 bg-brand-50/60 px-4 py-2.5">
            <div class="flex items-center gap-2">
              <span class="font-display text-[13px] font-bold text-brand-950">Ticket activo</span>
              <span
                class="rounded-full border border-brand-300 bg-white px-2 py-0.5 font-mono text-[10px] font-bold text-brand-900"
              >
                #T-{{ String(venta.venta_id).slice(-6) }}
              </span>
              <span class="text-[11px] font-semibold text-slate-500">{{ artsCount }} arts.</span>
            </div>
          </div>

          <!-- Cliente -->
          <div class="border-b border-brand-100 p-3">
            <div
              v-if="cliente"
              class="flex items-center justify-between rounded-xl border border-amethyst-200 bg-orchid-soft/60 px-3 py-2"
            >
              <div class="leading-tight">
                <div class="flex items-center gap-1.5 text-[12px] font-bold text-amethyst-900">
                  {{ cliente.nombre }}
                  <span
                    v-if="cliente.nivel_nombre"
                    class="rounded-full bg-amethyst-600 px-1.5 py-0.5 text-[9px] font-bold uppercase text-white"
                  >
                    {{ cliente.nivel_nombre }}
                  </span>
                </div>
                <div class="text-[10px] text-amethyst-700">
                  <template v-if="cliente.puntos != null">
                    {{ cliente.puntos.toLocaleString('es-EC') }} pts
                    <template v-if="cliente.valor_canje_usd">
                      · {{ money(cliente.valor_canje_usd) }} canjeables
                    </template>
                  </template>
                  <template v-else>Cliente afiliado</template>
                </div>
              </div>
              <button
                type="button"
                class="text-[11px] font-semibold text-amethyst-700 hover:underline"
                @click="quitarCliente"
              >
                Cambiar
              </button>
            </div>
            <div v-else class="flex items-start gap-2">
              <BuscadorCliente
                :seleccionado-id="null"
                class="!p-0 !shadow-none !bg-transparent flex-1"
                @seleccionar="vincularCliente"
              />
              <button
                type="button"
                title="Registrar un cliente nuevo"
                class="mt-0.5 shrink-0 rounded-lg border border-amethyst-300 bg-amethyst-50 p-2 text-amethyst-700 hover:bg-amethyst-100"
                @click="modalNuevoCliente = true"
              >
                <Icon name="plus" :size="16" />
              </button>
            </div>
          </div>

          <TicketVenta
            :venta="venta"
            :removible="venta.estado === 'en_curso'"
            @remover="remover"
            @descuento="aplicarDescuento"
            @incrementar="agregar({ productId: $event, cantidad: 1 })"
          />
        </div>

        <!-- Cobro -->
        <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
          <!-- Venta cobrada: comprobante + siguiente venta -->
          <template v-if="ventaCobrada">
            <div class="mb-3 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2.5">
              <Icon name="check" :size="18" class="shrink-0 text-emerald-600" />
              <div class="leading-tight">
                <p class="text-[13px] font-bold text-emerald-900">
                  Venta #{{ ventaCobrada.venta_id }} cobrada · {{ money(ventaCobrada.total) }}
                </p>
                <p class="text-[11px] text-emerald-700">
                  {{ ventaCobrada.tipo_comprobante === 'factura' ? 'Factura' : 'Nota de venta' }} emitida.
                </p>
              </div>
            </div>

            <div class="grid gap-2">
              <button
                type="button"
                class="flex items-center justify-center gap-1.5 rounded-xl border border-brand-300 bg-white px-4 py-2.5 text-[13px] font-bold text-brand-800 hover:bg-brand-50"
                @click="imprimirComprobante"
              >
                <Icon name="download" :size="15" /> Ver / imprimir comprobante
              </button>
              <button
                v-if="cliente"
                type="button"
                :disabled="emailEnviando"
                class="flex items-center justify-center gap-1.5 rounded-xl border border-amethyst-300 bg-amethyst-50 px-4 py-2.5 text-[13px] font-bold text-amethyst-800 hover:bg-amethyst-100 disabled:opacity-50"
                @click="enviarComprobantePorCorreo"
              >
                <Icon name="megaphone" :size="15" />
                {{ emailEnviando ? 'Enviando…' : 'Enviar comprobante por correo' }}
              </button>
              <button
                type="button"
                class="flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-brand-800 to-amethyst-700 px-4 py-3 text-sm font-bold text-white shadow-md hover:brightness-110"
                @click="nuevaVenta"
              >
                <Icon name="plus" :size="15" /> Nueva venta
                <span class="ml-1 font-mono text-white/70">F12</span>
              </button>
            </div>
            <p v-if="emailResultado" class="mt-2 text-center text-[12px] font-semibold text-brand-800">
              {{ emailResultado }}
            </p>
          </template>

          <!-- Venta en curso: cobro -->
          <template v-else>
            <div class="mb-2 flex items-baseline justify-between">
              <span class="text-[11px] font-bold uppercase tracking-wide text-slate-500">Total a pagar</span>
              <span class="font-display text-2xl font-extrabold tabular-nums text-brand-900">
                {{ money(venta.total) }}
              </span>
            </div>

            <div class="mb-3 grid grid-cols-3 gap-1.5">
              <button
                v-for="m in mediosPago"
                :key="m.medio_pago_id"
                type="button"
                :disabled="venta.estado !== 'en_curso'"
                class="flex flex-col items-center gap-1 rounded-lg border px-2 py-2 text-[11px] font-semibold transition disabled:opacity-40"
                :class="
                  medioPagoId === m.medio_pago_id
                    ? 'border-brand-600 bg-brand-50 text-brand-900'
                    : 'border-brand-200 bg-white text-slate-600 hover:border-brand-400'
                "
                @click="((medioPagoId = m.medio_pago_id), (pagoTarjetaAprobado = false))"
              >
                <Icon :name="ICONO_MEDIO(m.nombre)" :size="15" /> {{ m.nombre }}
              </button>
            </div>

            <p
              v-if="datafonoAviso"
              class="mb-3 flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-[11px] text-amber-800"
            >
              <Icon name="alert" :size="13" class="mt-px shrink-0" /> {{ datafonoAviso }}
            </p>

            <template v-if="esEfectivo">
              <input
                v-model="efectivoRecibido"
                type="number"
                min="0"
                placeholder="Efectivo recibido (opcional)"
                class="mb-1.5 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
                @keydown.enter.prevent="confirmar"
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

            <p v-if="esDigital" class="mb-3 rounded-lg bg-brand-50 px-3 py-2 text-[11px] text-brand-800">
              Muestra el QR al cliente y confirma cuando el pago aparezca aprobado.
            </p>

            <div class="mb-3 flex gap-1.5">
              <button
                v-for="t in [{ v: 'nota_venta', l: 'Nota de venta' }, { v: 'factura', l: 'Factura' }]"
                :key="t.v"
                type="button"
                class="flex-1 rounded-lg border px-2 py-1.5 text-[12px] font-semibold transition"
                :class="tipoComprobante === t.v ? 'border-brand-600 bg-brand-50 text-brand-900' : 'border-brand-200 bg-white text-slate-600 hover:border-brand-400'"
                @click="tipoComprobante = t.v"
              >
                {{ t.l }}
              </button>
            </div>

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
              class="w-full rounded-xl bg-gradient-to-r from-brand-800 to-amethyst-700 px-4 py-3 text-sm font-bold text-white shadow-md hover:brightness-110 disabled:opacity-40"
              @click="confirmar"
            >
              {{ cargando ? 'Procesando…' : `Cobrar ${money(venta.total)}` }}
              <span class="ml-1 font-mono text-white/70">F12</span>
            </button>
          </template>
        </div>

        <SimuladorDatafono
          v-if="requiereTarjeta && venta.estado === 'en_curso' && venta.lineas.length"
          :monto="money(venta.total)"
          :procesando="procesandoPago"
          @cobrar="cobrarTarjeta"
        />
      </aside>
    </div>

    <!-- Barra de atajos -->
    <div
      class="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-brand-200 bg-white px-4 py-2 font-mono text-[11px] font-semibold text-slate-500"
    >
      Teclas POS:
      <span><b class="text-brand-700">F2</b> Buscar</span>
      <span class="text-slate-300">·</span>
      <span><b class="text-brand-700">F4</b> Descuento</span>
      <span class="text-slate-300">·</span>
      <span><b class="text-brand-700">F6</b> Pausar</span>
      <span class="text-slate-300">·</span>
      <span><b class="text-brand-700">F12</b> Cobro</span>
    </div>

    <!-- Modal: alta rápida de cliente -->
    <Modal
      v-if="modalNuevoCliente"
      titulo="Registrar un cliente nuevo"
      @cerrar="modalNuevoCliente = false"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Queda vinculado a esta venta al guardarlo. Los datos completos se pueden editar luego en
        Clientes / CRM.
      </p>
      <form class="space-y-3" @submit.prevent="crearCliente">
        <label class="block text-[12px] font-semibold text-slate-600">
          Nombre
          <input
            v-model="formCliente.nombre"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Correo electrónico
          <input
            v-model="formCliente.email"
            type="email"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Identificación (opcional)
          <input
            v-model="formCliente.documento"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="flex items-start gap-2 text-[12px] text-slate-600">
          <input v-model="formCliente.consentimiento" type="checkbox" class="mt-0.5" />
          <span>El cliente autoriza el tratamiento de sus datos para el programa de fidelización.</span>
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <button
            type="button"
            class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
            @click="modalNuevoCliente = false"
          >
            Cancelar
          </button>
          <button
            type="submit"
            :disabled="guardandoCliente || !formCliente.consentimiento"
            class="rounded-xl bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {{ guardandoCliente ? 'Guardando…' : 'Guardar y vincular' }}
          </button>
        </div>
      </form>
    </Modal>

    <!-- Modal: abrir / cerrar caja -->
    <Modal
      v-if="modalCaja === 'abrir'"
      titulo="Abrir caja"
      @cerrar="modalCaja = null"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Declara el efectivo con el que inicia el turno. La caja es el manejo de efectivo de tu turno.
      </p>
      <form class="space-y-4" @submit.prevent="abrirCaja">
        <label class="block text-[12px] font-semibold text-slate-600">
          Caja
          <select
            v-model.number="formCaja.cajaId"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option v-for="c in cajas" :key="c.caja_id" :value="c.caja_id">{{ c.nombre }}</option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Fondo inicial (USD)
          <input
            v-model="formCaja.fondoInicial"
            type="number"
            min="0"
            step="0.01"
            required
            placeholder="150.00"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div class="flex justify-end gap-2.5">
          <button
            type="button"
            class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
            @click="modalCaja = null"
          >
            Cancelar
          </button>
          <button
            type="submit"
            :disabled="guardandoCaja || !formCaja.cajaId"
            class="rounded-xl bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {{ guardandoCaja ? 'Abriendo…' : 'Abrir caja' }}
          </button>
        </div>
      </form>
    </Modal>

    <Modal
      v-if="modalCaja === 'cerrar'"
      titulo="Cerrar caja — cuadre"
      @cerrar="modalCaja = null"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Cuenta el efectivo en la gaveta y regístralo. El sistema calcula la diferencia contra lo
        esperado.
      </p>
      <dl class="mb-4 grid grid-cols-2 gap-y-1 rounded-xl border border-brand-100 bg-brand-50/40 p-3 text-[13px]">
        <dt class="text-slate-500">Fondo inicial</dt>
        <dd class="text-right font-semibold text-slate-800">{{ money(turno?.fondo_inicial) }}</dd>
        <dt class="text-slate-500">Total esperado ahora</dt>
        <dd class="text-right font-semibold text-brand-900">{{ money(turno?.total_esperado_actual) }}</dd>
      </dl>
      <form class="space-y-4" @submit.prevent="cerrarCaja">
        <label class="block text-[12px] font-semibold text-slate-600">
          Total contado (USD)
          <input
            v-model="formCaja.totalContado"
            type="number"
            min="0"
            step="0.01"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <p
          v-if="formCaja.totalContado !== '' && turno"
          class="text-right text-[13px] font-bold"
          :class="
            Number(formCaja.totalContado) - Number(turno.total_esperado_actual || 0) === 0
              ? 'text-emerald-700'
              : 'text-crimson-ruby'
          "
        >
          Diferencia:
          {{ money(Number(formCaja.totalContado) - Number(turno.total_esperado_actual || 0)) }}
        </p>
        <div class="flex justify-end gap-2.5">
          <button
            type="button"
            class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
            @click="modalCaja = null"
          >
            Cancelar
          </button>
          <button
            type="submit"
            :disabled="guardandoCaja"
            class="rounded-xl bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {{ guardandoCaja ? 'Registrando…' : 'Registrar cuadre' }}
          </button>
        </div>
      </form>
    </Modal>
  </div>
</template>
