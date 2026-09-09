<script setup>
/**
 * Clima laboral semestral y su cruce con rotación (feature 011, US3 / FR-006,
 * FR-007, FR-010). El Jefe de RRHH registra el resultado promedio por tienda y
 * periodo (`AAAA-Sn`) y ve, junto a él, la tasa de rotación del mismo periodo
 * calculada por el backend desde `empleados.fecha_baja`. Un periodo sin encuesta
 * no muestra ningún indicador — se informa como sin datos.
 */
import { computed, reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
const puedeEditar = computed(() => sesion.rol === 'Jefe_RRHH')

const nuevo = reactive({ tienda_id: '', periodo: '', resultado_promedio: '' })
const consulta = reactive({ tienda_id: '', periodo: '' })
const cruce = ref(null)
const sinDatos = ref(false)
const error = ref('')

async function registrar() {
  error.value = ''
  try {
    await rrhhApi.registrarClima({
      tiendaId: Number(nuevo.tienda_id),
      periodo: nuevo.periodo.trim(),
      resultadoPromedio: Number(nuevo.resultado_promedio),
    })
    nuevo.resultado_promedio = ''
  } catch (e) {
    error.value = e.message
  }
}

async function verCruce() {
  error.value = ''
  cruce.value = null
  sinDatos.value = false
  try {
    cruce.value = await rrhhApi.climaRotacion(Number(consulta.tienda_id), consulta.periodo.trim())
  } catch (e) {
    if (e.response?.status === 404) sinDatos.value = true
    else error.value = e.message
  }
}
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Clima laboral y rotación</h1>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form
      v-if="puedeEditar"
      class="mb-6 grid gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 sm:grid-cols-3"
      @submit.prevent="registrar"
    >
      <h2 class="col-span-full text-sm font-semibold text-on-surface">Registrar resultado</h2>
      <label class="text-xs text-on-surface-variant">
        Tienda (id)
        <input
          v-model="nuevo.tienda_id"
          type="number"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Periodo
        <input
          v-model="nuevo.periodo"
          required
          placeholder="2026-S2"
          pattern="\d{4}-S[12]"
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Resultado promedio (0–10)
        <input
          v-model="nuevo.resultado_promedio"
          type="number"
          step="0.01"
          min="0"
          max="10"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="col-span-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Registrar
      </button>
    </form>

    <form
      class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="verCruce"
    >
      <h2 class="w-full text-sm font-semibold text-on-surface">Clima vs. rotación del periodo</h2>
      <label class="text-xs text-on-surface-variant">
        Tienda (id)
        <input
          v-model="consulta.tienda_id"
          type="number"
          required
          class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Periodo
        <input
          v-model="consulta.periodo"
          required
          placeholder="2026-S2"
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Consultar
      </button>
    </form>

    <article
      v-if="cruce"
      class="grid grid-cols-2 gap-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    >
      <div>
        <p class="text-xs text-on-surface-variant">Clima laboral</p>
        <p class="text-2xl font-bold text-on-surface">
          {{ cruce.resultado_promedio ?? '—' }}
        </p>
      </div>
      <div>
        <p class="text-xs text-on-surface-variant">Tasa de rotación</p>
        <p class="text-2xl font-bold text-on-surface">
          {{ cruce.tasa_rotacion_pct === null ? 'sin datos' : `${cruce.tasa_rotacion_pct}%` }}
        </p>
      </div>
    </article>
    <p
      v-else-if="sinDatos"
      class="rounded-lg bg-surface-container-high px-4 py-2 text-sm text-on-surface-variant"
    >
      Sin datos: no hay encuesta de clima registrada para esa tienda y periodo.
    </p>
  </main>
</template>
