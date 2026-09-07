<script setup>
/**
 * Modelos de pronóstico de demanda (FR-001 a FR-005, FR-011 a FR-013).
 *
 * El sistema entrena mensualmente; ningún modelo pasa a producción sin que el
 * Jefe de TI lo apruebe aquí (SC-002). El gráfico muestra la tendencia de
 * precisión semanal (WAPE) del modelo seleccionado con la línea del umbral de
 * degradación; una medición por encima del umbral genera alerta (FR-012/FR-013).
 */
import { computed, onMounted, ref, watch } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { forecastingApi } from '@/services/forecastingApi'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, MarkLineComponent])

const filtroEstado = ref('pendiente')
const modelos = ref([])
const seleccionado = ref(null)
const monitoreo = ref([])
const config = ref([])
const error = ref('')
const cargando = ref(false)

const umbralDegradacion = computed(() => {
  const fila = config.value.find((c) => c.clave === 'umbral_degradacion_semanal_pct')
  return fila ? Number(fila.valor) : 0.45
})

const opcionesGrafico = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 16, top: 16, bottom: 28 },
  xAxis: {
    type: 'category',
    data: monitoreo.value.map((m) => `${m.anio}-S${m.semana}`),
  },
  yAxis: { type: 'value', name: 'WAPE', min: 0 },
  series: [
    {
      type: 'line',
      smooth: true,
      data: monitoreo.value.map((m) => Number(m.metrica_precision)),
      markLine: {
        symbol: 'none',
        data: [{ yAxis: umbralDegradacion.value, name: 'Umbral' }],
        lineStyle: { type: 'dashed', color: '#b3261e' },
        label: { formatter: 'Umbral de degradación' },
      },
    },
  ],
}))

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    modelos.value = await forecastingApi.modelos(filtroEstado.value || undefined)
    config.value = await forecastingApi.configuracion()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function seleccionar(m) {
  seleccionado.value = m
  try {
    monitoreo.value = await forecastingApi.monitoreoDeModelo(m.modelo_id)
  } catch {
    monitoreo.value = []
  }
}

async function entrenar() {
  try {
    await forecastingApi.forzarEntrenamiento()
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function aprobar(m) {
  try {
    await forecastingApi.aprobarModelo(m.modelo_id)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function rechazar(m) {
  const motivo = window.prompt('Motivo del rechazo (obligatorio):')
  if (!motivo || !motivo.trim()) return
  try {
    await forecastingApi.rechazarModelo(m.modelo_id, motivo.trim())
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

watch(filtroEstado, cargar)
onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Modelos de pronóstico</h1>
      <div class="flex gap-2">
        <RouterLink
          to="/forecasting/demanda-perdida"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
        >
          Demanda perdida →
        </RouterLink>
        <button
          type="button"
          class="rounded-lg bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container"
          @click="entrenar"
        >
          Entrenar ahora (dev)
        </button>
      </div>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div class="mb-4 flex items-center gap-3">
      <select
        v-model="filtroEstado"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
      >
        <option value="pendiente">Pendientes</option>
        <option value="aprobado">Aprobado (vigente)</option>
        <option value="rechazado">Rechazados</option>
        <option value="reemplazado">Reemplazados</option>
        <option value="">Todos</option>
      </select>
    </div>

    <div class="grid gap-6 lg:grid-cols-[1fr_24rem]">
      <div
        class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
      >
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-outline-variant text-left text-on-surface-variant">
              <th class="px-4 py-2 font-semibold">Modelo</th>
              <th class="px-4 py-2 font-semibold">Entrenado</th>
              <th class="px-4 py-2 text-right font-semibold">WAPE validación</th>
              <th class="px-4 py-2 font-semibold">Estado</th>
              <th class="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            <tr v-if="cargando">
              <td colspan="5" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
            </tr>
            <tr v-else-if="!modelos.length">
              <td colspan="5" class="px-4 py-6 text-center text-on-surface-variant">Sin modelos</td>
            </tr>
            <tr
              v-for="m in modelos"
              :key="m.modelo_id"
              class="cursor-pointer border-b border-outline-variant last:border-0 hover:bg-surface-container-low"
              :class="{ 'bg-surface-container-low': seleccionado?.modelo_id === m.modelo_id }"
              @click="seleccionar(m)"
            >
              <td class="px-4 py-2 tabular-nums">#{{ m.modelo_id }}</td>
              <td class="px-4 py-2 text-on-surface-variant">
                {{ new Date(m.fecha_entrenamiento).toLocaleDateString('es-EC') }}
              </td>
              <td class="px-4 py-2 text-right tabular-nums">
                {{ m.metrica_precision_validacion ?? '—' }}
              </td>
              <td class="px-4 py-2">
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-semibold"
                  :class="{
                    'bg-secondary-container text-on-secondary-container': m.estado === 'pendiente',
                    'bg-tertiary-container text-on-tertiary-container': m.estado === 'aprobado',
                    'bg-error-container text-on-error-container': m.estado === 'rechazado',
                    'bg-surface-container-high text-on-surface-variant': m.estado === 'reemplazado',
                  }"
                >
                  {{ m.estado }}
                </span>
              </td>
              <td class="px-4 py-2 text-right">
                <div v-if="m.estado === 'pendiente'" class="flex justify-end gap-2">
                  <button
                    type="button"
                    class="rounded-lg bg-primary-container px-2 py-1 text-xs font-semibold text-on-primary-container"
                    @click.stop="aprobar(m)"
                  >
                    Aprobar
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-outline-variant px-2 py-1 text-xs font-semibold text-error"
                    @click.stop="rechazar(m)"
                  >
                    Rechazar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <aside class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
        <h2 class="mb-2 text-sm font-semibold text-on-surface">Precisión semanal en producción</h2>
        <p v-if="!seleccionado" class="text-sm text-on-surface-variant">
          Selecciona un modelo para ver la tendencia de su WAPE semanal.
        </p>
        <p v-else-if="!monitoreo.length" class="text-sm text-on-surface-variant">
          El modelo #{{ seleccionado.modelo_id }} aún no tiene mediciones de monitoreo.
        </p>
        <VChart v-else class="h-64 w-full" :option="opcionesGrafico" autoresize />
        <p
          v-if="monitoreo.some((m) => m.supero_umbral_alerta)"
          class="mt-2 rounded-lg bg-error-container px-3 py-2 text-xs font-semibold text-on-error-container"
        >
          El WAPE de al menos una semana superó el umbral de degradación — revisar el modelo.
        </p>
      </aside>
    </div>
  </main>
</template>
