<script setup>
/**
 * Inventario de datáfonos (FR-006 a FR-008). El Jefe de TI define el estándar de
 * seguridad de pagos vigente; el sistema marca automáticamente los datáfonos no
 * conformes (`requiere_actualizacion`) y el Jefe de TI registra su actualización.
 */
import { onMounted, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'

const datafonos = ref([])
const estandar = ref(null)
const nuevaVersionMinima = ref('')
const filtroEstado = ref('')
const error = ref('')
const cargando = ref(false)

const ETIQUETA_ESTADO = {
  activo: 'Conforme',
  requiere_actualizacion: 'No conforme',
  fuera_servicio: 'Fuera de servicio',
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    datafonos.value = await cajaApi.datafonos(filtroEstado.value)
    estandar.value = await cajaApi.configuracionSeguridad().catch(() => null)
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function definirEstandar() {
  error.value = ''
  try {
    await cajaApi.definirEstandarSeguridad(nuevaVersionMinima.value)
    nuevaVersionMinima.value = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function actualizar(d) {
  const version = window.prompt(`Nueva versión de firmware para el datáfono #${d.datafono_id}`, '')
  if (!version) return
  try {
    await cajaApi.actualizarDatafono(d.datafono_id, version)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Datáfonos y seguridad de pagos</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="definirEstandar"
    >
      <div class="text-xs text-on-surface-variant">
        Estándar vigente
        <p class="mt-1 text-sm font-semibold text-on-surface">
          {{ estandar ? `firmware ≥ ${estandar.version_minima_firmware}` : 'sin definir' }}
        </p>
      </div>
      <label class="text-xs text-on-surface-variant">
        Nueva versión mínima
        <input
          v-model="nuevaVersionMinima"
          type="text"
          placeholder="3.2.0"
          required
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Definir estándar
      </button>
    </form>

    <div class="mb-3 flex items-center gap-2">
      <label class="text-xs text-on-surface-variant" for="filtro-estado">Estado</label>
      <select
        id="filtro-estado"
        v-model="filtroEstado"
        class="rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
        @change="cargar"
      >
        <option value="">Todos</option>
        <option value="activo">Conforme</option>
        <option value="requiere_actualizacion">No conforme</option>
        <option value="fuera_servicio">Fuera de servicio</option>
      </select>
    </div>

    <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-3 py-2 font-semibold">Datáfono</th>
            <th class="px-3 py-2 font-semibold">Caja</th>
            <th class="px-3 py-2 font-semibold">Modelo</th>
            <th class="px-3 py-2 font-semibold">Firmware</th>
            <th class="px-3 py-2 font-semibold">Últ. actualización</th>
            <th class="px-3 py-2 font-semibold">Estado</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="7" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!datafonos.length">
            <td colspan="7" class="px-3 py-6 text-center text-on-surface-variant">Sin datáfonos</td>
          </tr>
          <tr
            v-for="d in datafonos"
            :key="d.datafono_id"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-3 py-2 tabular-nums">#{{ d.datafono_id }}</td>
            <td class="px-3 py-2 tabular-nums">#{{ d.caja_id }}</td>
            <td class="px-3 py-2">{{ d.modelo || '—' }}</td>
            <td class="px-3 py-2 tabular-nums">{{ d.version_firmware || '—' }}</td>
            <td class="px-3 py-2 tabular-nums">{{ d.fecha_ultima_actualizacion || '—' }}</td>
            <td class="px-3 py-2">
              <span
                class="rounded-md px-2 py-0.5 text-xs font-semibold"
                :class="
                  d.estado === 'requiere_actualizacion'
                    ? 'bg-error-container text-on-error-container'
                    : 'bg-tertiary-container text-on-tertiary-container'
                "
              >
                {{ ETIQUETA_ESTADO[d.estado] || d.estado }}
              </span>
            </td>
            <td class="px-3 py-2 text-right">
              <button
                v-if="d.estado === 'requiere_actualizacion'"
                type="button"
                class="rounded-lg bg-primary-container px-2 py-1 text-xs font-semibold text-on-primary-container"
                @click="actualizar(d)"
              >
                Registrar actualización
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
