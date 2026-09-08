<script setup>
/**
 * US2 / US3 — el Jefe de TI monitorea el resultado de cada corrida de carga
 * (filas cargadas, filas con error, duración, estado) y consulta los registros
 * de calidad señalados, sin depender de los logs de Airflow (SC-004).
 */
import { computed, onMounted, ref } from 'vue'
import { plataformaDatosApi } from '@/services/plataformaDatosApi'

const corridas = ref([])
const entidades = ref([])
const error = ref('')
const filtroEntidad = ref('')
const filtroEstado = ref('')
const calidadAbierta = ref(null)
const registrosCalidad = ref([])

const esDesarrollo = import.meta.env.DEV

async function cargar() {
  error.value = ''
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
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

const entidadesActivas = computed(() => entidades.value.filter((e) => e.activa))

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-6 px-6 py-8">
    <header>
      <h1 class="text-2xl font-bold text-primary-container">Monitoreo de corridas</h1>
      <p class="mt-1 text-sm text-on-surface-variant">
        Resultado de cada carga desde el operativo hacia el warehouse.
      </p>
    </header>

    <p
      v-if="error"
      class="rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div class="flex flex-wrap items-end gap-3">
      <label class="text-xs text-on-surface-variant">
        Entidad
        <select
          v-model="filtroEntidad"
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          @change="cargar"
        >
          <option value="">Todas</option>
          <option v-for="e in entidades" :key="e.entidad_id" :value="e.entidad_id">
            {{ e.nombre_entidad }}
          </option>
        </select>
      </label>
      <label class="text-xs text-on-surface-variant">
        Estado
        <select
          v-model="filtroEstado"
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          @change="cargar"
        >
          <option value="">Todos</option>
          <option value="en_progreso">en progreso</option>
          <option value="exitosa">exitosa</option>
          <option value="fallida">fallida</option>
        </select>
      </label>
    </div>

    <section
      v-if="esDesarrollo && entidadesActivas.length"
      class="rounded-xl border border-outline-variant p-4"
    >
      <h2 class="mb-2 text-sm font-semibold text-on-surface">Forzar corrida (sólo desarrollo)</h2>
      <div class="flex flex-wrap gap-2">
        <template v-for="e in entidadesActivas" :key="e.entidad_id">
          <button
            class="rounded-lg border border-outline-variant px-3 py-1 text-xs text-on-surface"
            @click="forzar(e.entidad_id, 'incremental')"
          >
            {{ e.nombre_entidad }} · incremental
          </button>
        </template>
      </div>
    </section>

    <div class="overflow-x-auto">
      <table v-if="corridas.length" class="w-full text-sm">
        <thead class="text-left text-xs text-on-surface-variant">
          <tr>
            <th class="py-1">#</th>
            <th class="py-1">Entidad</th>
            <th class="py-1">Tipo</th>
            <th class="py-1">Estado</th>
            <th class="py-1 text-right">Cargadas</th>
            <th class="py-1 text-right">Con error</th>
            <th class="py-1 text-right">Duración (s)</th>
            <th class="py-1" />
          </tr>
        </thead>
        <tbody>
          <template v-for="c in corridas" :key="c.corrida_id">
            <tr class="border-t border-outline-variant">
              <td class="py-1.5 text-on-surface-variant">{{ c.corrida_id }}</td>
              <td class="py-1.5 text-on-surface">{{ c.nombre_entidad }}</td>
              <td class="py-1.5 text-on-surface-variant">{{ c.tipo_carga }}</td>
              <td class="py-1.5">
                <span
                  :class="{
                    'text-on-surface': c.estado === 'exitosa',
                    'text-on-error-container': c.estado === 'fallida',
                    'text-on-surface-variant': c.estado === 'en_progreso',
                  }"
                >
                  {{ c.estado }}
                </span>
              </td>
              <td class="py-1.5 text-right text-on-surface">{{ c.filas_cargadas ?? '—' }}</td>
              <td
                class="py-1.5 text-right"
                :class="c.filas_error > 0 ? 'text-on-error-container' : 'text-on-surface-variant'"
              >
                {{ c.filas_error }}
              </td>
              <td class="py-1.5 text-right text-on-surface-variant">
                {{ c.duracion_segundos ?? '—' }}
              </td>
              <td class="py-1.5 text-right">
                <button
                  v-if="c.filas_error > 0"
                  class="text-xs text-primary underline"
                  @click="verCalidad(c)"
                >
                  {{ calidadAbierta === c.corrida_id ? 'ocultar' : 'ver calidad' }}
                </button>
              </td>
            </tr>
            <tr v-if="calidadAbierta === c.corrida_id" class="bg-surface-variant/40">
              <td colspan="8" class="px-3 py-2">
                <ul class="space-y-1 text-xs text-on-surface-variant">
                  <li v-for="(r, i) in registrosCalidad" :key="i">
                    <span class="text-on-surface">{{ r.descripcion_problema }}</span>
                    <span v-if="r.identificador_registro"> · {{ r.identificador_registro }}</span>
                  </li>
                  <li v-if="!registrosCalidad.length">Sin registros de calidad.</li>
                </ul>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-else class="text-sm text-on-surface-variant">Todavía no hay corridas registradas.</p>
    </div>
  </main>
</template>
