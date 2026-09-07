<script setup>
/** Registro de factura de proveedor (FR-033). Requiere una orden en estado 'recibida'. */
import { reactive, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'

const props = defineProps({ empleadoId: { type: Number, required: true } })
const emit = defineEmits(['registrada'])

const form = reactive({
  ordenId: null,
  numeroFactura: '',
  montoTotal: '',
  fechaEmision: '',
  fechaVencimiento: '',
})
const error = ref('')
const enviando = ref(false)

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    const factura = await comprasApi.crearFactura({
      ordenId: Number(form.ordenId),
      numeroFactura: form.numeroFactura,
      montoTotal: form.montoTotal,
      fechaEmision: form.fechaEmision,
      fechaVencimiento: form.fechaVencimiento,
      empleadoRegistraId: props.empleadoId,
    })
    emit('registrada', factura)
  } catch (e) {
    error.value = e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <form
    class="space-y-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    @submit.prevent="enviar"
  >
    <h3 class="text-sm font-semibold text-on-surface">Registrar factura de proveedor</h3>
    <input
      v-model.number="form.ordenId"
      type="number"
      placeholder="ID de orden (recibida)"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <input
      v-model="form.numeroFactura"
      placeholder="Número de factura"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <input
      v-model="form.montoTotal"
      type="number"
      step="0.01"
      placeholder="Monto total"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <div class="flex gap-3">
      <label class="w-1/2 text-xs text-on-surface-variant">
        Emisión
        <input
          v-model="form.fechaEmision"
          type="date"
          required
          class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="w-1/2 text-xs text-on-surface-variant">
        Vencimiento
        <input
          v-model="form.fechaVencimiento"
          type="date"
          required
          class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
    </div>
    <button
      type="submit"
      :disabled="enviando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Registrar factura
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
