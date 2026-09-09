<script setup>
/** Ver la imagen del producto en grande + cambiarla (subir archivo o Unsplash). */
import { ref } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  producto: { type: Object, required: true },
  puedeEditar: { type: Boolean, default: false },
})
const emit = defineEmits(['actualizada'])

const url = ref(props.producto.imagen_url)
const cargando = ref('')
const error = ref('')
const fileInput = ref(null)

const esFoto = (u) => u && u.startsWith('http')

async function subir(e) {
  const file = e.target.files?.[0]
  if (!file) return
  error.value = ''
  cargando.value = 'subir'
  try {
    const p = await catalogoApi.subirImagen(props.producto.product_id, file)
    url.value = p.imagen_url
    emit('actualizada', p.imagen_url)
  } catch (err) {
    error.value =
      err.response?.data?.error?.message || err.response?.data?.detail || err.message
  } finally {
    cargando.value = ''
    if (e.target) e.target.value = ''
  }
}

async function unsplash() {
  error.value = ''
  cargando.value = 'unsplash'
  try {
    const p = await catalogoApi.imagenAuto(props.producto.product_id)
    if (p.imagen_url && p.imagen_url.startsWith('http')) {
      url.value = p.imagen_url
      emit('actualizada', p.imagen_url)
    } else {
      error.value = 'Unsplash no devolvió una imagen (límite de la API o sin coincidencia).'
    }
  } catch (err) {
    error.value =
      err.response?.data?.error?.message || err.response?.data?.detail || err.message
  } finally {
    cargando.value = ''
  }
}
</script>

<template>
  <div class="space-y-4">
    <div
      class="grid aspect-square w-full place-items-center overflow-hidden rounded-xl border border-brand-200 bg-brand-50"
    >
      <img v-if="esFoto(url)" :src="url" alt="" class="h-full w-full object-contain" />
      <span v-else class="flex flex-col items-center gap-2 text-brand-400">
        <Icon name="image" :size="40" />
        <span class="text-[12px]">Sin imagen — usa el ícono por categoría</span>
      </span>
    </div>

    <p class="text-[13px] text-slate-600">
      {{ producto.nombre || 'Producto sin nombre' }}
      <span class="text-slate-400">· ID {{ producto.product_id }}</span>
    </p>

    <div v-if="puedeEditar" class="flex flex-wrap gap-2">
      <button
        type="button"
        :disabled="Boolean(cargando)"
        class="inline-flex items-center gap-1.5 rounded-xl border border-brand-600 bg-brand-800 px-3.5 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-50"
        @click="fileInput.click()"
      >
        <Icon name="image" :size="16" />
        {{ cargando === 'subir' ? 'Subiendo…' : 'Subir imagen propia' }}
      </button>
      <button
        type="button"
        :disabled="Boolean(cargando)"
        class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:border-brand-400 disabled:opacity-50"
        @click="unsplash"
      >
        <Icon name="search" :size="16" />
        {{ cargando === 'unsplash' ? 'Buscando…' : 'Buscar en Unsplash' }}
      </button>
      <input
        ref="fileInput"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        class="hidden"
        @change="subir"
      />
    </div>
    <p v-else class="text-[12px] italic text-slate-400">
      Solo lectura — no tienes permisos para cambiar la imagen.
    </p>

    <p v-if="error" class="text-[12px] text-crimson-ruby">{{ error }}</p>
    <p class="text-[11px] text-slate-400">JPG, PNG o WEBP · hasta 5 MB.</p>
  </div>
</template>
