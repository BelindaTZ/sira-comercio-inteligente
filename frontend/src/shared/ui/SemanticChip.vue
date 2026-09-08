<script setup>
/**
 * Chip / badge semántico del design-system (§Chips & Semantic Badges).
 *   fifo      — alerta de vencimiento / rotación lenta   (ámbar)
 *   quiebre   — quiebre de stock / merma / anomalía      (carmesí)
 *   ok        — stock sano / meta cumplida               (menta)
 *   ia        — insight predictivo / IA                  (amatista)
 *   neutral   — informativo                              (gris)
 */
defineProps({
  tipo: {
    type: String,
    default: 'neutral',
    validator: (v) => ['fifo', 'quiebre', 'ok', 'ia', 'neutral'].includes(v),
  },
})

const CLASES = {
  fifo: 'bg-[#fef3c7] text-[#b45309] ring-[#d97706]/20',
  quiebre: 'bg-[#ffe4e6] text-[#be123c] ring-[#e11d48]/20',
  ok: 'bg-[#d1fae5] text-[#047857] ring-[#059669]/20',
  ia: 'bg-orchid-soft text-[#6b21a8] ring-secondary/20',
  neutral: 'bg-surface-container text-on-surface-variant ring-outline-variant/40',
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.04em] ring-1"
    :class="CLASES[tipo]"
  >
    <slot />
  </span>
</template>
