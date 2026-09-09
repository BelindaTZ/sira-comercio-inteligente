<script setup>
/**
 * US3 (feature 009) — el Jefe de TI revisa qué dashboards operativos de tienda
 * (alertas de reposición, cuadre de caja, seguimiento de merma) están al día para
 * toda la red y cuáles llevan más de un día sin actualizarse (FR-007). Arquetipo
 * "Gestión" del kit.
 */
import { computed, onMounted, ref } from 'vue'
import { tiDashboardsApi } from '@/services/tiDashboardsApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'

const verificacion = ref(null)
const soloAlertas = ref(false)
const error = ref('')
const aviso = ref('')
const cargando = ref(false)

const fmtFecha = (s) => (s ? new Date(s).toLocaleString('es-EC') : 'sin dato')

const todas = computed(() => verificacion.value?.estado_por_tienda ?? [])
const filas = computed(() =>
  soloAlertas.value ? todas.value.filter((f) => !f.disponible) : todas.value,
)
const kpi = computed(() => {
  const alerta = todas.value.filter((f) => !f.disponible).length
  return {
    total: todas.value.length,
    alerta,
    alDia: todas.value.length - alerta,
    tiendas: new Set(todas.value.map((f) => f.tienda_id)).size,
  }
})

async function cargar() {
  error.value = ''
  aviso.value = ''
  cargando.value = true
  try {
    verificacion.value = await tiDashboardsApi.verificacionOperativos()
  } catch (e) {
    if (e.status === 404) aviso.value = 'Todavía no se ha ejecutado la verificación diaria.'
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
      titulo="Disponibilidad de dashboards operativos"
      subtitulo="Estado por tienda de los dashboards operativos (reposición, cuadre de caja, merma). Un dashboard con más de un día sin actualizarse se marca como alerta (FR-007)."
    >
      <template #badge>
        <SemanticChip v-if="verificacion" :tipo="kpi.alerta > 0 ? 'quiebre' : 'ok'">
          Verificado {{ fmtFecha(verificacion.fecha_verificacion) }}
        </SemanticChip>
      </template>
      <template #acciones>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <input v-model="soloAlertas" type="checkbox" /> Sólo alertas
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

    <section v-if="verificacion" class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile label="Dashboards al día" :valor="kpi.alDia.toLocaleString('es-EC')" variant="emerald" :microcopy="`${kpi.tiendas} tiendas`" />
      <KpiTile
        label="Desactualizados"
        :valor="kpi.alerta.toLocaleString('es-EC')"
        :estado-tipo="kpi.alerta > 0 ? 'quiebre' : 'ok'"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Total verificados" :valor="kpi.total.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Cobertura"
        :valor="kpi.total ? `${Math.round((kpi.alDia / kpi.total) * 100)}%` : '—'"
        estado-tipo="neutral"
        microcopy="Dashboards al día sobre el total"
      >
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
    </section>

    <div v-if="verificacion" class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[640px] text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-5 py-3">Tienda</th>
              <th class="px-4 py-3">Dashboard</th>
              <th class="px-4 py-3">Última actualización</th>
              <th class="px-4 py-3 text-center">Estado</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="cargando"><td colspan="4" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
            <tr v-else-if="!filas.length">
              <td colspan="4" class="px-5 py-8 text-center text-slate-400">
                {{ soloAlertas ? 'Ningún dashboard operativo con alerta.' : 'Sin filas.' }}
              </td>
            </tr>
            <tr
              v-for="f in filas"
              :key="f.tienda_id + f.nombre_dashboard"
              class="hover:bg-brand-50/70"
              :class="{ 'bg-rose-50/60': !f.disponible }"
            >
              <td class="px-5 py-2.5 font-mono text-[12px] font-semibold text-brand-800">#{{ f.tienda_id }}</td>
              <td class="px-4 py-2.5 text-slate-700">{{ f.nombre_dashboard }}</td>
              <td class="px-4 py-2.5 tabular-nums text-[12px] text-slate-500">
                {{ fmtFecha(f.fecha_ultima_actualizacion) }}
              </td>
              <td class="px-4 py-2.5 text-center">
                <SemanticChip :tipo="f.disponible ? 'ok' : 'quiebre'">
                  {{ f.disponible ? 'al día' : 'desactualizado' }}
                </SemanticChip>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
