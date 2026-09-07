<script setup>
/**
 * Riesgo de fuga (US3, feature 002). Filtro reactivo por severidad
 * (`en_riesgo` / `inactivo`) contra `GET /api/clientes/riesgo-fuga`. Rol
 * Jefe_Marketing. El backend calcula el ciclo individual y la severidad — aquí
 * sólo se filtra y se muestra (SC-005, FR-011).
 */
import { onMounted, ref, watch } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import TablaClientesRiesgo from './components/TablaClientesRiesgo.vue'

const SEVERIDADES = [
  { valor: '', etiqueta: 'Todas' },
  { valor: 'en_riesgo', etiqueta: 'En riesgo' },
  { valor: 'inactivo', etiqueta: 'Inactivo' },
]

const severidad = ref('')
const filas = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await clientesApi.riesgoFuga({ severidad: severidad.value })
    filas.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    cargando.value = false
  }
}

watch(severidad, cargar)
onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-8">
    <h1 class="mb-1 text-2xl font-bold text-primary-container">Riesgo de fuga</h1>
    <p class="mb-6 text-sm text-on-surface-variant">
      Severidad relativa al ciclo de compra propio de cada cliente (1.5× en riesgo, 3× inactivo).
    </p>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div
      class="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-3"
    >
      <label class="text-sm text-on-surface-variant">Severidad</label>
      <div class="flex gap-1">
        <button
          v-for="s in SEVERIDADES"
          :key="s.valor"
          type="button"
          class="rounded-lg border px-3 py-1.5 text-sm"
          :class="
            severidad === s.valor
              ? 'border-primary bg-primary-container text-on-primary-container'
              : 'border-outline-variant text-on-surface-variant hover:bg-surface-container-low'
          "
          @click="severidad = s.valor"
        >
          {{ s.etiqueta }}
        </button>
      </div>
      <span class="ml-auto text-sm text-on-surface-variant">{{ total }} cliente(s)</span>
    </div>

    <TablaClientesRiesgo :filas="filas" :cargando="cargando" />
  </main>
</template>
