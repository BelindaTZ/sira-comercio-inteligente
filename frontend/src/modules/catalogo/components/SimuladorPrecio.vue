<script setup>
/**
 * Simulador de Impacto de precio — panel lateral de la referencia
 * "Catálogo Maestro de Productos & Matriz de Precios".
 * Slider de ajuste de PVP → proyección de margen y ganancia mensual
 * (`POST /catalogo/productos/{id}/simular-precio`). "Aplicar" persiste el
 * nuevo precio_base vía `PATCH /catalogo/productos/{id}`.
 */
import { ref, watch } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  producto: { type: Object, default: null }, // fila de la matriz de precios
  puedeEditar: { type: Boolean, default: false },
})
const emit = defineEmits(['aplicado'])

const delta = ref(4)
const sim = ref(null)
const cargando = ref(false)
const error = ref('')
const aplicando = ref(false)
let deb

const money = (v) =>
  `$${Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

watch(
  () => props.producto?.product_id,
  () => {
    delta.value = 4
    sim.value = null
    error.value = ''
    if (props.producto) correr()
  },
)
watch(delta, () => {
  clearTimeout(deb)
  deb = setTimeout(correr, 220)
})

async function correr() {
  if (!props.producto) return
  cargando.value = true
  error.value = ''
  try {
    sim.value = await catalogoApi.simularPrecio(props.producto.product_id, Number(delta.value))
  } catch (e) {
    sim.value = null
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

async function aplicar() {
  if (!sim.value) return
  aplicando.value = true
  try {
    await catalogoApi.actualizar(props.producto.product_id, {
      precio_base: Number(sim.value.pvp_nuevo),
    })
    emit('aplicado')
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    aplicando.value = false
  }
}
</script>

<template>
  <div class="kpi-tinted rounded-2xl border-t-2 border-t-amethyst-500 p-4">
    <div class="flex items-center justify-between border-b border-amethyst-200/70 pb-2.5">
      <div class="flex items-center gap-2">
        <span
          class="flex h-7 w-7 items-center justify-center rounded-lg border border-amethyst-300 bg-amethyst-100 text-amethyst-700"
        >
          <Icon name="chart" :size="15" />
        </span>
        <div>
          <h3 class="font-display text-[13px] font-bold text-amethyst-950">Simulador de Impacto</h3>
          <p class="text-[10px] font-medium text-slate-500">Motor predictivo de elasticidad</p>
        </div>
      </div>
      <span
        class="rounded-full border border-amethyst-300 bg-amethyst-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amethyst-800"
      >
        Live
      </span>
    </div>

    <p v-if="!producto" class="mt-4 text-center text-[12px] text-slate-500">
      Elegí un producto de la tabla para simular un cambio de precio.
    </p>

    <template v-else>
      <div class="mt-3 rounded-xl border border-brand-200 bg-brand-50/50 p-2.5">
        <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          SKU seleccionado
        </p>
        <p class="mt-0.5 text-[12px] font-bold text-slate-800">
          {{ producto.nombre || `Producto ${producto.product_id}` }}
        </p>
        <div class="mt-1 flex items-center justify-between text-[11px] text-slate-600">
          <span>PVP actual (+IVA): <strong class="text-slate-900">{{ money(producto.precio_base) }}</strong></span>
          <span>
            Margen:
            <strong :class="(producto.margen_pct ?? 0) >= 30 ? 'text-emerald-700' : 'text-amber-700'">
              {{ producto.margen_pct != null ? producto.margen_pct.toFixed(1) + '%' : '—' }}
            </strong>
          </span>
        </div>
        <div class="mt-0.5 text-[10px] text-slate-500">
          Neto sin IVA: <strong class="text-slate-700">{{ money(producto.precio_neto ?? (producto.precio_base != null ? producto.precio_base / 1.15 : null)) }}</strong>
        </div>
      </div>

      <div class="mt-3 space-y-1.5">
        <div class="flex items-center justify-between text-[12px]">
          <label class="font-semibold text-slate-700">Ajuste proyectado de PVP</label>
          <span
            class="rounded border border-amethyst-300 bg-amethyst-100 px-2 py-0.5 text-[12px] font-bold text-amethyst-800 tabular-nums"
          >
            {{ delta > 0 ? '+' : '' }}{{ Number(delta).toFixed(1) }}%
          </span>
        </div>
        <input
          v-model.number="delta"
          type="range"
          min="-10"
          max="15"
          step="0.5"
          class="w-full accent-amethyst-600"
        />
        <div class="flex justify-between text-[9px] font-mono text-slate-400">
          <span>−10% (promo)</span><span>0%</span><span>+15% (markup máx)</span>
        </div>
      </div>

      <p v-if="error" class="mt-3 rounded-lg bg-rose-50 px-2.5 py-2 text-[11px] text-crimson-ruby">
        {{ error }}
      </p>

      <div
        v-else-if="sim"
        class="mt-3 space-y-2 rounded-xl border border-emerald-600/20 bg-emerald-500/[0.06] p-3"
        :class="cargando ? 'opacity-60' : ''"
      >
        <div class="flex items-center gap-1.5 text-[11px] font-bold text-emerald-900">
          <Icon name="chart" :size="13" /> Proyección mensual
        </div>
        <p class="text-[11px] leading-relaxed text-emerald-950">
          A <strong>{{ money(sim.pvp_nuevo) }}</strong> con IVA (neto: {{ money(Number(sim.pvp_nuevo) / 1.15) }}, {{ delta > 0 ? '+' : '' }}{{ Number(delta).toFixed(1) }}%) el
          margen pasa a
          <strong>{{ sim.margen_nuevo_pct != null ? sim.margen_nuevo_pct.toFixed(1) + '%' : '—' }}</strong>
          y la ganancia bruta mensual proyectada cambia en:
        </p>
        <p class="font-display text-xl font-extrabold tabular-nums" :class="sim.ganancia_mensual_delta >= 0 ? 'text-emerald-800' : 'text-crimson-ruby'">
          {{ sim.ganancia_mensual_delta >= 0 ? '+' : '' }}{{ money(sim.ganancia_mensual_delta) }}
          <span class="text-[10px] font-medium text-emerald-800">USD netos/mes</span>
        </p>
        <div class="flex items-center gap-1.5 border-t border-emerald-600/10 pt-1.5 text-[10px] text-emerald-800">
          <Icon name="check" :size="12" />
          <span>
            {{ sim.unidades_mes }} un./mes ·
            <template v-if="sim.es_inelastico">demanda inelástica (factor {{ sim.factor_elasticidad.toFixed(2) }})</template>
            <template v-else>elasticidad estimada {{ sim.factor_elasticidad.toFixed(2) }} → {{ sim.delta_unidades_mes > 0 ? '+' : '' }}{{ sim.delta_unidades_mes }} un.</template>
          </span>
        </div>
      </div>

      <div class="mt-3 space-y-2">
        <button
          type="button"
          :disabled="!sim || !puedeEditar || aplicando || Number(delta) === 0"
          class="w-full rounded-xl bg-amethyst-600 px-3 py-2 text-[12px] font-bold text-white transition hover:bg-amethyst-500 disabled:opacity-40"
          @click="aplicar"
        >
          <Icon name="bolt" :size="13" class="mr-1 inline" />
          {{ aplicando ? 'Aplicando…' : 'Aplicar nuevo PVP' }}
        </button>
        <p v-if="!puedeEditar" class="text-center text-[10px] text-slate-400">
          Solo lectura — no podés modificar precios.
        </p>
      </div>
    </template>
  </div>
</template>
