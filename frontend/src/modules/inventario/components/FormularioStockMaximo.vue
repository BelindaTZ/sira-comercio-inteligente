<script setup>
/**
 * Definir Stock Máximo, Mínimo & Parámetros de Capacidad por categoría
 * (FR-037). Estructura de
 * `docs/diseno-ui/.../sira_configurar_stock_m_ximo_por_categor_a/`:
 * 3 tarjetas (capacidad física de góndola · tope de compra EDI · punto de
 * reorden), días de cobertura objetivo y política de sobre-stock.
 *
 * `cantidad_maxima` es el único valor obligatorio; el resto son parámetros de
 * abastecimiento (migración 0023). La categoría se elige de las existentes.
 */
import { computed, ref, watch } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import CategoriaPicker from '@/shared/ui/CategoriaPicker.vue'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['definido', 'cerrar'])

const categoria = ref('')
const capacidad = ref(null)
const maximo = ref(300)
const minimo = ref(75)
const dias = ref(5)
const politica = ref('estricto')
const skus = ref(null)
const error = ref('')
const enviando = ref(false)

// Al elegir categoría: precarga los umbrales vigentes + cuenta de SKUs.
watch(categoria, async (c) => {
  if (!c) return
  try {
    const [smax, cat] = await Promise.all([
      inventarioApi.stockMaximo({ tiendaId: props.tiendaId, productCategory: c }),
      inventarioApi.stock({ tiendaId: props.tiendaId, categoria: c, size: 1 }),
    ])
    skus.value = cat.total
    const v = smax.items?.[0]
    if (v) {
      maximo.value = v.cantidad_maxima
      capacidad.value = v.capacidad_gondola
      minimo.value = v.stock_minimo_reorden ?? minimo.value
      dias.value = v.dias_cobertura ?? dias.value
      politica.value = v.politica_sobrestock ?? politica.value
    }
  } catch {
    /* categoría sin regla previa; se usan los valores por defecto */
  }
})

const lineal85 = computed(() => (capacidad.value ? Math.round(capacidad.value * 0.85) : null))
const capitalInmovilizado = computed(() => (maximo.value || 0) * 1.50) // ref. genérica en USD
const money = (v) =>
  `$${Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`
