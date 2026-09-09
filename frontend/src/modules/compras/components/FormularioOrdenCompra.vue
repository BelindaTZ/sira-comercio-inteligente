<script setup>
/**
 * Crear solicitud de pedido (orden de compra) — FR-023/FR-024/FR-029.
 *
 * Dos modos:
 *  - **Automática (programada)**: se carga la sugerencia semanal del sistema
 *    (productos bajo su punto de reposición) y se ajustan cantidades.
 *  - **Especial**: pedido fuera del calendario pactado; el motivo es obligatorio.
 *
 * El proveedor se elige de una lista cargada (nunca un id a memoria, Principio XII).
 * Si las líneas se apartan de la sugerencia, el backend exige `motivo_desviacion`
 * y aquí se pide de forma proactiva.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { comprasApi } from '@/services/comprasApi'
import { inventarioApi } from '@/services/inventarioApi'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
  // { product_id, nombre, cantidad } — llega desde "Solicitar reposición" de Inventario
  prefill: { type: Object, default: null },
})
const emit = defineEmits(['creada', 'cerrar'])

const proveedores = ref([])
const proveedorId = ref(null)
const tipo = ref(props.prefill ? 'especial' : 'programada')
const lineas = reactive([])
const motivo = ref('')
const error = ref('')
const cargando = ref(false)
const cargandoSugerencia = ref(false)
const nuevoProductId = ref(null)

const costoPorProducto = new Map()

const proveedorSel = computed(() =>
  proveedores.value.find((p) => p.proveedor_id === proveedorId.value),
)

const difiere = computed(
  () =>
    tipo.value === 'especial' ||
    lineas.some((l) => l.cantidad_sugerida == null || Number(l.cantidad) !== l.cantidad_sugerida),
)

const total = computed(() =>
  lineas.reduce((s, l) => s + Number(l.cantidad || 0) * Number(l.costo_unitario || 0), 0),
)

const puedeCrear = computed(
  () =>
    proveedorId.value &&
    lineas.length > 0 &&
    lineas.every((l) => Number(l.cantidad) > 0 && Number(l.costo_unitario) > 0) &&
    (!difiere.value || motivo.value.trim().length > 0),
)

onMounted(async () => {
  try {
    proveedores.value = await comprasApi.proveedores()
  } catch (e) {
    error.value = msg(e)
  }
  try {
    const r = await inventarioApi.stock({ tiendaId: props.tiendaId, size: 200 })
    for (const it of r.items || []) costoPorProducto.set(it.product_id, Number(it.costo ?? 0))
  } catch {
    /* sin costos precargados: se editan a mano */
  }
  if (props.prefill?.product_id) {
    agregarLinea({
      product_id: props.prefill.product_id,
      nombre: props.prefill.nombre,
      cantidad: props.prefill.cantidad || 1,
    })
  }
})

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo crear la solicitud.'
}

function agregarLinea({ product_id, nombre, cantidad = 1, cantidad_sugerida = null, costo = null }) {
  if (lineas.some((l) => l.product_id === product_id)) return
  const c = costo != null ? Number(costo) : costoPorProducto.get(product_id) || 0
  lineas.push({
    product_id,
    nombre: nombre || `Producto ${product_id}`,
    cantidad,
    cantidad_sugerida,
    costo_unitario: c.toFixed(2),
  })
}

function quitarLinea(pid) {
  const i = lineas.findIndex((l) => l.product_id === pid)
  if (i >= 0) lineas.splice(i, 1)
}

function onProductoElegido(p) {
  agregarLinea({ product_id: p.product_id, nombre: p.nombre })
  nuevoProductId.value = null
}

async function cargarSugerencia() {
  error.value = ''
  cargandoSugerencia.value = true
  try {
    const sug = await comprasApi.sugerencias(props.tiendaId)
    lineas.splice(0)
    for (const s of sug) {
      agregarLinea({
        product_id: s.product_id,
        nombre: s.nombre || `Producto ${s.product_id}`,
        cantidad: s.cantidad_sugerida,
        cantidad_sugerida: s.cantidad_sugerida,
      })
      if (!proveedorId.value && s.proveedor_id) proveedorId.value = s.proveedor_id
    }
    if (!sug.length) error.value = 'No hay productos bajo su punto de reposición en esta tienda.'
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargandoSugerencia.value = false
  }
}

