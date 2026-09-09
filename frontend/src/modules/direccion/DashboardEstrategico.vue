<script setup>
/**
 * US1 (feature 009) — el Gerente General ve, en una vista, los KPIs consolidados
 * de la red por Objetivo Estratégico, tal como los publicó el job diario
 * (FR-003/FR-008, Principio XII). Un KPI sin fuente real (OE-4) se distingue del
 * que sí tiene datos (Edge Cases). Arquetipo "Dashboard/BI" del kit.
 */
import { computed, onMounted, ref } from 'vue'
import { direccionApi } from '@/services/direccionApi'
import { formatoKpi, valorKpi } from '@/shared/kpiFormato'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'

const dashboard = ref(null)
const error = ref('')
const sinPublicacion = ref(false)
const cargando = ref(false)

const OBJETIVOS = {
  'OE-1': 'Crecimiento de ventas',
  'OE-2': 'Rentabilidad',
  'OE-3': 'Control de merma',
  'OE-4': 'Posición de mercado',
  'OE-8': 'Personas y clima',
}
const ICONO = { moneda: 'bank', indice: 'users', numero: 'chart' }

const fechaPublicacion = computed(() =>
  dashboard.value?.fecha_publicacion
    ? new Date(dashboard.value.fecha_publicacion).toLocaleString('es-EC')
    : null,
)
const disponibles = computed(() => (dashboard.value?.kpis || []).filter((k) => k.disponible).length)

async function cargar() {
  error.value = ''
  sinPublicacion.value = false
  cargando.value = true
  try {
    dashboard.value = await direccionApi.dashboardEstrategico()
  } catch (e) {
    if (e.status === 404) sinPublicacion.value = true
    else error.value = e.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Dashboard estratégico de la red"
      subtitulo="KPIs consolidados por Objetivo Estratégico, publicados por el proceso diario. La Gerencia los consulta en lectura; cada valor refleja el último cierre de datos, no el instante actual."
    >
      <template #badge>
        <SemanticChip v-if="fechaPublicacion" tipo="ok">
          Publicado {{ fechaPublicacion }}
        </SemanticChip>
        <SemanticChip tipo="neutral">
          {{ disponibles }} de {{ (dashboard?.kpis || []).length }} con fuente real
        </SemanticChip>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>

    <div
      v-if="sinPublicacion"
      class="satin-card grid place-items-center rounded-2xl p-14 text-center shadow-card-subtle"
    >
      <div>
        <Icon name="chart" :size="30" class="mx-auto mb-3 text-brand-300" />
        <p class="text-[14px] font-bold text-slate-800">Todavía no hay un dashboard publicado</p>
        <p class="mt-1 text-[12px] text-slate-500">
          El proceso diario lo genera automáticamente en el próximo ciclo.
        </p>
      </div>
    </div>

    <section v-else-if="dashboard" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <KpiTile
        v-for="(kpi, i) in dashboard.kpis"
        :key="kpi.dimension + kpi.nombre_kpi"
        :label="`${kpi.dimension} · ${OBJETIVOS[kpi.dimension] || 'Objetivo estratégico'}`"
        :valor="valorKpi(kpi) ?? 'Sin fuente real'"
        :variant="i === 0 && kpi.disponible ? 'emerald' : kpi.disponible ? 'default' : 'plain'"
        :microcopy="kpi.nombre_kpi"
        :estado="kpi.disponible ? '' : 'Fuera de alcance'"
        :estado-tipo="kpi.disponible ? 'neutral' : 'fifo'"
      >
        <template #icono><Icon :name="ICONO[formatoKpi(kpi.nombre_kpi)] || 'chart'" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="dashboard" class="mt-4 text-[11px] text-slate-400">
      OE-4 (posición de mercado / NPS) no tiene un canal de encuesta a cliente dentro del alcance del
      proyecto: se muestra sin dato en lugar de un valor inventado.
    </p>
  </div>
</template>
