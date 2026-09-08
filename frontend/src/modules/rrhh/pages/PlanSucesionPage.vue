<script setup>
/**
 * Plan de sucesión (feature 011, US4 / FR-008, FR-009). El Jefe de RRHH registra
 * candidatos internos para puestos críticos; el sistema señala explícitamente,
 * con un badge de alerta no bloqueante, los puestos críticos sin ningún candidato.
 */
import { onMounted, reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'

const nuevo = reactive({ puesto_id: '', empleado_candidato_id: '' })
const cobertura = ref([])
const error = ref('')

async function cargar() {
  error.value = ''
  try {
    cobertura.value = await rrhhApi.coberturaSucesion()
  } catch (e) {
    error.value = e.message
  }
}

async function registrar() {
  error.value = ''
  try {
    await rrhhApi.registrarCandidatoSucesion({
      puestoId: Number(nuevo.puesto_id),
      empleadoCandidatoId: Number(nuevo.empleado_candidato_id),
    })
    nuevo.empleado_candidato_id = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Plan de sucesión</h1>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="registrar"
    >
      <h2 class="w-full text-sm font-semibold text-on-surface">Registrar candidato</h2>
      <label class="text-xs text-on-surface-variant">
        Puesto crítico (id)
        <input
          v-model="nuevo.puesto_id"
          type="number"
          required
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Empleado candidato (id)
        <input
          v-model="nuevo.empleado_candidato_id"
          type="number"
          required
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Registrar
      </button>
    </form>

    <h2 class="mb-2 text-sm font-semibold text-on-surface">Cobertura de puestos críticos</h2>
    <p v-if="!cobertura.length" class="text-sm text-on-surface-variant">
      No hay puestos marcados como críticos.
    </p>
    <ul class="space-y-2">
      <li
        v-for="p in cobertura"
        :key="p.puesto_id"
        class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      >
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-on-surface">#{{ p.puesto_id }} — {{ p.nombre }}</h3>
          <span
            v-if="p.sin_cobertura"
            class="rounded-md bg-error-container px-2 py-0.5 text-xs font-semibold text-on-error-container"
          >
            Sin cobertura
          </span>
          <span
            v-else
            class="rounded-md bg-tertiary-container px-2 py-0.5 text-xs font-semibold text-on-tertiary-container"
          >
            {{ p.candidatos.length }} candidato(s)
          </span>
        </div>
        <ul v-if="p.candidatos.length" class="mt-2 text-xs text-on-surface-variant">
          <li v-for="c in p.candidatos" :key="c.empleado_candidato_id">
            {{ c.nombre }} — {{ c.fecha }}
          </li>
        </ul>
      </li>
    </ul>
  </main>
</template>
