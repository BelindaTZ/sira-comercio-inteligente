<script setup>
/**
 * Crea una orden de compra a partir de la sugerencia del sistema (FR-023/FR-024).
 * Si el usuario cambia alguna cantidad respecto a la sugerencia, se exige un
 * `motivo_desviacion` (el backend lo valida; aquí se pide de forma proactiva).
 */
import { computed, reactive, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['creada'])

const sugerencias = ref([])
const lineas = reactive([])
const proveedorId = ref(null)
const motivo = ref('')
const error = ref('')
const cargando = ref(false)

async function cargarSugerencia() {
  error.value = ''
  sugerencias.value = await comprasApi.sugerencias(props.tiendaId)
  lineas.splice(0)
  for (const s of sugerencias.value) {
    lineas.push({
      product_id: s.product_id,
      cantidad: s.cantidad_sugerida,
      cantidad_sugerida: s.cantidad_sugerida,
      costo_unitario: '1.00',
    })
    if (!proveedorId.value && s.proveedor_id) proveedorId.value = s.proveedor_id
  }
}

const difiere = computed(() => lineas.some((l) => Number(l.cantidad) !== l.cantidad_sugerida))

async function crear() {
  error.value = ''
  cargando.value = true
  try {
    const orden = await comprasApi.crearOrden({
      proveedorId: Number(proveedorId.value),
      tiendaId: props.tiendaId,
      empleadoId: props.empleadoId,
      lineas: lineas.map((l) => ({
        product_id: l.product_id,
        cantidad: Number(l.cantidad),
        costo_unitario: l.costo_unitario,
      })),
      motivoDesviacion: difiere.value ? motivo.value : null,
    })
    emit('creada', orden)
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="space-y-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-on-surface">Nueva orden de compra</h3>
      <button
        type="button"
        class="text-xs font-semibold text-primary-container hover:underline"
        @click="cargarSugerencia"
      >
        Cargar sugerencia semanal
      </button>
    </div>

    <input
      v-model.number="proveedorId"
      type="number"
      placeholder="ID de proveedor"
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />

    <table v-if="lineas.length" class="w-full text-sm">
      <thead>
        <tr class="text-left text-on-surface-variant">
          <th class="py-1">Producto</th>
          <th class="py-1 text-right">Sugerido</th>
          <th class="py-1 text-right">Cantidad</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="l in lineas" :key="l.product_id">
          <td class="py-1">#{{ l.product_id }}</td>
          <td class="py-1 text-right text-on-surface-variant">{{ l.cantidad_sugerida }}</td>
          <td class="py-1 text-right">
            <input
              v-model.number="l.cantidad"
              type="number"
              min="1"
              class="w-20 rounded border border-outline-variant bg-surface px-2 py-1 text-right"
            />
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="text-sm text-on-surface-variant">
      Sin sugerencias: no hay productos bajo su punto de reposición.
    </p>

    <textarea
      v-if="difiere"
      v-model="motivo"
      rows="2"
      placeholder="Motivo de la desviación respecto a la sugerencia (obligatorio)"
      class="w-full rounded-lg border border-error bg-surface px-3 py-2 text-on-surface"
    />

    <button
      type="button"
      :disabled="cargando || !lineas.length || !proveedorId"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
      @click="crear"
    >
      Crear orden
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </div>
</template>
