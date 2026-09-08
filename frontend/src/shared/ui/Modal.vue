<script setup>
/** Modal / diálogo del design-system (§Elevation Tier 2, radios 12px). */
defineProps({ titulo: { type: String, default: '' } })
const emit = defineEmits(['cerrar'])
</script>

<template>
  <div class="fixed inset-0 z-[60] flex items-start justify-center bg-black/30 p-4 pt-24">
    <div class="fixed inset-0" @click="emit('cerrar')" />
    <div
      class="relative w-full max-w-md rounded-xl border border-black/10 bg-white p-5 shadow-tier-2"
      role="dialog"
    >
      <header class="mb-3 flex items-center justify-between">
        <h2 class="font-display text-base font-semibold text-on-surface">{{ titulo }}</h2>
        <button
          type="button"
          class="rounded-md p-1 text-on-surface-variant hover:bg-surface-container"
          aria-label="Cerrar"
          @click="emit('cerrar')"
        >
          <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none">
            <path
              d="M4 4l8 8M12 4l-8 8"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </button>
      </header>
      <slot />
    </div>
  </div>
</template>
