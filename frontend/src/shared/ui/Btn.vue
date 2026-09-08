<script setup>
/**
 * Botón estándar — clases EXACTAS de la toolbar de acciones de
 * `docs/diseno-ui/.../sira_dashboard_ejecutivo/code.html`.
 *
 * `variant`: primary (emerald) | ghost (blanco) | ia (amatista) | danger (rose)
 */
defineProps({
  variant: { type: String, default: 'ghost' },
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
})

const CLASES = {
  primary:
    'bg-brand-800 hover:bg-brand-700 text-white font-bold border border-brand-600 shadow-md hover:shadow-glow-teal active:scale-[0.99]',
  ghost:
    'bg-white border border-brand-200 text-slate-700 font-semibold hover:bg-brand-50/70 hover:border-brand-400 shadow-2xs',
  ia: 'bg-gradient-to-r from-amethyst-100 to-amethyst-50 border border-amethyst-300 text-amethyst-900 font-bold hover:from-amethyst-200 hover:to-amethyst-100 hover:border-amethyst-400 hover:shadow-glow-amethyst',
  danger:
    'bg-white border border-rose-300 text-rose-700 font-semibold hover:bg-rose-50 hover:border-rose-400 shadow-2xs',
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled"
    class="inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-[13px] transition-all disabled:opacity-50"
    :class="CLASES[variant] || CLASES.ghost"
  >
    <slot />
  </button>
</template>