const p = (ref_, n, min = 0) => {
  ref_.value = Math.max(min, (Number(ref_.value) || 0) + n)
}

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    const res = await inventarioApi.definirStockMaximo({
      productCategory: categoria.value,
      tiendaId: props.tiendaId,
      cantidadMaxima: Number(maximo.value),
      empleadoId: props.empleadoId,
      capacidadGondola: capacidad.value ? Number(capacidad.value) : null,
      stockMinimoReorden: minimo.value != null ? Number(minimo.value) : null,
      diasCobertura: Number(dias.value),
      politicaSobrestock: politica.value,
    })
    emit('definido', res)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="enviar">
    <div class="flex flex-wrap items-end gap-3">
      <div class="min-w-[16rem] flex-1">
        <CategoriaPicker v-model="categoria" placeholder="Elegí la subfamilia…" required />
      </div>
      <span
        v-if="skus != null"
        class="rounded-full border border-brand-200 bg-brand-50 px-2.5 py-1 text-[11px] font-bold text-brand-900"
      >
        {{ skus }} SKUs
      </span>
    </div>

    <!-- 3 tarjetas de capacidad -->
    <div class="grid gap-3 md:grid-cols-3">
      <div class="rounded-xl border border-brand-200 bg-brand-50/50 p-3">
        <div class="flex items-center justify-between text-[11px] font-bold uppercase text-slate-500">
          Límite físico lineal <Icon name="cube" :size="15" />
        </div>
        <p class="mt-0.5 text-[12px] font-semibold text-slate-800">Capacidad máxima góndola</p>
        <div class="mt-2 flex items-center gap-2">
          <input
            v-model.number="capacidad"
            type="number"
            min="1"
            placeholder="—"
            class="w-24 rounded-lg border border-brand-300 bg-white py-1 text-center font-display text-[20px] font-extrabold tabular-nums text-brand-950"
          />
          <span class="text-[11px] text-slate-400">un. máx.</span>
        </div>
        <p
          v-if="lineal85"
          class="mt-2 rounded border border-amber-200 bg-amber-50 p-1.5 text-[10px] font-medium text-amber-800"
        >
          Alerta si la reposición supera el 85% lineal ({{ lineal85 }} un.)
        </p>
      </div>

      <div class="relative rounded-xl border-2 border-brand-400/40 bg-white p-3">
        <span
          class="absolute -top-2 right-3 rounded bg-brand-800 px-1.5 py-0.5 text-[9px] font-bold uppercase text-white"
          >Control operativo</span
        >
        <div class="flex items-center justify-between text-[11px] font-bold uppercase text-brand-800">
          Umbral de compra <Icon name="cart" :size="15" />
        </div>
        <p class="mt-0.5 text-[12px] font-semibold text-slate-800">
          Stock máximo permitido <span class="text-crimson-ruby">*</span>
        </p>
        <div class="mt-2 flex items-center justify-center gap-1.5">
          <button
            type="button"
            class="grid h-7 w-8 place-items-center rounded border border-brand-300 text-[11px] font-bold hover:bg-brand-50"
            @click="p(maximo, -5, 1)"
          >
            −5
          </button>
          <input
            v-model.number="maximo"
            type="number"
            min="1"
            required
            class="w-20 rounded-lg border border-brand-400/40 bg-brand-50/40 py-1 text-center font-display text-[20px] font-extrabold tabular-nums text-brand-800"
          />
          <button
            type="button"
            class="grid h-7 w-8 place-items-center rounded border border-brand-300 text-[11px] font-bold hover:bg-brand-50"
            @click="p(maximo, 5, 1)"
          >
            +5
          </button>
        </div>
        <div class="mt-1.5 grid grid-cols-4 gap-1">
          <button
            v-for="n in [-20, -5, 5, 20]"
            :key="n"
            type="button"
            class="rounded bg-slate-100 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-200"
            @click="p(maximo, n, 1)"
          >
            {{ n > 0 ? '+' + n : n }}
          </button>
        </div>
        <p class="mt-2 text-[10px] text-slate-500">Tope para órdenes de compra automáticas (EDI).</p>
      </div>

      <div class="rounded-xl border border-rose-200 bg-white p-3">
        <div class="flex items-center justify-between text-[11px] font-bold uppercase text-crimson-ruby">
          Buffer crítico <Icon name="alert" :size="15" />
        </div>
        <p class="mt-0.5 text-[12px] font-semibold text-slate-800">Stock mínimo / reorden</p>
        <div class="mt-2 flex items-center justify-center gap-1.5">
          <button
            type="button"
            class="grid h-7 w-8 place-items-center rounded border border-brand-300 text-[11px] font-bold hover:bg-brand-50"
            @click="p(minimo, -5)"
          >
            −5
          </button>
          <input
            v-model.number="minimo"
            type="number"
            min="0"
            class="w-16 rounded-lg border border-rose-200 bg-rose-50/40 py-1 text-center font-display text-[20px] font-extrabold tabular-nums text-crimson-ruby"
          />
          <button
            type="button"
            class="grid h-7 w-8 place-items-center rounded border border-brand-300 text-[11px] font-bold hover:bg-brand-50"
            @click="p(minimo, 5)"
          >
            +5
          </button>
        </div>
        <p class="mt-2 text-[10px] text-rose-700">
          Dispara solicitud prioritaria cuando el stock ≤ {{ minimo || 0 }} un.
        </p>
      </div>
    </div>

    <!-- Días de cobertura + política -->
    <div class="grid gap-4 lg:grid-cols-12">
      <div class="space-y-2 lg:col-span-5">
        <div class="flex items-center justify-between text-[12px] font-semibold text-slate-700">
          <span>Días de cobertura objetivo</span>
          <span class="rounded-full bg-amethyst-100 px-2 py-0.5 text-[11px] font-bold text-amethyst-800">
            {{ dias }} días
          </span>
        </div>
        <input
          v-model.number="dias"
          type="range"
          min="2"
          max="14"
          class="w-full accent-brand-700"
        />
        <div class="flex justify-between text-[10px] font-mono text-slate-400">
          <span>2d</span><span>5d</span><span>10d</span><span>14d</span>
        </div>
        <p class="rounded-lg border border-brand-200 bg-brand-50/60 p-2 text-[11px] text-slate-600">
          Frecuencia recomendada: <strong>diaria, turno nocturno</strong>. Una cobertura corta
          previene descarte por vencimiento y optimiza la rotación FIFO.
        </p>
      </div>

      <div class="space-y-2 lg:col-span-7">
        <span class="text-[12px] font-semibold text-slate-700">
          Política de control de sobre-stock
        </span>
        <label
          v-for="o in [
            {
              v: 'estricto',
              t: 'Bloqueo estricto de OC (recomendado)',
              d: 'No autorizar pedidos ni recepciones que excedan el tope. Previene saturación de góndola.',
            },
            {
              v: 'autorizado',
              t: 'Permitir sobre-stock con autorización',
              d: 'Compras de oportunidad o promos, con validación del Gerente Comercial (+15% temporal).',
            },
          ]"
          :key="o.v"
          class="flex cursor-pointer items-start gap-3 rounded-xl border-2 p-3 transition"
          :class="
            politica === o.v ? 'border-brand-600 bg-brand-50' : 'border-brand-200 hover:bg-brand-50/60'
          "
        >
          <input v-model="politica" :value="o.v" type="radio" name="politica" class="mt-0.5" />
          <span>
            <span class="block text-[12px] font-bold text-slate-900">{{ o.t }}</span>
            <span class="block text-[11px] leading-tight text-slate-500">{{ o.d }}</span>
          </span>
        </label>
      </div>
    </div>

    <div class="rounded-xl border border-brand-200 bg-brand-50/40 p-3 text-[12px]">
      <span class="text-slate-500">Capital inmovilizado proyectado al stock máximo:</span>
      <span class="ml-1 font-display font-bold tabular-nums text-brand-900">
        {{ money(capitalInmovilizado) }}
      </span>
      <span class="text-[10px] text-slate-400"> (referencial)</span>
    </div>

    <p v-if="error" class="text-[12px] text-crimson-ruby">{{ error }}</p>

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
        :disabled="!categoria || !maximo || enviando"
        class="inline-flex items-center gap-1.5 rounded-xl border border-brand-600 bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-40"
      >
        <Icon name="check" :size="16" />
        {{ enviando ? 'Guardando…' : 'Guardar umbrales y aplicar' }}
      </button>
    </div>
  </form>
</template>
