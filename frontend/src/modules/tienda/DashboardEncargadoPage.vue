<script setup>
/**
 * Dashboard Operativo del Encargado de Tienda (feature 013 — portal del rol).
 * Vista única de su tienda: agrega datos que el Encargado ya puede consultar
 * (cuadre de caja, datáfonos, inventario, alertas) en KPI + gráficos + estado de
 * sala por caja. No inventa datos: todo sale de endpoints existentes. La
 * telemetría IoT del mockup (sensores de temperatura, recepción DSD, agenda de
 * tareas, IA predictiva) queda fuera — no hay fuente para ella.
 */
import { computed, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { cajaApi } from '@/services/cajaApi'
import { inventarioApi } from '@/services/inventarioApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const sesion = useSesion()
const tiendaId = computed(() => sesion.tiendaId ?? (Number(localStorage.getItem("sira_tienda_id")) || 1))

const cajas = ref([])
const cierres = ref([])
const datafonos = ref([])
const resumen = ref({})
const alertasRepos = ref(0)
const alertasVenc = ref(0)
const cargando = ref(false)
const error = ref('')

const money = (v) => `$${Math.round(Number(v || 0)).toLocaleString('es-CL')}`

// --- datáfonos de esta tienda (filtrados por sus cajas) ---
const cajaIds = computed(() => new Set(cajas.value.map((c) => c.caja_id)))
const datafonosTienda = computed(() => datafonos.value.filter((d) => cajaIds.value.has(d.caja_id)))

const kpi = computed(() => {
  const dif = cierres.value.map((c) => Number(c.diferencia))
  const descuadres = dif.filter((n) => n !== 0).length
  const neta = dif.reduce((s, n) => s + n, 0)
  const dt = datafonosTienda.value
  return {
    cajas: cajas.value.length,
    cuadradas: new Set(cierres.value.map((c) => c.caja_id)).size,
    descuadres,
    neta,
    recaudacion: cierres.value.reduce((s, c) => s + Number(c.total_esperado), 0),
    quiebre: resumen.value.quiebre ?? 0,
    porVencer: resumen.value.por_vencer ?? 0,
    tasaMerma: Number(resumen.value.tasa_merma_pct ?? 0),
    datafonosOk: dt.filter((d) => d.estado === 'activo').length,
    datafonosTotal: dt.length,
    alertas: alertasRepos.value + alertasVenc.value,
  }
})

// --- gráfico 1: estado del stock (donut) ---
const chartStock = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, icon: 'circle', textStyle: { fontSize: 11 } },
  series: [
    {
      type: 'pie',
      radius: ['45%', '72%'],
      center: ['50%', '44%'],
      label: { show: false },
      data: [
        { value: resumen.value.normal ?? 0, name: 'Normal', itemStyle: { color: '#047857' } },
        { value: resumen.value.por_vencer ?? 0, name: 'Por vencer', itemStyle: { color: '#d97706' } },
        { value: resumen.value.quiebre ?? 0, name: 'Quiebre', itemStyle: { color: '#be123c' } },
        { value: resumen.value.sobre_stock ?? 0, name: 'Sobre stock', itemStyle: { color: '#7c3aed' } },
      ],
    },
  ],
}))

// --- gráfico 2: diferencia de cuadre por caja (bar) ---
const cierresConDif = computed(() => cierres.value.some((c) => Number(c.diferencia) !== 0))
const cortoCLP = (v) =>
  Math.abs(v) >= 1000 ? `${Math.round(v / 1000)}k` : String(Math.round(v))
const chartCuadre = computed(() => {
  const filas = [...cierres.value].sort((a, b) => a.caja_id - b.caja_id)
  return {
    tooltip: { trigger: 'axis', valueFormatter: (v) => money(v) },
    grid: { left: 8, right: 12, top: 16, bottom: 24, containLabel: true },
    xAxis: {
      type: 'category',
      data: filas.map((c) => cajaNombre(c.caja_id)),
      axisLabel: { fontSize: 10, interval: 0, rotate: filas.length > 6 ? 35 : 0 },
    },
    yAxis: { type: 'value', axisLabel: { formatter: cortoCLP } },
    series: [
      {
        type: 'bar',
        data: filas.map((c) => ({
          value: Number(c.diferencia),
          itemStyle: {
            color: Number(c.diferencia) === 0 ? '#047857' : Number(c.diferencia) < 0 ? '#be123c' : '#d97706',
            borderRadius: 3,
          },
        })),
        barMaxWidth: 34,
      },
    ],
  }
})

