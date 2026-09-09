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
import Icon from '@/shared/ui/Icon.vue'

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
    class="mb-3 flex items-center gap-2 rounded-xl border border-amethyst-200 bg-orchid-soft px-4 py-2 text-[12px] text-amethyst-900"
  >
    <span class="font-bold">Sugerencia:</span>
    ofrecer el producto #{{ recomendacion.product_id_recomendado }} — suele comprarse junto ({{
      (Number(recomendacion.confianza) * 100).toFixed(0)
    }}% de las veces).
  </div>

  <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
    <div class="border-b border-brand-200 bg-gradient-to-r from-brand-100/80 via-sage-100 to-brand-50 px-4 py-2.5">
      <div class="flex items-center gap-2">
        <h2 class="font-display text-[13px] font-bold text-brand-950">Ticket activo</h2>
        <span
          v-if="venta"
          class="rounded-full border border-brand-300 bg-white px-2 py-0.5 text-[10px] font-bold text-brand-900"
        >
          #{{ venta.venta_id }} · {{ (venta.lineas || []).length }} art.
        </span>
      </div>
    </div>
    <table class="w-full text-[13px]">
      <thead>
        <tr
          class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100"
        >
          <th class="px-4 py-2 text-left">Producto</th>
          <th class="px-3 py-2 text-right">Cant.</th>
          <th class="px-3 py-2 text-right">P. unit.</th>
          <th class="px-4 py-2 text-right">Subtotal</th>
          <th v-if="removible" class="px-3 py-2" />
        </tr>
      </thead>
      <tbody class="divide-y divide-brand-100/90 bg-white/80">
        <tr v-if="!venta || !venta.lineas.length">
          <td :colspan="removible ? 5 : 4" class="px-4 py-10 text-center text-slate-500">
            Sin líneas todavía — escaneá el primer producto.
          </td>
        </tr>
        <tr v-for="linea in venta?.lineas || []" :key="linea.venta_detalle_id">
          <td class="px-4 py-2.5">
            <span class="font-mono text-[12px] font-semibold text-brand-800">#{{ linea.product_id }}</span>
            <span
              v-if="Number(linea.retail_disc) > 0"
              class="ml-1.5 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800"
            >
              −{{ moneda(linea.retail_disc) }}
            </span>
            <span
              v-if="linea.margen_bajo_minimo"
              class="ml-1.5 rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-crimson-ruby"
            >
              margen bajo mínimo
            </span>
          </td>
          <td class="px-3 py-2.5 text-right tabular-nums">{{ linea.cantidad }}</td>
          <td class="px-3 py-2.5 text-right tabular-nums text-slate-600">{{ moneda(linea.sales_value) }}</td>
          <td class="px-4 py-2.5 text-right font-semibold tabular-nums text-slate-900">
            {{ moneda(linea.subtotal) }}
          </td>
          <td v-if="removible" class="px-3 py-2.5 text-right">
            <div class="flex justify-end gap-1">
              <button
                type="button"
                class="rounded-md p-1 text-slate-400 hover:bg-amethyst-50 hover:text-amethyst-700"
                title="Descuento manual"
                @click="abrirDescuento(linea)"
              >
                <Icon name="tag" :size="14" />
              </button>
              <button
                type="button"
                class="rounded-md p-1 text-slate-400 hover:bg-rose-50 hover:text-crimson-ruby"
                title="Quitar línea"
                @click="pedirRemocion(linea)"
              >
                <Icon name="trash" :size="14" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
      <tfoot>
        <tr class="border-t-2 border-brand-200 bg-brand-50/60">
          <td :colspan="removible ? 3 : 2" class="px-4 py-3 text-right text-[11px] font-bold uppercase tracking-wide text-slate-600">
            Total
          </td>
          <td class="px-4 py-3 text-right font-display text-lg font-extrabold tabular-nums text-brand-900">
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
    class="fixed inset-0 z-[60] flex items-start justify-center bg-black/40 p-4 pt-24 backdrop-blur-sm"
    @click.self="modal.abierto = false"
  >
    <div class="w-full max-w-md rounded-2xl border border-black/10 bg-white p-5 shadow-tier-2">
      <h3 class="mb-1 font-display text-base font-bold text-brand-950">
        Descuento manual — producto #{{ modal.linea?.product_id }}
      </h3>
      <p class="mb-4 text-[12px] text-slate-600">
        Requiere autorización de un Encargado_Tienda (o superior) distinto del cajero, sin excepción
        por monto.
      </p>

      <div class="mb-3 flex gap-2">
        <select
          v-model="modal.tipo"
          class="rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
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
          class="flex-1 rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
        />
      </div>
      <input
        v-model="modal.motivo"
        placeholder="Motivo del descuento (obligatorio)"
        class="mb-3 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
      />

      <p class="mb-1 text-[12px] font-semibold text-slate-600">Autorización del Encargado</p>
      <div class="mb-3 flex gap-2">
        <input
          v-model="modal.encargadoId"
          type="number"
          placeholder="ID empleado"
          class="w-1/2 rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
        />
        <input
          v-model="modal.encargadoPin"
          type="password"
          placeholder="PIN"
          class="w-1/2 rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
        />
      </div>

      <p v-if="errorModal" class="mb-2 text-[12px] text-crimson-ruby">{{ errorModal }}</p>

      <div class="flex justify-end gap-2">
        <button
          type="button"
          class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
          @click="modal.abierto = false"
        >
          Cancelar
        </button>
        <button
          type="button"
          class="rounded-xl bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700"
          @click="confirmarDescuento"
        >
          Aplicar descuento
        </button>
      </div>
    </div>
  </div>
</template>
