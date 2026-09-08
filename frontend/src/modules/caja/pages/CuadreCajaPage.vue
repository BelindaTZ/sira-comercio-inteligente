<script setup>
/**
 * Cuadre de caja horario (FR-001 a FR-005). El Cajero registra la apertura y el
 * cuadre; el sistema calcula la diferencia server-side (Principio V — aquí no se
 * resta nada). El Encargado de Tienda ve el estado de todas las cajas de su
 * tienda en una sola consulta.
 */
import { onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'

const tiendaId = ref(Number(localStorage.getItem('sira_tienda_id')) || 1)
const apertura = reactive({ caja_id: '', fondo_inicial: '' })
const cuadre = reactive({ caja_id: '', total_registrado: '' })
const ultimoCierre = ref(null)
const cierres = ref([])
const error = ref('')
const cargando = ref(false)

function claseDiferencia(dif) {
  const n = Number(dif)
  if (n === 0) return 'bg-tertiary-container text-on-tertiary-container'
  return n < 0
    ? 'bg-error-container text-on-error-container'
    : 'bg-primary-container text-on-primary-container'
}

async function cargarCierres() {
  cargando.value = true
  error.value = ''
  try {
    cierres.value = await cajaApi.cierres({ tiendaId: tiendaId.value })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function registrarApertura() {
  error.value = ''
  try {
    await cajaApi.registrarApertura({
      cajaId: Number(apertura.caja_id),
      fondoInicial: apertura.fondo_inicial,
    })
    apertura.fondo_inicial = ''
  } catch (e) {
    error.value = e.message
  }
}

async function registrarCuadre() {
  error.value = ''
  try {
    ultimoCierre.value = await cajaApi.registrarCierre({
      cajaId: Number(cuadre.caja_id),
      totalRegistrado: cuadre.total_registrado,
    })
    cuadre.total_registrado = ''
    await cargarCierres()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargarCierres)
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Cuadre de caja</h1>
      <input
        v-model.number="tiendaId"
        type="number"
        aria-label="Tienda"
        class="w-24 rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
        @change="cargarCierres"
      />
    </div>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <div class="mb-8 grid gap-4 md:grid-cols-2">
      <form
        class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
        @submit.prevent="registrarApertura"
      >
        <h2 class="mb-3 text-sm font-semibold text-on-surface">Apertura de caja</h2>
        <div class="flex flex-wrap items-end gap-3">
          <label class="text-xs text-on-surface-variant">
            Caja
            <input
              v-model="apertura.caja_id"
              type="number"
              required
              class="mt-1 block w-24 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
            />
          </label>
          <label class="text-xs text-on-surface-variant">
            Fondo inicial
            <input
              v-model="apertura.fondo_inicial"
              type="number"
              step="0.01"
              required
              class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
            />
          </label>
          <button
            type="submit"
            class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
          >
            Abrir
          </button>
        </div>
      </form>

      <form
        class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
        @submit.prevent="registrarCuadre"
      >
        <h2 class="mb-3 text-sm font-semibold text-on-surface">Cuadre horario</h2>
        <div class="flex flex-wrap items-end gap-3">
          <label class="text-xs text-on-surface-variant">
            Caja
            <input
              v-model="cuadre.caja_id"
              type="number"
              required
              class="mt-1 block w-24 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
            />
          </label>
          <label class="text-xs text-on-surface-variant">
            Total contado
            <input
              v-model="cuadre.total_registrado"
              type="number"
              step="0.01"
              required
              class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
            />
          </label>
          <button
            type="submit"
            class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
          >
            Cuadrar
          </button>
        </div>
        <p
          v-if="ultimoCierre"
          class="mt-3 flex items-center gap-2 text-sm text-on-surface-variant"
        >
          Esperado {{ ultimoCierre.total_esperado }} · Contado {{ ultimoCierre.total_registrado }} ·
          <span class="rounded-md px-2 py-0.5 font-semibold" :class="claseDiferencia(ultimoCierre.diferencia)">
            {{ Number(ultimoCierre.diferencia) > 0 ? '+' : '' }}{{ ultimoCierre.diferencia }}
          </span>
          <span v-if="ultimoCierre.marcado_para_revision" class="text-xs font-semibold text-error"
            >· marcado para revisión</span
          >
        </p>
      </form>
    </div>

    <h2 class="mb-2 text-sm font-semibold text-on-surface">Cajas de la tienda #{{ tiendaId }}</h2>
    <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-3 py-2 font-semibold">Caja</th>
            <th class="px-3 py-2 font-semibold">Cajero</th>
            <th class="px-3 py-2 text-right font-semibold">Esperado</th>
            <th class="px-3 py-2 text-right font-semibold">Contado</th>
            <th class="px-3 py-2 text-right font-semibold">Diferencia</th>
            <th class="px-3 py-2 font-semibold">Revisión</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="6" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!cierres.length">
            <td colspan="6" class="px-3 py-6 text-center text-on-surface-variant">
              Sin cuadres registrados hoy
            </td>
          </tr>
          <tr
            v-for="c in cierres"
            :key="c.cierre_id"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-3 py-2 tabular-nums">#{{ c.caja_id }}</td>
            <td class="px-3 py-2 tabular-nums">#{{ c.cajero_id }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ c.total_esperado }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ c.total_registrado }}</td>
            <td class="px-3 py-2 text-right">
              <span class="rounded-md px-2 py-0.5 font-semibold tabular-nums" :class="claseDiferencia(c.diferencia)">
                {{ Number(c.diferencia) > 0 ? '+' : '' }}{{ c.diferencia }}
              </span>
            </td>
            <td class="px-3 py-2">
              <span v-if="c.marcado_para_revision" class="text-xs font-semibold text-error">Sí</span>
              <span v-else class="text-xs text-on-surface-variant">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
