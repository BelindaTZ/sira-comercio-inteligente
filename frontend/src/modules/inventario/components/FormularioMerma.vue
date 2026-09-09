<script setup>
/**
 * Declarar & Registrar Merma de Inventario (FR-018/FR-019). Estructura de
 * `docs/diseno-ui/.../sira_declarar_y_registrar_merma_de_inventario/`:
 * motivo/causal (obligatorio) → stock disponible vs. unidades a dar de baja
 * (stepper) → impacto financiero en vivo → destino físico de las unidades.
 *
 * La merma queda `pendiente` hasta que el Encargado la valida (ahí descuenta
 * stock, FR-019). El PIN de supervisor y la foto de respaldo de la referencia
 * quedan fuera del alcance del endpoint actual.
 */
import { computed, ref, watch } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
  productoInicial: { type: Object, default: null },
  causaInicial: { type: String, default: '' },
})
const emit = defineEmits(['registrada', 'cerrar'])

// 5 causales de la referencia → 4 valores de `causa` que acepta el backend.
const CAUSAS = [
  {
    v: 'rotura',
    t: 'Rotura / envase dañado',
    d: 'Fisura de empaque, golpe en tránsito o derrame.',
  },
  {
    v: 'caducidad',
    t: 'Vencida / alerta FIFO',
    d: 'Fecha de caducidad superada en góndola o almacén.',
  },
  {
    v: 'rotura',
    t: 'Quiebre de cadena de frío',
    d: 'Cámara térmica fuera de rango reglamentario.',
  },
  {
    v: 'error_humano',
    t: 'Falla / defecto de fábrica',
    d: 'Sellado deficiente, anomalía organoléptica o de lote.',
  },
  {
    v: 'error_humano',
    t: 'Retiro preventivo',
    d: 'Bloqueo sanitario o recall legal del proveedor.',
  },
]
const DESTINOS = [
  { v: 'destruccion', t: 'Destrucción in situ', d: 'Vertedero / compactador.' },
  { v: 'devolucion', t: 'Devolución a proveedor', d: 'Nota de crédito.' },
  { v: 'donacion', t: 'Donación autorizada', d: 'Red de alimentos (apta consumo).' },
  { v: 'cuarentena', t: 'Jaula de cuarentena', d: 'Peritaje de calidad / seguros.' },
]

const productId = ref(props.productoInicial?.product_id ?? null)
const sku = ref(props.productoInicial ?? null)
const causaIx = ref(props.causaInicial ? CAUSAS.findIndex((c) => c.v === props.causaInicial) : -1)
const cantidad = ref(1)
const destino = ref('destruccion')
const observaciones = ref('')
const error = ref('')
const enviando = ref(false)

async function cargarSku(pid) {
  if (!pid) return
  // La ficha ya está completa (trae stock) → no re-consultar. Cuando el producto
  // llega desde una alerta de vencimiento sólo trae {product_id, nombre}, así que
  // hay que ir a buscar `cantidad_disponible` / `costo` igual.
  if (sku.value?.product_id === pid && sku.value?.cantidad_disponible != null) return
  try {
    const r = await inventarioApi.stock({ tiendaId: props.tiendaId, search: String(pid), size: 1 })
    const hit = r.items.find((x) => x.product_id === pid) ?? r.items[0]
    if (hit) sku.value = hit
  } catch {
    /* sin ficha */
  }
}
watch(productId, cargarSku, { immediate: true })

const disponible = computed(() => sku.value?.cantidad_disponible ?? null)
const costo = computed(() => Number(sku.value?.costo ?? 0))
const impacto = computed(() => (Number(cantidad.value) || 0) * costo.value)
const stockFinal = computed(() =>
  disponible.value == null ? null : disponible.value - (Number(cantidad.value) || 0)
)
const money = (v) =>
  `$${Math.abs(Number(v || 0)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`
const paso = (n) => {
  const max = disponible.value ?? Infinity
  cantidad.value = Math.min(max, Math.max(1, (Number(cantidad.value) || 0) + n))
}

