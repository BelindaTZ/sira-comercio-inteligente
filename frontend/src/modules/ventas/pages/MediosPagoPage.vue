<script setup>
/**
 * Catálogo de medios de pago (feature 007, FR-005 a FR-007). El Jefe de TI da de
 * alta un medio de pago con constancia de aprobación y da de baja uno existente
 * sin afectar ninguna venta ya registrada.
 */
import { onMounted, ref } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import { confirm } from '@/shared/ui/dialogs'

const medios = ref([])
const nuevoNombre = ref('')
const error = ref('')
const cargando = ref(false)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    medios.value = await ventasApi.mediosPago()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function alta() {
  error.value = ''
  try {
    await ventasApi.altaMedioPago(nuevoNombre.value.trim())
    nuevoNombre.value = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function baja(m) {
  const ok = await confirm({
    title: 'Dar de baja el medio de pago',
    message: `«${m.nombre}» dejará de ofrecerse en caja. No afecta ventas ya registradas.`,
    confirmText: 'Dar de baja',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await ventasApi.bajaMedioPago(m.medio_pago_id)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Medios de pago</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="alta"
    >
      <label class="text-xs text-on-surface-variant">
        Nombre del nuevo medio de pago
        <input
          v-model="nuevoNombre"
          type="text"
          maxlength="30"
          required
          class="mt-1 block w-64 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Dar de alta (aprobado)
      </button>
    </form>

    <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-3 py-2 font-semibold">Medio</th>
            <th class="px-3 py-2 font-semibold">Estado</th>
            <th class="px-3 py-2 font-semibold">Aprobado por</th>
            <th class="px-3 py-2 font-semibold">Baja</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr
            v-for="m in medios"
            :key="m.medio_pago_id"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-3 py-2">{{ m.nombre }}</td>
            <td class="px-3 py-2">
              <span
                class="rounded-md px-2 py-0.5 text-xs font-semibold"
                :class="
                  m.aprobado
                    ? 'bg-tertiary-container text-on-tertiary-container'
                    : 'bg-error-container text-on-error-container'
                "
              >
                {{ m.aprobado ? 'Aprobado' : 'Dado de baja' }}
              </span>
            </td>
            <td class="px-3 py-2 tabular-nums">{{ m.aprobado_por ? `#${m.aprobado_por}` : '—' }}</td>
            <td class="px-3 py-2 tabular-nums text-on-surface-variant">{{ m.fecha_baja || '—' }}</td>
            <td class="px-3 py-2 text-right">
              <button
                v-if="m.aprobado"
                type="button"
                class="rounded-lg bg-error-container px-2 py-1 text-xs font-semibold text-on-error-container"
                @click="baja(m)"
              >
                Dar de baja
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
