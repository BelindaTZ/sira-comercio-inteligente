<script setup>
/** Ubica un SKU en sala (pasillo/góndola/nivel). Reponedor / Encargado (FR-013). */
import { reactive, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'

const props = defineProps({
  producto: { type: Object, required: true }, // fila de /inventario/stock
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['guardada'])

const form = reactive({
  pasillo: props.producto.pasillo || '',
  gondola: props.producto.gondola || '',
  nivel: '',
})
const error = ref('')
const enviando = ref(false)

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    await inventarioApi.definirUbicacion({
      productId: props.producto.product_id,
      tiendaId: props.tiendaId,
      pasillo: form.pasillo,
      gondola: form.gondola,
      nivel: form.nivel,
      empleadoId: props.empleadoId,
    })
    emit('guardada')
  } catch (e) {
    error.value = e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <form class="space-y-3" @submit.prevent="enviar">
    <p class="text-[13px] text-slate-600">
      {{ producto.nombre || 'Producto sin nombre' }}
      <span class="text-slate-400">· ID {{ producto.product_id }}</span>
    </p>
    <label class="block text-[12px] font-semibold text-slate-600">
      Pasillo <span class="text-crimson-ruby">*</span>
      <input
        v-model="form.pasillo"
        required
        placeholder="Pasillo 01 · Cámara Fría A"
        class="mt-1 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-[13px] text-slate-800"
      />
    </label>
    <div class="flex gap-3">
      <label class="block flex-1 text-[12px] font-semibold text-slate-600">
        Góndola
        <input
          v-model="form.gondola"
          placeholder="G-03"
          class="mt-1 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-[13px] text-slate-800"
        />
      </label>
      <label class="block flex-1 text-[12px] font-semibold text-slate-600">
        Nivel
        <input
          v-model="form.nivel"
          placeholder="Nivel medio"
          class="mt-1 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-[13px] text-slate-800"
        />
      </label>
    </div>
    <button
      type="submit"
      :disabled="enviando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Guardar ubicación
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
