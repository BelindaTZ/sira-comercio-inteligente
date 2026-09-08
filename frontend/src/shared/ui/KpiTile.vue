<script setup>
/**
 * KPI tile — markup EXACTO de `docs/diseno-ui/.../sira_dashboard_ejecutivo/code.html`
 * (KPI 0 "hero" en emerald profundo, KPI 1-5 "tinted" con `border-t-2`).
 *
 * `variant`:
 *   hero    → tarjeta rellena emerald profundo, texto blanco (la primera de la fila)
 *   default → `.kpi-tinted`, borde superior emerald
 *   ia      → `.kpi-tinted`, borde superior amatista (métricas de IA/predictivo)
 *   amber / crimson / mint → `.kpi-tinted`, borde superior semántico
 *
 * Compat: acepta también `emerald`→hero, `plain`→default.
 */
import SemanticChip from './SemanticChip.vue'

const props = defineProps({
  label: { type: String, required: true },
  valor: { type: [String, Number], default: null }, // null → "no disponible"
  unidad: { type: String, default: '' },
  microcopy: { type: String, default: '' },
  estado: { type: String, default: '' }, // texto del chip de delta
  estadoTipo: { type: String, default: 'neutral' }, // color del chip (SemanticChip)
  variant: { type: String, default: 'default' },
})

const modo = {
  emerald: 'hero',
  hero: 'hero',
  plain: 'default',
  default: 'default',
  mint: 'mint',
  ia: 'ia',
  amber: 'amber',
  crimson: 'crimson',
}[props.variant]

const BORDE = {
  default: 'border-t-brand-600',
  mint: 'border-t-brand-600',
  ia: 'border-t-amethyst-500',
  amber: 'border-t-damask-amber',
  crimson: 'border-t-crimson-ruby',
}

const hayValor = () => props.valor !== null && props.valor !== undefined && props.valor !== ''
</script>

<template>
  <!-- Hero -->
  <div
    v-if="modo === 'hero'"
    class="flex flex-col justify-between rounded-2xl border border-brand-600 bg-gradient-to-br from-brand-900 via-brand-800 to-brand-750 p-4 text-white shadow-hero-teal transition-all hover:-translate-y-1"
  >
    <div class="flex items-center justify-between">
      <span class="text-[11px] font-extrabold uppercase tracking-wider text-brand-200">{{
        label
      }}</span>
      <span
        class="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-300 px-2 py-0.5 text-[10px] font-bold text-emerald-950"
      >
        <span class="live-indicator h-1.5 w-1.5 rounded-full bg-emerald-700" /> En vivo
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
          class="rounded bg-emerald-200 px-1.5 py-0.5 text-[11px] font-extrabold text-emerald-900"
        >
          {{ estado }}
        </span>
      </div>
      <p v-if="microcopy" class="mt-0.5 text-[10px] font-medium text-brand-200">{{ microcopy }}</p>
    </div>
    <slot name="sparkline" />
  </div>

  <!-- Tinted -->
  <div
    v-else
    class="kpi-tinted flex flex-col justify-between rounded-2xl border-t-2 p-4"
    :class="BORDE[modo] || BORDE.default"
  >
    <div class="flex items-center justify-between">
      <span class="text-[11px] font-bold uppercase tracking-wider text-brand-900">{{ label }}</span>
      <div
        v-if="$slots.icono"
        class="flex h-7 w-7 items-center justify-center rounded-lg border text-brand-800"
        :class="
          modo === 'ia'
            ? 'border-amethyst-300 bg-amethyst-100 text-amethyst-700'
            : 'border-brand-300 bg-brand-100'
        "
      >
        <slot name="icono" />
      </div>
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
        <SemanticChip v-if="estado" :tipo="estadoTipo">{{ estado }}</SemanticChip>
      </div>
      <p v-if="microcopy" class="mt-0.5 text-[10px] font-medium text-slate-500">{{ microcopy }}</p>
    </div>
    <div
      v-if="$slots.pie || $slots.sparkline"
      class="flex items-center justify-between border-t border-brand-200/80 pt-2"
    >
      <slot name="pie" />
      <slot name="sparkline" />
    </div>
  </div>
</template>
