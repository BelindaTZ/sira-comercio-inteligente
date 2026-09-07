<script setup>
/**
 * Autorización de pago a proveedor (FR-034, T073). Control de doble persona
 * entre pasos separados: quien usa este formulario es el AUTORIZADOR (su sesión
 * firma la operación); indica además el ID del empleado que registró el pago en
 * el paso previo, que debe ser distinto de él. El backend rechaza (403) si el
 * autorizador no coincide con el usuario autenticado o si registra == autoriza.
 */
import { computed, reactive, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'

const props = defineProps({
  // Empleado en sesión = autorizador del pago.
  empleadoAutorizaId: { type: Number, required: true },
})
const emit = defineEmits(['pagado'])

const form = reactive({
  facturaId: null,
  monto: '',
  medioPagoId: 1,
  referencia: '',
  empleadoRegistraId: null,
})
const error = ref('')
const enviando = ref(false)

const registranteInvalido = computed(
  () =>
    form.empleadoRegistraId != null && Number(form.empleadoRegistraId) === props.empleadoAutorizaId
)

async function enviar() {
  error.value = ''
  if (registranteInvalido.value) {
    error.value = 'Quien registró el pago debe ser distinto de quien lo autoriza'
    return
  }
  enviando.value = true
  try {
    const pago = await comprasApi.registrarPago(Number(form.facturaId), {
      monto: form.monto,
      medioPagoId: Number(form.medioPagoId),
      referencia: form.referencia,
      empleadoRegistraId: Number(form.empleadoRegistraId),
      empleadoAutorizaId: props.empleadoAutorizaId,
    })
    emit('pagado', pago)
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
    <h3 class="text-sm font-semibold text-on-surface">Autorizar pago a proveedor</h3>
    <p class="text-xs text-on-surface-variant">
      Autorizas como empleado #{{ empleadoAutorizaId }}.
    </p>
    <input
      v-model.number="form.facturaId"
      type="number"
      placeholder="ID de factura"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <div class="flex gap-3">
      <input
        v-model="form.monto"
        type="number"
        step="0.01"
        placeholder="Monto"
        required
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
      <select
        v-model.number="form.medioPagoId"
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      >
        <option :value="1">Efectivo</option>
        <option :value="2">Tarjeta</option>
        <option :value="3">Transferencia</option>
        <option :value="4">Billetera Digital</option>
      </select>
    </div>
    <input
      v-model="form.referencia"
      placeholder="Referencia (opcional)"
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <label class="block text-xs text-on-surface-variant">
      ID del empleado que REGISTRÓ el pago (paso 1, distinto de ti)
      <input
        v-model.number="form.empleadoRegistraId"
        type="number"
        required
        class="mt-1 w-full rounded-lg border px-3 py-2 text-on-surface"
        :class="
          registranteInvalido
            ? 'border-error bg-error-container'
            : 'border-outline-variant bg-surface'
        "
      />
    </label>
    <button
      type="submit"
      :disabled="enviando || registranteInvalido"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Autorizar y registrar pago
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
