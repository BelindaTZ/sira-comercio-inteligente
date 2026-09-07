<script setup>
/**
 * Alta de producto (FR-009/FR-012/FR-013). Si nombre/categoría se dejan vacíos,
 * el backend intenta autocompletar por el código de barras vía Open Food Facts.
 * La clasificación ancla/nicho es obligatoria.
 */
import { reactive, ref } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'

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
</script>

<template>
  <form
    class="space-y-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    @submit.prevent="enviar"
  >
    <h3 class="text-sm font-semibold text-on-surface">Nuevo producto</h3>
    <input
      v-model="form.codigoBarras"
      placeholder="Código de barras (real)"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <div class="flex gap-3">
      <input
        v-model="form.nombre"
        placeholder="Nombre (se autocompleta si se deja vacío)"
        class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
      <input
        v-model="form.categoria"
        placeholder="Categoría"
        class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
    </div>
    <div class="flex gap-3">
      <input
        v-model="form.costo"
        type="number"
        step="0.01"
        placeholder="Costo"
        required
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
      <input
        v-model="form.precioBase"
        type="number"
        step="0.01"
        placeholder="Precio base"
        required
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
    </div>
    <div class="flex items-center gap-4">
      <label class="flex items-center gap-2 text-sm text-on-surface-variant">
        <input v-model="form.esPerecedero" type="checkbox" />
        Perecedero
      </label>
      <input
        v-if="form.esPerecedero"
        v-model.number="form.vidaUtilDias"
        type="number"
        min="1"
        placeholder="Vida útil (días)"
        class="w-40 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <select
        v-model="form.clasificacion"
        class="ml-auto rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      >
        <option value="ancla">Ancla</option>
        <option value="nicho">Nicho</option>
      </select>
    </div>
    <button
      type="submit"
      :disabled="enviando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Crear producto
    </button>
    <p v-if="aviso" class="text-sm text-on-tertiary-container">{{ aviso }}</p>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
