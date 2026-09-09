<script setup>
/**
 * Alta de producto (FR-009/FR-012/FR-013). Si nombre/categoría se dejan vacíos,
 * el backend intenta autocompletar por el código de barras vía Open Food Facts.
 * La clasificación ancla/nicho es obligatoria.
 */
import { reactive, ref } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'
import Btn from '@/shared/ui/Btn.vue'

const emit = defineEmits(['creado'])

const form = reactive({
  codigoBarras: '',
  nombre: '',
  categoria: '',
  marca: '',
  costo: '',
  precioBase: '',
  esPerecedero: false,
  vidaUtilDias: null,
  clasificacion: 'nicho',
})
const error = ref('')
const aviso = ref('')
const enviando = ref(false)

async function enviar() {
  error.value = ''
  aviso.value = ''
  enviando.value = true
  try {
    const p = await catalogoApi.crear({
      codigoBarras: form.codigoBarras,
      nombre: form.nombre,
      categoria: form.categoria,
      marca: form.marca,
      costo: form.costo,
      precioBase: form.precioBase,
      esPerecedero: form.esPerecedero,
      vidaUtilDias: form.vidaUtilDias,
      clasificacion: form.clasificacion,
    })
    aviso.value = p.autocompletado
      ? `Alta creada (datos autocompletados desde Open Food Facts): ${p.nombre}`
      : `Alta creada: ${p.nombre || p.product_id}`
    emit('creado', p)
    form.codigoBarras = ''
    form.nombre = ''
    form.categoria = ''
    form.marca = ''
  } catch (e) {
    error.value = e.message
  } finally {
    enviando.value = false
  }
}

const inputClass =
  'mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none'
</script>

<template>
  <form class="space-y-3" @submit.prevent="enviar">
    <label class="block text-[12px] font-semibold text-slate-600">
      Código de barras
      <input v-model="form.codigoBarras" required :class="inputClass" />
    </label>
    <div class="grid grid-cols-2 gap-3">
      <label class="block text-[12px] font-semibold text-slate-600">
        Nombre
        <input v-model="form.nombre" placeholder="Se autocompleta si se deja vacío" :class="inputClass" />
      </label>
      <label class="block text-[12px] font-semibold text-slate-600">
        Categoría
        <input v-model="form.categoria" :class="inputClass" />
      </label>
      <label class="block text-[12px] font-semibold text-slate-600">
        Costo
        <input v-model="form.costo" type="number" step="0.01" required :class="inputClass" />
      </label>
      <label class="block text-[12px] font-semibold text-slate-600">
        Precio base
        <input v-model="form.precioBase" type="number" step="0.01" required :class="inputClass" />
      </label>
    </div>
    <div class="flex flex-wrap items-center gap-4">
      <label class="flex items-center gap-2 text-[12px] font-semibold text-slate-600">
        <input v-model="form.esPerecedero" type="checkbox" /> Perecedero
      </label>
      <label v-if="form.esPerecedero" class="text-[12px] font-semibold text-slate-600">
        Vida útil (días)
        <input v-model.number="form.vidaUtilDias" type="number" min="1" class="mt-1 w-32 rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
      </label>
      <label class="ml-auto text-[12px] font-semibold text-slate-600">
        Clasificación
        <select v-model="form.clasificacion" class="mt-1 block rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
          <option value="ancla">Ancla</option>
          <option value="nicho">Nicho</option>
        </select>
      </label>
    </div>
    <p v-if="aviso" class="rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-sm text-brand-800">
      {{ aviso }}
    </p>
    <p v-if="error" class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-crimson-ruby">{{ error }}</p>
    <div class="flex justify-end pt-1">
      <Btn variant="primary" type="submit" :disabled="enviando">
        {{ enviando ? 'Creando…' : 'Crear producto' }}
      </Btn>
    </div>
  </form>
</template>
