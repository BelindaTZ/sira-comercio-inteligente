<script setup>
/**
 * Liquidación de categoría C (FR-011 a FR-014) y productos reclasificados del mes
 * (FR-010). El Jefe de Operaciones define el umbral y el descuento; el Encargado
 * de Tienda ejecuta los candidatos de su tienda.
 */
import { onMounted, reactive, ref } from 'vue'
import { promocionesApi } from '@/services/promocionesApi'

const tiendaId = ref(Number(localStorage.getItem('sira_tienda_id')) || 1)
const candidatos = ref([])
const cambiosAbc = ref([])
const regla = reactive({ rotacion_minima_liquidacion_semanal: '', descuento_liquidacion_pct: '' })
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const r = await promocionesApi.reglaLiquidacion()
    regla.rotacion_minima_liquidacion_semanal = r.rotacion_minima_liquidacion_semanal
    regla.descuento_liquidacion_pct = r.descuento_liquidacion_pct
    candidatos.value = await promocionesApi.candidatosLiquidacion({ tiendaId: tiendaId.value })
    cambiosAbc.value = await promocionesApi.cambiosAbc()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function guardarRegla() {
  try {
    await promocionesApi.actualizarReglaLiquidacion({
      rotacionMinima: regla.rotacion_minima_liquidacion_semanal,
      descuento: regla.descuento_liquidacion_pct,
    })
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function recalcular() {
  try {
    await promocionesApi.forzarClasificacionAbc()
    await promocionesApi.forzarCandidatos()
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function ejecutar(c) {
  try {
    await promocionesApi.ejecutarCandidato(c.candidato_id)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Liquidación de categoría C</h1>
      <div class="flex items-center gap-2">
        <input
          v-model.number="tiendaId"
          type="number"
          class="w-24 rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
          @change="cargar"
        />
        <button
          type="button"
          class="rounded-lg bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container"
          @click="recalcular"
        >
          Recalcular ABC + candidatos (dev)
        </button>
      </div>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="guardarRegla"
    >
      <label class="text-xs text-on-surface-variant">
        Rotación mínima (uds/semana)
        <input
          v-model="regla.rotacion_minima_liquidacion_semanal"
          type="number"
          step="0.1"
          class="mt-1 block w-40 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Descuento sugerido (%)
        <input
          v-model="regla.descuento_liquidacion_pct"
          type="number"
          step="1"
          class="mt-1 block w-40 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Guardar regla
      </button>
    </form>

    <div class="grid gap-6 lg:grid-cols-2">
      <section>
        <h2 class="mb-2 text-sm font-semibold text-on-surface">
          Candidatos de la tienda #{{ tiendaId }}
        </h2>
        <div
          class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-3 py-2 font-semibold">Producto</th>
                <th class="px-3 py-2 text-right font-semibold">Rotación</th>
                <th class="px-3 py-2 text-right font-semibold">Desc.</th>
                <th class="px-3 py-2 font-semibold">Estado</th>
                <th class="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
              </tr>
              <tr v-else-if="!candidatos.length">
                <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">
                  Sin candidatos esta semana
                </td>
              </tr>
              <tr
                v-for="c in candidatos"
                :key="c.candidato_id"
                class="border-b border-outline-variant last:border-0"
              >
                <td class="px-3 py-2 tabular-nums">#{{ c.product_id }}</td>
                <td class="px-3 py-2 text-right tabular-nums">
                  {{ Number(c.rotacion_reciente_calculada).toFixed(2) }}
                </td>
                <td class="px-3 py-2 text-right tabular-nums">{{ c.descuento_sugerido_pct }}%</td>
                <td class="px-3 py-2">{{ c.estado }}</td>
                <td class="px-3 py-2 text-right">
                  <button
                    v-if="c.estado === 'candidato'"
                    type="button"
                    class="rounded-lg bg-primary-container px-2 py-1 text-xs font-semibold text-on-primary-container"
                    @click="ejecutar(c)"
                  >
                    Ejecutar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 class="mb-2 text-sm font-semibold text-on-surface">Reclasificaciones ABC del mes</h2>
        <div
          class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-3 py-2 font-semibold">Producto</th>
                <th class="px-3 py-2 font-semibold">Antes</th>
                <th class="px-3 py-2 font-semibold">Ahora</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!cambiosAbc.length">
                <td colspan="3" class="px-3 py-6 text-center text-on-surface-variant">
                  Sin cambios registrados
                </td>
              </tr>
              <tr
                v-for="(c, i) in cambiosAbc"
                :key="i"
                class="border-b border-outline-variant last:border-0"
              >
                <td class="px-3 py-2 tabular-nums">#{{ c.product_id }}</td>
                <td class="px-3 py-2 text-on-surface-variant">
                  {{ c.clasificacion_anterior || '—' }}
                </td>
                <td class="px-3 py-2 font-semibold">{{ c.clasificacion_nueva }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
</template>
