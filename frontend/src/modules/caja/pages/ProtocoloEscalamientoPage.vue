<script setup>
/**
 * Protocolo de escalamiento ante fraude confirmado (FR-012, FR-013). El texto
 * vigente es consultable por cualquier Encargado de Tienda; el Jefe de Finanzas
 * publica una nueva versión (append-only — la anterior queda en el historial).
 */
import { onMounted, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'

const vigente = ref(null)
const borrador = ref('')
const error = ref('')
const guardado = ref(false)

async function cargar() {
  error.value = ''
  try {
    vigente.value = await cajaApi.protocolo()
    borrador.value = vigente.value?.texto || ''
  } catch (e) {
    vigente.value = null
    if (e.status !== 404) error.value = e.message
  }
}

async function publicar() {
  error.value = ''
  guardado.value = false
  try {
    vigente.value = await cajaApi.definirProtocolo(borrador.value)
    guardado.value = true
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Protocolo de escalamiento</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <section class="mb-6 rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
      <h2 class="mb-2 text-sm font-semibold text-on-surface">Versión vigente</h2>
      <p v-if="vigente" class="whitespace-pre-wrap text-sm text-on-surface-variant">
        {{ vigente.texto }}
      </p>
      <p v-else class="text-sm text-on-surface-variant">Aún no se ha definido un protocolo.</p>
      <p v-if="vigente" class="mt-2 text-xs text-on-surface-variant">
        Definido por #{{ vigente.definido_por }} · {{ vigente.fecha_creacion }}
      </p>
    </section>

    <form class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4" @submit.prevent="publicar">
      <h2 class="mb-2 text-sm font-semibold text-on-surface">Publicar nueva versión</h2>
      <textarea
        v-model="borrador"
        rows="8"
        required
        class="block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <div class="mt-3 flex items-center gap-3">
        <button
          type="submit"
          class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
        >
          Publicar
        </button>
        <span v-if="guardado" class="text-xs font-semibold text-tertiary">Guardado</span>
      </div>
    </form>
  </main>
</template>
