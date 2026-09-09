<script setup>
/**
 * Historial proveedor↔producto (Ronda 11, FR-044). Dos consultas de solo lectura
 * sobre el historial real de órdenes de compra. Sirve para que el Jefe de
 * Operaciones complete el proveedor cuando la sugerencia lo trae en `null`.
 */
import { onMounted, ref, watch } from 'vue'
import { comprasApi } from '@/services/comprasApi'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'

const modo = ref('proveedor') // 'proveedor' | 'producto'
const proveedores = ref([])
const proveedorId = ref(null)
const productId = ref(null)
const filas = ref([])
const error = ref('')
const cargando = ref(false)

onMounted(async () => {
  proveedores.value = await comprasApi.proveedores().catch(() => [])
})

watch([modo, proveedorId, productId], consultar)

async function consultar() {
  const id = modo.value === 'proveedor' ? proveedorId.value : productId.value
  if (!id) {
    filas.value = []
    return
  }
  error.value = ''
  cargando.value = true
  try {
    filas.value =
      modo.value === 'proveedor'
        ? await comprasApi.productosDeProveedor(Number(id))
        : await comprasApi.proveedoresDeProducto(Number(id))
  } catch (e) {
    error.value = e.message
    filas.value = []
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="rounded-xl border border-brand-200 bg-white p-4">
    <h3 class="mb-3 text-[13px] font-bold text-brand-950">Historial proveedor ↔ producto</h3>

    <div class="mb-3 space-y-2">
      <select
        v-model="modo"
        class="w-full rounded-lg border border-brand-300 bg-white px-2 py-1.5 text-[12px] text-slate-800"
      >
        <option value="proveedor">Productos de un proveedor</option>
        <option value="producto">Proveedores de un producto</option>
      </select>
      <select
        v-if="modo === 'proveedor'"
        v-model.number="proveedorId"
        class="w-full rounded-lg border border-brand-300 bg-white px-2 py-1.5 text-[12px] text-slate-800"
      >
        <option :value="null">Elegí un proveedor…</option>
        <option v-for="p in proveedores" :key="p.proveedor_id" :value="p.proveedor_id">
          {{ p.nombre }}
        </option>
      </select>
      <ProductoPicker v-else v-model="productId" label="Producto" />
    </div>

    <p v-if="error" class="text-sm text-crimson-ruby">{{ error }}</p>

    <table v-if="filas.length" class="w-full text-[12px]">
      <thead>
        <tr class="text-left text-slate-400">
          <th class="py-1 font-semibold">{{ modo === 'proveedor' ? 'Producto' : 'Proveedor' }}</th>
          <th class="py-1 text-right font-semibold">Órdenes</th>
          <th class="py-1 text-right font-semibold">Cant. total</th>
          <th class="py-1 font-semibold">Última</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="f in filas"
          :key="modo === 'proveedor' ? f.product_id : f.proveedor_id"
          class="border-t border-brand-100"
        >
          <td class="py-1.5 text-slate-700">
            <template v-if="modo === 'proveedor'">
              {{ f.nombre || f.product_category || `Producto #${f.product_id}` }}
            </template>
            <template v-else>{{ f.nombre || `Proveedor #${f.proveedor_id}` }}</template>
          </td>
          <td class="py-1.5 text-right tabular-nums">{{ f.ordenes }}</td>
          <td class="py-1.5 text-right tabular-nums">{{ f.cantidad_total }}</td>
          <td class="py-1.5 text-slate-500">{{ f.ultima_fecha || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="cargando" class="text-[12px] text-slate-400">Buscando…</p>
    <p
      v-else-if="(modo === 'proveedor' && proveedorId) || (modo === 'producto' && productId)"
      class="text-[12px] text-slate-400"
    >
      Sin historial.
    </p>
  </div>
</template>
