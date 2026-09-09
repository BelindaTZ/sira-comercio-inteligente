<script setup>
/**
 * Ajuste de Conteo Físico & Corrección de Stock (FR-017). Estructura de
 * `docs/diseno-ui/.../sira_ajuste_de_conteo_f_sico_y_auditor_a_de_stock/`:
 * comparativa Stock teórico vs. conteo físico (stepper) → discrepancia e impacto
 * financiero en vivo, motivo del descuadre (obligatorio) y observaciones.
 *
 * El backend calcula la diferencia (columna `GENERATED` en BD). `motivo` y
 * `observaciones` se envían para la trazabilidad de auditoría; el PIN de
 * supervisor / asiento contable automático de la referencia quedan fuera del
 * alcance del endpoint actual.
 */
import { computed, ref, watch } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
  productoInicial: { type: Object, default: null },
})
const emit = defineEmits(['ajustado', 'cerrar'])

const MOTIVOS = [
  { v: 'rotura', t: 'Merma por rotura / derrame', d: 'Daño físico en góndola o reposición.' },
  {
    v: 'caducidad',
    t: 'Vencimiento anticipado / merma FIFO',
    d: 'Pérdida de hermeticidad o fecha cumplida.',
  },
  {
    v: 'error_humano',
    t: 'Diferencia en recepción / digitación',
    d: 'Error al ingresar la factura o guía.',
  },
  {
    v: 'robo',
    t: 'Sospecha de hurto / pérdida no identificada',
    d: 'Sustracción sin registro en el terminal POS.',
  },
]

const productId = ref(props.productoInicial?.product_id ?? null)
const sku = ref(props.productoInicial ?? null)
const conteoFisico = ref(props.productoInicial?.cantidad_disponible ?? null)
const motivo = ref('')
const observaciones = ref('')
const resultado = ref(null)
const error = ref('')
const enviando = ref(false)

function onSku(fila) {
  sku.value = fila
  conteoFisico.value = fila?.cantidad_disponible ?? null
}
async function cargarSku(pid) {
  if (!pid) {
    sku.value = null
    return
  }
  if (sku.value?.product_id === pid) return
  try {
    const r = await inventarioApi.stock({ tiendaId: props.tiendaId, search: String(pid), size: 1 })
    sku.value = r.items.find((x) => x.product_id === pid) ?? r.items[0] ?? null
    conteoFisico.value = sku.value?.cantidad_disponible ?? null
  } catch {
    /* sin ficha; el usuario igual puede contar */
  }
}
watch(productId, cargarSku)

const teorico = computed(() => sku.value?.cantidad_disponible ?? null)
const costo = computed(() => Number(sku.value?.costo ?? 0))
const valorLibros = computed(() => (teorico.value ?? 0) * costo.value)
const discrepancia = computed(() =>
  teorico.value == null || conteoFisico.value == null ? null : conteoFisico.value - teorico.value
)
const discrepanciaPct = computed(() =>
  discrepancia.value == null || !teorico.value ? null : (discrepancia.value / teorico.value) * 100
)
const impacto = computed(() =>
  discrepancia.value == null ? null : discrepancia.value * costo.value
)
const money = (v) => `$${Math.round(Math.abs(v || 0)).toLocaleString('es-CL')} CLP`
const paso = (n) => {
  conteoFisico.value = Math.max(0, (Number(conteoFisico.value) || 0) + n)
}

const puedeEnviar = computed(
  () =>
    productId.value &&
    conteoFisico.value != null &&
    motivo.value &&
    discrepancia.value !== 0 &&
    discrepancia.value != null
)

