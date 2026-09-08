<script setup>
/** Ajuste de inventario tras conteo físico (FR-017). La diferencia la calcula el backend. */
import { reactive, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['ajustado'])

const form = reactive({ productId: null, cantidadFisica: null })
const resultado = ref(null)
const error = ref('')
const enviando = ref(false)

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    resultado.value = await inventarioApi.ajuste({
      productId: form.productId,
      tiendaId: props.tiendaId,
      cantidadFisica: form.cantidadFisica,
      empleadoId: props.empleadoId,
    })
    emit('ajustado', resultado.value)
  } catch (e) {
    error.value = e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <form class="space-y-3" @submit.prevent="enviar">
    <ProductoPicker v-model="form.productId" label="Producto contado" required />
    <label class="block text-[12px] font-semibold text-slate-600">
      Cantidad física contada
      <input
        v-model.number="form.cantidadFisica"
        type="number"
        min="0"
        required
        class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
    </label>
    <button
      type="submit"
      :disabled="enviando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Registrar ajuste
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
    <p v-if="resultado" class="text-sm text-on-surface-variant">
      Sistema {{ resultado.cantidad_sistema }} → físico {{ resultado.cantidad_fisica }} (diferencia
      {{ resultado.diferencia }})
    </p>
  </form>
</template>
