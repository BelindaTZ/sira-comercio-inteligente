<script setup>
/**
 * Puestos críticos (feature 011, US1 / FR-001). El Jefe de RRHH marca o desmarca
 * un puesto como crítico para toda la red — precondición de la retención (OT-8.1)
 * y del plan de sucesión (OT-8.4). Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'

const sesion = useSesion()
const puedeEditar = computed(() => !sesion.esGerente && sesion.rol === 'Jefe_RRHH')

const puestos = ref([])
const empleados = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')
const guardando = ref(null)

const porPuesto = computed(() => {
  const m = {}
  for (const e of empleados.value) {
    if (!e.activo) continue
    m[e.puesto_id] = (m[e.puesto_id] || 0) + 1
  }
  return m
})
const kpi = computed(() => ({
  total: puestos.value.length,
  criticos: puestos.value.filter((p) => p.es_critico).length,
  personasCriticas: puestos.value
    .filter((p) => p.es_critico)
    .reduce((a, p) => a + (porPuesto.value[p.puesto_id] || 0), 0),
}))

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    ;[puestos.value, empleados.value] = await Promise.all([
      rrhhApi.listarPuestos(),
      rrhhApi.listarEmpleados(),
    ])
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function alternar(puesto) {
  guardando.value = puesto.puesto_id
  error.value = ''
  try {
    const r = await rrhhApi.marcarPuestoCritico(puesto.puesto_id, !puesto.es_critico)
    puesto.es_critico = r.es_critico
    aviso.value = `"${puesto.nombre}" ${r.es_critico ? 'marcado como crítico' : 'ya no es crítico'}.`
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = null
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1100px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Puestos críticos"
      subtitulo="Un puesto crítico para la red condiciona el seguimiento de retención (OT-8.1) y el plan de sucesión (OT-8.4). La marca la define el Jefe de RRHH (FR-001)."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.criticos > 0 ? 'fifo' : 'ok'">
          {{ kpi.criticos }} de {{ kpi.total }} marcados como críticos
        </SemanticChip>
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
      <button class="text-brand-600 hover:text-brand-900" @click="aviso = ''"><Icon name="x" :size="14" /></button>
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-3">
      <KpiTile label="Puestos definidos" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile label="Marcados como críticos" :valor="kpi.criticos.toLocaleString('es-EC')" estado-tipo="fifo">
        <template #icono><Icon name="shield" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Personas en puestos críticos"
        :valor="kpi.personasCriticas.toLocaleString('es-EC')"
        estado-tipo="neutral"
        microcopy="Empleados activos en un puesto marcado como crítico"
      >
        <template #icono><Icon name="users" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <table class="w-full text-left text-[13px]">
        <thead>
          <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
            <th class="px-5 py-3">Puesto</th>
            <th class="px-4 py-3 text-right">Personas activas</th>
            <th class="px-4 py-3 text-center">Crítico</th>
            <th v-if="puedeEditar" class="px-4 py-3 text-right" />
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100/90 bg-white/80">
          <tr v-if="cargando"><td :colspan="puedeEditar ? 4 : 3" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
          <tr v-else-if="!puestos.length"><td :colspan="puedeEditar ? 4 : 3" class="px-5 py-8 text-center text-slate-400">Sin puestos definidos.</td></tr>
          <tr v-for="p in puestos" :key="p.puesto_id" class="hover:bg-brand-50/70">
            <td class="px-5 py-3">
              <div class="text-[13px] font-semibold text-slate-800">{{ p.nombre }}</div>
              <div v-if="p.descripcion" class="text-[11px] text-slate-400">{{ p.descripcion }}</div>
            </td>
            <td class="px-4 py-3 text-right tabular-nums text-slate-700">{{ porPuesto[p.puesto_id] || 0 }}</td>
            <td class="px-4 py-3 text-center">
              <SemanticChip :tipo="p.es_critico ? 'fifo' : 'neutral'">
                {{ p.es_critico ? 'crítico' : 'estándar' }}
              </SemanticChip>
            </td>
            <td v-if="puedeEditar" class="px-4 py-3 text-right">
              <Btn
                :variant="p.es_critico ? 'ghost' : 'primary'"
                class="!px-2.5 !py-1 !text-[12px]"
                :disabled="guardando === p.puesto_id"
                @click="alternar(p)"
              >
                {{ p.es_critico ? 'Quitar marca' : 'Marcar crítico' }}
              </Btn>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
