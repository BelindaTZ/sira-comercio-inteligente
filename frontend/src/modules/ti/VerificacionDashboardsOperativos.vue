<script setup>
/**
 * US3 — el Jefe de TI revisa diariamente qué dashboards operativos de tienda
 * (alertas de reposición, cuadre de caja, seguimiento de merma) están
 * disponibles y actualizados para toda la red, y cuáles no. Las filas no
 * disponibles (más de un día sin actualizarse, FR-007) se resaltan como alerta.
 */
import { computed, onMounted, ref } from 'vue'
import { tiDashboardsApi } from '@/services/tiDashboardsApi'

const verificacion = ref(null)
const soloAlertas = ref(false)
const error = ref('')
const aviso = ref('')

function fmtFecha(iso) {
  return iso ? new Date(iso).toLocaleString() : 'sin dato'
}

const filas = computed(() => {
  const todas = verificacion.value?.estado_por_tienda ?? []
  return soloAlertas.value ? todas.filter((f) => !f.disponible) : todas
})

async function cargar() {
  error.value = ''
  aviso.value = ''
  try {
    verificacion.value = await tiDashboardsApi.verificacionOperativos()
  } catch (e) {
    if (e.status === 404) aviso.value = 'Todavía no se ha ejecutado la verificación diaria.'
    else error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl space-y-6 px-6 py-8">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-primary-container">
          Disponibilidad de dashboards operativos
        </h1>
        <p v-if="verificacion" class="mt-1 text-sm text-on-surface-variant">
          Verificación del {{ fmtFecha(verificacion.fecha_verificacion) }}
        </p>
      </div>
      <label class="flex items-center gap-2 text-xs text-on-surface-variant">
        <input v-model="soloAlertas" type="checkbox" />
        Sólo alertas
      </label>
    </header>

    <p v-if="error" class="rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="rounded-lg bg-surface-container-high px-4 py-2 text-sm text-on-surface-variant"
    >
      {{ aviso }}
    </p>

    <div v-if="verificacion" class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-xs text-on-surface-variant">
          <tr>
            <th class="py-1">Tienda</th>
            <th class="py-1">Dashboard</th>
            <th class="py-1">Última actualización</th>
            <th class="py-1">Estado</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="f in filas"
            :key="f.tienda_id + f.nombre_dashboard"
            class="border-t border-outline-variant"
            :class="{ 'bg-error-container/40': !f.disponible }"
          >
            <td class="py-1.5 text-on-surface-variant">{{ f.tienda_id }}</td>
            <td class="py-1.5 text-on-surface">{{ f.nombre_dashboard }}</td>
            <td class="py-1.5 text-on-surface-variant">
              {{ fmtFecha(f.fecha_ultima_actualizacion) }}
            </td>
            <td
              class="py-1.5 font-medium"
              :class="f.disponible ? 'text-on-surface' : 'text-on-error-container'"
            >
              {{ f.disponible ? 'al día' : 'desactualizado' }}
            </td>
          </tr>
          <tr v-if="!filas.length">
            <td colspan="4" class="py-3 text-center text-on-surface-variant">
              {{ soloAlertas ? 'Ningún dashboard operativo con alerta.' : 'Sin filas.' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
