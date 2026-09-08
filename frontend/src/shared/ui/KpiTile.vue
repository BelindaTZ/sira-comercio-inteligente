<script setup>
/**
 * KPI tile — markup EXACTO de `docs/diseno-ui/.../sira_inventario_y_alertas_fifo…/code.html`
 * y `…/sira_dashboard_ejecutivo…/code.html`.
 *
 *   hero    → tarjeta rellena verde abisal (#0a3632), texto blanco. La primera de la fila.
 *   default → `.kpi-tinted`, borde superior 4px verde + label verde abisal.
 *   mint    → borde + label VERDE éxito  (métrica sana / en meta)
 *   crimson → borde + label ROJO carmesí (quiebre / crítico / merma)
 *   amber   → tinte cálido + borde + label ÁMBAR (alerta FIFO / vencimiento)
 *   ia      → borde + label AMATISTA (métrica de IA / predictivo)
 *
 * Compat: `emerald`→hero, `plain`→default.
 */
import SemanticChip from './SemanticChip.vue'

const props = defineProps({
  label: { type: String, required: true },
  valor: { type: [String, Number], default: null }, // null → "No disponible"
  unidad: { type: String, default: '' },
  microcopy: { type: String, default: '' },
  estado: { type: String, default: '' }, // texto del chip de delta
  estadoTipo: { type: String, default: 'neutral' }, // color del chip (SemanticChip)
  variant: { type: String, default: 'default' },
})

const modo =
  {
    emerald: 'hero',
    hero: 'hero',
    plain: 'default',
    default: 'default',
    mint: 'mint',
    ia: 'ia',
    amber: 'amber',
    crimson: 'crimson',
  }[props.variant] ?? 'default'

// Config por modo: contenedor, color del borde superior, color del label y caja de ícono.
const ESTILO = {
  default: {
    caja: 'kpi-tinted',
    borde: 'border-t-brand-600',
    label: 'text-brand-800',
    icono: 'border-brand-300 bg-brand-100 text-brand-800',
  },
  mint: {
    caja: 'kpi-tinted',
    borde: 'border-t-emerald-600',
    label: 'text-emerald-700',
    icono: 'border-emerald-300 bg-emerald-100 text-emerald-700',
  },
  crimson: {
    caja: 'kpi-tinted',
    borde: 'border-t-crimson-ruby',
    label: 'text-crimson-ruby',
    icono: 'border-rose-300 bg-rose-100 text-crimson-ruby',
  },
  amber: {
    caja: 'kpi-amber',
    borde: 'border-t-damask-amber',
    label: 'text-damask-amber',
    icono: 'border-amber-300 bg-amber-100 text-damask-amber',
  },
  ia: {
    caja: 'kpi-tinted',
    borde: 'border-t-amethyst-500',
    label: 'text-amethyst-700',
    icono: 'border-amethyst-300 bg-amethyst-100 text-amethyst-700',
  },
}

const e = ESTILO[modo] ?? ESTILO.default
const hayValor = () => props.valor !== null && props.valor !== undefined && props.valor !== ''
</script>

<template>
  <!-- Hero: verde abisal profundo, texto blanco -->
  <div
    v-if="modo === 'hero'"
    class="relative flex flex-col justify-between overflow-hidden rounded-2xl border border-brand-600 bg-brand-800 p-5 text-white shadow-hero-teal transition-all hover:-translate-y-1"
  >
    <div
      class="pointer-events-none absolute -bottom-6 -right-6 h-32 w-32 rounded-full bg-brand-600/40 blur-2xl"
    />
    <div class="relative z-10 flex items-start justify-between">
      <div>
        <div class="flex items-center gap-1.5">
          <span class="text-[11px] font-bold uppercase tracking-wider text-primary-fixed">{{
            label
          }}</span>
          <span
            v-if="estado"
            class="rounded-full border border-primary-fixed/30 bg-brand-700 px-1.5 py-0.5 text-[9.5px] font-extrabold uppercase text-primary-fixed"
          >
            {{ estado }}
          </span>
        </div>
        <div class="mt-0.5 font-display text-[32px] font-extrabold tracking-tight tabular-nums">
          <template v-if="hayValor()">{{ valor }}{{ unidad ? ' ' + unidad : '' }}</template>
          <template v-else>No disponible</template>
        </div>
      </div>
      <span
        class="inline-flex items-center gap-1 rounded-full border border-primary-fixed/30 bg-brand-700 px-2 py-0.5 text-[10px] font-bold text-primary-fixed"
      >
        <span class="live-indicator h-1.5 w-1.5 rounded-full bg-primary-fixed" /> En vivo
      </span>
    </div>
    <div
      class="relative z-10 mt-3 flex items-center justify-between border-t border-white/15 pt-2.5 text-[11.5px]"
    >
      <span class="font-medium text-primary-fixed">{{ microcopy || 'Sincronizado' }}</span>
      <slot name="pie" />
      <slot name="sparkline" />
    </div>
  </div>

  <!-- Tinted: fondo claro, borde superior 4px y label en color semántico -->
  <div
    v-else
    class="flex flex-col justify-between gap-2 rounded-2xl border-t-4 p-4"
    :class="[e.caja, e.borde]"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="text-[11px] font-bold uppercase tracking-wider" :class="e.label">{{
            label
          }}</span>
          <SemanticChip v-if="estado" :tipo="estadoTipo">{{ estado }}</SemanticChip>
        </div>
        <div
          class="mt-1 font-display text-[32px] font-extrabold leading-none tracking-tight tabular-nums text-on-surface"
        >
          <template v-if="hayValor()">{{ valor }}{{ unidad ? ' ' + unidad : '' }}</template>
          <span v-else class="text-base font-bold text-on-surface-variant">No disponible</span>
        </div>
      </div>
      <span
        v-if="$slots.icono"
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border"
        :class="e.icono"
      >
        <slot name="icono" />
      </span>
    </div>
    <div
      class="flex items-center justify-between border-t border-surface-border pt-2 text-[11px] font-medium text-on-surface-variant"
    >
      <span class="truncate">{{ microcopy || 'Actualizado en vivo' }}</span>
      <slot name="pie" />
      <slot name="sparkline" />
    </div>
  </div>
</template>
