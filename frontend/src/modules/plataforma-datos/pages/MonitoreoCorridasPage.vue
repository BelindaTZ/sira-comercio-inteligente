<script setup>
/**
 * US2 / US3 (feature 010) — el Jefe de TI monitorea el resultado de cada corrida
 * de carga hacia el warehouse (filas cargadas, filas con error, duración, estado)
 * y consulta los registros de calidad señalados (SC-004). Arquetipo "Gestión".
 */
import { computed, onMounted, ref } from 'vue'
import { plataformaDatosApi } from '@/services/plataformaDatosApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'

const corridas = ref([])
const entidades = ref([])
const error = ref('')
const aviso = ref('')
const cargando = ref(false)
const filtroEntidad = ref('')
const filtroEstado = ref('')
const calidadAbierta = ref(null)
const registrosCalidad = ref([])
const esDesarrollo = import.meta.env.DEV

const CHIP = { exitosa: 'ok', fallida: 'quiebre', en_progreso: 'fifo' }
const kpi = computed(() => ({
  total: corridas.value.length,
  exitosas: corridas.value.filter((c) => c.estado === 'exitosa').length,
  fallidas: corridas.value.filter((c) => c.estado === 'fallida').length,
  filasError: corridas.value.reduce((a, c) => a + (c.filas_error || 0), 0),
}))
const entidadesActivas = computed(() => entidades.value.filter((e) => e.activa))

