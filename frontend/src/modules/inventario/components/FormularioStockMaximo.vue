<script setup>
/** Define el stock máximo vigente por categoría y tienda (FR-037, Jefe de Operaciones). */
import { reactive, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['definido'])

const form = reactive({ productCategory: '', cantidadMaxima: null })
const error = ref('')
const enviando = ref(false)

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    const res = await inventarioApi.definirStockMaximo({
      productCategory: form.productCategory,
      tiendaId: props.tiendaId,
      cantidadMaxima: form.cantidadMaxima,
      empleadoId: props.empleadoId,
    })
    emit('definido', res)
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
    <h3 class="text-sm font-semibold text-on-surface">Stock máximo por categoría</h3>
    <input
      v-model="form.productCategory"
      placeholder="Categoría de producto"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <input
      v-model.number="form.cantidadMaxima"
      type="number"
      min="1"
      placeholder="Cantidad máxima"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <button
      type="submit"
      :disabled="enviando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Guardar máximo
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
