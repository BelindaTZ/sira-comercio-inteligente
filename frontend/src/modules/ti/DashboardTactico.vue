<script setup>
/**
 * US2 (feature 009) — cada Jefe de departamento consulta el dashboard táctico de
 * su propio departamento (el backend valida el alcance por RBAC / FR-005; el
 * Gerente General puede consultar cualquiera). Un mismo componente sirve a los 6
 * roles, parametrizado por `modulo`. Los KPIs con datos insuficientes se muestran
 * atenuados sin bloquear el resto (Acceptance Scenario 3). Arquetipo "Dashboard".
 */
import { computed, onMounted, ref, watch } from 'vue'
import { tiDashboardsApi } from '@/services/tiDashboardsApi'
import { useSesion } from '@/stores/sesion'
import { formatoKpi, valorKpi } from '@/shared/kpiFormato'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'

const MODULOS = [
  { id: 'Comercial', label: 'Comercial' },
  { id: 'Marketing_CRM', label: 'Marketing & CRM' },
  { id: 'Operaciones', label: 'Operaciones' },
  { id: 'Finanzas', label: 'Finanzas' },
  { id: 'TI', label: 'Tecnología' },
  { id: 'RRHH', label: 'Recursos Humanos' },
]
const ICONO = { moneda: 'bank', indice: 'users', numero: 'chart' }

const sesion = useSesion()
const modulo = ref(sesion.miModulo || MODULOS[0].id)
const dashboard = ref(null)
const error = ref('')
const aviso = ref('')
const cargando = ref(false)

const moduloLabel = computed(() => MODULOS.find((m) => m.id === modulo.value)?.label || modulo.value)
const fechaPublicacion = computed(() =>
  dashboard.value?.fecha_publicacion
    ? new Date(dashboard.value.fecha_publicacion).toLocaleString('es-EC')
    : null,
)

async function cargar() {
  error.value = ''
  aviso.value = ''
  dashboard.value = null
  cargando.value = true
  try {
    dashboard.value = await tiDashboardsApi.dashboardTactico(modulo.value)
  } catch (e) {
    if (e.status === 403) aviso.value = 'No tienes acceso al dashboard de este departamento.'
    else if (e.status === 404) aviso.value = 'Todavía no se ha publicado este dashboard táctico.'
    else error.value = e.message
  } finally {
    cargando.value = false
  }
}

watch(modulo, cargar)
onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      :titulo="`Dashboard táctico · ${moduloLabel}`"
      subtitulo="KPIs operativos del departamento, publicados por el proceso diario. Cada Jefe ve el suyo; la Gerencia puede alternar entre departamentos."
    >
      <template #badge>
        <SemanticChip v-if="fechaPublicacion" tipo="ok">Publicado {{ fechaPublicacion }}</SemanticChip>
      </template>
      <template #acciones>
        <label
          v-if="sesion.esGerente"
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="filter" :size="14" class="text-brand-700" />
          <select v-model="modulo" class="bg-transparent text-slate-800 focus:outline-none">
            <option v-for="m in MODULOS" :key="m.id" :value="m.id">{{ m.label }}</option>
          </select>
        </label>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-4 flex items-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800"
    >
      <Icon name="alert" :size="16" class="text-brand-600" /> {{ aviso }}
    </p>

    <section v-if="dashboard && dashboard.kpis.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <KpiTile
        v-for="(kpi, i) in dashboard.kpis"
        :key="kpi.nombre_kpi"
        :label="kpi.nombre_kpi"
        :valor="valorKpi(kpi) ?? 'Datos insuficientes'"
        :variant="i === 0 && kpi.disponible ? 'emerald' : kpi.disponible ? 'default' : 'plain'"
        :estado="kpi.disponible ? '' : 'Sin datos suficientes'"
        :estado-tipo="kpi.disponible ? 'neutral' : 'fifo'"
      >
        <template #icono><Icon :name="ICONO[formatoKpi(kpi.nombre_kpi)] || 'chart'" :size="16" /></template>
      </KpiTile>
    </section>
  </div>
</template>
