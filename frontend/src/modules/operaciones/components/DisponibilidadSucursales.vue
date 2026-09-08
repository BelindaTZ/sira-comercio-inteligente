<script setup>
/**
 * US1 / FR-001 — disponibilidad de un producto en todas las sucursales de la red,
 * en una sola vista. Reutilizable: la pantalla de sugerencias de compra puede
 * embeber esta misma tabla con el prop `filas` (FR-002).
 */
import { ref } from 'vue'
import { trasladosApi } from '@/services/trasladosApi'

const props = defineProps({
  filas: { type: Array, default: null },
  titulo: { type: String, default: 'Disponibilidad por sucursal' },
})

const productId = ref('')
const disponibilidad = ref(props.filas || [])
const error = ref('')

async function consultar() {
  error.value = ''
  try {
    const data = await trasladosApi.disponibilidadSucursales(Number(productId.value))
    disponibilidad.value = data.disponibilidad
  } catch (e) {
    error.value = e.message
    disponibilidad.value = []
  }
}
</script>

<template>
  <section>
    <h2 class="mb-2 text-sm font-semibold text-on-surface">{{ titulo }}</h2>
    <p
      v-if="error"
      class="mb-3 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form v-if="!props.filas" class="mb-3 flex items-end gap-3" @submit.prevent="consultar">
      <label class="text-xs text-on-surface-variant">
        Producto (id)
        <input
          v-model="productId"
          type="number"
          required
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

    <table v-if="disponibilidad.length" class="w-full text-sm">
      <thead class="text-left text-xs text-on-surface-variant">
        <tr>
          <th class="py-1">Tienda</th>
          <th class="py-1 text-right">Stock disponible</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in disponibilidad" :key="d.tienda_id" class="border-t border-outline-variant">
          <td class="py-1.5 text-on-surface">{{ d.nombre_tienda }}</td>
          <td
            class="py-1.5 text-right"
            :class="d.cantidad_disponible > 0 ? 'text-on-surface' : 'text-on-surface-variant'"
          >
            {{ d.cantidad_disponible }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
