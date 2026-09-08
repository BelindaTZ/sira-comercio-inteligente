<script setup>
/**
 * Medición del tiempo de cobro (feature 007, FR-016 a FR-018). El Encargado de
 * Tienda revisa el promedio semanal por caja; el Jefe Comercial el mensual por
 * tienda a nivel de red. El cálculo (`fecha_hora - fecha_inicio_cobro`, sin
 * anuladas ni ventas sembradas) vive en el backend (Principio V).
 */
import { onMounted, reactive, ref } from 'vue'
import { ventasApi } from '@/services/ventasApi'

const hoy = new Date()

function isoWeek(d) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  const day = (t.getUTCDay() + 6) % 7
  t.setUTCDate(t.getUTCDate() - day + 3)
  const firstThursday = new Date(Date.UTC(t.getUTCFullYear(), 0, 4))
  return 1 + Math.round((t - firstThursday) / 604800000)
}

const semanal = reactive({
  cajaId: Number(localStorage.getItem('sira_caja_id')) || 1,
  semana: isoWeek(hoy),
  anio: hoy.getFullYear(),
})
const mensual = reactive({ mes: hoy.getMonth() + 1, anio: hoy.getFullYear() })
const resultadoSemanal = ref(null)
const resultadoMensual = ref([])
const error = ref('')

function fmt(segundos) {
  if (segundos == null) return '—'
  return segundos < 60 ? `${segundos.toFixed(1)} s` : `${(segundos / 60).toFixed(1)} min`
}

async function consultarSemanal() {
  error.value = ''
  try {
    resultadoSemanal.value = await ventasApi.tiempoCobroSemanal(semanal.cajaId, {
      semana: semanal.semana,
      anio: semanal.anio,
    })
  } catch (e) {
    error.value = e.message
  }
}

async function consultarMensual() {
  error.value = ''
  try {
    resultadoMensual.value = await ventasApi.tiempoCobroMensual({
      mes: mensual.mes,
      anio: mensual.anio,
    })
  } catch (e) {
    error.value = e.message
  }
}

onMounted(consultarSemanal)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Tiempo de cobro</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <section class="mb-8">
      <h2 class="mb-2 text-sm font-semibold text-on-surface">Semanal por caja (Encargado de Tienda)</h2>
      <form class="flex flex-wrap items-end gap-3" @submit.prevent="consultarSemanal">
        <label class="text-xs text-on-surface-variant">
          Caja
          <input
            v-model.number="semanal.cajaId"
            type="number"
            class="mt-1 block w-24 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="text-xs text-on-surface-variant">
          Semana ISO
          <input
            v-model.number="semanal.semana"
            type="number"
            min="1"
            max="53"
            class="mt-1 block w-20 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="text-xs text-on-surface-variant">
          Año
          <input
            v-model.number="semanal.anio"
            type="number"
            class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <button
          type="submit"
          class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
        >
          Consultar
        </button>
      </form>
      <p v-if="resultadoSemanal" class="mt-3 text-sm text-on-surface">
        Caja #{{ resultadoSemanal.caja_id }}, semana {{ resultadoSemanal.semana }}:
        <strong>{{ fmt(resultadoSemanal.duracion_promedio_segundos) }}</strong>
        de promedio ({{ resultadoSemanal.cantidad_ventas_consideradas }} venta(s) consideradas).
      </p>
    </section>

    <section>
      <h2 class="mb-2 text-sm font-semibold text-on-surface">
        Mensual por tienda a nivel de red (Jefe Comercial)
      </h2>
      <form class="mb-3 flex flex-wrap items-end gap-3" @submit.prevent="consultarMensual">
        <label class="text-xs text-on-surface-variant">
          Mes
          <input
            v-model.number="mensual.mes"
            type="number"
            min="1"
            max="12"
            class="mt-1 block w-20 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="text-xs text-on-surface-variant">
          Año
          <input
            v-model.number="mensual.anio"
            type="number"
            class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <button
          type="submit"
          class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
        >
          Consultar
        </button>
      </form>
      <div
        class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
      >
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-outline-variant text-left text-on-surface-variant">
              <th class="px-3 py-2 font-semibold">Tienda</th>
              <th class="px-3 py-2 text-right font-semibold">Promedio</th>
              <th class="px-3 py-2 text-right font-semibold">Ventas consideradas</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!resultadoMensual.length">
              <td colspan="3" class="px-3 py-6 text-center text-on-surface-variant">Sin datos</td>
            </tr>
            <tr
              v-for="fila in resultadoMensual"
              :key="fila.tienda_id"
              class="border-b border-outline-variant last:border-0"
            >
              <td class="px-3 py-2 tabular-nums">#{{ fila.tienda_id }}</td>
              <td class="px-3 py-2 text-right font-semibold tabular-nums">
                {{ fmt(fila.duracion_promedio_segundos) }}
              </td>
              <td class="px-3 py-2 text-right tabular-nums">
                {{ fila.cantidad_ventas_consideradas }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>
