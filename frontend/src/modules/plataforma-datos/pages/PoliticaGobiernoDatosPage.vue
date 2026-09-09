<script setup>
/**
 * US4 / FR-009, FR-010 — el Jefe de TI mantiene el texto vigente de la política
 * de gobierno de datos. Append-only: registrar una nueva versión nunca reemplaza
 * la anterior, que queda en el historial (mismo criterio que 006/007).
 */
import { computed, onMounted, ref } from 'vue'
import { plataformaDatosApi } from '@/services/plataformaDatosApi'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
const puedeEditar = computed(() => sesion.puedeEditarTabla('TI', 'politica_gobierno_datos'))

const vigente = ref(null)
const historial = ref([])
const nuevoTexto = ref('')
const error = ref('')
const sinPolitica = ref(false)

async function cargar() {
  error.value = ''
  sinPolitica.value = false
  try {
    vigente.value = await plataformaDatosApi.politicaVigente()
  } catch (e) {
    if (e.status === 404) sinPolitica.value = true
    else error.value = e.message
  }
  try {
    historial.value = await plataformaDatosApi.politicaHistorial()
  } catch (e) {
    error.value = e.message
  }
}

async function registrar() {
  error.value = ''
  try {
    await plataformaDatosApi.registrarPolitica(nuevoTexto.value)
    nuevoTexto.value = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-3xl space-y-8 px-6 py-8">
    <header>
      <h1 class="text-2xl font-bold text-primary-container">Política de gobierno de datos</h1>
      <p class="mt-1 text-sm text-on-surface-variant">
        Calidad, trazabilidad y acceso a los datos del sistema. La versión vigente es siempre la
        más reciente.
      </p>
    </header>

    <p
      v-if="error"
      class="rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <section>
      <h2 class="mb-2 text-sm font-semibold text-on-surface">Versión vigente</h2>
      <p v-if="sinPolitica" class="text-sm text-on-surface-variant">
        Todavía no se registró ninguna política.
      </p>
      <article
        v-else-if="vigente"
        class="whitespace-pre-wrap rounded-xl border border-outline-variant p-4 text-sm text-on-surface"
      >
        {{ vigente.texto }}
        <footer class="mt-3 text-xs text-on-surface-variant">
          Registrada el {{ new Date(vigente.fecha_creacion).toLocaleString() }}
        </footer>
      </article>
    </section>

    <section v-if="puedeEditar" class="rounded-xl border border-outline-variant p-4">
      <h2 class="mb-2 text-sm font-semibold text-on-surface">Registrar nueva versión</h2>
      <form @submit.prevent="registrar">
        <textarea
          v-model="nuevoTexto"
          required
          rows="6"
          class="block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          placeholder="Texto completo de la política…"
        />
        <button
          type="submit"
          class="mt-3 rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
        >
          Guardar versión
        </button>
      </form>
    </section>

    <section v-if="historial.length > 1">
      <h2 class="mb-2 text-sm font-semibold text-on-surface">Historial</h2>
      <ol class="space-y-2">
        <li
          v-for="p in historial"
          :key="p.politica_id"
          class="rounded-lg border border-outline-variant p-3 text-xs text-on-surface-variant"
        >
          <span class="text-on-surface">{{ new Date(p.fecha_creacion).toLocaleString() }}</span>
          <p class="mt-1 line-clamp-3 whitespace-pre-wrap">{{ p.texto }}</p>
        </li>
      </ol>
    </section>
  </main>
</template>
