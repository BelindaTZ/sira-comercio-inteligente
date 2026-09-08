<script setup>
/**
 * US1 / FR-001 — el Jefe de TI define el modelo de datos único del warehouse
 * (fact_venta + dimensiones) y activa/desactiva cada entidad. El DAG de carga
 * sólo procesa entidades activas (research.md Decisión 1). Toda la regla vive en
 * el backend.
 */
import { onMounted, reactive, ref } from 'vue'
import { plataformaDatosApi } from '@/services/plataformaDatosApi'

const entidades = ref([])
const error = ref('')
const cargando = ref(false)
const form = reactive({
  nombreEntidad: '',
  tipo: 'dimension',
  tablaOrigenPostgres: '',
  descripcion: '',
})

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    entidades.value = await plataformaDatosApi.modelo()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function registrar() {
  error.value = ''
  try {
    await plataformaDatosApi.registrarEntidad({ ...form })
    form.nombreEntidad = ''
    form.tablaOrigenPostgres = ''
    form.descripcion = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function alternarActiva(entidad) {
  error.value = ''
  try {
    await plataformaDatosApi.actualizarEntidad(entidad.entidad_id, { activa: !entidad.activa })
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl space-y-8 px-6 py-8">
    <header>
      <h1 class="text-2xl font-bold text-primary-container">Modelo de datos del warehouse</h1>
      <p class="mt-1 text-sm text-on-surface-variant">
        Entidades que la carga diaria puebla en el warehouse. Una entidad inactiva queda definida
        pero su carga no arranca hasta activarla.
      </p>
    </header>

    <p
      v-if="error"
      class="rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <section>
      <table v-if="entidades.length" class="w-full text-sm">
        <thead class="text-left text-xs text-on-surface-variant">
          <tr>
            <th class="py-1">Entidad</th>
            <th class="py-1">Tipo</th>
            <th class="py-1">Tabla origen</th>
            <th class="py-1">Estado</th>
            <th class="py-1" />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ent in entidades"
            :key="ent.entidad_id"
            class="border-t border-outline-variant"
          >
            <td class="py-1.5 font-medium text-on-surface">{{ ent.nombre_entidad }}</td>
            <td class="py-1.5 text-on-surface-variant">{{ ent.tipo }}</td>
            <td class="py-1.5 text-on-surface-variant">{{ ent.tabla_origen_postgres }}</td>
            <td class="py-1.5">
              <span :class="ent.activa ? 'text-on-surface' : 'text-on-surface-variant'">
                {{ ent.activa ? 'activa' : 'inactiva' }}
              </span>
            </td>
            <td class="py-1.5 text-right">
              <button
                class="rounded-lg border border-outline-variant px-3 py-1 text-xs text-on-surface"
                @click="alternarActiva(ent)"
              >
                {{ ent.activa ? 'Desactivar' : 'Activar' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="!cargando" class="text-sm text-on-surface-variant">
        Todavía no hay ninguna entidad en el modelo.
      </p>
    </section>

    <section class="rounded-xl border border-outline-variant p-4">
      <h2 class="mb-3 text-sm font-semibold text-on-surface">Registrar una entidad</h2>
      <form class="grid gap-3 sm:grid-cols-2" @submit.prevent="registrar">
        <label class="text-xs text-on-surface-variant">
          Nombre de la entidad
          <input
            v-model="form.nombreEntidad"
            required
            placeholder="dim_producto"
            class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="text-xs text-on-surface-variant">
          Tipo
          <select
            v-model="form.tipo"
            class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          >
            <option value="fact">fact</option>
            <option value="dimension">dimension</option>
          </select>
        </label>
        <label class="text-xs text-on-surface-variant">
          Tabla origen (PostgreSQL)
          <input
            v-model="form.tablaOrigenPostgres"
            required
            placeholder="productos"
            class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="text-xs text-on-surface-variant sm:col-span-2">
          Descripción
          <input
            v-model="form.descripcion"
            class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <div class="sm:col-span-2">
          <button
            type="submit"
            class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
          >
            Registrar
          </button>
        </div>
      </form>
    </section>
  </main>
</template>
