<script setup>
/**
 * Combobox de categoría: se escribe para filtrar las categorías existentes del
 * catálogo (no hay alta de categoría suelta — nace al crear un producto).
 * `v-model` = la categoría elegida (string) o '' .
 */
import { computed, onMounted, ref } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'
import Icon from './Icon.vue'

defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Categoría' },
  placeholder: { type: String, default: 'Todas las categorías' },
  required: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const todas = ref([])
const texto = ref('')
const abierto = ref(false)

onMounted(async () => {
  try {
    todas.value = await catalogoApi.categorias()
  } catch {
    /* el combobox queda vacío pero no rompe */
  }
})

const filtradas = computed(() => {
  const q = texto.value.trim().toLowerCase()
  const base = q ? todas.value.filter((c) => c.toLowerCase().includes(q)) : todas.value
  return base.slice(0, 40)
})

function elegir(c) {
  emit('update:modelValue', c)
  texto.value = c
  abierto.value = false
}
function limpiar() {
  emit('update:modelValue', '')
  texto.value = ''
}
function cerrarDiferido() {
  setTimeout(() => (abierto.value = false), 150)
}
</script>

<template>
  <div class="relative">
    <label v-if="label" class="mb-1 block text-[12px] font-semibold text-slate-600">
      {{ label }} <span v-if="required" class="text-crimson-ruby">*</span>
    </label>
    <div class="relative">
      <Icon
        name="filter"
        :size="15"
        class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
      />
      <input
        v-model="texto"
        type="text"
        :placeholder="modelValue || placeholder"
        :required="required && !modelValue"
        autocomplete="off"
        class="h-10 w-full rounded-xl border border-brand-300 bg-white pl-8 pr-8 text-[13px] text-slate-800 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        @focus="abierto = true"
        @blur="cerrarDiferido"
      />
      <button
        v-if="modelValue || texto"
        type="button"
        class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
        @click="limpiar"
      >
        <Icon name="x" :size="14" />
      </button>
    </div>
    <ul
      v-if="abierto && filtradas.length"
      class="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-brand-200 bg-white py-1 shadow-card-hover"
    >
      <li
        v-for="c in filtradas"
        :key="c"
        class="cursor-pointer px-3 py-1.5 text-[12px] hover:bg-brand-50"
        :class="c === modelValue ? 'font-semibold text-brand-900' : 'text-slate-700'"
        @mousedown.prevent="elegir(c)"
      >
        {{ c }}
      </li>
    </ul>
  </div>
</template>
