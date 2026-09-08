<script setup>
/**
 * US2 — cada Jefe de departamento consulta el dashboard táctico de su propio
 * departamento (el backend valida el alcance por RBAC / FR-005; el Gerente
 * General puede consultar cualquiera). Un mismo componente sirve a los 6 roles,
 * parametrizado por `modulo`. Junto a cada valor, la fecha de última publicación
 * (FR-008); los KPIs con datos insuficientes se muestran atenuados sin bloquear
 * el resto (Acceptance Scenario 3).
 */
import { onMounted, ref, watch } from 'vue'
import { tiDashboardsApi } from '@/services/tiDashboardsApi'

const MODULOS = ['Comercial', 'Marketing_CRM', 'Operaciones', 'Finanzas', 'TI', 'RRHH']

const modulo = ref(MODULOS[0])
const dashboard = ref(null)
const error = ref('')
const aviso = ref('')

function fmtFecha(iso) {
  return iso ? new Date(iso).toLocaleString() : '—'
}

async function cargar() {
  error.value = ''
  aviso.value = ''
  dashboard.value = null
  try {
    dashboard.value = await tiDashboardsApi.dashboardTactico(modulo.value)
  } catch (e) {
    if (e.status === 403) aviso.value = 'No tienes acceso al dashboard de este departamento.'
    else if (e.status === 404) aviso.value = 'Todavía no se ha publicado este dashboard táctico.'
    else error.value = e.message
  }
}

watch(modulo, cargar)
onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl space-y-6 px-6 py-8">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-primary-container">Dashboard táctico</h1>
        <p v-if="dashboard" class="mt-1 text-sm text-on-surface-variant">
          Última actualización: {{ fmtFecha(dashboard.fecha_publicacion) }}
        </p>
      </div>
      <label class="text-xs text-on-surface-variant">
        Departamento
        <select
          v-model="modulo"
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        >
          <option v-for="m in MODULOS" :key="m" :value="m">{{ m }}</option>
        </select>
      </label>
    </header>

    <p v-if="error" class="rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="rounded-lg bg-surface-container-high px-4 py-2 text-sm text-on-surface-variant"
    >
      {{ aviso }}
    </p>

    <section v-if="dashboard" class="grid gap-4 sm:grid-cols-2">
      <article
        v-for="kpi in dashboard.kpis"
        :key="kpi.nombre_kpi"
        class="rounded-xl border border-outline-variant p-4"
        :class="
          kpi.disponible ? 'bg-surface-container-lowest' : 'bg-surface-container-high opacity-70'
        "
      >
        <p class="text-sm text-on-surface">{{ kpi.nombre_kpi }}</p>
        <p v-if="kpi.disponible" class="mt-2 text-3xl font-bold text-on-surface">{{ kpi.valor }}</p>
        <p v-else class="mt-2 text-sm font-medium text-on-surface-variant">Datos insuficientes</p>
      </article>
    </section>
  </main>
</template>
