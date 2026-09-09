<script setup>
/**
 * Muestra las líneas de la venta en curso y su total. Dos acciones exigen doble
 * autorización de un empleado distinto del cajero (Principio anti-fraude):
 *  - remoción de línea (FR-027 de 001)
 *  - descuento manual (FR-009 de 003) — autorización de un Encargado_Tienda (o
 *    superior) que se re-autentica; el backend valida rol y que sea otro empleado,
 *    sin excepción por monto. Si el margen resultante cae bajo el mínimo, la línea
 *    se marca para revisión sin bloquear la venta (FR-010).
 */
import { reactive, ref, watch } from 'vue'
import { promocionesApi } from '@/services/promocionesApi'
import { prompt } from '@/shared/ui/dialogs'

const props = defineProps({
  venta: { type: Object, default: null },
  removible: { type: Boolean, default: true },
})

const emit = defineEmits(['remover', 'descuento'])

function moneda(v) {
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(
    Number(v || 0)
  )
}

// FR-003 (feature 005): recomendación de cross-sell por afinidad de canasta.
const recomendacion = ref(null)
watch(
  () => (props.venta?.lineas || []).map((l) => l.product_id).join(','),
  async (ids) => {
    recomendacion.value = null
    const productIds = ids ? ids.split(',').map(Number) : []
    if (!productIds.length || !props.removible) return
    try {
      const r = await promocionesApi.recomendacionCrossSell(productIds)
      recomendacion.value = r.recomendacion_disponible ? r : null
    } catch {
      recomendacion.value = null
    }
  }
)

async function pedirRemocion(linea) {
  const autoriza = await prompt({
    title: `Remover línea — producto ${linea.product_id}`,
    message: 'Requiere la autorización de un empleado distinto del cajero.',
    label: 'ID del empleado que autoriza',
    inputType: 'number',
    required: true,
    confirmText: 'Continuar',
  })
  if (!autoriza) return
  const motivo = await prompt({
    title: 'Motivo de la remoción',
    label: 'Motivo',
    confirmText: 'Remover línea',
    tone: 'danger',
  })
  if (motivo === null) return
  emit('remover', { lineaId: linea.venta_detalle_id, autorizaEmpleadoId: Number(autoriza), motivo })
}

// --- modal de descuento manual con autorización ---
const modal = reactive({
  abierto: false,
  linea: null,
  tipo: 'monto',
  valor: '',
  motivo: '',
  encargadoId: '',
  encargadoPin: '',
})
const errorModal = ref('')

function abrirDescuento(linea) {
  Object.assign(modal, {
    abierto: true,
    linea,
    tipo: 'monto',
    valor: '',
    motivo: '',
    encargadoId: '',
    encargadoPin: '',
  })
  errorModal.value = ''
}

function confirmarDescuento() {
  errorModal.value = ''
  if (!modal.valor || Number(modal.valor) <= 0) {
    errorModal.value = 'Indica un valor de descuento mayor a 0.'
    return
  }
  if (!modal.motivo.trim()) {
    errorModal.value = 'El motivo del descuento es obligatorio.'
    return
  }
  if (!modal.encargadoId || !modal.encargadoPin) {
    errorModal.value =
      'El Encargado_Tienda debe re-autenticarse (ID + PIN) para autorizar el descuento.'
    return
  }
  emit('descuento', {
    lineaId: modal.linea.venta_detalle_id,
    tipo: modal.tipo,
    valor: modal.valor,
    motivo: modal.motivo.trim(),
    empleadoAutorizaId: Number(modal.encargadoId),
  })
  modal.abierto = false
}
</script>

<template>
  <div
    v-if="recomendacion"
    class="mb-3 flex items-center gap-2 rounded-xl border border-tertiary bg-tertiary-container px-4 py-2 text-sm text-on-tertiary-container"
  >
    <span class="font-semibold">Sugerencia:</span>
    ofrecer el producto #{{ recomendacion.product_id_recomendado }} — suele comprarse junto ({{
      (Number(recomendacion.confianza) * 100).toFixed(0)
    }}% de las veces).
  </div>

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
          <td class="px-4 py-2">
            #{{ linea.product_id }}
            <span
              v-if="Number(linea.retail_disc) > 0"
              class="ml-1 rounded-full bg-tertiary-container px-2 py-0.5 text-xs text-on-tertiary-container"
            >
              −{{ moneda(linea.retail_disc) }}
            </span>
            <span
              v-if="linea.margen_bajo_minimo"
              class="ml-1 rounded-full bg-error-container px-2 py-0.5 text-xs font-semibold text-on-error-container"
            >
              margen bajo mínimo
            </span>
          </td>
          <td class="px-4 py-2 text-right tabular-nums">{{ linea.cantidad }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ moneda(linea.sales_value) }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ moneda(linea.subtotal) }}</td>
          <td v-if="removible" class="px-4 py-2 text-right">
            <div class="flex justify-end gap-2">
              <button
                type="button"
                class="text-xs font-semibold text-primary-container hover:underline"
                @click="abrirDescuento(linea)"
              >
                Descuento
              </button>
              <button
                type="button"
                class="text-xs font-semibold text-error hover:underline"
                @click="pedirRemocion(linea)"
              >
                Quitar
              </button>
            </div>
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

  <!-- Modal de descuento manual con autorización obligatoria (FR-009) -->
  <div
    v-if="modal.abierto"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="modal.abierto = false"
  >
    <div class="w-full max-w-md rounded-xl border border-outline-variant bg-surface p-5 shadow-xl">
      <h3 class="mb-1 text-sm font-bold text-on-surface">
        Descuento manual — producto #{{ modal.linea?.product_id }}
      </h3>
      <p class="mb-4 text-xs text-on-surface-variant">
        Requiere autorización de un Encargado_Tienda (o superior) distinto del cajero, sin excepción
        por monto.
      </p>

      <div class="mb-3 flex gap-2">
        <select
          v-model="modal.tipo"
          class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        >
          <option value="monto">Monto ($)</option>
          <option value="porcentaje">Porcentaje (%)</option>
        </select>
        <input
          v-model="modal.valor"
          type="number"
          min="0"
          step="0.01"
          placeholder="Valor"
          class="flex-1 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </div>
      <input
        v-model="modal.motivo"
        placeholder="Motivo del descuento (obligatorio)"
        class="mb-3 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />

      <p class="mb-1 text-xs font-semibold text-on-surface-variant">Autorización del Encargado</p>
      <div class="mb-3 flex gap-2">
        <input
          v-model="modal.encargadoId"
          type="number"
          placeholder="ID empleado"
          class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
        <input
          v-model="modal.encargadoPin"
          type="password"
          placeholder="PIN"
          class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </div>

      <p v-if="errorModal" class="mb-2 text-xs text-error">{{ errorModal }}</p>

      <div class="flex justify-end gap-2">
        <button
          type="button"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface"
          @click="modal.abierto = false"
        >
          Cancelar
        </button>
        <button
          type="button"
          class="rounded-lg bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container"
          @click="confirmarDescuento"
        >
          Aplicar descuento
        </button>
      </div>
    </div>
  </div>
</template>