watch(tipo, (t) => {
  if (t === 'programada' && lineas.some((l) => l.cantidad_sugerida == null)) {
    // al volver a "automática" se descartan las líneas manuales sin sugerencia
    for (let i = lineas.length - 1; i >= 0; i--) {
      if (lineas[i].cantidad_sugerida == null) lineas.splice(i, 1)
    }
  }
})

async function crear() {
  error.value = ''
  cargando.value = true
  try {
    const orden = await comprasApi.crearOrden({
      proveedorId: Number(proveedorId.value),
      tiendaId: props.tiendaId,
      empleadoId: props.empleadoId,
      tipo: tipo.value,
      lineas: lineas.map((l) => ({
        product_id: l.product_id,
        cantidad: Number(l.cantidad),
        costo_unitario: String(l.costo_unitario),
      })),
      motivoDesviacion: difiere.value ? motivo.value.trim() : null,
    })
    emit('creada', orden)
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

const money = (v) =>
  `$${Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
</script>

<template>
  <form class="space-y-4" @submit.prevent="crear">
    <p v-if="error" class="rounded-lg bg-rose-50 px-3 py-2 text-[13px] text-crimson-ruby" role="alert">
      {{ error }}
    </p>

    <!-- Tipo de pedido -->
    <div class="grid grid-cols-2 gap-2">
      <button
        type="button"
        class="rounded-xl border p-3 text-left transition"
        :class="tipo === 'programada' ? 'border-brand-600 bg-brand-50/60 ring-1 ring-brand-500/20' : 'border-brand-200 bg-white hover:border-brand-400'"
        @click="tipo = 'programada'"
      >
        <span class="flex items-center gap-1.5 text-[13px] font-bold text-slate-800">
          <Icon name="chart" :size="15" /> Automática
        </span>
        <span class="mt-0.5 block text-[11px] text-slate-500">
          Según la sugerencia semanal del sistema (productos bajo su punto de reposición).
        </span>
      </button>
      <button
        type="button"
        class="rounded-xl border p-3 text-left transition"
        :class="tipo === 'especial' ? 'border-amethyst-500 bg-amethyst-50/60 ring-1 ring-amethyst-400/20' : 'border-brand-200 bg-white hover:border-brand-400'"
        @click="tipo = 'especial'"
      >
        <span class="flex items-center gap-1.5 text-[13px] font-bold text-slate-800">
          <Icon name="bolt" :size="15" /> Especial
        </span>
        <span class="mt-0.5 block text-[11px] text-slate-500">
          Fuera del calendario pactado con el proveedor. Requiere motivo.
        </span>
      </button>
    </div>

    <!-- Proveedor -->
    <label class="block text-[12px] font-semibold text-slate-600">
      Proveedor <span class="text-crimson-ruby">*</span>
      <select
        v-model.number="proveedorId"
        required
        class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
      >
        <option :value="null" disabled>Selecciona un proveedor…</option>
        <option v-for="p in proveedores" :key="p.proveedor_id" :value="p.proveedor_id">
          {{ p.nombre }}{{ p.frecuencia_reposicion ? ` · reposición ${p.frecuencia_reposicion}` : '' }}
        </option>
      </select>
      <span v-if="proveedorSel && !proveedorSel.frecuencia_reposicion" class="mt-1 block text-[11px] text-amber-700">
        Este proveedor no tiene una frecuencia de reposición pactada.
      </span>
    </label>

    <!-- Líneas -->
    <div class="rounded-xl border border-brand-200">
      <div class="flex items-center justify-between border-b border-brand-100 bg-brand-50/50 px-3 py-2">
        <span class="text-[12px] font-bold text-brand-900">Productos del pedido</span>
        <Btn
          v-if="tipo === 'programada'"
          variant="ghost"
          class="!px-2.5 !py-1 !text-[12px]"
          :disabled="cargandoSugerencia"
          @click="cargarSugerencia"
        >
          <Icon name="chart" :size="13" />
          {{ cargandoSugerencia ? 'Cargando…' : 'Cargar sugerencia semanal' }}
        </Btn>
      </div>

      <table v-if="lineas.length" class="w-full text-[13px]">
        <thead>
          <tr class="text-left text-[11px] uppercase tracking-wide text-slate-400">
            <th class="px-3 py-1.5">Producto</th>
            <th class="px-2 py-1.5 text-right">Sugerido</th>
            <th class="px-2 py-1.5 text-right">Cantidad</th>
            <th class="px-2 py-1.5 text-right">Costo unit.</th>
            <th class="px-2 py-1.5 text-right">Subtotal</th>
            <th class="px-2 py-1.5" />
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100">
          <tr v-for="l in lineas" :key="l.product_id">
            <td class="px-3 py-1.5">
              <div class="font-medium text-slate-800">{{ l.nombre }}</div>
              <div class="font-mono text-[10px] text-slate-400">ID {{ l.product_id }}</div>
            </td>
            <td class="px-2 py-1.5 text-right text-slate-500">
              {{ l.cantidad_sugerida ?? '—' }}
            </td>
            <td class="px-2 py-1.5 text-right">
              <input
                v-model.number="l.cantidad"
                type="number"
                min="1"
                class="w-16 rounded border border-brand-300 bg-white px-2 py-1 text-right"
              />
            </td>
            <td class="px-2 py-1.5 text-right">
              <input
                v-model="l.costo_unitario"
                type="number"
                min="0"
                step="0.01"
                class="w-20 rounded border border-brand-300 bg-white px-2 py-1 text-right"
              />
            </td>
            <td class="px-2 py-1.5 text-right font-semibold tabular-nums text-slate-700">
              {{ money(Number(l.cantidad) * Number(l.costo_unitario)) }}
            </td>
            <td class="px-2 py-1.5 text-right">
              <button
                type="button"
                class="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-crimson-ruby"
                title="Quitar"
                @click="quitarLinea(l.product_id)"
              >
                <Icon name="trash" :size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="px-3 py-4 text-[12px] text-slate-500">
        {{
          tipo === 'programada'
            ? 'Carga la sugerencia semanal o agrega productos manualmente.'
            : 'Agrega los productos del pedido especial.'
        }}
      </p>

      <div class="border-t border-brand-100 px-3 py-2">
        <ProductoPicker
          v-model="nuevoProductId"
          label="Agregar producto"
          :tienda-id="tiendaId"
          @seleccionado="onProductoElegido"
        />
      </div>
    </div>

    <!-- Motivo -->
    <label v-if="difiere" class="block text-[12px] font-semibold text-slate-600">
      Motivo <span class="text-crimson-ruby">*</span>
      <span class="font-normal text-slate-400">
        — {{ tipo === 'especial' ? 'por qué se pide fuera de calendario' : 'por qué se ajustan las cantidades sugeridas' }}
      </span>
      <textarea
        v-model="motivo"
        rows="2"
        required
        class="mt-1 block w-full rounded-lg border border-amber-300 bg-amber-50/40 px-3 py-2 text-sm text-slate-800"
      />
    </label>

    <div class="flex items-center justify-between border-t border-brand-100 pt-3">
      <span class="text-[13px] font-bold text-slate-700">
        Total estimado: <span class="tabular-nums text-brand-900">{{ money(total) }}</span>
      </span>
      <div class="flex gap-2.5">
        <Btn variant="ghost" @click="emit('cerrar')">Cancelar</Btn>
        <Btn variant="primary" type="submit" :disabled="cargando || !puedeCrear">
          {{ cargando ? 'Creando…' : 'Crear solicitud de pedido' }}
        </Btn>
      </div>
    </div>
  </form>
</template>
