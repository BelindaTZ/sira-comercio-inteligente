<script setup>
/**
 * Capacitación en el sistema (feature 011, US2 / FR-003 a FR-005). El Jefe de RRHH
 * programa una capacitación dirigida a uno o más roles: el backend hace el fan-out
 * hacia todos los empleados con cuenta activa en esos roles. El Encargado de
 * Tienda consulta el cumplimiento de su propio personal.
 */
import { reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'

const nueva = reactive({ nombre: '', descripcion: '', role_ids: '' })
const ultima = ref(null)
const completar = reactive({ empleado_id: '', capacitacion_id: '', fecha: '' })
const tiendaId = ref('')
const cumplimiento = ref([])
const error = ref('')

async function programar() {
  error.value = ''
  try {
    const roleIds = nueva.role_ids
      .split(',')
      .map((s) => Number(s.trim()))
      .filter(Boolean)
    ultima.value = await rrhhApi.programarCapacitacion({
      nombre: nueva.nombre.trim(),
      descripcion: nueva.descripcion,
      roleIds,
    })
    nueva.nombre = ''
    nueva.descripcion = ''
  } catch (e) {
    error.value = e.message
  }
}

async function marcarCompletada() {
  error.value = ''
  try {
    await rrhhApi.completarCapacitacion(
      Number(completar.empleado_id),
      Number(completar.capacitacion_id),
      completar.fecha
    )
    if (tiendaId.value) await verCumplimiento()
  } catch (e) {
    error.value = e.message
  }
}

async function verCumplimiento() {
  error.value = ''
  try {
    cumplimiento.value = await rrhhApi.cumplimientoCapacitacionTienda(Number(tiendaId.value))
  } catch (e) {
    error.value = e.message
    cumplimiento.value = []
  }
}
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Capacitación en el sistema</h1>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form
      class="mb-6 grid gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 sm:grid-cols-2"
      @submit.prevent="programar"
    >
      <h2 class="col-span-full text-sm font-semibold text-on-surface">
        Programar capacitación (Jefe de RRHH)
      </h2>
      <label class="text-xs text-on-surface-variant">
        Nombre
        <input
          v-model="nueva.nombre"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Roles objetivo (ids separados por coma)
        <input
          v-model="nueva.role_ids"
          required
          placeholder="3, 5"
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="col-span-full text-xs text-on-surface-variant">
        Descripción (opcional)
        <input
          v-model="nueva.descripcion"
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="col-span-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Programar
      </button>
      <p v-if="ultima" class="col-span-full text-xs text-tertiary">
        Capacitación #{{ ultima.capacitacion_id }} — {{ ultima.empleados_asignados }} empleado(s)
        asignado(s).
      </p>
    </form>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="marcarCompletada"
    >
      <h2 class="w-full text-sm font-semibold text-on-surface">Registrar finalización</h2>
      <label class="text-xs text-on-surface-variant">
        Empleado (id)
        <input
          v-model="completar.empleado_id"
          type="number"
          required
          class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Capacitación (id)
        <input
          v-model="completar.capacitacion_id"
          type="number"
          required
          class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Fecha de finalización
        <input
          v-model="completar.fecha"
          type="date"
          required
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Confirmar
      </button>
    </form>

    <form class="mb-4 flex items-end gap-3" @submit.prevent="verCumplimiento">
      <label class="text-xs text-on-surface-variant">
        Cumplimiento por tienda (id) — Encargado de Tienda
        <input
          v-model="tiendaId"
          type="number"
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Ver
      </button>
    </form>

    <table v-if="cumplimiento.length" class="w-full text-sm">
      <thead class="text-left text-xs text-on-surface-variant">
        <tr>
          <th class="py-1">Empleado</th>
          <th class="py-1">Capacitación</th>
          <th class="py-1">Estado</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="fila in cumplimiento"
          :key="`${fila.empleado_id}-${fila.capacitacion_id}`"
          class="border-t border-outline-variant"
        >
          <td class="py-1.5 text-on-surface">{{ fila.nombre }}</td>
          <td class="py-1.5 text-on-surface-variant">{{ fila.nombre_capacitacion }}</td>
          <td class="py-1.5">
            <span
              class="rounded-md px-2 py-0.5 text-xs font-semibold"
              :class="
                fila.fecha_completado
                  ? 'bg-tertiary-container text-on-tertiary-container'
                  : 'bg-surface-container-high text-on-surface-variant'
              "
            >
              {{ fila.fecha_completado ? `Completada ${fila.fecha_completado}` : 'Pendiente' }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="tiendaId" class="text-sm text-on-surface-variant">
      Sin registros de capacitación
    </p>
  </main>
</template>
