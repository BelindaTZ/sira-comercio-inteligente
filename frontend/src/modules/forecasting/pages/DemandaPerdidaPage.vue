<script setup>
/**
 * FR-014 — reporte mensual de demanda perdida por quiebre de stock, desglosado
 * por tienda y categoría de producto (consolida `eventos_quiebre_stock` de 001).
 * Una tienda/categoría sin eventos simplemente no aparece.
 */
import { computed, onMounted, ref } from 'vue'
import { forecastingApi } from '@/services/forecastingApi'

const hoy = new Date()
const mes = ref(`${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`)
const filas = ref([])
const cargando = ref(false)
const error = ref('')

const rango = computed(() => {
  const [y, m] = mes.value.split('-').map(Number)
  const finMes = new Date(y, m, 0).getDate()
  return {
    desde: `${y}-${String(m).padStart(2, '0')}-01`,
    hasta: `${y}-${String(m).padStart(2, '0')}-${finMes}`,
  }
})

const totalPerdida = computed(() =>
  filas.value.reduce((acc, f) => acc + Number(f.demanda_estimada_no_satisfecha || 0), 0)
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    filas.value = await forecastingApi.demandaPerdida({
      fechaDesde: rango.value.desde,
      fechaHasta: rango.value.hasta,
    })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Demanda perdida</h1>
      <RouterLink
        to="/forecasting"
        class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
      >
        ← Modelos
      </RouterLink>
    </div>

    <div class="mb-4 flex items-center gap-3">
      <input
        v-model="mes"
        type="month"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
        @change="cargar"
      />
      <button
        type="button"
        class="rounded-lg bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container"
        @click="cargar"
      >
        Generar
      </button>
      <span class="text-sm text-on-surface-variant">
        Total estimado no satisfecho: <strong class="text-on-surface">{{ totalPerdida }}</strong>
      </span>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div
      class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
    >
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-4 py-2 font-semibold">Tienda</th>
            <th class="px-4 py-2 font-semibold">Categoría</th>
            <th class="px-4 py-2 text-right font-semibold">Eventos de quiebre</th>
            <th class="px-4 py-2 text-right font-semibold">Demanda estimada no satisfecha</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!filas.length">
            <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">
              Sin eventos de quiebre de stock en el mes
            </td>
          </tr>
          <tr
            v-for="(f, i) in filas"
            :key="`${f.tienda_id}-${f.product_category}-${i}`"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-4 py-2 tabular-nums">#{{ f.tienda_id }}</td>
            <td class="px-4 py-2">{{ f.product_category }}</td>
            <td class="px-4 py-2 text-right tabular-nums">{{ f.cantidad_eventos }}</td>
            <td class="px-4 py-2 text-right font-semibold tabular-nums">
              {{ f.demanda_estimada_no_satisfecha }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