const puedeEnviar = computed(
  () =>
    productId.value &&
    causaIx.value >= 0 &&
    cantidad.value > 0 &&
    (disponible.value == null || cantidad.value <= disponible.value)
)

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    await inventarioApi.merma({
      productId: productId.value,
      tiendaId: props.tiendaId,
      cantidad: Number(cantidad.value),
      causa: CAUSAS[causaIx.value].v,
      empleadoId: props.empleadoId,
      loteId: sku.value?.lote_id || null,
      destino: destino.value,
      observaciones: observaciones.value || undefined,
    })
    emit('registrada')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="enviar">
    <ProductoPicker
      v-if="!productoInicial"
      v-model="productId"
      :tienda-id="tiendaId"
      label="Producto a dar de baja"
      required
      @seleccionado="sku = $event"
    />
    <p v-else class="text-[13px]">
      <span class="font-semibold text-slate-900">{{ sku?.nombre || 'Producto' }}</span>
      <span class="text-slate-400"> · ID {{ productId }}</span>
      <span v-if="sku?.pasillo" class="text-slate-500"> · {{ sku.pasillo }}</span>
    </p>

    <div>
      <div
        class="mb-2 flex items-center justify-between text-[11px] font-bold uppercase text-slate-500"
      >
        <span>1 · Motivo primario / causal de pérdida</span>
        <span class="text-crimson-ruby">*</span>
      </div>
      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <label
          v-for="(c, i) in CAUSAS"
          :key="i"
          class="flex cursor-pointer items-start gap-2.5 rounded-lg border-2 p-2.5 transition"
          :class="
            causaIx === i
              ? 'border-damask-amber bg-amber-50'
              : 'border-brand-200 hover:bg-brand-50/60'
          "
        >
          <input
            :checked="causaIx === i"
            type="radio"
            name="causa"
            class="mt-0.5"
            @change="causaIx = i"
          />
          <span class="text-left">
            <span class="block text-[12px] font-bold text-slate-900">{{ c.t }}</span>
            <span class="block text-[11px] leading-tight text-slate-500">{{ c.d }}</span>
          </span>
        </label>
      </div>
    </div>

    <div class="grid gap-3 md:grid-cols-12">
      <div class="rounded-xl border border-brand-200 bg-brand-50/50 p-3 md:col-span-4">
        <span class="text-[11px] font-semibold uppercase text-slate-500">Stock disponible</span>
        <div class="mt-1 font-display text-[24px] font-extrabold tabular-nums text-brand-950">
          {{ disponible != null ? disponible : '—' }}
          <span class="text-[13px] font-medium text-slate-400">un.</span>
        </div>
        <div class="mt-2 border-t border-brand-200/70 pt-1.5 text-[11px] text-slate-500">
          Costo unitario <span class="font-semibold text-slate-700">{{ money(costo) }}</span>
        </div>
      </div>

      <div class="rounded-xl border-2 border-crimson-ruby/40 bg-white p-3 md:col-span-5">
        <span class="text-[11px] font-bold uppercase text-crimson-ruby"
          >Unidades a dar de baja</span
        >
        <div class="my-1 flex items-center justify-center gap-2">
          <button
            type="button"
            class="grid h-9 w-9 place-items-center rounded-lg border border-brand-300 text-lg font-bold hover:bg-brand-50"
            @click="paso(-1)"
          >
            −
          </button>
          <input
            v-model.number="cantidad"
            type="number"
            min="1"
            :max="disponible ?? undefined"
            required
            class="w-full rounded-lg border border-crimson-ruby/30 bg-rose-50/40 py-1 text-center font-display text-[24px] font-extrabold tabular-nums text-crimson-ruby focus:outline-none focus:ring-2 focus:ring-rose-400/30"
          />
          <button
            type="button"
            class="grid h-9 w-9 place-items-center rounded-lg border border-brand-300 text-lg font-bold hover:bg-brand-50"
            @click="paso(1)"
          >
            +
          </button>
        </div>
        <div class="flex justify-center gap-1.5">
          <button
            v-for="n in [-1, 1, 5, 10]"
            :key="n"
            type="button"
            class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-200"
            @click="paso(n)"
          >
            {{ n > 0 ? '+' + n : n }}
          </button>
        </div>
      </div>

      <div class="rounded-xl border border-amber-300 bg-amber-50 p-3 md:col-span-3">
        <span class="text-[11px] font-bold uppercase text-amber-700">Impacto financiero</span>
        <div class="mt-1 font-display text-[18px] font-extrabold tabular-nums text-crimson-ruby">
          −{{ money(impacto) }}
        </div>
        <div class="mt-2 border-t border-amber-200 pt-1.5 text-[11px] text-slate-600">
          Stock final proyectado
          <span class="font-bold text-slate-800">
            {{ stockFinal != null ? stockFinal + ' un.' : '—' }}</span
          >
        </div>
      </div>
    </div>

    <div>
      <div class="mb-2 text-[11px] font-bold uppercase text-slate-500">
        2 · Destino físico de las unidades
      </div>
      <div class="grid gap-2 sm:grid-cols-2">
        <label
          v-for="d in DESTINOS"
          :key="d.v"
          class="flex cursor-pointer items-start gap-2.5 rounded-lg border-2 p-2.5 transition"
          :class="
            destino === d.v
              ? 'border-brand-600 bg-brand-50'
              : 'border-brand-200 hover:bg-brand-50/60'
          "
        >
          <input v-model="destino" :value="d.v" type="radio" name="destino" class="mt-0.5" />
          <span class="text-left">
            <span class="block text-[12px] font-bold text-slate-900">{{ d.t }}</span>
            <span class="block text-[11px] leading-tight text-slate-500">{{ d.d }}</span>
          </span>
        </label>
      </div>
    </div>

    <label class="block text-[12px] font-semibold text-slate-600">
      Detalle del siniestro / evidencia
      <textarea
        v-model="observaciones"
        rows="2"
        maxlength="250"
        placeholder="Qué pasó, dónde, quién lo constató…"
        class="mt-1 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-[13px] text-slate-800"
      />
    </label>

    <p v-if="error" class="text-[12px] text-crimson-ruby">{{ error }}</p>
    <p class="text-[11px] text-slate-400">
      Queda <strong>pendiente</strong> hasta que el Encargado la valida; ahí descuenta el stock.
    </p>

    <div class="flex items-center justify-end gap-2.5">
      <button
        type="button"
        class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
        @click="emit('cerrar')"
      >
        Cancelar
      </button>
      <button
        type="submit"
        :disabled="!puedeEnviar || enviando"
        class="inline-flex items-center gap-1.5 rounded-xl border border-crimson-ruby/50 bg-crimson-ruby px-4 py-2 text-[13px] font-bold text-white hover:brightness-95 disabled:opacity-40"
      >
        <Icon name="alert" :size="16" />
        {{ enviando ? 'Registrando…' : `Registrar baja de merma (${cantidad || 0} un.)` }}
      </button>
    </div>
  </form>
</template>
