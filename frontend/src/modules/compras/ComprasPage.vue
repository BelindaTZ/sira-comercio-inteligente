<script setup>
/**
 * Abastecimiento & Órdenes de Compra — feature 001 US3 (+ extensión 018:
 * confirmación de la respuesta del proveedor). Arquetipo "Gestión" del kit ya
 * implementado (mismo lenguaje que Datáfonos / Traslados / Inventario).
 *
 * Ciclo: crear solicitud (automática o especial) → aprobar internamente →
 * registrar la respuesta del proveedor (un actor humano, con motivo obligatorio)
 * → recibir mercadería (en Inventario) → factura y pago (Finanzas).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { comprasApi } from '@/services/comprasApi'
import { inventarioApi } from '@/services/inventarioApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import FormularioOrdenCompra from './components/FormularioOrdenCompra.vue'
import ResumenCuentasPorPagar from './components/ResumenCuentasPorPagar.vue'
import ReporteComprasAutomaticoManual from './components/ReporteComprasAutomaticoManual.vue'
import HistorialProveedorProducto from './components/HistorialProveedorProducto.vue'
import FormularioFacturaProveedor from './components/FormularioFacturaProveedor.vue'
import FormularioPagoProveedor from './components/FormularioPagoProveedor.vue'

const sesion = useSesion()
const route = useRoute()
const router = useRouter()
const tiendaId = computed(() => sesion.tiendaId ?? 1)
const empleadoId = computed(() => sesion.empleadoId ?? 1)
const puedeOperar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Operaciones', 'ordenes_compra'),
)
const puedeFinanzas = computed(() => sesion.puedeLeerTabla('Finanzas', 'facturas_proveedor'))

const ESTADO = {
  pendiente: { tipo: 'fifo', txt: 'Pendiente de aprobación' },
  aprobada: { tipo: 'neutral', txt: 'Enviada al proveedor' },
  confirmada: { tipo: 'ia', txt: 'Confirmada por proveedor' },
  recibida: { tipo: 'ok', txt: 'Recibida' },
  rechazada: { tipo: 'quiebre', txt: 'Rechazada por proveedor' },
  cancelada: { tipo: 'neutral', txt: 'Cancelada' },
}
const CANALES = [
  { v: 'correo', t: 'Correo electrónico' },
  { v: 'whatsapp', t: 'WhatsApp' },
  { v: 'telefono', t: 'Teléfono' },
  { v: 'presencial', t: 'Presencial' },
  { v: 'otro', t: 'Otro' },
]

const ordenes = ref([])
const sugerencias = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const busqueda = ref('')
const pill = ref('')
const page = ref(1)
const size = ref(15)

const modalCrear = ref(false)
const prefillOrden = ref(null)
const ordenDetalle = ref(null)
const modalRespuesta = ref(null) // orden
const modalRecibir = ref(null) // orden
const lineasRecibir = ref([])
const recibiendo = ref(false)
const mostrarFinanzas = ref(false)
const mostrarAnalisis = ref(false)

const formResp = reactive({ decision: 'aceptar', canal: 'correo', motivo: '' })
const enviandoResp = ref(false)

const money = (v) =>
  v == null
    ? '—'
    : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo completar la operación.'
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const [lo, ls] = await Promise.all([
      comprasApi.ordenes({ tiendaId: tiendaId.value }),
      comprasApi.sugerencias(tiendaId.value).catch(() => []),
    ])
    ordenes.value = lo || []
    sugerencias.value = ls || []
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

const kpi = computed(() => {
  const d = ordenes.value
  const por = (e) => d.filter((o) => o.estado === e).length
  const mes = new Date().toISOString().slice(0, 7)
  const gastoMes = d
    .filter((o) => (o.fecha || '').startsWith(mes) && !['cancelada', 'rechazada'].includes(o.estado))
    .reduce((s, o) => s + Number(o.total_neto || 0), 0)
  return {
    total: d.length,
    pendientes: por('pendiente'),
    enviadas: por('aprobada'),
    confirmadas: por('confirmada'),
    recibidas: por('recibida'),
    rechazadas: por('rechazada') + por('cancelada'),
    gastoMes,
  }
})

const pills = computed(() => [
  { value: '', label: 'Todas', count: kpi.value.total },
  { value: 'pendiente', label: 'Pendientes', count: kpi.value.pendientes },
  { value: 'aprobada', label: 'Enviadas al proveedor', count: kpi.value.enviadas },
  { value: 'confirmada', label: 'Confirmadas', count: kpi.value.confirmadas },
  { value: 'recibida', label: 'Recibidas', count: kpi.value.recibidas },
  { value: 'cerradas', label: 'Rechazadas / canceladas', count: kpi.value.rechazadas },
])

const columnas = [
  { key: 'ref', label: 'Orden', width: '110px' },
  { key: 'proveedor', label: 'Tipo / Proveedor' },
  { key: 'carga', label: 'Carga', width: '110px' },
  { key: 'monto', label: 'Monto neto', align: 'right', width: '120px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '170px' },
  { key: 'acciones', label: '', align: 'right', width: '220px' },
]

const filtradas = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return ordenes.value.filter((o) => {
    if (pill.value === 'cerradas') {
      if (!['rechazada', 'cancelada'].includes(o.estado)) return false
    } else if (pill.value && o.estado !== pill.value) return false
    if (!q) return true
    return (
      String(o.orden_id).includes(q) ||
      (o.proveedor_nombre || '').toLowerCase().includes(q) ||
      (o.tipo || '').toLowerCase().includes(q)
    )
  })
})
const filas = computed(() =>
  filtradas.value.slice((page.value - 1) * size.value, page.value * size.value),
)

async function aprobar(orden) {
  error.value = ''
  aviso.value = ''
  try {
    await comprasApi.aprobarOrden(orden.orden_id)
    aviso.value = `Orden #${orden.orden_id} aprobada internamente. Envíala al proveedor y registra su respuesta.`
    if (ordenDetalle.value?.orden_id === orden.orden_id) ordenDetalle.value = null
    await cargar()
  } catch (e) {
    error.value = msg(e)
  }
}

function abrirRespuesta(orden) {
  Object.assign(formResp, { decision: 'aceptar', canal: 'correo', motivo: '' })
  modalRespuesta.value = orden
  ordenDetalle.value = null
}

async function enviarRespuesta() {
  if (!formResp.motivo.trim()) return
  enviandoResp.value = true
  error.value = ''
  try {
    const r = await comprasApi.respuestaProveedor(modalRespuesta.value.orden_id, {
      decision: formResp.decision,
      canal: formResp.canal,
      motivo: formResp.motivo.trim(),
    })
    modalRespuesta.value = null
    aviso.value =
      r.estado === 'confirmada'
        ? `El proveedor confirmó la orden #${r.orden_id}. Lista para recepción en Inventario.`
        : `Orden #${r.orden_id} marcada como rechazada por el proveedor.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    enviandoResp.value = false
  }
}

function abrirRecibir(orden) {
  lineasRecibir.value = (orden.lineas || []).map((l) => ({
    product_id: l.product_id,
    nombre: l.product_nombre || `Producto ${l.product_id}`,
    cantidad: l.cantidad,
    fecha_vencimiento: '',
    codigo_lote: '',
  }))
  modalRecibir.value = orden
  ordenDetalle.value = null
}

async function registrarRecepcion() {
  recibiendo.value = true
  error.value = ''
  try {
    for (const l of lineasRecibir.value) {
      if (Number(l.cantidad) <= 0) continue
      await inventarioApi.recepcion({
        ordenId: modalRecibir.value.orden_id,
        productId: l.product_id,
        tiendaId: tiendaId.value,
        cantidad: Number(l.cantidad),
        fechaVencimiento: l.fecha_vencimiento || null,
        codigoLoteProveedor: l.codigo_lote || null,
      })
    }
    modalRecibir.value = null
    aviso.value = 'Recepción registrada. El stock de la tienda se actualizó por FIFO.'
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    recibiendo.value = false
  }
}

function ordenCreada(orden) {
  modalCrear.value = false
  prefillOrden.value = null
  aviso.value = `Solicitud de pedido #${orden.orden_id} creada (${orden.tipo === 'especial' ? 'especial' : 'automática'}).`
  cargar()
}

function pedirDeSugerencia() {
  prefillOrden.value = null
  modalCrear.value = true
}

function pedirProducto(s) {
  prefillOrden.value = {
    product_id: s.product_id,
    nombre: s.nombre || `Producto ${s.product_id}`,
    cantidad: s.cantidad_sugerida,
  }
  modalCrear.value = true
}

async function correrJobs() {
  aviso.value = ''
  error.value = ''
  try {
    const r = await inventarioApi.jobReposicion(tiendaId.value)
    aviso.value = `Job de reposición ejecutado: ${r.alertas_generadas.length} alerta(s).`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  }
}

onMounted(async () => {
  await cargar()
  // "Solicitar reposición" desde Inventario abre esta pantalla con el pedido casi listo
  const pid = Number(route.query.nuevaOrden)
  if (pid) {
    const s = sugerencias.value.find((x) => x.product_id === pid)
    prefillOrden.value = {
      product_id: pid,
      nombre: s?.nombre || `Producto ${pid}`,
      cantidad: s?.cantidad_sugerida || 1,
    }
    modalCrear.value = true
    router.replace({ query: {} })
  }
})
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Abastecimiento & órdenes de compra"
      subtitulo="Solicitudes de pedido automáticas y especiales, confirmación de la respuesta del proveedor y seguimiento hasta la recepción en tienda."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.pendientes > 0 ? 'fifo' : 'ok'">
          {{ kpi.pendientes > 0 ? `${kpi.pendientes} por aprobar` : 'Sin pendientes' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeOperar" variant="ghost" @click="correrJobs">
          <Icon name="cog" :size="16" /> Recalcular sugerencia
        </Btn>
        <Btn v-if="puedeOperar" variant="ghost" @click="mostrarAnalisis = !mostrarAnalisis">
          <Icon name="chart" :size="16" />
          {{ mostrarAnalisis ? 'Ocultar análisis' : 'Análisis de compras' }}
        </Btn>
        <Btn
          v-if="puedeFinanzas"
          variant="ghost"
          @click="mostrarFinanzas = !mostrarFinanzas"
        >
          <Icon name="bank" :size="16" />
          {{ mostrarFinanzas ? 'Ocultar cuentas por pagar' : 'Cuentas por pagar' }}
        </Btn>
        <Btn v-if="puedeOperar" variant="primary" @click="pedirDeSugerencia">
          <Icon name="plus" :size="17" /> Crear solicitud de pedido
        </Btn>
        <span
          v-if="!puedeOperar"
          class="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600"
        >
          <Icon name="shield" :size="14" /> Solo lectura
        </span>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-4 flex items-center justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      <span>{{ aviso }}</span>
      <button class="text-brand-600 hover:text-brand-900" @click="aviso = ''">
        <Icon name="x" :size="14" />
      </button>
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Pendientes de aprobación"
        :valor="kpi.pendientes.toLocaleString('es-EC')"
        variant="emerald"
        microcopy="Solicitudes creadas que aún no se aprueban internamente"
        pie-label="Órdenes registradas"
        :pie-valor="`${kpi.total} en total`"
      />
      <KpiTile
        label="Esperando al proveedor"
        :valor="kpi.enviadas.toLocaleString('es-EC')"
        :estado-tipo="kpi.enviadas > 0 ? 'fifo' : 'ok'"
        microcopy="Aprobadas — falta registrar la respuesta del proveedor"
      >
        <template #icono><Icon name="megaphone" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Confirmadas por proveedor"
        :valor="kpi.confirmadas.toLocaleString('es-EC')"
        estado-tipo="ia"
        microcopy="El proveedor aceptó el pedido; listas para recepción"
      >
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Gasto de compra del mes"
        :valor="money(kpi.gastoMes)"
        estado-tipo="neutral"
        :microcopy="`${kpi.recibidas} orden(es) recibida(s) este período`"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
    </section>

    <!-- Sugerencias del sistema -->
    <section v-if="sugerencias.length" class="satin-card mb-6 rounded-2xl p-5 shadow-card-subtle">
      <div class="mb-3 flex items-center gap-2">
        <Icon name="chart" :size="16" class="text-brand-700" />
        <h2 class="font-display text-base font-bold text-brand-950">
          Sugerencia semanal del sistema
        </h2>
        <SemanticChip tipo="neutral">{{ sugerencias.length }} productos bajo su punto</SemanticChip>
      </div>
      <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <div
          v-for="s in sugerencias.slice(0, 6)"
          :key="s.product_id"
          class="flex items-center justify-between rounded-xl border border-brand-200 bg-white px-3 py-2"
        >
          <div class="min-w-0">
            <div class="truncate text-[12px] font-semibold text-slate-800">
              {{ s.nombre || `Producto ${s.product_id}` }}
            </div>
            <div class="text-[11px] text-slate-500">
              stock {{ s.cantidad_disponible }} · punto {{ s.punto_reposicion }} ·
              <span class="font-semibold text-brand-800">sugerido +{{ s.cantidad_sugerida }}</span>
            </div>
          </div>
          <Btn
            v-if="puedeOperar"
            variant="ghost"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="pedirProducto(s)"
          >
            Pedir
          </Btn>
        </div>
      </div>
    </section>

    <DataTable
      titulo="Órdenes de compra"
      subtitulo="Ciclo completo: solicitud → aprobación → respuesta del proveedor → recepción."
      :columns="columnas"
      :rows="filas"
      row-key="orden_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtradas.length"
      :search="busqueda"
      search-placeholder="Orden, proveedor o tipo…"
      :pills="pills"
      :pill-activa="pill"
      empty-text="No hay órdenes de compra"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
      @pill="((pill = $event), (page = 1))"
    >
      <template #cell:ref="{ row }">
        <div class="leading-tight">
          <div class="font-mono text-[12px] font-semibold text-slate-800">
            OC-{{ String(row.orden_id).padStart(4, '0') }}
          </div>
          <div class="text-[10px] text-slate-400">{{ row.fecha }}</div>
        </div>
      </template>

      <template #cell:proveedor="{ row }">
        <div class="leading-tight">
          <div class="flex items-center gap-1.5">
            <span
              class="rounded px-1.5 py-0.5 text-[9px] font-bold uppercase"
              :class="row.tipo === 'especial' ? 'bg-amethyst-100 text-amethyst-800' : 'bg-brand-100 text-brand-800'"
            >
              {{ row.tipo === 'especial' ? 'Especial' : 'Automática' }}
            </span>
            <span class="text-[12px] font-semibold text-slate-800">
              {{ row.proveedor_nombre || `Proveedor ${row.proveedor_id}` }}
            </span>
          </div>
          <div v-if="row.motivo_desviacion" class="mt-0.5 text-[10px] italic text-amber-700">
            {{ row.motivo_desviacion }}
          </div>
        </div>
      </template>

      <template #cell:carga="{ row }">
        <div class="text-[12px] text-slate-700">{{ row.cantidad_skus ?? row.lineas?.length ?? '—' }} SKUs</div>
        <div class="text-[10px] text-slate-400">{{ row.total_unidades ?? '—' }} u</div>
      </template>

      <template #cell:monto="{ row }">
        <span class="tabular-nums text-[13px] font-bold text-slate-900">{{ money(row.total_neto) }}</span>
      </template>

      <template #cell:estado="{ row }">
        <SemanticChip :tipo="ESTADO[row.estado]?.tipo || 'neutral'">
          {{ ESTADO[row.estado]?.txt || row.estado }}
        </SemanticChip>
        <div
          v-if="row.respuesta_proveedor"
          class="mt-1 text-[10px] leading-tight text-slate-500"
          :title="row.respuesta_proveedor"
        >
          {{ row.canal_respuesta }}: {{ row.respuesta_proveedor }}
        </div>
      </template>

      <template #cell:acciones="{ row }">
        <div class="flex items-center justify-end gap-1 whitespace-nowrap">
          <Btn
            v-if="row.estado === 'pendiente' && puedeOperar"
            variant="primary"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="aprobar(row)"
          >
            <Icon name="check" :size="13" /> Aprobar
          </Btn>
          <Btn
            v-if="row.estado === 'aprobada' && puedeOperar"
            variant="primary"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="abrirRespuesta(row)"
          >
            <Icon name="megaphone" :size="13" /> Respuesta del proveedor
          </Btn>
          <Btn
            v-if="row.estado === 'confirmada' && puedeOperar"
            variant="ghost"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="abrirRecibir(row)"
          >
            <Icon name="truck" :size="13" /> Recibir
          </Btn>
          <button
            type="button"
            class="rounded-md p-1.5 text-slate-400 hover:bg-brand-50 hover:text-brand-800"
            title="Ver detalle"
            @click="ordenDetalle = row"
          >
            <Icon name="chevron" :size="15" class="-rotate-90" />
          </button>
        </div>
      </template>
    </DataTable>

    <!-- Análisis de compras (Operaciones) -->
    <section
      v-if="mostrarAnalisis && puedeOperar"
      class="satin-card mt-6 rounded-2xl p-5 shadow-card-subtle"
    >
      <h2 class="mb-4 font-display text-base font-bold text-brand-950">Análisis de compras</h2>
      <div class="grid gap-4 lg:grid-cols-2">
        <ReporteComprasAutomaticoManual />
        <HistorialProveedorProducto />
      </div>
    </section>

    <!-- Cuentas por pagar (Finanzas) -->
    <section
      v-if="mostrarFinanzas && puedeFinanzas"
      class="satin-card mt-6 rounded-2xl p-5 shadow-card-subtle"
    >
      <h2 class="mb-4 font-display text-base font-bold text-brand-950">
        Cuentas por pagar a proveedores
      </h2>
      <ResumenCuentasPorPagar class="max-w-sm" />
      <div class="mt-4 grid gap-6 border-t border-brand-100 pt-4 lg:grid-cols-2">
        <FormularioFacturaProveedor :empleado-id="empleadoId" />
        <FormularioPagoProveedor :empleado-autoriza-id="empleadoId" />
      </div>
    </section>

    <!-- Modal: crear solicitud -->
    <Modal
      v-if="modalCrear"
      titulo="Crear solicitud de pedido"
      size="lg"
      @cerrar="((modalCrear = false), (prefillOrden = null))"
    >
      <FormularioOrdenCompra
        :tienda-id="tiendaId"
        :empleado-id="empleadoId"
        :prefill="prefillOrden"
        @creada="ordenCreada"
        @cerrar="((modalCrear = false), (prefillOrden = null))"
      />
    </Modal>

    <!-- Modal: respuesta del proveedor -->
    <Modal
      v-if="modalRespuesta"
      :titulo="`Respuesta del proveedor — OC-${String(modalRespuesta.orden_id).padStart(4, '0')}`"
      @cerrar="modalRespuesta = null"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Registra lo que respondió <strong>{{ modalRespuesta.proveedor_nombre }}</strong> a este pedido,
        por el medio en que lo hizo. El motivo es obligatorio y queda como constancia.
      </p>
      <form class="space-y-4" @submit.prevent="enviarRespuesta">
        <div class="grid grid-cols-2 gap-2">
          <button
            type="button"
            class="rounded-xl border p-3 text-center text-[13px] font-bold transition"
            :class="formResp.decision === 'aceptar' ? 'border-brand-600 bg-brand-50/60 text-brand-900 ring-1 ring-brand-500/20' : 'border-brand-200 bg-white text-slate-700 hover:border-brand-400'"
            @click="formResp.decision = 'aceptar'"
          >
            <Icon name="check" :size="15" /> El proveedor acepta
          </button>
          <button
            type="button"
            class="rounded-xl border p-3 text-center text-[13px] font-bold transition"
            :class="formResp.decision === 'rechazar' ? 'border-rose-400 bg-rose-50 text-crimson-ruby ring-1 ring-rose-300/40' : 'border-brand-200 bg-white text-slate-700 hover:border-brand-400'"
            @click="formResp.decision = 'rechazar'"
          >
            <Icon name="x" :size="15" /> El proveedor rechaza
          </button>
        </div>

        <label class="block text-[12px] font-semibold text-slate-600">
          Canal de la respuesta <span class="text-crimson-ruby">*</span>
          <select
            v-model="formResp.canal"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option v-for="c in CANALES" :key="c.v" :value="c.v">{{ c.t }}</option>
          </select>
        </label>

        <label class="block text-[12px] font-semibold text-slate-600">
          Motivo / detalle de la respuesta <span class="text-crimson-ruby">*</span>
          <textarea
            v-model="formResp.motivo"
            rows="3"
            required
            maxlength="500"
            :placeholder="
              formResp.decision === 'aceptar'
                ? 'Ej.: confirma despacho completo el jueves, factura a 30 días.'
                : 'Ej.: sin stock hasta marzo; sugiere traslado desde otra tienda.'
            "
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>

        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" @click="modalRespuesta = null">Cancelar</Btn>
          <Btn
            :variant="formResp.decision === 'rechazar' ? 'danger' : 'primary'"
            type="submit"
            :disabled="enviandoResp || !formResp.motivo.trim()"
          >
            {{ enviandoResp ? 'Guardando…' : 'Registrar respuesta' }}
          </Btn>
        </div>
      </form>
    </Modal>

    <!-- Modal: recibir mercadería -->
    <Modal
      v-if="modalRecibir"
      :titulo="`Recibir mercadería — OC-${String(modalRecibir.orden_id).padStart(4, '0')}`"
      size="lg"
      @cerrar="modalRecibir = null"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Registra lo que llegó de <strong>{{ modalRecibir.proveedor_nombre }}</strong>. Cada línea
        crea un lote y suma el stock a la tienda; la orden se cierra cuando todas las líneas se
        reciben.
      </p>
      <form class="space-y-3" @submit.prevent="registrarRecepcion">
        <div
          v-for="l in lineasRecibir"
          :key="l.product_id"
          class="rounded-xl border border-brand-200 p-3"
        >
          <div class="mb-2 text-[13px] font-semibold text-slate-800">{{ l.nombre }}</div>
          <div class="grid gap-2 sm:grid-cols-3">
            <label class="block text-[11px] font-semibold text-slate-600">
              Cantidad recibida
              <input
                v-model.number="l.cantidad"
                type="number"
                min="0"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-2.5 py-1.5 text-sm text-slate-800"
              />
            </label>
            <label class="block text-[11px] font-semibold text-slate-600">
              Vence (si aplica)
              <input
                v-model="l.fecha_vencimiento"
                type="date"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-2.5 py-1.5 text-sm text-slate-800"
              />
            </label>
            <label class="block text-[11px] font-semibold text-slate-600">
              Lote del proveedor
              <input
                v-model="l.codigo_lote"
                type="text"
                maxlength="40"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-2.5 py-1.5 text-sm text-slate-800"
              />
            </label>
          </div>
        </div>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" @click="modalRecibir = null">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="recibiendo || !lineasRecibir.length">
            {{ recibiendo ? 'Registrando…' : 'Registrar recepción' }}
          </Btn>
        </div>
      </form>
    </Modal>

    <!-- Modal: detalle -->
    <Modal
      v-if="ordenDetalle"
      :titulo="`Detalle OC-${String(ordenDetalle.orden_id).padStart(4, '0')}`"
      size="lg"
      @cerrar="ordenDetalle = null"
    >
      <div class="space-y-4 text-[13px]">
        <div class="grid grid-cols-2 gap-3 rounded-xl border border-brand-100 bg-white p-3">
          <div>
            <span class="text-[11px] font-semibold text-slate-600">Proveedor</span>
            <div class="font-semibold text-slate-800">
              {{ ordenDetalle.proveedor_nombre || `Proveedor ${ordenDetalle.proveedor_id}` }}
            </div>
          </div>
          <div>
            <span class="text-[11px] font-semibold text-slate-600">Estado</span>
            <div><SemanticChip :tipo="ESTADO[ordenDetalle.estado]?.tipo || 'neutral'">{{ ESTADO[ordenDetalle.estado]?.txt || ordenDetalle.estado }}</SemanticChip></div>
          </div>
          <div>
            <span class="text-[11px] font-semibold text-slate-600">Tipo</span>
            <div class="font-semibold text-slate-800">{{ ordenDetalle.tipo === 'especial' ? 'Especial' : 'Automática' }}</div>
          </div>
          <div>
            <span class="text-[11px] font-semibold text-slate-600">Total neto</span>
            <div class="font-bold tabular-nums text-brand-900">{{ money(ordenDetalle.total_neto) }}</div>
          </div>
        </div>

        <div v-if="ordenDetalle.respuesta_proveedor" class="rounded-lg border border-brand-200 bg-white p-3">
          <span class="text-[11px] font-bold uppercase text-slate-600">
            Respuesta del proveedor · {{ ordenDetalle.canal_respuesta }}
          </span>
          <p class="mt-1 text-slate-700">{{ ordenDetalle.respuesta_proveedor }}</p>
        </div>
        <div v-if="ordenDetalle.motivo_desviacion" class="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-amber-900">
          <strong>Motivo de desviación:</strong> {{ ordenDetalle.motivo_desviacion }}
        </div>

        <div>
          <h4 class="mb-2 font-bold text-slate-800">Líneas</h4>
          <table class="w-full text-left">
            <thead>
              <tr class="border-b border-brand-100 text-[11px] uppercase text-slate-400">
                <th class="py-1">Producto</th>
                <th class="py-1 text-right">Cantidad</th>
                <th class="py-1 text-right">Costo unit.</th>
                <th class="py-1 text-right">Subtotal</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-brand-100">
              <tr v-for="l in ordenDetalle.lineas" :key="l.product_id">
                <td class="py-1.5 font-medium text-slate-700">{{ l.product_nombre || `Producto ${l.product_id}` }}</td>
                <td class="py-1.5 text-right tabular-nums">{{ l.cantidad }}</td>
                <td class="py-1.5 text-right tabular-nums">{{ money(l.costo_unitario) }}</td>
                <td class="py-1.5 text-right font-semibold tabular-nums">
                  {{ money(Number(l.cantidad) * Number(l.costo_unitario)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex justify-end gap-2 border-t border-brand-100 pt-3">
          <Btn
            v-if="ordenDetalle.estado === 'pendiente' && puedeOperar"
            variant="primary"
            @click="aprobar(ordenDetalle)"
          >
            Aprobar orden
          </Btn>
          <Btn
            v-if="ordenDetalle.estado === 'aprobada' && puedeOperar"
            variant="primary"
            @click="abrirRespuesta(ordenDetalle)"
          >
            Registrar respuesta del proveedor
          </Btn>
          <Btn
            v-if="ordenDetalle.estado === 'confirmada' && puedeOperar"
            variant="primary"
            @click="abrirRecibir(ordenDetalle)"
          >
            Recibir mercadería
          </Btn>
          <Btn variant="ghost" @click="ordenDetalle = null">Cerrar</Btn>
        </div>
      </div>
    </Modal>
  </div>
</template>
