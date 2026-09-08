<script setup>
/**
 * Reporte mensual de auditoría de accesos (feature 008, FR-016). Agrupado por
 * usuario: logins exitosos, intentos fallidos y acciones registradas en
 * `auditoria_log` — sin consolidar manualmente ninguna fuente.
 */
import { onMounted, reactive, ref } from 'vue'
import { sistemaApi } from '@/services/sistemaApi'

const hoy = new Date()
const filtro = reactive({ mes: hoy.getMonth() + 1, anio: hoy.getFullYear() })
const filas = ref([])
const error = ref('')
const cargando = ref(false)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    filas.value = await sistemaApi.reporteAuditoria({ mes: filtro.mes, anio: filtro.anio })
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
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Auditoría de accesos</h1>

    <form class="mb-4 flex flex-wrap items-end gap-3" @submit.prevent="cargar">
      <label class="text-xs text-on-surface-variant">
        Mes
        <input v-model.number="filtro.mes" type="number" min="1" max="12" class="mt-1 block w-20 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Año
        <input v-model.number="filtro.anio" type="number" class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <button type="submit" class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container">
        Consultar
      </button>
    </form>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-3 py-2 font-semibold">Usuario</th>
            <th class="px-3 py-2 text-right font-semibold">Logins exitosos</th>
            <th class="px-3 py-2 text-right font-semibold">Intentos fallidos</th>
            <th class="px-3 py-2 text-right font-semibold">Acciones</th>
            <th class="px-3 py-2 font-semibold">Último login</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!filas.length">
            <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">Sin actividad en el periodo</td>
          </tr>
          <tr v-for="(f, i) in filas" :key="i" class="border-b border-outline-variant last:border-0">
            <td class="px-3 py-2">{{ f.username || '(intentos anónimos)' }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ f.logins_exitosos }}</td>
            <td
              class="px-3 py-2 text-right font-semibold tabular-nums"
              :class="f.intentos_fallidos > 0 ? 'text-error' : 'text-on-surface-variant'"
            >
              {{ f.intentos_fallidos }}
            </td>
            <td class="px-3 py-2 text-right tabular-nums">{{ f.acciones_registradas }}</td>
            <td class="px-3 py-2 tabular-nums text-on-surface-variant">{{ f.ultimo_login || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
