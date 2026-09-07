<script setup>
/**
 * Historial proveedor↔producto (Ronda 11, FR-044). Dos consultas de solo lectura
 * sobre el historial real de órdenes de compra. Sirve para que el Jefe de
 * Operaciones complete el proveedor cuando la sugerencia lo trae en `null`.
 */
import { ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'

const modo = ref('proveedor') // 'proveedor' | 'producto'
const id = ref(null)
const filas = ref([])
const error = ref('')
const cargando = ref(false)

async function consultar() {
  if (!id.value) return
  error.value = ''
  cargando.value = true
  try {
    filas.value =
      modo.value === 'proveedor'
        ? await comprasApi.productosDeProveedor(Number(id.value))
        : await comprasApi.proveedoresDeProducto(Number(id.value))
  } catch (e) {
    error.value = e.message
    filas.value = []
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
    <h3 class="mb-3 text-sm font-semibold text-on-surface">Historial proveedor ↔ producto</h3>

    <div class="mb-3 flex flex-wrap items-center gap-2">
      <select
        v-model="modo"
        class="rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
      >
        <option value="proveedor">Productos de un proveedor</option>
        <option value="producto">Proveedores de un producto</option>
      </select>
      <input
        v-model.number="id"
        type="number"
        :placeholder="modo === 'proveedor' ? 'ID de proveedor' : 'ID de producto'"
        class="w-40 rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
        @keyup.enter="consultar"
      />
      <button
        type="button"
        class="rounded-lg bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container"
        @click="consultar"
      >
        Consultar
      </button>
    </div>

    <p v-if="error" class="text-sm text-error">{{ error }}</p>

    <table v-if="filas.length" class="w-full text-sm">
      <thead>
        <tr class="text-left text-on-surface-variant">
          <th class="py-1">{{ modo === 'proveedor' ? 'Producto' : 'Proveedor' }}</th>
          <th class="py-1 text-right">Órdenes</th>
          <th class="py-1 text-right">Cantidad total</th>
          <th class="py-1">Última</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="f in filas"
          :key="modo === 'proveedor' ? f.product_id : f.proveedor_id"
          class="border-t border-outline-variant"
        >
          <td class="py-1">
            <template v-if="modo === 'proveedor'">
              #{{ f.product_id }} · {{ f.nombre || f.product_category || '—' }}
            </template>
            <template v-else> #{{ f.proveedor_id }} · {{ f.nombre || '—' }} </template>
          </td>
          <td class="py-1 text-right tabular-nums">{{ f.ordenes }}</td>
          <td class="py-1 text-right tabular-nums">{{ f.cantidad_total }}</td>
          <td class="py-1 text-on-surface-variant">{{ f.ultima_fecha || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!cargando && id" class="text-sm text-on-surface-variant">Sin historial.</p>
  </div>
</template>
