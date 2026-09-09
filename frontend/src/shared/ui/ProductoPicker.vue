<script setup>
/**
 * Selector de producto por **nombre o ID** con autocompletado (Principio XII:
 * nunca pedir un id "a memoria"). Usado por los formularios de operación de
 * Inventario. `v-model` = product_id seleccionado (o null).
 */
import { ref, watch } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import Icon from './Icon.vue'

const props = defineProps({
  modelValue: { type: Number, default: null },
  label: { type: String, default: 'Producto' },
  required: { type: Boolean, default: false },
  // Si se pasa, busca sólo entre los SKU con stock en esa tienda (vista /stock)
  // y el evento `seleccionado` entrega la fila completa (con costo, disponible…).
  tiendaId: { type: Number, default: null },
})
const emit = defineEmits(['update:modelValue', 'seleccionado'])

const texto = ref('')
const abierto = ref(false)
const cargando = ref(false)
const opciones = ref([])
const elegido = ref(null)
let deb

// El padre puede resetear a null tras enviar el formulario.
watch(
  () => props.modelValue,
  (v) => {
    if (v == null && elegido.value) {
      elegido.value = null
      texto.value = ''
    }
  }
)

watch(texto, (v) => {
  if (elegido.value && v !== etiqueta(elegido.value)) {
    elegido.value = null
    emit('update:modelValue', null)
  }
  clearTimeout(deb)
  const q = v.trim()
  if (q.length < 2) {
    opciones.value = []
    return
  }
  deb = setTimeout(async () => {
    cargando.value = true
    try {
      if (props.tiendaId) {
        const r = await inventarioApi.stock({ tiendaId: props.tiendaId, search: q, size: 12 })
        opciones.value = r.items
      } else {
        opciones.value = await inventarioApi.buscarProductos(q)
      }
      abierto.value = true
    } finally {
      cargando.value = false
    }
  }, 250)
})

function etiqueta(p) {
  return `${p.nombre || 'Producto sin nombre'} — ID ${p.product_id}`
}
function elegir(p) {
  elegido.value = p
  texto.value = etiqueta(p)
  opciones.value = []
  abierto.value = false
  emit('update:modelValue', p.product_id)
  emit('seleccionado', p)
}
function limpiar() {
  texto.value = ''
  elegido.value = null
  opciones.value = []
  emit('update:modelValue', null)
}
function cerrarDiferido() {
  setTimeout(() => (abierto.value = false), 150)
}
</script>

<template>
  <div class="relative">
    <label class="mb-1 block text-[12px] font-semibold text-slate-600">
      {{ label }} <span v-if="required" class="text-crimson-ruby">*</span>
    </label>
    <div class="relative">
      <Icon
        name="search"
        :size="16"
        class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
      />
      <input
        v-model="texto"
        type="text"
        :required="required && !modelValue"
        placeholder="Escribí nombre o ID…"
        autocomplete="off"
        class="h-10 w-full rounded-xl border border-brand-300 bg-white pl-9 pr-8 text-[13px] text-slate-800 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        @focus="opciones.length && (abierto = true)"
        @blur="cerrarDiferido"
      />
      <button
        v-if="texto"
        type="button"
        class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
        @click="limpiar"
      >
        <Icon name="x" :size="15" />
      </button>
    </div>

    <ul
      v-if="abierto && (opciones.length || cargando)"
      class="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-brand-200 bg-white py-1 shadow-card-hover"
    >
      <li v-if="cargando" class="px-3 py-2 text-[12px] text-slate-400">Buscando…</li>
      <li
        v-for="p in opciones"
        :key="p.product_id"
        class="cursor-pointer px-3 py-2 hover:bg-brand-50"
        @mousedown.prevent="elegir(p)"
      >
        <div class="text-[13px] font-medium text-slate-900">
          {{ p.nombre || 'Producto sin nombre' }}
        </div>
        <div class="text-[11px] text-slate-500">
          ID {{ p.product_id }}
          <template v-if="p.marca"> · {{ p.marca }}</template>
          <template v-if="p.product_category"> · {{ p.product_category }}</template>
          <template v-if="p.clasificacion_abc"> · ABC {{ p.clasificacion_abc }}</template>
        </div>
      </li>
      <li v-if="!cargando && !opciones.length" class="px-3 py-2 text-[12px] text-slate-400">
        Sin coincidencias
      </li>
    </ul>
  </div>
</template>