// --- gráfico 3: alertas pendientes por tipo (bar) ---
const chartAlertas = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 8, right: 12, top: 16, bottom: 8, containLabel: true },
  xAxis: { type: 'category', data: ['Reposición', 'Vencimiento'] },
  yAxis: { type: 'value' },
  series: [
    {
      type: 'bar',
      data: [
        { value: alertasRepos.value, itemStyle: { color: '#0a3632', borderRadius: 4 } },
        { value: alertasVenc.value, itemStyle: { color: '#d97706', borderRadius: 4 } },
      ],
      barMaxWidth: 60,
    },
  ],
}))

// --- gráfico 4: conformidad de datáfonos (donut) ---
const chartDatafonos = computed(() => {
  const dt = datafonosTienda.value
  const por = (e) => dt.filter((d) => d.estado === e).length
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', textStyle: { fontSize: 11 } },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '44%'],
        label: { show: false },
        data: [
          { value: por('activo'), name: 'Conformes', itemStyle: { color: '#047857' } },
          { value: por('requiere_actualizacion'), name: 'No conformes', itemStyle: { color: '#d97706' } },
          { value: por('fuera_servicio'), name: 'Fuera de servicio', itemStyle: { color: '#be123c' } },
        ],
      },
    ],
  }
})

function cajaNombre(id) {
  return cajas.value.find((c) => c.caja_id === id)?.nombre || `Caja ${id}`
}