async function cargar() {
  error.value = ''
  cargando.value = true
  try {
    ;[corridas.value, entidades.value] = await Promise.all([
      plataformaDatosApi.corridas({
        entidadId: filtroEntidad.value || undefined,
        estado: filtroEstado.value || undefined,
      }),
      entidades.value.length ? Promise.resolve(entidades.value) : plataformaDatosApi.modelo(),
    ])
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function verCalidad(corrida) {
  if (calidadAbierta.value === corrida.corrida_id) {
    calidadAbierta.value = null
    return
  }
  try {
    const data = await plataformaDatosApi.calidadDeCorrida(corrida.corrida_id)
    registrosCalidad.value = data.registros
    calidadAbierta.value = corrida.corrida_id
  } catch (e) {
    error.value = e.message
  }
}

async function forzar(entidadId, tipoCarga) {
  error.value = ''
  try {
    await plataformaDatosApi.forzarCorrida({ entidadId, tipoCarga })
    aviso.value = 'Corrida forzada. Se actualizará el listado al terminar.'
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Monitoreo de corridas de carga"
      subtitulo="Resultado de cada carga desde el operativo hacia el warehouse: filas cargadas, filas con error, duración y estado, sin depender de los logs de Airflow (SC-004)."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.fallidas > 0 ? 'quiebre' : 'ok'">
          {{ kpi.fallidas > 0 ? `${kpi.fallidas} corridas fallidas` : 'Sin corridas fallidas' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="filter" :size="14" class="text-brand-700" />
          <select v-model="filtroEntidad" class="bg-transparent text-slate-800 focus:outline-none" @change="cargar">
            <option value="">Todas las entidades</option>
            <option v-for="e in entidades" :key="e.entidad_id" :value="e.entidad_id">
              {{ e.nombre_entidad }}
            </option>
          </select>
        </label>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <select v-model="filtroEstado" class="bg-transparent text-slate-800 focus:outline-none" @change="cargar">
            <option value="">Todos los estados</option>
            <option value="en_progreso">En progreso</option>
            <option value="exitosa">Exitosa</option>
            <option value="fallida">Fallida</option>
          </select>
        </label>
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

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile label="Corridas registradas" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile label="Exitosas" :valor="kpi.exitosas.toLocaleString('es-EC')" estado-tipo="ok">
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Fallidas"
        :valor="kpi.fallidas.toLocaleString('es-EC')"
        :estado-tipo="kpi.fallidas > 0 ? 'quiebre' : 'ok'"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Filas con error"
        :valor="kpi.filasError.toLocaleString('es-EC')"
        :estado-tipo="kpi.filasError > 0 ? 'fifo' : 'ok'"
      >
        <template #icono><Icon name="database" :size="16" /></template>
      </KpiTile>
    </section>

    <section
      v-if="esDesarrollo && entidadesActivas.length"
      class="mb-6 rounded-2xl border border-amethyst-200 bg-orchid-soft/40 p-4"
    >
      <h2 class="mb-2 text-[12px] font-bold uppercase tracking-wide text-amethyst-800">
        Forzar corrida (sólo desarrollo)
      </h2>
      <div class="flex flex-wrap gap-2">
        <Btn
          v-for="e in entidadesActivas"
          :key="e.entidad_id"
          variant="ghost"
          class="!py-1 !text-[12px]"
          @click="forzar(e.entidad_id, 'incremental')"
        >
          <Icon name="bolt" :size="13" /> {{ e.nombre_entidad }} · incremental
        </Btn>
      </div>
    </section>

    <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[820px] text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-5 py-3">#</th>
              <th class="px-4 py-3">Entidad</th>
              <th class="px-4 py-3">Tipo</th>
              <th class="px-4 py-3 text-center">Estado</th>
              <th class="px-4 py-3 text-right">Cargadas</th>
              <th class="px-4 py-3 text-right">Con error</th>
              <th class="px-4 py-3 text-right">Duración</th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="cargando"><td colspan="8" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
            <tr v-else-if="!corridas.length"><td colspan="8" class="px-5 py-8 text-center text-slate-400">Todavía no hay corridas registradas.</td></tr>
            <template v-for="c in corridas" :key="c.corrida_id">
              <tr class="hover:bg-brand-50/70">
                <td class="px-5 py-2.5 font-mono text-[12px] text-slate-500">{{ c.corrida_id }}</td>
                <td class="px-4 py-2.5 font-semibold text-slate-800">{{ c.nombre_entidad }}</td>
                <td class="px-4 py-2.5 text-slate-600">{{ c.tipo_carga }}</td>
                <td class="px-4 py-2.5 text-center">
                  <SemanticChip :tipo="CHIP[c.estado] || 'neutral'">{{ c.estado }}</SemanticChip>
                </td>
                <td class="px-4 py-2.5 text-right tabular-nums text-slate-700">
                  {{ c.filas_cargadas != null ? c.filas_cargadas.toLocaleString('es-EC') : '—' }}
                </td>
                <td
                  class="px-4 py-2.5 text-right tabular-nums font-bold"
                  :class="c.filas_error > 0 ? 'text-crimson-ruby' : 'text-slate-400'"
                >
                  {{ c.filas_error }}
                </td>
                <td class="px-4 py-2.5 text-right tabular-nums text-slate-500">
                  {{ c.duracion_segundos != null ? `${c.duracion_segundos}s` : '—' }}
                </td>
                <td class="px-4 py-2.5 text-right">
                  <button
                    v-if="c.filas_error > 0"
                    type="button"
                    class="text-[12px] font-semibold text-brand-700 hover:underline"
                    @click="verCalidad(c)"
                  >
                    {{ calidadAbierta === c.corrida_id ? 'Ocultar' : 'Ver calidad' }}
                  </button>
                </td>
              </tr>
              <tr v-if="calidadAbierta === c.corrida_id" class="bg-rose-50/50">
                <td colspan="8" class="px-5 py-3">
                  <ul class="space-y-1 text-[12px] text-slate-600">
                    <li v-for="(r, i) in registrosCalidad" :key="i" class="flex gap-2">
                      <Icon name="alert" :size="13" class="mt-0.5 shrink-0 text-rose-500" />
                      <span>
                        <span class="font-semibold text-slate-800">{{ r.descripcion_problema }}</span>
                        <span v-if="r.identificador_registro" class="text-slate-400"> · {{ r.identificador_registro }}</span>
                      </span>
                    </li>
                    <li v-if="!registrosCalidad.length">Sin registros de calidad.</li>
                  </ul>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
