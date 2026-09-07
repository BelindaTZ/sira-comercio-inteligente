<script setup>
/**
 * Muestra las líneas de la venta en curso y su total. La remoción de una línea
 * exige doble autorización (FR-027): se pide el id del empleado que autoriza.
 */
defineProps({
  venta: { type: Object, default: null },
  removible: { type: Boolean, default: true },
})

const emit = defineEmits(['remover'])

function moneda(v) {
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(
    Number(v || 0)
  )
}

function pedirRemocion(linea) {
  const autoriza = window.prompt(
    `Remoción de línea (producto ${linea.product_id}).\n` +
      'ID del EMPLEADO que autoriza (debe ser distinto del cajero):'
  )
  if (!autoriza) return
  const motivo = window.prompt('Motivo de la remoción:') || ''
  emit('remover', { lineaId: linea.venta_detalle_id, autorizaEmpleadoId: Number(autoriza), motivo })
}
</script>

<template>
  <div class="rounded-xl border border-outline-variant bg-surface-container-lowest">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-outline-variant text-left text-on-surface-variant">
          <th class="px-4 py-2 font-semibold">Producto</th>
          <th class="px-4 py-2 text-right font-semibold">Cant.</th>
          <th class="px-4 py-2 text-right font-semibold">P. Unit.</th>
          <th class="px-4 py-2 text-right font-semibold">Subtotal</th>
          <th v-if="removible" class="px-4 py-2" />
        </tr>
      </thead>
      <tbody>
        <tr v-if="!venta || !venta.lineas.length">
          <td :colspan="removible ? 5 : 4" class="px-4 py-6 text-center text-on-surface-variant">
            Sin líneas todavía
          </td>
        </tr>
        <tr
          v-for="linea in venta?.lineas || []"
          :key="linea.venta_detalle_id"
          class="border-b border-outline-variant last:border-0"
        >
          <td class="px-4 py-2">#{{ linea.product_id }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ linea.cantidad }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ moneda(linea.sales_value) }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ moneda(linea.subtotal) }}</td>
          <td v-if="removible" class="px-4 py-2 text-right">
            <button
              type="button"
              class="text-xs font-semibold text-error hover:underline"
              @click="pedirRemocion(linea)"
            >
              Quitar
            </button>
          </td>
        </tr>
      </tbody>
      <tfoot>
        <tr class="border-t border-outline-variant">
          <td :colspan="removible ? 3 : 2" class="px-4 py-3 text-right font-semibold">TOTAL</td>
          <td class="px-4 py-3 text-right text-lg font-bold tabular-nums">
            {{ moneda(venta?.total) }}
          </td>
          <td v-if="removible" />
        </tr>
      </tfoot>
    </table>
  </div>
</template>