async function enviar() {
  error.value = ''
  enviando.value = true
  try {
    resultado.value = await inventarioApi.ajuste({
      productId: productId.value,
      tiendaId: props.tiendaId,
      cantidadFisica: Number(conteoFisico.value),
      empleadoId: props.empleadoId,
      motivo: motivo.value,
      observaciones: observaciones.value || undefined,
    })
    emit('ajustado', resultado.value)
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
      label="Producto a auditar"
      required
      @seleccionado="onSku"
    />
    <p v-else class="text-[13px]">
      <span class="font-semibold text-slate-900">{{ sku?.nombre || 'Producto' }}</span>
      <span class="text-slate-400"> · ID {{ productId }}</span>
      <span v-if="sku?.pasillo" class="text-slate-500"> · {{ sku.pasillo }}</span>
    </p>

    <div class="grid gap-3 md:grid-cols-12">
      <div class="rounded-xl border border-brand-200 bg-brand-50/50 p-3 md:col-span-4">
        <div
          class="flex items-center justify-between text-[11px] font-semibold uppercase text-slate-500"
        >
          Stock teórico (SIRA) <Icon name="database" :size="15" />
        </div>
        <div class="mt-1 font-display text-[26px] font-extrabold tabular-nums text-brand-950">
          {{ teorico != null ? teorico : '—' }}
          <span class="text-[13px] font-medium text-slate-400">un.</span>
        </div>
        <div class="mt-2 flex justify-between border-t border-brand-200/70 pt-1.5 text-[11px]">
          <span class="text-slate-500">Valor en libros</span>
          <span class="font-semibold tabular-nums">{{ money(valorLibros) }}</span>
        </div>
      </div>

      <div class="rounded-xl border-2 border-brand-400/50 bg-white p-3 md:col-span-5">
        <span class="text-[11px] font-bold uppercase text-brand-800">Conteo físico real</span>
        <div class="my-1 flex items-center justify-center gap-2">
          <button
            type="button"
            class="grid h-9 w-9 place-items-center rounded-lg border border-brand-300 text-lg font-bold hover:bg-brand-50"
            @click="paso(-1)"
          >
            −
          </button>
          <input
            v-model.number="conteoFisico"
            type="number"
            min="0"
            required
            class="w-full rounded-lg border border-brand-400/40 bg-brand-50/40 py-1 text-center font-display text-[24px] font-extrabold tabular-nums text-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
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
            v-for="n in [-10, -1, 1, 10]"
            :key="n"
            type="button"
            class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-200"
            @click="paso(n)"
          >
            {{ n > 0 ? '+' + n : n }}
          </button>
        </div>
        <div class="mt-2 flex justify-between border-t border-brand-200/70 pt-1.5 text-[11px]">
          <span class="text-slate-500">Costo unitario ref.</span>
          <span class="font-semibold tabular-nums">{{ money(costo) }} / un.</span>
        </div>
      </div>

      <div
        class="rounded-xl border p-3 md:col-span-3"
        :class="
          discrepancia == null || discrepancia === 0
            ? 'border-slate-200 bg-slate-50'
            : discrepancia < 0
              ? 'border-amber-300 bg-amber-50'
              : 'border-emerald-300 bg-emerald-50'
        "
      >
        <div
          class="flex items-center justify-between text-[11px] font-bold uppercase text-amber-700"
        >
          Discrepancia <Icon name="alert" :size="15" />
        </div>
        <div class="mt-1 font-display text-[22px] font-extrabold tabular-nums">
          <template v-if="discrepancia != null">
            {{ discrepancia > 0 ? '+' : '' }}{{ discrepancia }}
            <span v-if="discrepanciaPct != null" class="text-[12px] font-semibold">
              un. ({{ discrepanciaPct > 0 ? '+' : '' }}{{ discrepanciaPct.toFixed(1) }}%)
            </span>
          </template>
          <template v-else>—</template>
        </div>
        <div class="mt-2 flex flex-col border-t border-black/5 pt-1.5">
          <span class="text-[10px] font-semibold uppercase text-slate-500">Impacto financiero</span>
          <span
            class="font-display text-[14px] font-bold tabular-nums"
            :class="impacto != null && impacto < 0 ? 'text-crimson-ruby' : 'text-emerald-700'"
          >
            {{ impacto != null ? (impacto < 0 ? '−' : '+') + money(impacto) : '—' }}
          </span>
        </div>
      </div>
    </div>

    <div>
      <div
        class="mb-2 flex items-center justify-between text-[11px] font-bold uppercase text-slate-500"
      >
        <span>Motivo primario del descuadre</span>
        <span class="text-crimson-ruby">* Requerido por auditoría</span>
      </div>
      <div class="grid gap-2 sm:grid-cols-2">
        <label
          v-for="m in MOTIVOS"
          :key="m.v"
          class="flex cursor-pointer items-start gap-2.5 rounded-lg border-2 p-2.5 transition"
          :class="
            motivo === m.v
              ? 'border-brand-600 bg-brand-50'
              : 'border-brand-200 hover:bg-brand-50/60'
          "
        >
          <input v-model="motivo" :value="m.v" type="radio" name="motivo" class="mt-0.5" />
          <span class="text-left">
            <span class="block text-[12px] font-bold text-slate-900">{{ m.t }}</span>
            <span class="block text-[11px] leading-tight text-slate-500">{{ m.d }}</span>
          </span>
        </label>
      </div>
    </div>

    <label class="block text-[12px] font-semibold text-slate-600">
      Observaciones / justificación de auditoría
      <textarea
        v-model="observaciones"
        rows="2"
        maxlength="250"
        placeholder="Contexto del recuento, quién validó, evidencia…"
        class="mt-1 w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-[13px] text-slate-800"
      />
    </label>

    <p v-if="error" class="text-[12px] text-crimson-ruby">{{ error }}</p>
    <div v-if="resultado" class="rounded-lg bg-emerald-50 px-3 py-2 text-[12px] text-emerald-800">
      Ajuste aplicado — sistema {{ resultado.cantidad_sistema }} → físico
      {{ resultado.cantidad_fisica }} (Δ {{ resultado.diferencia }}).
    </div>

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
        class="inline-flex items-center gap-1.5 rounded-xl border border-brand-600 bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-40"
      >
        <Icon name="check" :size="16" />
        {{ enviando ? 'Aplicando…' : 'Confirmar y aplicar ajuste' }}
      </button>
    </div>
  </form>
</template>
