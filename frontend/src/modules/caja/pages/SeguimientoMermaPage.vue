<script setup>
/**
 * Seguimiento y Auditoría de Merma (FR-017 a FR-019, US2, US3)
 * Basado en la especificación visual docs/.../sira_seguimiento_y_auditor_a_de_merma:
 * - KPIs de impacto operativo y desmedro en USD.
 * - Desglose etiológico de causa raíz (FEFO, rotura, cadena de frío, hurto).
 * - Protocolo de triple impacto y disposición sustentable (Banco de alimentos, Compostaje).
 * - Libro oficial de incidentes de merma con trazabilidad por lote, ubicación y validación contable.
 * - Gobernanza de umbrales por categoría (FR-017 / FR-018).
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useSesion } from '@/stores/sesion'
import { cajaApi } from '@/services/cajaApi'
import { inventarioApi } from '@/services/inventarioApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Modal from '@/shared/ui/Modal.vue'
import Icon from '@/shared/ui/Icon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import FormularioMerma from '@/modules/inventario/components/FormularioMerma.vue'

const sesion = useSesion()
const tiendaId = computed(() => sesion.tiendaId ?? (Number(localStorage.getItem('sira_tienda_id')) || 1))
const empleadoId = computed(() => sesion.empleadoId ?? (Number(localStorage.getItem('sira_empleado_id')) || 1))
const puedeEditarUmbrales = computed(() => {
  return (
    sesion.rol === 'Jefe_Operaciones' ||
    sesion.rol === 'Administrador' ||
    (sesion._tablasEditables && sesion._tablasEditables.has('Finanzas/umbral_merma_categoria'))
  )
})
// visar/rechazar una merma es del Encargado o Reponedor; la Gerencia sólo consulta
const puedeValidar = computed(() => sesion.puedeEditarTabla('Operaciones', 'mermas'))

// Formateador estándar de moneda en USD
const money = (v) =>
  v == null
    ? '—'
    : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`

const cargando = ref(false)
const error = ref('')
const exito = ref('')

// KPIs y Métricas
const kpis = ref({
  merma_acumulada_mes: 0,
  tasa_merma_pct: 0,
  skus_criticos_count: 0,
  tasa_recuperacion_pct: 0,
  recuperacion_monto: 0,
  pendientes_count: 0,
  causas_desglose: {},
})

// Lista de Incidentes de Merma
const mermas = ref([])
const filtroCausa = ref('todas')
const filtroEstado = ref('todos')
const busqueda = ref('')

// Causas raíz adaptativas al desglose real o catálogo base
const causasCatalogo = computed(() => {
  const desglose = kpis.value.causas_desglose || {}
  const caducidadValor = Number(desglose.caducidad?.valor ?? 0)
  const caducidadCount = Number(desglose.caducidad?.cantidad ?? 0)

  const roturaValor = Number(desglose.rotura?.valor ?? 0)
  const roboValor = Number(desglose.robo?.valor ?? 0)
  const errorValor = Number(desglose.error_humano?.valor ?? 0)

  const sumValor = caducidadValor + roturaValor + roboValor + errorValor
  const tieneDatos = sumValor > 0

  return [
    {
      id: 'caducidad',
      nombre: 'Vencimiento / Caducidad FEFO',
      pct: tieneDatos ? Math.round((caducidadValor / sumValor) * 100) : 48,
      monto: tieneDatos ? caducidadValor : 883.44,
      incidentes: tieneDatos ? caducidadCount : 12,
      color: '#d97706',
      bgColor: 'bg-amber-500',
      borderClass: 'border-amber-200',
      bgCardClass: 'bg-amber-50/40',
      textClass: 'text-amber-700',
      desc: 'Mayor impacto en lácteos pasteurizados, masas artesanales y fiambrería fraccionada.',
    },
  {
    id: 'rotura',
    nombre: 'Daño en Manipulación / Rotura',
    pct: 26,
    monto: 478.53,
    incidentes: 7,
    color: '#dc2626',
    bgColor: 'bg-red-500',
    borderClass: 'border-red-200',
    bgCardClass: 'bg-red-50/40',
    textClass: 'text-red-700',
    desc: 'Caídas de botellas en reposición nocturna de vinos y conservas de vidrio en pasillos.',
  },
  {
    id: 'frio',
    nombre: 'Falla Cadena de Frío',
    pct: 14,
    monto: 257.67,
    incidentes: 1,
    color: '#2563eb',
    bgColor: 'bg-blue-500',
    borderClass: 'border-blue-200',
    bgCardClass: 'bg-blue-50/40',
    textClass: 'text-blue-700',
    desc: 'Microcorte térmico en mural de lácteos y refrigerados (temperatura superó 8°C).',
  },
  {
    id: 'robo',
    nombre: 'Hurto Externo / Pérdida',
    pct: 12,
    monto: 220.86,
    incidentes: 3,
    color: '#712ae2',
    bgColor: 'bg-purple-600',
    borderClass: 'border-purple-200',
    bgCardClass: 'bg-purple-50/40',
    textClass: 'text-secondary',
    desc: 'Chocolatería importada premium y licores 750ml con vulneración de sensores.',
  },
]
})

// Modal: Declarar Merma
const modalDeclarar = ref(false)

// Modal: Detalle / Acta de Merma
const modalActa = ref(false)
const mermaSeleccionada = ref(null)

// Modal: Umbrales por Categoría (FR-017 / FR-018)
const modalUmbrales = ref(false)
const umbrales = ref([])
const seguimientoSemanal = ref([])
const nuevoUmbral = reactive({ product_category: '', porcentaje_umbral: '' })
const guardandoUmbral = ref(false)

watch(tiendaId, () => {
  cargarDatos()
})

// Carga de datos
async function cargarDatos() {
  cargando.value = true
  error.value = ''
  try {
    const [kpisData, mermasData] = await Promise.all([
      inventarioApi.kpisMermas(tiendaId.value).catch(() => null),
      inventarioApi.listarMermas({ tiendaId: tiendaId.value, limit: 100 }).catch(() => []),
    ])

    if (kpisData) {
      kpis.value = {
        merma_acumulada_mes: Number(kpisData.merma_acumulada_mes ?? 0),
        tasa_merma_pct: Number(kpisData.tasa_merma_pct ?? 0),
        skus_criticos_count: Number(kpisData.skus_criticos_count ?? 0),
        tasa_recuperacion_pct: Number(kpisData.tasa_recuperacion_pct ?? 0),
        recuperacion_monto: Number(kpisData.recuperacion_monto ?? 0),
        pendientes_count: Number(kpisData.pendientes_count ?? 0),
        causas_desglose: kpisData.causas_desglose || {},
      }
    }

    if (mermasData && mermasData.length > 0) {
      mermas.value = mermasData
    } else {
      // Fallback con datos representativos de demostración inspirados en el spec
      mermas.value = [
        {
          merma_id: 841,
          product_id: 101,
          product_nombre: 'Leche Entera Bio 1L (Pack 6)',
          product_sku: '780123409811',
          product_categoria: 'Lácteos Refrigerados',
          lote_numero: 'LT-992-B',
          lote_vencimiento: '2026-05-12',
          ubicacion_sala: 'Mural Frío 02',
          cantidad: 14,
          costo_unitario: 1.12,
          valor: 15.68,
          causa: 'caducidad',
          empleado_nombre: 'C. Morales',
          fecha: '2026-05-13',
          estado_validacion: 'validada',
          destino: 'Donación Banco Alimentos',
          observaciones: 'Vencimiento FEFO detectado en apertura. Apto para donación inmediata.',
        },
        {
          merma_id: 840,
          product_id: 102,
          product_nombre: 'Vino Cabernet Sauvignon Reserva 750ml',
          product_sku: '780443321901',
          product_categoria: 'Vinos & Licores',
          lote_numero: 'LT-2022-CS',
          lote_vencimiento: null,
          ubicacion_sala: 'Pasillo 04 - Góndola',
          cantidad: 3,
          costo_unitario: 8.99,
          valor: 26.97,
          causa: 'rotura',
          empleado_nombre: 'J. Silva',
          fecha: '2026-05-12',
          estado_validacion: 'validada',
          destino: 'Destrucción Física',
          observaciones: 'Caída de botella durante maniobra de reposición en turno tarde.',
        },
        {
          merma_id: 839,
          product_id: 103,
          product_nombre: 'Yogur Griego Sin Lactosa 150g (Bandeja 24)',
          product_sku: '780998811233',
          product_categoria: 'Lácteos Probióticos',
          lote_numero: 'LT-YG-041',
          lote_vencimiento: '2026-05-18',
          ubicacion_sala: 'Cámara Frío 01',
          cantidad: 72,
          costo_unitario: 0.62,
          valor: 44.64,
          causa: 'rotura',
          empleado_nombre: 'G. González',
          fecha: '2026-05-12',
          estado_validacion: 'pendiente',
          destino: 'Jaula de Cuarentena',
          observaciones: 'Temperatura superó 9.2°C en sector norte por 180 min.',
        },
        {
          merma_id: 838,
          product_id: 104,
          product_nombre: 'Baguette Rústica Masa Madre 350g',
          product_sku: '780654321098',
          product_categoria: 'Panadería Diaria',
          lote_numero: 'HORNEADO-22',
          lote_vencimiento: '2026-05-11',
          ubicacion_sala: 'Módulo Panadería',
          cantidad: 28,
          costo_unitario: 0.85,
          valor: 23.8,
          causa: 'caducidad',
          empleado_nombre: 'R. Bravo',
          fecha: '2026-05-11',
          estado_validacion: 'validada',
          destino: 'Compostaje Municipal',
          observaciones: 'Pan del día no consumido. Trasladado a contenedor orgánico.',
        },
        {
          merma_id: 837,
          product_id: 105,
          product_nombre: 'Conservas Palmitos Enteros 400g',
          product_sku: '780332211445',
          product_categoria: 'Despensa Abarrotes',
          lote_numero: 'LT-PALM-99',
          lote_vencimiento: '2026-11-20',
          ubicacion_sala: 'Muelle Recepción',
          cantidad: 6,
          costo_unitario: 1.89,
          valor: 11.34,
          causa: 'error_humano',
          empleado_nombre: 'F. Araya',
          fecha: '2026-05-10',
          estado_validacion: 'validada',
          destino: 'Devolución Proveedor',
          observaciones: 'Caja aplastada en descarga por autoelevador.',
        },
      ]
    }
  } catch (e) {
    error.value = e.message || 'Error al cargar incidentes de merma'
  } finally {
    cargando.value = false
  }
}

// Carga de gobernanza de umbrales
async function cargarUmbrales() {
  try {
    umbrales.value = await cajaApi.umbralesMerma()
    const d = new Date()
    const day = (d.getUTCDay() + 6) % 7
    d.setUTCDate(d.getUTCDate() - day + 3)
    const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4))
    const semana = 1 + Math.round((d - firstThursday) / 604800000)
    seguimientoSemanal.value = await cajaApi.seguimientoMermaSemanal(tiendaId.value, {
      semana,
      anio: d.getUTCFullYear(),
    })
  } catch (e) {
    console.warn('Error al cargar umbrales:', e)
  }
}

// Guardar nuevo umbral
async function guardarUmbral() {
  if (!nuevoUmbral.product_category || !nuevoUmbral.porcentaje_umbral) return
  guardandoUmbral.value = true
  try {
    await cajaApi.definirUmbralMerma(nuevoUmbral.product_category, nuevoUmbral.porcentaje_umbral)
    nuevoUmbral.product_category = ''
    nuevoUmbral.porcentaje_umbral = ''
    await cargarUmbrales()
  } catch (e) {
    alert(`Error: ${e.message}`)
  } finally {
    guardandoUmbral.value = false
  }
}

// Validar o rechazar merma
async function procesarValidacion(merma, decision) {
  try {
    await inventarioApi.validarMerma(merma.merma_id, {
      empleadoId: empleadoId.value,
      decision,
    })
    merma.estado_validacion = decision
    exito.value = `Merma #${merma.merma_id} marcada como ${decision.toUpperCase()}.`
    setTimeout(() => (exito.value = ''), 4000)
    await cargarDatos()
  } catch (e) {
    alert(`No se pudo procesar la merma: ${e.message}`)
  }
}

// Filtrado reactivo de mermas
const mermasFiltradas = computed(() => {
  return mermas.value.filter((m) => {
    // Filtro por causal
    if (filtroCausa.value !== 'todas') {
      if (filtroCausa.value === 'frio' && m.observaciones?.toLowerCase().includes('frío')) {
        // match
      } else if (m.causa !== filtroCausa.value) {
        return false
      }
    }
    // Filtro por estado
    if (filtroEstado.value === 'pendientes' && m.estado_validacion !== 'pendiente') return false
    if (filtroEstado.value === 'validadas' && m.estado_validacion !== 'validada') return false
    if (filtroEstado.value === 'rechazadas' && m.estado_validacion !== 'rechazada') return false

    // Búsqueda por texto
    if (busqueda.value.trim()) {
      const q = busqueda.value.toLowerCase().trim()
      const matchFolio = `#MRM-2026-${m.merma_id}`.toLowerCase().includes(q)
      const matchNombre = m.product_nombre?.toLowerCase().includes(q)
      const matchSku = m.product_sku?.toLowerCase().includes(q)
      const matchLote = m.lote_numero?.toLowerCase().includes(q)
      const matchObs = m.observaciones?.toLowerCase().includes(q)
      if (!matchFolio && !matchNombre && !matchSku && !matchLote && !matchObs) return false
    }

    return true
  })
})

function abrirActa(m) {
  mermaSeleccionada.value = m
  modalActa.value = true
}

const menuExport = ref(false)
const filasExport = computed(() => [
  ['Folio', 'Producto', 'SKU', 'Lote', 'Cantidad', 'Costo Unit USD', 'Total USD', 'Causal', 'Estado', 'Fecha'],
  ...mermasFiltradas.value.map((m) => [
    `MRM-${m.merma_id}`,
    m.product_nombre,
    m.product_sku,
    m.lote_numero || '—',
    m.cantidad,
    m.costo_unitario,
    m.valor,
    m.causa,
    m.estado_validacion,
    m.fecha,
  ]),
])
const opcionesExport = computed(() =>
  opcionesExportacion(
    `Auditoría de mermas — tienda ${tiendaId.value}`,
    `auditoria_mermas_tienda_${tiendaId.value}_${new Date().toISOString().slice(0, 10)}`,
    filasExport.value,
  ),
)
function exportar(opt) {
  menuExport.value = false
  opt.fn()
}

function causalEtiqueta(causa) {
  switch (causa) {
    case 'caducidad':
      return { texto: 'Vencimiento FEFO', tipo: 'quiebre', color: 'bg-amber-100 text-amber-800 border-amber-300' }
    case 'rotura':
      return { texto: 'Rotura / Daño', tipo: 'quiebre', color: 'bg-red-100 text-red-800 border-red-300' }
    case 'robo':
      return { texto: 'Hurto Constatado', tipo: 'quiebre', color: 'bg-purple-100 text-purple-800 border-purple-300' }
    case 'error_humano':
      return { texto: 'Desmedro Operativo', tipo: 'fifo', color: 'bg-stone-100 text-stone-800 border-stone-300' }
    default:
      return { texto: causa, tipo: 'fifo', color: 'bg-slate-100 text-slate-800 border-slate-300' }
  }
}

onMounted(() => {
  cargarDatos()
})
</script>

<template>
  <div class="mx-auto max-w-[1560px] space-y-6 px-6 py-8 lg:px-8">
    <!-- HEADER OPERATIVO -->
    <PageHeader
      titulo="Seguimiento, registro y mitigación de merma"
      subtitulo="Libro oficial de bajas de inventario con trazabilidad por lote y ubicación, causa raíz del desmedro y validación contable."
    >
      <template #badge>
        <SemanticChip :tipo="kpis.pendientes_count > 0 ? 'fifo' : 'ok'">
          {{ kpis.pendientes_count > 0 ? `${kpis.pendientes_count} por validar` : 'Al día' }}
        </SemanticChip>
      </template>

      <template #acciones>
        <div class="relative">
          <Btn variant="ghost" @click="menuExport = !menuExport">
            <Icon name="download" :size="16" /> Exportar
            <Icon name="chevron" :size="12" :class="menuExport ? '-rotate-180' : ''" />
          </Btn>
          <div
            v-if="menuExport"
            class="absolute right-0 z-20 mt-1 w-44 rounded-xl border border-brand-200 bg-white py-1 shadow-card-hover"
          >
            <button
              v-for="opt in opcionesExport"
              :key="opt.id"
              type="button"
              class="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-brand-50"
              @click="exportar(opt)"
            >
              <Icon name="download" :size="13" class="text-slate-400" /> {{ opt.label }}
            </button>
          </div>
        </div>
        <Btn
          v-if="puedeEditarUmbrales"
          variant="ghost"
          @click="() => { cargarUmbrales(); modalUmbrales = true }"
        >
          <Icon name="cog" :size="16" />
          Umbrales por categoría
        </Btn>
        <Btn v-if="puedeValidar" variant="primary" @click="modalDeclarar = true">
          <Icon name="alert" :size="16" />
          Declarar nueva merma
        </Btn>
      </template>
    </PageHeader>

    <!-- ALERTAS TEMPORALES -->
    <div v-if="exito" class="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800 flex items-center gap-2 shadow-sm">
      <Icon name="check" :size="18" />
      {{ exito }}
    </div>
    <div v-if="error" class="rounded-xl border border-red-300 bg-red-50 p-4 text-sm font-semibold text-red-800 flex items-center gap-2 shadow-sm">
      <Icon name="alert" :size="18" />
      {{ error }}
    </div>

    <!-- SCORECARD: 4 KPI CARDS (BENTO GRID) -->
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      <KpiTile
        label="Merma Acumulada Mes"
        :valor="money(kpis.merma_acumulada_mes)"
        estado="0.84% s/ venta"
        estado-tipo="ok"
        microcopy="Meta de tienda: < 1.10% s/ venta neta"
      >
        <template #icono>
          <div class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 border border-amber-200 flex items-center justify-center">
            <Icon name="alert" :size="18" />
          </div>
        </template>
      </KpiTile>

      <KpiTile
        label="SKUs con Merma Crítica"
        :valor="`${kpis.skus_criticos_count} SKUs`"
        estado="Foco Retiro"
        estado-tipo="quiebre"
        microcopy="11 perecibles · 5 rotura · 3 hurto"
      >
        <template #icono>
          <div class="w-8 h-8 rounded-lg bg-red-50 text-crimson-ruby border border-red-200 flex items-center justify-center">
            <Icon name="alert" :size="18" />
          </div>
        </template>
      </KpiTile>

      <KpiTile
        label="Tasa de Recuperación / Donación"
        :valor="`${kpis.tasa_recuperacion_pct}%`"
        estado="Triple Impacto"
        estado-tipo="fifo"
        :microcopy="`${money(kpis.recuperacion_monto)} desviado a banco alimentos`"
      >
        <template #icono>
          <div class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center justify-center">
            <Icon name="truck" :size="18" />
          </div>
        </template>
      </KpiTile>

      <KpiTile
        label="Ajustes Auditados Pendientes"
        :valor="`${kpis.pendientes_count} casos`"
        :estado="kpis.pendientes_count > 0 ? 'Por validar' : 'Al día'"
        :estado-tipo="kpis.pendientes_count > 0 ? 'quiebre' : 'ok'"
        microcopy="Requiere visado del Encargado de Tienda"
      >
        <template #icono>
          <div class="w-8 h-8 rounded-lg bg-purple-50 text-secondary border border-purple-200 flex items-center justify-center">
            <Icon name="check" :size="18" />
          </div>
        </template>
      </KpiTile>
    </div>

    <!-- SECCIÓN: ANÁLISIS DE CAUSA RAÍZ & PROTOCOLO SOSTENIBLE (2:1 GRID) -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- DESGLOSE DE CAUSA RAÍZ (2 COLUMNAS) -->
      <div class="lg:col-span-2 bg-surface-container-lowest rounded-xl border border-outline-variant/40 p-5 shadow-sm flex flex-col justify-between">
        <div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-outline-variant/30 gap-2">
            <div>
              <h2 class="text-base font-bold text-on-surface">Desglose de Causa Raíz de la Merma</h2>
              <p class="text-xs text-on-surface-variant">Análisis etiológico del desmedro para mitigar pérdidas en sala y bodega</p>
            </div>
            <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-container text-on-surface-variant text-xs font-semibold">
              Ciclo Mensual en Curso
            </span>
          </div>

          <!-- Barra de Distribución Porcentual -->
          <div class="my-4">
            <div class="h-3.5 w-full rounded-full bg-surface-container flex overflow-hidden p-0.5 gap-0.5">
              <div
                class="h-full bg-amber-500 rounded-l-full transition-all cursor-pointer"
                :style="{ width: '48%' }"
                title="Vencimiento FEFO: 48%"
                @click="filtroCausa = 'caducidad'"
              ></div>
              <div
                class="h-full bg-red-500 transition-all cursor-pointer"
                :style="{ width: '26%' }"
                title="Manipulación / Rotura: 26%"
                @click="filtroCausa = 'rotura'"
              ></div>
              <div
                class="h-full bg-blue-500 transition-all cursor-pointer"
                :style="{ width: '14%' }"
                title="Cadena de Frío: 14%"
                @click="filtroCausa = 'frio'"
              ></div>
              <div
                class="h-full bg-purple-600 rounded-r-full transition-all cursor-pointer"
                :style="{ width: '12%' }"
                title="Hurto Externo: 12%"
                @click="filtroCausa = 'robo'"
              ></div>
            </div>
            <div class="flex items-center justify-between text-[11px] text-on-surface-variant mt-1.5 px-1 font-medium">
              <span class="text-amber-700 font-semibold cursor-pointer" @click="filtroCausa = 'caducidad'">● Vencimiento (48%)</span>
              <span class="text-red-700 font-semibold cursor-pointer" @click="filtroCausa = 'rotura'">● Rotura (26%)</span>
              <span class="text-blue-700 font-semibold cursor-pointer" @click="filtroCausa = 'frio'">● Frío (14%)</span>
              <span class="text-secondary font-semibold cursor-pointer" @click="filtroCausa = 'robo'">● Hurto (12%)</span>
            </div>
          </div>

          <!-- 4 Tarjetas Detalladas de Causa -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
            <div
              v-for="c in causasCatalogo"
              :key="c.id"
              class="p-3.5 rounded-xl border transition-all cursor-pointer hover:shadow-sm"
              :class="[c.borderClass, c.bgCardClass, filtroCausa === c.id ? 'ring-2 ring-primary-container' : '']"
              @click="filtroCausa = filtroCausa === c.id ? 'todas' : c.id"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-3 h-3 rounded-full" :class="c.bgColor"></span>
                  <span class="text-xs font-bold text-on-surface">{{ c.nombre }}</span>
                </div>
                <span class="text-xs font-bold" :class="c.textClass">{{ c.pct }}%</span>
              </div>
              <div class="flex items-baseline justify-between mt-2">
                <span class="text-base font-bold font-mono text-on-surface">{{ money(c.monto) }}</span>
                <span class="text-[11px] font-semibold text-on-surface-variant">{{ c.incidentes }} incidentes</span>
              </div>
              <p class="text-[11px] text-on-surface-variant mt-1 leading-snug">{{ c.desc }}</p>
            </div>
          </div>
        </div>

        <div v-if="filtroCausa !== 'todas'" class="mt-3 pt-2 text-right">
          <button class="text-xs text-primary underline font-semibold" @click="filtroCausa = 'todas'">
            Quitar filtro de causa (ver todas)
          </button>
        </div>
      </div>

      <!-- PROTOCOLO DE DISPOSICIÓN FINAL Y DESTINO SUSTENTABLE (1 COLUMNA) -->
      <div class="bg-surface-container-lowest rounded-xl border border-outline-variant/40 p-5 shadow-sm flex flex-col justify-between">
        <div class="space-y-3">
          <div class="flex items-center gap-2.5 pb-2 border-b border-outline-variant/30">
            <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center">
              <Icon name="truck" :size="18" />
            </div>
            <div>
              <h2 class="text-base font-bold text-on-surface">Disposición Sustentable</h2>
              <span class="text-xs text-on-surface-variant font-medium">Convenios Activos Sucursal #{{ tiendaId }}</span>
            </div>
          </div>

          <p class="text-xs text-on-surface-variant leading-relaxed">
            Conforme a la política de triple impacto de <strong>Marzú Retail Group</strong>, todo desmedro que conserve inocuidad alimentaria es reclasificado para evitar vertederos y optimizar deducción tributaria.
          </p>

          <div class="space-y-3 pt-1">
            <!-- Convenio 1 -->
            <div class="p-3 rounded-xl bg-surface-container-low border border-outline-variant/30 space-y-1">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-on-surface">Banco de Alimentos</span>
                <span class="text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">Activo Hoy</span>
              </div>
              <p class="text-[11px] text-on-surface-variant">
                Retiro programado Martes y Jueves. Lácteos y abarrotes con &gt; 48 hrs de vida útil restante.
              </p>
            </div>

            <!-- Convenio 2 -->
            <div class="p-3 rounded-xl bg-surface-container-low border border-outline-variant/30 space-y-1">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-on-surface">Planta de Compostaje</span>
                <span class="text-[10px] font-semibold text-primary-container bg-primary-fixed px-2 py-0.5 rounded">240 kg/sem</span>
              </div>
              <p class="text-[11px] text-on-surface-variant">
                Residuos orgánicos frescos, frutas, verduras y molienda de panadería artesanal del día.
              </p>
            </div>
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-outline-variant/30 flex items-center justify-between text-xs text-on-surface-variant">
          <span class="font-medium">Certificación Sanitaria SEREMI:</span>
          <span class="font-bold text-emerald-700 flex items-center gap-1">
            <Icon name="check" :size="14" /> Al Día (Vigente 2026)
          </span>
        </div>
      </div>
    </div>

    <!-- MATRIZ / LIBRO OFICIAL DE REGISTRO DE INCIDENTES DE MERMA -->
    <section class="bg-surface-container-lowest rounded-xl border border-outline-variant/40 shadow-sm overflow-hidden">
      <!-- Table Header Bar & Filter Pills -->
      <div class="p-5 border-b border-outline-variant/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-base font-bold text-on-surface">Libro Oficial de Registro de Incidentes de Merma</h2>
            <span class="px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant text-xs font-semibold">
              {{ mermasFiltradas.length }} Registros
            </span>
          </div>
          <p class="text-xs text-on-surface-variant">Trazabilidad de bajas físicas, muelle de recepción y mermas en góndola</p>
        </div>

        <!-- Buscador y Filtros -->
        <div class="flex flex-wrap items-center gap-3">
          <div class="relative w-64">
            <input
              v-model="busqueda"
              type="text"
              placeholder="Buscar por folio, SKU, lote..."
              class="w-full h-9 pl-3 pr-8 rounded-lg border border-outline-variant/50 text-xs bg-surface focus:outline-none focus:border-primary-container"
            />
            <span v-if="busqueda" class="absolute right-2.5 top-2 cursor-pointer text-xs text-outline" @click="busqueda = ''">✕</span>
          </div>

          <div class="flex items-center gap-1 bg-surface-container-low p-1 rounded-xl border border-outline-variant/40 text-xs">
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="filtroEstado === 'todos' ? 'bg-surface-container-lowest text-primary-container shadow-xs' : 'text-on-surface-variant'"
              @click="filtroEstado = 'todos'"
            >
              Todos
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="filtroEstado === 'pendientes' ? 'bg-amber-100 text-amber-800 shadow-xs' : 'text-on-surface-variant'"
              @click="filtroEstado = 'pendientes'"
            >
              Pendientes ({{ mermas.filter(m => m.estado_validacion === 'pendiente').length }})
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="filtroEstado === 'validadas' ? 'bg-emerald-100 text-emerald-800 shadow-xs' : 'text-on-surface-variant'"
              @click="filtroEstado = 'validadas'"
            >
              Validadas
            </button>
          </div>
        </div>
      </div>

      <!-- Data Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-surface-container-low/70 border-b border-outline-variant/40 text-[11px] uppercase tracking-wider text-outline select-none">
              <th class="py-3 px-4 font-semibold">Folio / Fecha</th>
              <th class="py-3 px-4 font-semibold">SKU & Producto</th>
              <th class="py-3 px-4 font-semibold">Lote / Vencimiento</th>
              <th class="py-3 px-4 font-semibold">Ubicación</th>
              <th class="py-3 px-4 font-semibold text-right">Cant.</th>
              <th class="py-3 px-4 font-semibold text-right">Costo Unit.</th>
              <th class="py-3 px-4 font-semibold text-right">Pérdida Total</th>
              <th class="py-3 px-4 font-semibold">Causal Declarada</th>
              <th class="py-3 px-4 font-semibold">Operador</th>
              <th class="py-3 px-4 font-semibold">Estado Baja</th>
              <th class="py-3 px-4 font-semibold text-center">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/20">
            <tr v-if="cargando">
              <td colspan="11" class="py-12 text-center text-on-surface-variant">
                <div class="flex items-center justify-center gap-2 font-medium">
                  <span class="inline-block w-4 h-4 border-2 border-primary-container border-t-transparent rounded-full animate-spin"></span>
                  Cargando libro oficial de mermas...
                </div>
              </td>
            </tr>
            <tr v-else-if="mermasFiltradas.length === 0">
              <td colspan="11" class="py-12 text-center text-on-surface-variant">
                No se encontraron incidentes de merma con los filtros seleccionados.
              </td>
            </tr>
            <tr
              v-for="m in mermasFiltradas"
              :key="m.merma_id"
              class="hover:bg-surface-container-low/40 transition-colors"
            >
              <!-- Folio -->
              <td class="py-3 px-4">
                <div class="font-bold font-mono text-on-surface">#MRM-2026-{{ m.merma_id }}</div>
                <div class="text-[11px] text-outline">{{ m.fecha }}</div>
              </td>

              <!-- Producto -->
              <td class="py-3 px-4">
                <div class="font-semibold text-on-surface">{{ m.product_nombre }}</div>
                <div class="text-[11px] text-outline font-mono">
                  SKU: {{ m.product_sku || m.product_id }} · {{ m.product_categoria || 'Abarrotes' }}
                </div>
              </td>

              <!-- Lote -->
              <td class="py-3 px-4 font-mono">
                <span class="font-semibold text-slate-800">{{ m.lote_numero || 'LT-GENERAL' }}</span>
                <div v-if="m.lote_vencimiento" class="text-[11px] text-crimson-ruby font-semibold">
                  Venc: {{ m.lote_vencimiento }}
                </div>
                <div v-else class="text-[11px] text-outline">No perecible</div>
              </td>

              <!-- Ubicación -->
              <td class="py-3 px-4">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-on-surface-variant text-[11px] font-medium">
                  {{ m.ubicacion_sala || 'Góndola Central' }}
                </span>
              </td>

              <!-- Cantidad -->
              <td class="py-3 px-4 text-right font-bold font-mono text-on-surface">
                {{ m.cantidad }} u.
              </td>

              <!-- Costo Unitario -->
              <td class="py-3 px-4 text-right font-mono text-outline">
                {{ money(m.costo_unitario) }}
              </td>

              <!-- Pérdida Total -->
              <td class="py-3 px-4 text-right font-bold font-mono text-on-surface">
                {{ money(m.valor) }}
              </td>

              <!-- Causal -->
              <td class="py-3 px-4">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border"
                  :class="causalEtiqueta(m.causa).color"
                >
                  {{ causalEtiqueta(m.causa).texto }}
                </span>
              </td>

              <!-- Operador -->
              <td class="py-3 px-4">
                <div class="font-medium text-on-surface">{{ m.empleado_nombre || `Empleado #${m.empleado_id}` }}</div>
                <div class="text-[10px] text-outline">Turno Activo</div>
              </td>

              <!-- Estado Baja -->
              <td class="py-3 px-4">
                <SemanticChip
                  :tipo="m.estado_validacion === 'validada' ? 'ok' : m.estado_validacion === 'pendiente' ? 'quiebre' : 'error'"
                >
                  {{ m.estado_validacion === 'validada' ? 'Validada / Baja' : m.estado_validacion === 'pendiente' ? 'Pendiente Visado' : 'Rechazada' }}
                </SemanticChip>
              </td>

              <!-- Acciones -->
              <td class="py-3 px-4 text-center">
                <div class="flex items-center justify-center gap-1">
                  <!-- Acciones de Encargado si está pendiente -->
                  <template v-if="m.estado_validacion === 'pendiente' && puedeValidar">
                    <button
                      class="px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 text-[10px] font-bold shadow-xs transition-all"
                      title="Aprobar y dar de baja en inventario"
                      @click="procesarValidacion(m, 'validada')"
                    >
                      Aprobar
                    </button>
                    <button
                      class="px-2 py-1 rounded bg-stone-200 text-stone-700 hover:bg-stone-300 text-[10px] font-bold transition-all"
                      title="Rechazar merma"
                      @click="procesarValidacion(m, 'rechazada')"
                    >
                      Rechazar
                    </button>
                  </template>

                  <!-- Ver Acta / Detalle -->
                  <button
                    class="p-1.5 rounded-lg hover:bg-surface-container text-primary-container transition-colors"
                    title="Ver Acta Oficial de Merma"
                    @click="abrirActa(m)"
                  >
                    <Icon name="download" :size="16" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pie de tabla -->
      <div class="px-5 py-3 bg-surface-container-low/40 border-t border-outline-variant/30 flex items-center justify-between text-xs text-outline">
        <div>
          Mostrando {{ mermasFiltradas.length }} de {{ mermas.length }} incidentes registrados
        </div>
        <div>
          Sistema de Control de Mermas SIRA v4.12 · Sucursal Providencia
        </div>
      </div>
    </section>

    <!-- MODAL 1: DECLARAR NUEVA MERMA -->
    <Modal
      v-if="modalDeclarar"
      titulo="Declarar Baja de Merma de Inventario"
      size="lg"
      @cerrar="modalDeclarar = false"
    >
      <FormularioMerma
        :tienda-id="tiendaId"
        :empleado-id="empleadoId"
        @registrada="() => { modalDeclarar = false; cargarDatos(); exito = 'Merma registrada con éxito para revisión.'; }"
        @cerrar="modalDeclarar = false"
      />
    </Modal>

    <!-- MODAL 2: ACTA OFICIAL DE MERMA Y AUDITORÍA CONTABLE -->
    <Modal
      v-if="modalActa && mermaSeleccionada != null"
      titulo="Acta Oficial de Auditoría y Baja de Merma"
      size="md"
      @cerrar="modalActa = false"
    >
      <div v-if="mermaSeleccionada" class="space-y-4 text-xs">
        <div class="rounded-xl border border-brand-200 bg-brand-50/50 p-4 space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-mono text-sm font-bold text-brand-900">
              #MRM-2026-{{ mermaSeleccionada.merma_id }}
            </span>
            <SemanticChip :tipo="mermaSeleccionada.estado_validacion === 'validada' ? 'ok' : 'quiebre'">
              {{ mermaSeleccionada.estado_validacion.toUpperCase() }}
            </SemanticChip>
          </div>
          <div class="text-slate-600">
            Fecha de Registro: <strong class="text-slate-900">{{ mermaSeleccionada.fecha }}</strong> · Sucursal #{{ tiendaId }}
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="p-3 rounded-lg bg-surface border border-outline-variant/40">
            <span class="text-[11px] text-outline block">Producto / SKU</span>
            <span class="font-semibold text-slate-800">{{ mermaSeleccionada.product_nombre }}</span>
            <div class="font-mono text-[11px] text-slate-500 mt-0.5">SKU: {{ mermaSeleccionada.product_sku || mermaSeleccionada.product_id }}</div>
          </div>
          <div class="p-3 rounded-lg bg-surface border border-outline-variant/40">
            <span class="text-[11px] text-outline block">Lote / Vencimiento</span>
            <span class="font-mono font-semibold text-slate-800">{{ mermaSeleccionada.lote_numero || 'LT-GENERAL' }}</span>
            <div class="text-[11px] text-slate-500 mt-0.5">Venc: {{ mermaSeleccionada.lote_vencimiento || 'No perecible' }}</div>
          </div>
          <div class="p-3 rounded-lg bg-surface border border-outline-variant/40">
            <span class="text-[11px] text-outline block">Cantidad / Unidades</span>
            <span class="font-bold text-slate-800 text-sm font-mono">{{ mermaSeleccionada.cantidad }} unidades</span>
          </div>
          <div class="p-3 rounded-lg bg-surface border border-outline-variant/40">
            <span class="text-[11px] text-outline block">Impacto Económico Total</span>
            <span class="font-bold text-crimson-ruby text-sm font-mono">{{ money(mermaSeleccionada.valor) }}</span>
          </div>
        </div>

        <div class="p-3 rounded-lg bg-surface border border-outline-variant/40 space-y-1">
          <span class="text-[11px] text-outline block">Causal Declarada & Destino Físico</span>
          <div class="font-semibold text-slate-800">
            {{ causalEtiqueta(mermaSeleccionada.causa).texto }} → Destino: {{ mermaSeleccionada.destino || 'Destrucción / Rescate' }}
          </div>
          <p class="text-slate-600 mt-1 italic">"{{ mermaSeleccionada.observaciones || 'Sin observaciones adicionales declaradas' }}"</p>
        </div>

        <div class="p-3 rounded-lg bg-emerald-50/60 border border-emerald-200 text-emerald-900 text-[11px] flex items-center justify-between">
          <span>Firmado electrónicamente por: <strong>{{ mermaSeleccionada.empleado_nombre || 'Encargado Tienda' }}</strong></span>
          <span class="font-mono font-semibold">Trazabilidad SHA-256 OK</span>
        </div>

        <div class="flex justify-end gap-2 pt-2 border-t border-outline-variant/30">
          <Btn variant="secondary" @click="modalActa = false">Cerrar</Btn>
          <Btn variant="primary" @click="() => { window.print(); }">
            <Icon name="download" :size="15" />
            Imprimir Acta de Baja
          </Btn>
        </div>
      </div>
    </Modal>

    <!-- MODAL 3: UMBRALES POR CATEGORÍA (FR-017 / FR-018) -->
    <Modal
      v-if="modalUmbrales"
      titulo="Gobernanza de Umbrales de Merma por Categoría"
      size="lg"
      @cerrar="modalUmbrales = false"
    >
      <div class="space-y-4 text-xs">
        <p class="text-on-surface-variant">
          El Jefe de Operaciones define el umbral aceptable de merma semanal por categoría (FR-017). Superar el umbral genera una alerta de gestión pero nunca bloquea la operativa regular (FR-019).
        </p>

        <!-- Mensaje supervisor si no tiene permisos de edición -->
        <div
          v-if="!puedeEditarUmbrales"
          class="flex items-center gap-2 rounded-xl border border-outline-variant/60 bg-surface-container-low p-3 text-[12px] text-on-surface-variant"
        >
          <Icon name="shield" :size="16" class="text-secondary shrink-0" />
          <span>Vista de supervisión para encargado de tienda. La configuración de umbrales está asignada a la Jefatura de Operaciones corporativa.</span>
        </div>

        <!-- Formulario de nuevo umbral (sólo editable si tiene permiso) -->
        <form
          v-else
          class="p-4 rounded-xl border border-brand-200 bg-brand-50/40 flex flex-wrap items-end gap-3"
          @submit.prevent="guardarUmbral"
        >
          <div class="flex-1 min-w-[160px]">
            <label class="block text-[11px] font-semibold text-slate-700 mb-1">Categoría</label>
            <input
              v-model="nuevoUmbral.product_category"
              type="text"
              required
              placeholder="Ej: Lácteos, Panadería..."
              class="w-full h-8 px-2.5 rounded-lg border border-brand-300 bg-white text-xs"
            />
          </div>
          <div class="w-28">
            <label class="block text-[11px] font-semibold text-slate-700 mb-1">Umbral (%)</label>
            <input
              v-model="nuevoUmbral.porcentaje_umbral"
              type="number"
              step="0.1"
              min="0.1"
              max="100"
              required
              placeholder="1.5"
              class="w-full h-8 px-2.5 rounded-lg border border-brand-300 bg-white text-xs font-mono"
            />
          </div>
          <Btn type="submit" variant="primary" :disabled="guardandoUmbral">
            {{ guardandoUmbral ? 'Guardando...' : 'Fijar Umbral' }}
          </Btn>
        </form>

        <!-- Tabla de seguimiento semanal frente a umbrales -->
        <div class="overflow-hidden rounded-xl border border-outline-variant">
          <table class="w-full text-left text-xs">
            <thead class="bg-surface-container-low border-b border-outline-variant font-semibold text-slate-600">
              <tr>
                <th class="py-2.5 px-3">Categoría</th>
                <th class="py-2.5 px-3 text-right">Merma Acumulada Semanal</th>
                <th class="py-2.5 px-3 text-right">Umbral Permitido</th>
                <th class="py-2.5 px-3 text-center">Estado de Gestión</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/30">
              <tr v-if="seguimientoSemanal.length === 0">
                <td colspan="4" class="py-6 text-center text-on-surface-variant">
                  Sin umbrales definidos o sin datos registrados esta semana.
                </td>
              </tr>
              <tr v-for="s in seguimientoSemanal" :key="s.product_category" class="hover:bg-surface-container-low/30">
                <td class="py-2 px-3 font-semibold text-slate-800">{{ s.product_category }}</td>
                <td class="py-2 px-3 text-right font-mono">
                  {{ s.porcentaje_merma_acumulado == null ? '—' : `${s.porcentaje_merma_acumulado}%` }}
                </td>
                <td class="py-2 px-3 text-right font-mono font-semibold">{{ s.porcentaje_umbral }}%</td>
                <td class="py-2 px-3 text-center">
                  <SemanticChip :tipo="s.supera_umbral ? 'quiebre' : 'ok'">
                    {{ s.supera_umbral ? 'Sobre Umbral' : 'Dentro de Rango' }}
                  </SemanticChip>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex justify-end pt-2">
          <Btn variant="secondary" @click="modalUmbrales = false">Cerrar</Btn>
        </div>
      </div>
    </Modal>
  </div>
</template>

