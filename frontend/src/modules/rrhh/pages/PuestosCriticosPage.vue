<script setup>
/**
 * Puestos críticos (feature 011, US1 / FR-001). El Jefe de RRHH marca o desmarca
 * un puesto como crítico para toda la red — precondición de la retención (OT-8.1)
 * y del plan de sucesión (OT-8.4).
 */
import { reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'

const form = reactive({ puesto_id: '', es_critico: true })
const ultimo = ref(null)
const error = ref('')

async function marcar() {
  error.value = ''
  try {
    ultimo.value = await rrhhApi.marcarPuestoCritico(Number(form.puesto_id), form.es_critico)
  } catch (e) {
    error.value = e.message
    ultimo.value = null
  }
}
</script>

<template>
  <main class="mx-auto max-w-2xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Puestos críticos</h1>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form
      class="flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="marcar"
    >
      <label class="text-xs text-on-surface-variant">
        Puesto (id)
        <input
          v-model="form.puesto_id"
          type="number"
          required
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="flex items-center gap-2 text-xs text-on-surface-variant">
        <input v-model="form.es_critico" type="checkbox" class="rounded border-outline-variant" />
        Marcar como crítico
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Aplicar
      </button>
    </form>

    <article
      v-if="ultimo"
      class="mt-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    >
      <h3 class="text-sm font-semibold text-on-surface">
        #{{ ultimo.puesto_id }} — {{ ultimo.nombre }}
      </h3>
      <span
        class="mt-1 inline-block rounded-md px-2 py-0.5 text-xs font-semibold"
        :class="
          ultimo.es_critico
            ? 'bg-error-container text-on-error-container'
            : 'bg-surface-container-high text-on-surface-variant'
        "
      >
        {{ ultimo.es_critico ? 'Crítico' : 'No crítico' }}
      </span>
    </article>
  </main>
</template>
