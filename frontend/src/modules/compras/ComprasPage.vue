<script setup>
/**
 * Abastecimiento Local & Órdenes de Compra (US3 / Feature 014).
 * Rediseño basado en `docs/diseno-ui/.../sira_rdenes_de_compra_abastecimiento_local/`:
 *  - Header ejecutivo con identidad de sucursal y acciones primarias.
 *  - 4 KpiTiles: Órdenes en Tránsito, Fill Rate, Gasto Compra Mes, Recepciones en Muelle.
 *  - Matriz de Órdenes de Compra con tabs de estado operativo, búsqueda y acciones.
 *  - Panel dual inferior: Sugerencias automáticas por algoritmo Min/Max (AI SIRA) + Bitácora y Cuentas por Pagar.
 *  - Modales in-app para creación de OC y visualización de líneas de detalle.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useSesion } from '@/stores/sesion'
import { comprasApi } from '@/services/comprasApi'
import { inventarioApi } from '@/services/inventarioApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import FormularioOrdenCompra from './components/FormularioOrdenCompra.vue'
import ResumenCuentasPorPagar from './components/ResumenCuentasPorPagar.vue'
import ReporteComprasAutomaticoManual from './components/ReporteComprasAutomaticoManual.vue'
import HistorialProveedorProducto from './components/HistorialProveedorProducto.vue'
import FormularioFacturaProveedor from './components/FormularioFacturaProveedor.vue'
import FormularioPagoProveedor from './components/FormularioPagoProveedor.vue'

const sesion = useSesion()
const tiendaId = computed(() => sesion.tiendaId ?? 1)
const empleadoId = computed(() => sesion.empleadoId ?? 1)

const ordenes = ref([])
const sugerencias = ref([])
const alertas = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const tabEstado = ref('todas') // 'todas' | 'transito' | 'pendiente' | 'recibida'
const filtroOrigen = ref('todos') // 'todos' | 'cd' | 'dsd'
const busqueda = ref('')

// Modales
const modalCrear = ref(false)
const ordenSeleccionada = ref(null)
const mostrarFinanzas = ref(false)

const money = (v) =>
  v == null
    ? '—'
    : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`

async function cargarDatos() {
  cargando.value = true
  error.value = ''
  try {
    const [listaOrdenes, listaSugerencias, listaAlertas] = await Promise.all([
      comprasApi.ordenes({ tiendaId: tiendaId.value }).catch(() => []),
      comprasApi.sugerencias(tiendaId.value).catch(() => []),
      inventarioApi.alertas({ tiendaId: tiendaId.value }).catch(() => ({ items: [] })),
    ])
    ordenes.value = listaOrdenes || []
    sugerencias.value = listaSugerencias || []
    alertas.value = listaAlertas?.items || []
  } catch (e) {
    error.value = e.message || 'Error al sincronizar con abastecimiento'
  } finally {
    cargando.value = false
  }
}

// Métricas de KPIs
const kpiTransito = computed(() => ordenes.value.filter((o) => o.estado === 'aprobada').length)
const kpiPendientes = computed(() => ordenes.value.filter((o) => o.estado === 'pendiente').length)
const kpiGastoMes = computed(() => {
  const ahora = new Date()
  const mesActual = ahora.toISOString().slice(0, 7)
  return ordenes.value
    .filter((o) => (o.fecha || '').startsWith(mesActual) && o.estado !== 'cancelada')
    .reduce((sum, o) => sum + Number(o.total_neto || 0), 0)
})

// Filtrado de la matriz
const ordenesFiltradas = computed(() => {
  return ordenes.value.filter((o) => {
    // Filtro por tab de estado
    if (tabEstado.value === 'transito' && o.estado !== 'aprobada') return false
    if (tabEstado.value === 'pendiente' && o.estado !== 'pendiente') return false
    if (tabEstado.value === 'recibida' && o.estado !== 'recibida') return false

    // Filtro por origen (CD vs DSD)
    const prov = (o.proveedor_nombre || '').toLowerCase()
    if (filtroOrigen.value === 'cd' && !prov.includes('cd ') && !prov.includes('central') && !prov.includes('boza')) {
      return false
    }
    if (filtroOrigen.value === 'dsd' && (prov.includes('cd ') || prov.includes('central') || prov.includes('boza'))) {
      return false
    }

    // Búsqueda
    if (busqueda.value.trim()) {
      const q = busqueda.value.toLowerCase()
      const matchId = String(o.orden_id).includes(q)
      const matchProv = (o.proveedor_nombre || '').toLowerCase().includes(q)
      const matchTipo = (o.tipo || '').toLowerCase().includes(q)
      if (!matchId && !matchProv && !matchTipo) return false
    }
    return true
  })
})

async function aprobar(ordenId) {
  try {
    await comprasApi.aprobarOrden(ordenId)
    aviso.value = `Orden #${ordenId} aprobada con éxito.`
    await cargarDatos()
  } catch (e) {
    error.value = e.message
  }
}

async function correrJobs() {
  aviso.value = ''
  try {
    const r = await inventarioApi.jobReposicion(tiendaId.value)
    const v = await inventarioApi.jobVencimiento(tiendaId.value)
    aviso.value = `Jobs ejecutados: reposición (${r.alertas_generadas.length}) · vencimiento (${v.alertas_generadas.length})`
    await cargarDatos()
  } catch (e) {
    error.value = e.message
  }
}

function verDetalle(orden) {
  ordenSeleccionada.value = orden
}

function ordenCreada() {
  modalCrear.value = false
  aviso.value = 'Orden de compra creada exitosamente.'
  cargarDatos()
}

onMounted(cargarDatos)
</script>

<template>
  <main class="mx-auto w-full max-w-[1720px] px-4 py-6 sm:px-6 lg:px-8 space-y-6">
    <!-- 1. ENCABEZADO Y ACCIONES PRINCIPALES -->
    <PageHeader
      titulo="Abastecimiento Local &amp; Órdenes de Compra"
      subtitulo="Coordinación logística de entradas en muelle, pedidos sugeridos por modelo Min/Max y seguimiento directo a CD y proveedores DSD."
    >
      <template #badge>
        <span
          class="inline-flex items-center gap-1.5 rounded-full border border-emerald-200/80 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800"
        >
          <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          Sucursal #{{ tiendaId }} • Providencia
        </span>
      </template>

      <template #acciones>
        <Btn variant="outline" @click="correrJobs">
          <Icon name="refresh" :size="16" /> Ejecutar jobs Min/Max
        </Btn>
        <Btn variant="outline" @click="mostrarFinanzas = !mostrarFinanzas">
          <Icon name="card" :size="16" />
          {{ mostrarFinanzas ? 'Ocultar Cuentas por Pagar' : 'Cuentas por Pagar' }}
        </Btn>
        <Btn variant="primary" @click="modalCrear = true">
          <Icon name="plus" :size="16" /> + Crear Solicitud de Pedido
        </Btn>
      </template>
    </PageHeader>

    <!-- ALERTAS O AVISOS -->
    <div
      v-if="aviso"
      class="flex items-center justify-between rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 shadow-xs"
    >
      <div class="flex items-center gap-2">
        <Icon name="check" :size="18" class="text-emerald-600" />
        <span>{{ aviso }}</span>
      </div>
      <button class="text-emerald-700 hover:text-emerald-950 font-bold" @click="aviso = ''">✕</button>
    </div>

    <div
      v-if="error"
      class="flex items-center justify-between rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900 shadow-xs"
    >
      <div class="flex items-center gap-2">
        <Icon name="alert" :size="18" class="text-rose-600" />
        <span>{{ error }}</span>
      </div>
      <button class="text-rose-700 hover:text-rose-950 font-bold" @click="error = ''">✕</button>
    </div>

    <!-- 2. TARJETAS DE KPIS PRINCIPALES -->
    <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiTile
        label="Órdenes en Tránsito"
        :valor="`${kpiTransito} OC`"
        microcopy="Aprobadas con despacho en ruta"
        estado="En ruta a sucursal"
        estado-tipo="ia"
        pie-label="CD Central / DSD"
        :pie-valor="`${ordenes.length} registradas`"
      >
        <template #icono><Icon name="truck" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Fill Rate Proveedores"
        valor="96.4%"
        microcopy="Cumplimiento de entrega en muelle"
        estado="+1.8%"
        estado-tipo="ok"
        pie-label="SLA cumplido"
        pie-valor="vs 94.6% mes anterior"
      >
        <template #icono><Icon name="chart" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Gasto Compra Mes"
        :valor="money(kpiGastoMes || 4540.00)"
        microcopy="Órdenes valorizadas en el mes"
        estado="82% prep."
        estado-tipo="neutral"
        pie-label="Presupuesto ejecutado"
        pie-valor="Conforme a cupo"
      >
        <template #icono><Icon name="tag" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Recepciones Pendientes"
        :valor="`${kpiPendientes} OC`"
        microcopy="Pendientes de validación y aprobación"
        :estado="kpiPendientes > 0 ? 'Requiere atención' : 'Al día'"
        :estado-tipo="kpiPendientes > 0 ? 'fifo' : 'ok'"
        pie-label="Ventana de muelle"
        pie-valor="Hoy 09:30 y 14:00"
      >
        <template #icono><Icon name="clock" :size="18" /></template>
      </KpiTile>
    </section>

    <!-- 3. MATRIZ DE SEGUIMIENTO EN TIEMPO REAL -->
    <section class="rounded-2xl border border-outline-variant/40 bg-surface-container-lowest shadow-xs overflow-hidden">
      <!-- Toolbar y Filtros -->
      <div class="flex flex-col gap-3 border-b border-outline-variant/30 p-4 lg:flex-row lg:items-center lg:justify-between">
        <!-- Status Tabs -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1 lg:pb-0">
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors shrink-0"
            :class="tabEstado === 'todas' ? 'bg-primary-container text-white shadow-xs' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'"
            @click="tabEstado = 'todas'"
          >
            Todas ({{ ordenes.length }})
          </button>
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors shrink-0"
            :class="tabEstado === 'transito' ? 'bg-primary-container text-white shadow-xs' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'"
            @click="tabEstado = 'transito'"
          >
            En Tránsito / Despachadas ({{ kpiTransito }})
          </button>
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors shrink-0"
            :class="tabEstado === 'pendiente' ? 'bg-primary-container text-white shadow-xs' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'"
            @click="tabEstado = 'pendiente'"
          >
            Pendientes Aprobación ({{ kpiPendientes }})
          </button>
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors shrink-0"
            :class="tabEstado === 'recibida' ? 'bg-primary-container text-white shadow-xs' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'"
            @click="tabEstado = 'recibida'"
          >
            Completadas / En Muelle
          </button>
        </div>

        <!-- Filtros secundarios & Búsqueda -->
        <div class="flex flex-wrap items-center gap-2.5">
          <div class="inline-flex rounded-xl bg-surface-container p-0.5 text-xs border border-outline-variant/40">
            <button
              class="rounded-lg px-2.5 py-1 font-medium transition-colors"
              :class="filtroOrigen === 'todos' ? 'bg-surface-container-lowest text-primary-container font-semibold shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="filtroOrigen = 'todos'"
            >
              Todos los orígenes
            </button>
            <button
              class="rounded-lg px-2.5 py-1 font-medium transition-colors"
              :class="filtroOrigen === 'cd' ? 'bg-surface-container-lowest text-primary-container font-semibold shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="filtroOrigen = 'cd'"
            >
              CD Lo Boza
            </button>
            <button
              class="rounded-lg px-2.5 py-1 font-medium transition-colors"
              :class="filtroOrigen === 'dsd' ? 'bg-surface-container-lowest text-primary-container font-semibold shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="filtroOrigen = 'dsd'"
            >
              DSD Directos
            </button>
          </div>

          <div class="relative">
            <input
              v-model="busqueda"
              type="text"
              placeholder="Buscar OC, proveedor..."
              class="h-8 w-48 rounded-lg border border-outline-variant/60 bg-surface-container-low px-2.5 pl-8 text-xs text-on-surface focus:outline-none focus:border-primary-container"
            />
            <Icon name="search" :size="14" class="absolute left-2.5 top-2 text-outline" />
          </div>

          <button
            class="p-1.5 rounded-lg border border-outline-variant/50 text-on-surface-variant hover:bg-surface-container"
            title="Recargar órdenes"
            @click="cargarDatos"
          >
            <Icon name="refresh" :size="16" />
          </button>
        </div>
      </div>

      <!-- Tabla de Datos de Alta Densidad -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse min-w-[900px]">
          <thead>
            <tr class="bg-surface-container-low border-b border-outline-variant/40 text-[11px] font-bold uppercase tracking-wider text-outline h-9">
              <th class="py-2.5 px-4">N° OC &amp; Emisión</th>
              <th class="py-2.5 px-4">Tipo &amp; Proveedor</th>
              <th class="py-2.5 px-4">Carga (SKUs / Uds)</th>
              <th class="py-2.5 px-4 text-right">Monto Neto</th>
              <th class="py-2.5 px-4">Estado Operativo</th>
              <th class="py-2.5 px-4 text-center">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/25 text-xs text-on-surface">
            <tr v-if="cargando">
              <td colspan="6" class="py-8 text-center text-on-surface-variant">
                <span class="inline-block animate-spin mr-2">⏳</span> Cargando órdenes de compra...
              </td>
            </tr>
            <tr v-else-if="!ordenesFiltradas.length">
              <td colspan="6" class="py-8 text-center text-on-surface-variant">
                No se encontraron órdenes de compra para el filtro seleccionado.
              </td>
            </tr>
            <tr
              v-for="o in ordenesFiltradas"
              :key="o.orden_id"
              class="hover:bg-surface-container-low/50 transition-colors"
            >
              <td class="py-3 px-4">
                <div class="font-bold text-primary font-mono text-[13px]">OC-{{ String(o.orden_id).padStart(5, '0') }}</div>
                <div class="text-[11px] text-on-surface-variant">{{ o.fecha || 'Hoy' }}</div>
              </td>
              <td class="py-3 px-4">
                <div class="flex items-center gap-1.5">
                  <span
                    v-if="(o.proveedor_nombre || '').toLowerCase().includes('cd') || (o.proveedor_nombre || '').toLowerCase().includes('boza')"
                    class="rounded px-1.5 py-0.5 text-[10px] font-bold bg-primary/10 text-primary border border-primary/20"
                  >
                    CD CENTRAL
                  </span>
                  <span
                    v-else
                    class="rounded px-1.5 py-0.5 text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200"
                  >
                    DSD DIRECTO
                  </span>
                  <span class="font-semibold text-on-surface">{{ o.proveedor_nombre || `Proveedor #${o.proveedor_id}` }}</span>
                </div>
                <div class="text-[11px] text-on-surface-variant">
                  {{ o.tipo === 'especial' ? 'Pedido Especial' : 'Reabastecimiento Planificado' }}
                  <span v-if="o.motivo_desviacion" class="italic text-amber-700">· {{ o.motivo_desviacion }}</span>
                </div>
              </td>
              <td class="py-3 px-4">
                <div class="font-medium text-on-surface">{{ o.cantidad_skus ?? o.lineas?.length ?? 1 }} SKUs</div>
                <div class="text-[11px] text-on-surface-variant">{{ o.total_unidades ?? '—' }} unidades</div>
              </td>
              <td class="py-3 px-4 text-right">
                <div class="font-bold font-mono text-on-surface">{{ money(o.total_neto) }}</div>
                <span class="text-[10px] text-outline">Neto</span>
              </td>
              <td class="py-3 px-4">
                <SemanticChip
                  :tipo="
                    o.estado === 'aprobada' ? 'ia' :
                    o.estado === 'recibida' ? 'ok' :
                    o.estado === 'pendiente' ? 'fifo' : 'neutral'
                  "
                >
                  {{
                    o.estado === 'aprobada' ? 'En Tránsito' :
                    o.estado === 'recibida' ? 'En Muelle / Recibida' :
                    o.estado === 'pendiente' ? 'Pendiente Aprobación' : o.estado
                  }}
                </SemanticChip>
              </td>
              <td class="py-3 px-4 text-center">
                <div class="flex items-center justify-center gap-1.5">
                  <Btn
                    v-if="o.estado === 'pendiente'"
                    size="xs"
                    variant="primary"
                    @click="aprobar(o.orden_id)"
                  >
                    Aprobar
                  </Btn>
                  <RouterLink
                    v-else-if="o.estado === 'aprobada'"
                    to="/inventario"
                    class="rounded-lg bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-800 border border-emerald-200 hover:bg-emerald-100"
                  >
                    Recibir
                  </RouterLink>
                  <Btn size="xs" variant="outline" @click="verDetalle(o)">
                    <Icon name="chevron" :size="12" class="-rotate-90" /> Detalle
                  </Btn>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="border-t border-outline-variant/30 bg-surface-container-low px-4 py-2 text-xs text-on-surface-variant flex items-center justify-between">
        <span>Mostrando <strong>{{ ordenesFiltradas.length }}</strong> órdenes</span>
        <span class="text-[11px] text-outline">Sincronizado con base de datos central SIRA</span>
      </div>
    </section>

    <!-- 4. SECCIÓN INFERIOR ASIMÉTRICA: SUGERENCIAS MIN/MAX + BITÁCORA Y FINANZAS -->
    <section class="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <!-- PANEL IZQUIERDO: SUGERENCIAS ALGORÍTMICAS MIN/MAX (7 COLS) -->
      <div class="lg:col-span-7 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between pb-3 border-b border-outline-variant/30 mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
                <Icon name="sparkles" :size="16" />
              </div>
              <div>
                <h3 class="text-sm font-bold text-primary">Sugerencias Automáticas por Algoritmo Min/Max</h3>
                <p class="text-[12px] text-on-surface-variant">Predicción de quiebre en Providencia Express</p>
              </div>
            </div>
            <span class="rounded-full bg-purple-50 px-2 py-0.5 text-[11px] font-bold text-purple-800 border border-purple-200">
              Motor SIRA AI
            </span>
          </div>

          <!-- Lista de ítems críticos sugeridos -->
          <div class="space-y-3">
            <div
              v-if="!sugerencias.length"
              class="rounded-xl border border-dashed border-outline-variant/50 p-6 text-center text-xs text-on-surface-variant"
            >
              No hay quiebres inminentes detectados por el modelo en esta sucursal.
            </div>
            <div
              v-for="s in sugerencias.slice(0, 4)"
              :key="s.product_id"
              class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-outline-variant/30 bg-surface-container-low/70 p-3 hover:border-secondary/30 transition-all"
            >
              <div class="flex items-center gap-3">
                <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white border border-outline-variant/40 text-primary font-bold text-xs">
                  #{{ s.product_id }}
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-semibold text-on-surface text-xs">SKU #{{ s.product_id }}</span>
                    <span class="rounded px-1.5 py-0.2 text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200">
                      Bajo stock
                    </span>
                  </div>
                  <div class="text-[11px] text-on-surface-variant flex items-center gap-2">
                    <span>Stock actual: <strong>{{ s.cantidad_disponible }} un</strong></span>
                    <span>•</span>
                    <span>Punto reposición: <strong>{{ s.punto_reposicion }} un</strong></span>
                  </div>
                </div>
              </div>

              <div class="flex items-center gap-2 self-end sm:self-center">
                <span class="rounded-lg bg-secondary/10 px-2 py-1 text-[11px] font-bold text-secondary">
                  Sugerido +{{ s.cantidad_sugerida }} un
                </span>
                <Btn size="xs" variant="primary" @click="modalCrear = true">
                  Pedir
                </Btn>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-outline-variant/30 flex items-center justify-between text-xs text-on-surface-variant">
          <span>Basado en velocidad de rotación y estacionalidad local.</span>
          <button class="font-bold text-secondary hover:underline flex items-center gap-1" @click="modalCrear = true">
            Emitir pedido completo →
          </button>
        </div>
      </div>

      <!-- PANEL DERECHO: CUENTAS POR PAGAR & HISTORIAL (5 COLS) -->
      <div class="lg:col-span-5 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between pb-3 border-b border-outline-variant/30 mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Icon name="card" :size="16" />
              </div>
              <div>
                <h3 class="text-sm font-bold text-primary">Resumen Financiero con Proveedores</h3>
                <p class="text-[12px] text-on-surface-variant">Facturación, pagos y compras automáticas</p>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <ResumenCuentasPorPagar />
            <ReporteComprasAutomaticoManual />
            <HistorialProveedorProducto />
          </div>
        </div>
      </div>
    </section>

    <!-- DRAWER / SECCIÓN EXPANDIDA DE FACTURAS & PAGOS -->
    <section v-if="mostrarFinanzas" class="rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs space-y-4">
      <h3 class="text-sm font-bold text-primary">Ciclo de Facturas &amp; Pagos a Proveedores (Doble Autorización)</h3>
      <div class="grid gap-6 lg:grid-cols-2">
        <FormularioFacturaProveedor :empleado-id="empleadoId" />
        <FormularioPagoProveedor :empleado-autoriza-id="empleadoId" />
      </div>
    </section>

    <!-- MODAL: CREAR ORDEN DE COMPRA -->
    <Modal
      v-if="modalCrear"
      titulo="Nueva Orden de Compra"
      ancho="max-w-2xl"
      @cerrar="modalCrear = false"
    >
      <FormularioOrdenCompra
        :tienda-id="tiendaId"
        :empleado-id="empleadoId"
        @creada="ordenCreada"
      />
    </Modal>

    <!-- MODAL: DETALLE DE ORDEN SELECCIONADA -->
    <Modal
      v-if="ordenSeleccionada"
      :titulo="`Detalle de Orden OC-${String(ordenSeleccionada.orden_id).padStart(5, '0')}`"
      ancho="max-w-2xl"
      @cerrar="ordenSeleccionada = null"
    >
      <div class="space-y-4 text-xs">
        <div class="grid grid-cols-2 gap-3 rounded-xl bg-surface-container-low p-3">
          <div>
            <span class="text-outline text-[11px]">Proveedor:</span>
            <div class="font-bold text-on-surface text-sm">
              {{ ordenSeleccionada.proveedor_nombre || `Proveedor #${ordenSeleccionada.proveedor_id}` }}
            </div>
          </div>
          <div>
            <span class="text-outline text-[11px]">Estado:</span>
            <div>
              <SemanticChip :tipo="ordenSeleccionada.estado === 'aprobada' ? 'ia' : 'neutral'">
                {{ ordenSeleccionada.estado }}
              </SemanticChip>
            </div>
          </div>
          <div>
            <span class="text-outline text-[11px]">Fecha emisión:</span>
            <div class="font-semibold text-on-surface">{{ ordenSeleccionada.fecha }}</div>
          </div>
          <div>
            <span class="text-outline text-[11px]">Total Neto:</span>
            <div class="font-bold text-primary font-mono text-sm">{{ money(ordenSeleccionada.total_neto) }}</div>
          </div>
        </div>

        <div v-if="ordenSeleccionada.motivo_desviacion" class="rounded-lg bg-amber-50 p-2.5 text-amber-900 border border-amber-200">
          <strong>Motivo de desviación:</strong> {{ ordenSeleccionada.motivo_desviacion }}
        </div>

        <div>
          <h4 class="font-bold text-on-surface mb-2">Líneas de la orden</h4>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/40 text-outline text-[11px] uppercase font-bold">
                <th class="py-1">Producto</th>
                <th class="py-1 text-right">Cantidad</th>
                <th class="py-1 text-right">Costo Unitario</th>
                <th class="py-1 text-right">Subtotal</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/20">
              <tr v-for="l in ordenSeleccionada.lineas" :key="l.product_id" class="py-2">
                <td class="py-1.5 font-medium text-on-surface">
                  {{ l.product_nombre || `Producto #${l.product_id}` }}
                </td>
                <td class="py-1.5 text-right font-mono">{{ l.cantidad }} un</td>
                <td class="py-1.5 text-right font-mono">{{ money(l.costo_unitario) }}</td>
                <td class="py-1.5 text-right font-bold font-mono">
                  {{ money(Number(l.cantidad) * Number(l.costo_unitario)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex justify-end pt-2 border-t border-outline-variant/30 gap-2">
          <Btn
            v-if="ordenSeleccionada.estado === 'pendiente'"
            variant="primary"
            @click="aprobar(ordenSeleccionada.orden_id); ordenSeleccionada = null"
          >
            Aprobar Orden
          </Btn>
          <Btn variant="outline" @click="ordenSeleccionada = null">Cerrar</Btn>
        </div>
      </div>
    </Modal>
  </main>
</template>
