<script setup>
/**
 * KPI tile del design-system (§Cards & KPI Tiles): micro-label + icono arriba,
 * cifra tabular grande, pill de delta semántico, y microcopy / slot de sparkline
 * abajo. Réplica de las tarjetas de `docs/diseno-ui/.../screen.png`.
 *
 * `variant`:  emerald (relleno, primera tile) | plain | amber | crimson | mint
 * `estado`: texto del chip de delta;  `estadoTipo`: color del chip (SemanticChip).
 */
import SemanticChip from './SemanticChip.vue'

defineProps({
  label: { type: String, required: true },
  valor: { type: [String, Number], default: null }, // null => "no disponible"
  unidad: { type: String, default: '' },
  microcopy: { type: String, default: '' },
  estado: { type: String, default: '' },
  estadoTipo: { type: String, default: 'neutral' },
  variant: { type: String, default: 'plain' },
})

const BORDES = {
  plain: 'border-t border-outline-variant',
  amber: 'border-t-2 border-damask-amber',
  crimson: 'border-t-2 border-crimson-ruby',
  mint: 'border-t-2 border-tertiary',
}
</script>

<template>
  <article
    class="flex flex-col gap-2 rounded-lg p-4 shadow-tier-1"
    :class="
      variant === 'emerald'
        ? 'bg-primary-container text-on-primary'
        : `bg-surface-container-lowest ${BORDES[variant] || BORDES.plain}`
    "
  >
    <header class="flex items-center justify-between">
      <span
        class="text-[11px] font-semibold uppercase tracking-[0.04em]"
        :class="variant === 'emerald' ? 'text-primary-fixed-dim' : 'text-on-surface-variant'"
      >
        {{ label }}
      </span>
      <slot name="icono" />
    </header>

    <p
      class="font-display text-[28px] font-semibold leading-8 tabular-nums"
      :class="variant === 'emerald' ? 'text-white' : 'text-on-surface'"
    >
      <template v-if="valor !== null && valor !== undefined && valor !== ''">
        {{ valor
        }}<span v-if="unidad" class="ml-1 text-sm font-medium opacity-70">{{ unidad }}</span>
      </template>
      <span v-else class="text-base font-medium opacity-70">No disponible</span>
    </p>

    <footer class="flex items-center gap-2">
      <SemanticChip v-if="estado" :tipo="estadoTipo">{{ estado }}</SemanticChip>
      <span
        v-if="microcopy"
        class="text-xs"
        :class="variant === 'emerald' ? 'text-primary-fixed-dim' : 'text-on-surface-variant'"
      >
        {{ microcopy }}
      </span>
      <slot name="sparkline" />
    </footer>
  </article>
</template>
