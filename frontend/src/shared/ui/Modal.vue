<script setup>
/** Modal / diálogo del design-system (§Elevation Tier 2, radios 12px). */
const props = defineProps({
  titulo: { type: String, default: '' },
  abierto: { type: Boolean, default: true },
  // md (formularios simples) · lg · xl (auditoría de stock / merma, como docs/diseno-ui)
  size: { type: String, default: 'md' },
})
const emit = defineEmits(['cerrar'])

const ancho = { md: 'max-w-md', lg: 'max-w-2xl', xl: 'max-w-4xl' }[props.size] ?? 'max-w-md'
const grande = props.size === 'xl' || props.size === 'lg'
</script>

<template>
  <div
    v-if="abierto"
    class="fixed inset-0 z-[60] flex justify-center overflow-y-auto bg-black/40 backdrop-blur-sm"
    :class="grande ? 'items-start p-4 sm:p-6' : 'items-start p-4 pt-24'"
  >
    <div class="fixed inset-0" @click="emit('cerrar')" />
    <div
      class="relative my-auto flex w-full flex-col rounded-2xl border border-black/10 bg-white shadow-tier-2"
      :class="[ancho, grande ? 'max-h-[92vh]' : '']"
      role="dialog"
    >
      <header
        class="flex items-start justify-between gap-4 border-b border-brand-200/70 px-5 py-4"
        :class="grande ? '' : 'pb-3'"
      >
        <div class="min-w-0">
          <slot name="cabecera">
            <h2 class="font-display text-base font-bold text-brand-950">{{ titulo }}</h2>
          </slot>
        </div>
        <button
          type="button"
          class="shrink-0 rounded-lg p-1 text-on-surface-variant hover:bg-surface-container"
          aria-label="Cerrar"
          @click="emit('cerrar')"
        >
          <svg class="h-5 w-5" viewBox="0 0 16 16" fill="none">
            <path
              d="M4 4l8 8M12 4l-8 8"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </button>
      </header>
      <div :class="grande ? 'flex-1 overflow-y-auto p-5' : 'p-5 pt-4'">
        <slot />
      </div>
      <footer
        v-if="$slots.footer"
        class="flex flex-wrap items-center justify-end gap-2.5 border-t border-brand-200/70 px-5 py-3.5"
      >
        <slot name="footer" />
      </footer>
    </div>
  </div>
</template>