// estado de sala por caja: cruza cuadre + datáfono
const salaPorCaja = computed(() =>
  [...cajas.value]
    .sort((a, b) => a.caja_id - b.caja_id)
    .map((c) => {
      const cierre = cierres.value.find((x) => x.caja_id === c.caja_id)
      const df = datafonos.value.find((x) => x.caja_id === c.caja_id)
      return {
        ...c,
        diferencia: cierre ? Number(cierre.diferencia) : null,
        revision: cierre?.marcado_para_revision ?? false,
        datafono: df?.estado ?? null,
      }
    }),
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const [cj, ci, df, rs, ar, av] = await Promise.all([
      cajaApi.cajas(tiendaId.value).catch(() => []),
      cajaApi.cierres({ tiendaId: tiendaId.value }).catch(() => []),
      cajaApi.datafonos().catch(() => []),
      inventarioApi.stockResumen(tiendaId.value).catch(() => ({})),
      inventarioApi.alertas({ tiendaId: tiendaId.value, tipo: 'reposicion', size: 1 }).catch(() => ({ total: 0 })),
      inventarioApi.alertas({ tiendaId: tiendaId.value, tipo: 'vencimiento', size: 1 }).catch(() => ({ total: 0 })),
    ])
    cajas.value = cj
    cierres.value = ci
    datafonos.value = df
    resumen.value = rs || {}
    alertasRepos.value = ar.total ?? 0
    alertasVenc.value = av.total ?? 0
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Dashboard Operativo de Sucursal"
      :subtitulo="`Estado en vivo de la tienda #${tiendaId}: cuadre de caja, seguridad de pagos e inventario en una sola vista.`"
    >
      <template #badge>
        <SemanticChip :tipo="kpi.descuadres > 0 || kpi.quiebre > 0 ? 'fifo' : 'ok'">
          {{ kpi.descuadres > 0 || kpi.quiebre > 0 ? 'Requiere atención' : 'Operación nominal' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <RouterLink to="/caja" class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50/70">
          <Icon name="bank" :size="16" /> Cuadre de caja
        </RouterLink>
        <RouterLink to="/inventario" class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50/70">
          <Icon name="cube" :size="16" /> Inventario
        </RouterLink>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">{{ error }}</p>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <KpiTile
        label="Recaudación del turno"
        :valor="money(kpi.recaudacion)"
        variant="emerald"
        :microcopy="`${kpi.cuadradas} de ${kpi.cajas} cajas con cuadre`"
        pie-label="Diferencia neta"
        :pie-valor="(kpi.neta >= 0 ? '+' : '') + money(kpi.neta)"
      />
      <KpiTile
        label="Descuadres del día"
        :valor="kpi.descuadres.toLocaleString('es-CL')"
        :estado="kpi.descuadres > 0 ? 'revisar' : 'todo cuadra'"
        :estado-tipo="kpi.descuadres > 0 ? 'quiebre' : 'ok'"
        microcopy="Cuadres con diferencia ≠ 0"
      >
        <template #icono><Icon name="bank" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Datáfonos conformes"
        :valor="`${kpi.datafonosOk} / ${kpi.datafonosTotal}`"
        :estado="kpi.datafonosOk < kpi.datafonosTotal ? 'no conformes' : 'al día'"
        :estado-tipo="kpi.datafonosOk < kpi.datafonosTotal ? 'fifo' : 'ok'"
        microcopy="Frente al estándar de seguridad vigente"
      >
        <template #icono><Icon name="shield" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="SKUs en quiebre"
        :valor="kpi.quiebre.toLocaleString('es-CL')"
        :estado="kpi.quiebre > 0 ? 'reponer' : 'sin quiebres'"
        :estado-tipo="kpi.quiebre > 0 ? 'quiebre' : 'ok'"
        :microcopy="`${kpi.porVencer} SKUs por vencer · ${kpi.alertas} alertas pendientes`"
      >
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Tasa de merma del mes"
        :valor="kpi.tasaMerma.toFixed(2) + '%'"
        :estado="kpi.tasaMerma < 1 ? 'bajo umbral' : 'sobre umbral'"
        :estado-tipo="kpi.tasaMerma < 1 ? 'ok' : 'quiebre'"
        microcopy="Unidades mermadas validadas / stock"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="mb-6 grid gap-5 lg:grid-cols-2 xl:grid-cols-4">
      <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
        <h3 class="mb-1 font-display text-[13px] font-bold text-brand-950">Estado del stock</h3>
        <p class="mb-2 text-[11px] text-slate-500">SKUs por situación de inventario</p>
        <VChart class="h-56" :option="chartStock" autoresize />
      </div>
      <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
        <h3 class="mb-1 font-display text-[13px] font-bold text-brand-950">Diferencia de cuadre por caja</h3>
        <p class="mb-2 text-[11px] text-slate-500">Verde: cuadra · rojo: faltante · ámbar: sobrante</p>
        <VChart v-if="cierresConDif" class="h-56" :option="chartCuadre" autoresize />
        <div v-else class="grid h-56 place-items-center text-center">
          <div>
            <Icon name="check" :size="26" class="mx-auto mb-2 text-emerald-600" />
            <p class="text-[12px] font-semibold text-slate-700">Todas las cajas cuadran</p>
            <p class="text-[11px] text-slate-500">{{ cierres.length }} cuadres sin diferencia hoy</p>
          </div>
        </div>
      </div>
      <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
        <h3 class="mb-1 font-display text-[13px] font-bold text-brand-950">Alertas de inventario pendientes</h3>
        <p class="mb-2 text-[11px] text-slate-500">Generadas por los jobs diarios</p>
        <VChart class="h-56" :option="chartAlertas" autoresize />
      </div>
      <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
        <h3 class="mb-1 font-display text-[13px] font-bold text-brand-950">Conformidad de datáfonos</h3>
        <p class="mb-2 text-[11px] text-slate-500">Terminales de pago de la tienda</p>
        <VChart class="h-56" :option="chartDatafonos" autoresize />
      </div>
    </div>

    <section class="satin-card rounded-2xl p-5 shadow-card-subtle">
      <h3 class="mb-3 font-display text-base font-bold text-brand-950">Estado de sala por caja</h3>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <div
          v-for="c in salaPorCaja"
          :key="c.caja_id"
          class="rounded-xl border border-brand-200 bg-white p-3"
        >
          <div class="flex items-center justify-between">
            <span class="text-[13px] font-bold text-slate-800">{{ c.nombre }}</span>
            <SemanticChip
              :tipo="c.diferencia == null ? 'neutral' : c.revision ? 'quiebre' : 'ok'"
            >
              {{ c.diferencia == null ? 'Sin cuadre' : c.revision ? 'En revisión' : 'Cuadrada' }}
            </SemanticChip>
          </div>
          <div class="mt-2 flex items-center justify-between text-[11px] text-slate-500">
            <span>Diferencia</span>
            <span
              class="tabular-nums font-semibold"
              :class="c.diferencia == null ? 'text-slate-400' : c.diferencia === 0 ? 'text-emerald-700' : c.diferencia < 0 ? 'text-crimson-ruby' : 'text-amber-700'"
            >
              {{ c.diferencia == null ? '—' : (c.diferencia > 0 ? '+' : '') + money(c.diferencia) }}
            </span>
          </div>
          <div class="mt-1 flex items-center justify-between text-[11px] text-slate-500">
            <span>Datáfono</span>
            <span
              class="font-semibold"
              :class="c.datafono === 'activo' ? 'text-emerald-700' : c.datafono ? 'text-amber-700' : 'text-slate-400'"
            >
              {{ c.datafono === 'activo' ? 'Conforme' : c.datafono === 'requiere_actualizacion' ? 'No conforme' : c.datafono === 'fuera_servicio' ? 'Fuera de servicio' : '—' }}
            </span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
