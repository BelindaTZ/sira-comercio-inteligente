<script setup>
/**
 * US1 — el Gerente General consulta, en una sola vista, los KPIs consolidados de
 * la red por Objetivo Estratégico, actualizados por el job diario. Junto a cada
 * valor se muestra la fecha de la última publicación (FR-003, FR-008, Principio
 * XII); un KPI sin fuente real (OE-4) se distingue visualmente del que sí tiene
 * datos (Edge Cases).
 */
import { onMounted, ref } from 'vue'
import { direccionApi } from '@/services/direccionApi'

const dashboard = ref(null)
const error = ref('')
const sinPublicacion = ref(false)

function fmtFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

async function cargar() {
  error.value = ''
  sinPublicacion.value = false
  try {
    dashboard.value = await direccionApi.dashboardEstrategico()
  } catch (e) {
    if (e.status === 404) sinPublicacion.value = true
    else error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl space-y-6 px-6 py-8">
    <header>
      <h1 class="text-2xl font-bold text-primary-container">Dashboard estratégico</h1>
      <p v-if="dashboard" class="mt-1 text-sm text-on-surface-variant">
        Última actualización: {{ fmtFecha(dashboard.fecha_publicacion) }}
      </p>
    </header>

    <p v-if="error" class="rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <p
      v-if="sinPublicacion"
      class="rounded-lg bg-surface-container-high px-4 py-2 text-sm text-on-surface-variant"
    >
      Todavía no se ha publicado ningún dashboard estratégico.
    </p>

    <section v-if="dashboard" class="grid gap-4 sm:grid-cols-2">
      <article
        v-for="kpi in dashboard.kpis"
        :key="kpi.dimension + kpi.nombre_kpi"
        class="rounded-xl border border-outline-variant p-4"
        :class="
          kpi.disponible ? 'bg-surface-container-lowest' : 'bg-surface-container-high opacity-70'
        "
      >
        <p class="text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
          {{ kpi.dimension }}
        </p>
        <p class="mt-1 text-sm text-on-surface">{{ kpi.nombre_kpi }}</p>
        <p v-if="kpi.disponible" class="mt-2 text-3xl font-bold text-on-surface">
          {{ kpi.valor }}
        </p>
        <p v-else class="mt-2 text-sm font-medium text-on-surface-variant">
          Dato no disponible — sin fuente real
        </p>
      </article>
    </section>
  </main>
</template>
