<script setup>
/**
 * KPI tile — markup EXACTO de las "High Impact KPIs" de
 * `docs/diseno-ui/.../sira_dashboard_ejecutivo…/code.html` (líneas 322-498).
 *
 * Un solo lenguaje visual para TODA la app:
 *  - etiqueta en tono oscuro de marca (NO en color semántico)
 *  - borde superior fino de 2px (verde de marca; amatista sólo en métricas de IA)
 *  - el color semántico vive en el "delta pill" (verde sube / rosa baja / ámbar ojo)
 *  - pie con divisor: mini-label + valor a la izq., sparkline/chip a la der. (slots)
 *
 * `variant`: emerald|hero → tarjeta rellena verde abisal · ia → borde amatista ·
 * default (o mint/plain/amber/crimson, por compat) → tinted con borde verde.
 */
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  valor: { type: [String, Number], default: null },
  unidad: { type: String, default: '' },
  microcopy: { type: String, default: '' },
  estado: { type: String, default: '' }, // texto del delta pill
  estadoTipo: { type: String, default: 'neutral' }, // ok | quiebre | fifo | ia | neutral
  variant: { type: String, default: 'default' },
  pieLabel: { type: String, default: '' },
  pieValor: { type: String, default: '' },
})

const esHero = computed(() => props.variant === 'emerald' || props.variant === 'hero')
const esIA = computed(() => props.variant === 'ia')

const DELTA = {
  ok: 'text-emerald-800 bg-emerald-100 border-emerald-300',
  quiebre: 'text-rose-800 bg-rose-100 border-rose-300',
  fifo: 'text-amber-800 bg-amber-100 border-amber-300',
  ia: 'text-amethyst-800 bg-amethyst-100 border-amethyst-300',
  neutral: 'text-slate-700 bg-slate-100 border-slate-300',
}
const deltaCls = computed(() => DELTA[props.estadoTipo] || DELTA.neutral)
const hayValor = () => props.valor !== null && props.valor !== undefined && props.valor !== ''
const hayPie = () => props.pieLabel || props.pieValor
</script>

<template>
  <!-- HERO — verde abisal profundo -->
  <div
    v-if="esHero"
    class="flex flex-col justify-between rounded-2xl border border-brand-600 bg-gradient-to-br from-brand-900 via-brand-800 to-brand-750 p-4 text-white shadow-hero-teal transition-all hover:-translate-y-1"
  >
    <div class="flex items-center justify-between">
      <span class="text-[11px] font-extrabold uppercase tracking-wider text-brand-200">{{
        label
      }}</span>
      <span
        class="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-300 px-2 py-0.5 text-[10px] font-bold text-emerald-950 shadow-xs"
      >
        <span class="live-indicator h-1.5 w-1.5 rounded-full bg-emerald-700" /> En Vivo
      </span>
    </div>
    <div class="my-2.5">
      <div class="flex items-baseline gap-2">
        <span class="font-display text-[24px] font-extrabold tracking-tight tabular-nums">
          <template v-if="hayValor()">{{ valor }}{{ unidad ? ' ' + unidad : '' }}</template>
          <template v-else>No disponible</template>
        </span>
        <span
          v-if="estado"
          class="rounded bg-emerald-200 px-1.5 py-0.5 text-[11px] font-extrabold text-emerald-900 shadow-2xs"
          >{{ estado }}</span
        >
      </div>
      <p v-if="microcopy" class="mt-0.5 text-[10px] font-medium text-brand-200">{{ microcopy }}</p>
    </div>
    <div v-if="hayPie() || $slots.sparkline" class="border-t border-white/15 pt-2">
      <div class="flex items-center justify-between">
        <div v-if="hayPie()" class="flex flex-col leading-tight">
          <span class="text-[9px] font-bold uppercase tracking-wider text-brand-200">{{
            pieLabel
          }}</span>
          <span class="text-[11px] font-bold text-white">{{ pieValor }}</span>
        </div>
        <slot name="sparkline" />
      </div>
    </div>
  </div>

  <!-- TINTED — tarjeta clara, borde superior 2px, etiqueta oscura -->
  <div
    v-else
    class="kpi-tinted flex flex-col justify-between rounded-2xl border-t-2 p-4"
    :class="esIA ? 'border-t-amethyst-500' : 'border-t-brand-600'"
  >
    <div class="flex items-center justify-between">
      <span
        class="text-[11px] font-bold uppercase tracking-wider"
        :class="esIA ? 'text-amethyst-950' : 'text-brand-900'"
        >{{ label }}</span
      >
      <span
        v-if="$slots.icono"
        class="flex h-7 w-7 items-center justify-center rounded-lg border"
        :class="
          esIA
            ? 'border-amethyst-300 bg-amethyst-100 text-amethyst-700'
            : 'border-brand-300 bg-brand-100 text-brand-800'
        "
      >
        <slot name="icono" />
      </span>
    </div>
    <div class="my-2">
      <div class="flex items-baseline gap-2">
        <span
          class="font-display text-[22px] font-extrabold tracking-tight tabular-nums text-brand-950"
        >
          <template v-if="hayValor()">{{ valor }}{{ unidad ? ' ' + unidad : '' }}</template>
          <template v-else
            ><span class="text-base font-bold text-slate-500">No disponible</span></template
          >
        </span>
        <span
          v-if="estado"
          class="inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-bold"
          :class="deltaCls"
          >{{ estado }}</span
        >
      </div>
      <p v-if="microcopy" class="mt-0.5 text-[10px] font-medium text-slate-500">{{ microcopy }}</p>
    </div>
    <!-- Cuerpo opcional: barra graduada, gauge, etc. -->
    <div v-if="$slots.cuerpo" class="mb-1"><slot name="cuerpo" /></div>
    <div
      v-if="hayPie() || $slots.pie || $slots.sparkline || $slots.cta"
      class="flex items-center justify-between gap-2 border-t border-brand-200/80 pt-2"
    >
      <div v-if="hayPie()" class="flex min-w-0 flex-col leading-tight">
        <span class="text-[9px] font-bold uppercase tracking-wider text-slate-500">{{
          pieLabel
        }}</span>
        <span class="truncate text-[11px] font-bold text-brand-900">{{ pieValor }}</span>
      </div>
      <slot name="pie" />
      <slot name="sparkline" />
      <slot name="cta" />
    </div>
  </div>
</template>
