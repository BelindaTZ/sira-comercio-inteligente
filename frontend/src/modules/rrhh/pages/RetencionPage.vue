<script setup>
/**
 * Acciones de retención (feature 011, US1 / FR-002). El Jefe de RRHH registra una
 * acción (fecha, descripción) para un empleado y la consulta en cualquier momento.
 * Se permite para cualquier empleado; sólo los puestos críticos alimentan el KPI
 * de OT-8.1.
 */
import { computed, reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
const puedeEditar = computed(() => sesion.rol === 'Jefe_RRHH')

const nueva = reactive({
  empleado_id: '',
  fecha: new Date().toISOString().slice(0, 10),
  descripcion: '',
})
const consultaId = ref('')
const acciones = ref([])
const error = ref('')

async function registrar() {
  error.value = ''
  try {
    await rrhhApi.registrarAccionRetencion({
      empleadoId: Number(nueva.empleado_id),
      fecha: nueva.fecha,
      descripcion: nueva.descripcion.trim(),
    })
    nueva.descripcion = ''
    if (Number(consultaId.value) === Number(nueva.empleado_id)) await consultar()
  } catch (e) {
    error.value = e.message
  }
}

async function consultar() {
  error.value = ''
  try {
    acciones.value = await rrhhApi.accionesRetencion(Number(consultaId.value))
  } catch (e) {
    error.value = e.message
    acciones.value = []
  }
}
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Acciones de retención</h1>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form
      v-if="puedeEditar"
      class="mb-6 grid gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 sm:grid-cols-2"
      @submit.prevent="registrar"
    >
      <h2 class="col-span-full text-sm font-semibold text-on-surface">Registrar acción</h2>
      <label class="text-xs text-on-surface-variant">
        Empleado (id)
        <input
          v-model="nueva.empleado_id"
          type="number"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Fecha
        <input
          v-model="nueva.fecha"
          type="date"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="col-span-full text-xs text-on-surface-variant">
        Descripción
        <input
          v-model="nueva.descripcion"
          type="text"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="col-span-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Registrar
      </button>
    </form>

    <form class="mb-4 flex items-end gap-3" @submit.prevent="consultar">
      <label class="text-xs text-on-surface-variant">
        Ver acciones del empleado (id)
        <input
          v-model="consultaId"
          type="number"
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Consultar
      </button>
    </form>

    <ul class="space-y-2">
      <li
        v-for="a in acciones"
        :key="a.accion_id"
        class="rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-2 text-sm text-on-surface"
      >
        <span class="text-on-surface-variant">{{ a.fecha }}</span> — {{ a.descripcion }}
      </li>
      <li v-if="consultaId && !acciones.length" class="text-sm text-on-surface-variant">
        Sin acciones registradas
      </li>
    </ul>
  </main>
</template>
