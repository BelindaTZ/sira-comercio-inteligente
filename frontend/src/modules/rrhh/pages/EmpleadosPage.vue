<script setup>
/**
 * Catálogo de empleados (feature 008, FR-005/FR-006/FR-014). Alta, actualización y
 * baja — el Jefe de RRHH. Al dar de baja, el trigger de PostgreSQL inhabilita la
 * cuenta asociada automáticamente (research.md Decisión 4).
 */
import { reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { prompt } from '@/shared/ui/dialogs'

const nuevo = reactive({
  nombre: '',
  puesto_id: '',
  tienda_id: '',
  email: '',
  telefono: '',
  fecha_contratacion: new Date().toISOString().slice(0, 10),
})
const ultimo = ref(null)
const consultaId = ref('')
const consultado = ref(null)
const error = ref('')

async function crear() {
  error.value = ''
  try {
    ultimo.value = await rrhhApi.crearEmpleado({
      nombre: nuevo.nombre.trim(),
      puestoId: Number(nuevo.puesto_id),
      tiendaId: nuevo.tienda_id ? Number(nuevo.tienda_id) : null,
      email: nuevo.email,
      telefono: nuevo.telefono,
      fechaContratacion: nuevo.fecha_contratacion,
    })
    nuevo.nombre = ''
    nuevo.email = ''
    nuevo.telefono = ''
  } catch (e) {
    error.value = e.message
  }
}

async function consultar() {
  error.value = ''
  try {
    consultado.value = await rrhhApi.obtenerEmpleado(Number(consultaId.value))
  } catch (e) {
    error.value = e.message
    consultado.value = null
  }
}

async function darBaja(emp) {
  const fecha = await prompt({
    title: `Dar de baja a ${emp.nombre || `empleado #${emp.empleado_id}`}`,
    label: 'Fecha de baja',
    inputType: 'date',
    required: true,
    initial: new Date().toISOString().slice(0, 10),
    confirmText: 'Dar de baja',
    tone: 'danger',
  })
  if (!fecha) return
  try {
    consultado.value = await rrhhApi.darBajaEmpleado(emp.empleado_id, fecha)
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Empleados</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <form
      class="mb-6 grid gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 sm:grid-cols-2"
      @submit.prevent="crear"
    >
      <h2 class="col-span-full text-sm font-semibold text-on-surface">Alta de empleado</h2>
      <label class="text-xs text-on-surface-variant">
        Nombre
        <input v-model="nuevo.nombre" required class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Puesto (id)
        <input v-model="nuevo.puesto_id" type="number" required class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Tienda (id, opcional)
        <input v-model="nuevo.tienda_id" type="number" class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Fecha de contratación
        <input v-model="nuevo.fecha_contratacion" type="date" required class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Correo
        <input v-model="nuevo.email" type="email" class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Teléfono
        <input v-model="nuevo.telefono" class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <button type="submit" class="col-span-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container">
        Registrar
      </button>
      <p v-if="ultimo" class="col-span-full text-xs text-tertiary">
        Empleado #{{ ultimo.empleado_id }} creado.
      </p>
    </form>

    <form class="mb-4 flex items-end gap-3" @submit.prevent="consultar">
      <label class="text-xs text-on-surface-variant">
        Buscar empleado por id
        <input v-model="consultaId" type="number" class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <button type="submit" class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container">
        Consultar
      </button>
    </form>

    <article
      v-if="consultado"
      class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    >
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-on-surface">
          #{{ consultado.empleado_id }} — {{ consultado.nombre }}
        </h3>
        <span
          class="rounded-md px-2 py-0.5 text-xs font-semibold"
          :class="consultado.activo ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-error-container text-on-error-container'"
        >
          {{ consultado.activo ? 'Activo' : 'Dado de baja' }}
        </span>
      </div>
      <p class="mt-1 text-xs text-on-surface-variant">
        {{ consultado.email || 'sin correo' }} · {{ consultado.telefono || 'sin teléfono' }}
        <span v-if="consultado.fecha_baja"> · baja {{ consultado.fecha_baja }}</span>
      </p>
      <button
        v-if="consultado.activo"
        type="button"
        class="mt-3 rounded-lg bg-error-container px-3 py-1.5 text-xs font-semibold text-on-error-container"
        @click="darBaja(consultado)"
      >
        Dar de baja (inhabilita la cuenta)
      </button>
    </article>
  </main>
</template>
