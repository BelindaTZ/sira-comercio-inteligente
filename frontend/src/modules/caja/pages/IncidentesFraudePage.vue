<script setup>
/**
 * Ciclo de vida de un incidente de fraude (FR-014 a FR-016). El Encargado de
 * Tienda aplica el protocolo sobre un incidente abierto (registrando acciones);
 * el Jefe de Finanzas lo cierra con su resultado, sin acusar al empleado si la
 * investigación no lo confirma. Un empleado dado de baja no bloquea el ciclo.
 */
import { onMounted, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { prompt } from '@/shared/ui/dialogs'

const incidentes = ref([])
const filtroEstado = ref('')
const error = ref('')
const cargando = ref(false)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    incidentes.value = await cajaApi.incidentes(filtroEstado.value)
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function aplicarProtocolo(inc) {
  const acciones = await prompt({
    title: `Aplicar protocolo — incidente #${inc.incidente_id}`,
    label: 'Acciones tomadas',
    placeholder: 'Qué se hizo según el protocolo de escalamiento',
    required: true,
    confirmText: 'Registrar',
  })
  if (!acciones) return
  try {
    await cajaApi.aplicarProtocolo(inc.incidente_id, acciones)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function cerrar(inc, resultado) {
  try {
    await cajaApi.cerrarIncidente(inc.incidente_id, resultado)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Incidentes de fraude</h1>

    <div class="mb-3 flex items-center gap-2">
      <label class="text-xs text-on-surface-variant" for="filtro-inc">Estado</label>
      <select
        id="filtro-inc"
        v-model="filtroEstado"
        class="rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
        @change="cargar"
      >
        <option value="">Todos</option>
        <option value="abierto">Abierto</option>
        <option value="en_revision">En revisión</option>
        <option value="cerrado">Cerrado</option>
      </select>
    </div>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <div class="space-y-3">
      <p v-if="cargando" class="text-sm text-on-surface-variant">Cargando…</p>
      <p v-else-if="!incidentes.length" class="text-sm text-on-surface-variant">Sin incidentes</p>
      <article
        v-for="inc in incidentes"
        :key="inc.incidente_id"
        class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      >
        <div class="mb-2 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-on-surface">
            Incidente #{{ inc.incidente_id }} · empleado #{{ inc.empleado_id }}
          </h2>
          <span
            class="rounded-md px-2 py-0.5 text-xs font-semibold"
            :class="{
              'bg-error-container text-on-error-container': inc.estado === 'abierto',
              'bg-secondary-container text-on-secondary-container': inc.estado === 'en_revision',
              'bg-tertiary-container text-on-tertiary-container': inc.estado === 'cerrado',
            }"
          >
            {{ inc.estado }}
          </span>
        </div>
        <p class="text-sm text-on-surface-variant">{{ inc.descripcion }}</p>
        <p v-if="inc.acciones_tomadas" class="mt-1 text-xs text-on-surface-variant">
          <strong>Acciones:</strong> {{ inc.acciones_tomadas }}
        </p>
        <p v-if="inc.resultado" class="mt-1 text-xs text-on-surface-variant">
          <strong>Resultado:</strong> {{ inc.resultado }}
        </p>
        <div class="mt-3 flex gap-2">
          <button
            v-if="inc.estado === 'abierto'"
            type="button"
            class="rounded-lg bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
            @click="aplicarProtocolo(inc)"
          >
            Aplicar protocolo
          </button>
          <template v-if="inc.estado === 'en_revision'">
            <button
              type="button"
              class="rounded-lg bg-error-container px-3 py-1.5 text-xs font-semibold text-on-error-container"
              @click="cerrar(inc, 'fraude_confirmado')"
            >
              Cerrar: fraude confirmado
            </button>
            <button
              type="button"
              class="rounded-lg bg-tertiary-container px-3 py-1.5 text-xs font-semibold text-on-tertiary-container"
              @click="cerrar(inc, 'descartado')"
            >
              Cerrar: descartado
            </button>
          </template>
        </div>
      </article>
    </div>
  </main>
</template>
