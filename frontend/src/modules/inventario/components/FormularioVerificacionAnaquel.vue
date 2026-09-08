<script setup>
/** Verificación diaria de anaquel de un producto clasificación A (FR-042, Reponedor). */
import { reactive, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['registrada'])

const form = reactive({ productId: null, disponible: true })
const error = ref('')
const ok = ref('')
const enviando = ref(false)

async function enviar() {
  error.value = ''
  ok.value = ''
  enviando.value = true
  try {
    await inventarioApi.verificacionAnaquel({
      productId: form.productId,
      tiendaId: props.tiendaId,
      disponible: form.disponible,
      empleadoId: props.empleadoId,
    })
    ok.value = 'Verificación registrada'
    emit('registrada')
  } catch (e) {
    error.value = e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <form class="space-y-3" @submit.prevent="enviar">
    <ProductoPicker v-model="form.productId" label="Producto a verificar" required />
    <label class="flex items-center gap-2 text-sm text-on-surface-variant">
      <input v-model="form.disponible" type="checkbox" />
      Producto disponible en anaquel
    </label>
    <button
      type="submit"
      :disabled="enviando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Registrar verificación
    </button>
    <p v-if="ok" class="text-sm text-on-tertiary-container">{{ ok }}</p>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
