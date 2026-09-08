<script setup>
/**
 * Umbral de merma aceptable por categoría (FR-017) y seguimiento semanal
 * (FR-018, FR-019). El Jefe de Operaciones define el umbral; el Encargado de
 * Tienda ve el porcentaje de merma acumulada frente a ese umbral. Superar el
 * umbral es una alerta de gestión — nunca bloquea ninguna operación.
 */
import { onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'

const iso = (() => {
  const d = new Date()
  const day = (d.getUTCDay() + 6) % 7
  d.setUTCDate(d.getUTCDate() - day + 3)
  const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4))
  const week = 1 + Math.round((d - firstThursday) / 604800000)
  return { anio: d.getUTCFullYear(), semana: week }
})()

const tiendaId = ref(Number(localStorage.getItem('sira_tienda_id')) || 1)
const filtro = reactive({ semana: iso.semana, anio: iso.anio })
const umbrales = ref([])
const seguimiento = ref([])
const nuevoUmbral = reactive({ product_category: '', porcentaje_umbral: '' })
const error = ref('')
const cargando = ref(false)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    umbrales.value = await cajaApi.umbralesMerma()
    seguimiento.value = await cajaApi.seguimientoMermaSemanal(tiendaId.value, {
      semana: filtro.semana,
      anio: filtro.anio,
    })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function definirUmbral() {
  error.value = ''
  try {
    await cajaApi.definirUmbralMerma(nuevoUmbral.product_category, nuevoUmbral.porcentaje_umbral)
    nuevoUmbral.product_category = ''
    nuevoUmbral.porcentaje_umbral = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Seguimiento de merma</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="definirUmbral"
    >
      <h2 class="w-full text-sm font-semibold text-on-surface">Definir umbral de una categoría</h2>
      <label class="text-xs text-on-surface-variant">
        Categoría
        <input
          v-model="nuevoUmbral.product_category"
          type="text"
          required
          class="mt-1 block w-48 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Umbral (%)
        <input
          v-model="nuevoUmbral.porcentaje_umbral"
          type="number"
          step="0.1"
          min="0.1"
          max="100"
          required
          class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Guardar
      </button>
    </form>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <label class="text-xs text-on-surface-variant">
        Tienda
        <input
          v-model.number="tiendaId"
          type="number"
          class="mt-1 block w-24 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Semana ISO
        <input
          v-model.number="filtro.semana"
          type="number"
          min="1"
          max="53"
          class="mt-1 block w-20 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Año
        <input
          v-model.number="filtro.anio"
          type="number"
          class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="button"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
        @click="cargar"
      >
        Consultar
      </button>
    </div>

    <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-3 py-2 font-semibold">Categoría</th>
            <th class="px-3 py-2 text-right font-semibold">Merma acumulada</th>
            <th class="px-3 py-2 text-right font-semibold">Umbral</th>
            <th class="px-3 py-2 font-semibold">Estado</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="4" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!seguimiento.length">
            <td colspan="4" class="px-3 py-6 text-center text-on-surface-variant">
              Sin umbrales definidos o sin datos de la semana
            </td>
          </tr>
          <tr
            v-for="s in seguimiento"
            :key="s.product_category"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-3 py-2">{{ s.product_category }}</td>
            <td class="px-3 py-2 text-right tabular-nums">
              {{ s.porcentaje_merma_acumulado == null ? '—' : `${s.porcentaje_merma_acumulado}%` }}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">{{ s.porcentaje_umbral }}%</td>
            <td class="px-3 py-2">
              <span
                v-if="s.supera_umbral"
                class="rounded-md bg-error-container px-2 py-0.5 text-xs font-semibold text-on-error-container"
              >
                Sobre el umbral
              </span>
              <span v-else class="text-xs text-on-surface-variant">Dentro del umbral</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="mt-3 text-xs text-on-surface-variant">
      Superar el umbral es una alerta de gestión: no bloquea ventas, recepciones ni registro de mermas.
    </p>
  </main>
</template>
