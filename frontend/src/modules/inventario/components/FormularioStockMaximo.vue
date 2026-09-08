<script setup>
/** Define el stock máximo vigente por categoría y tienda (FR-037, Jefe de Operaciones).
 *  La categoría se elige (escribiendo para filtrar) de las que ya existen en el
 *  catálogo — no hay alta de categoría suelta: nace cuando un producto la usa. */
import { reactive, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import CategoriaPicker from '@/shared/ui/CategoriaPicker.vue'

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
  <form class="space-y-3" @submit.prevent="enviar">
    <div>
      <CategoriaPicker
        v-model="form.productCategory"
        placeholder="Escribí para filtrar…"
        required
      />
      <p class="mt-1 text-[11px] text-slate-400">
        Categorías del catálogo. Una categoría nueva aparece al crear un producto con ella (Jefe
        Comercial).
      </p>
    </div>
    <label class="block text-[12px] font-semibold text-slate-600">
      Cantidad máxima
      <input
        v-model.number="form.cantidadMaxima"
        type="number"
        min="1"
        required
        class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
    </label>
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
