<script setup>
/** Registro de merma (FR-018). Queda 'pendiente' hasta que el Encargado la valide (FR-019). */
import { reactive, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['registrada'])

const CAUSAS = ['caducidad', 'robo', 'rotura', 'error_humano']
const form = reactive({ productId: null, cantidad: null, causa: 'caducidad', loteId: null })
const error = ref('')
const enviando = ref(false)

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    const merma = await inventarioApi.merma({
      productId: form.productId,
      tiendaId: props.tiendaId,
      cantidad: form.cantidad,
      causa: form.causa,
      empleadoId: props.empleadoId,
      loteId: form.loteId || null,
    })
    emit('registrada', merma)
    form.productId = null
    form.cantidad = null
    form.loteId = null
  } catch (e) {
    error.value = e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <form class="space-y-3" @submit.prevent="enviar">
    <ProductoPicker v-model="form.productId" label="Producto" required />
    <div class="flex gap-3">
      <input
        v-model.number="form.cantidad"
        type="number"
        min="1"
        placeholder="Cantidad"
        required
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
      <input
        v-model.number="form.loteId"
        type="number"
        placeholder="Lote (opcional)"
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
    </div>
    <select
      v-model="form.causa"
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    >
      <option v-for="c in CAUSAS" :key="c" :value="c">{{ c.replace('_', ' ') }}</option>
    </select>
    <button
      type="submit"
      :disabled="enviando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Registrar merma
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
