<script setup>
/**
 * Panel de trabajo estandarizado (Principio XII): título + set fijo de acciones
 * en la misma ubicación/estilo en toda la app. Las acciones específicas de cada
 * entidad (Anular en ventas, Aprobar en compras, …) se pasan por `actions`.
 */
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  // [{ key, label, variant?: 'primary'|'neutral'|'danger', disabled?, hidden? }]
  actions: { type: Array, default: () => [] },
})

const emit = defineEmits(['action'])

const variantClass = {
  primary: 'bg-primary-container text-on-primary-container hover:opacity-90',
  neutral: 'border border-outline-variant text-on-surface hover:bg-surface-container-low',
  danger: 'bg-error text-on-error hover:opacity-90',
}
</script>

<template>
  <section class="rounded-2xl bg-surface-container-lowest p-6 shadow-sm">
    <header class="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-bold text-on-surface">
          {{ title }}
        </h2>
        <p v-if="subtitle" class="mt-1 text-sm text-on-surface-variant">
          {{ subtitle }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="action in actions.filter((a) => !a.hidden)"
          :key="action.key"
          type="button"
          class="rounded-lg px-4 py-2 text-sm font-semibold transition disabled:opacity-40"
          :class="variantClass[action.variant || 'neutral']"
          :disabled="action.disabled"
          @click="emit('action', action.key)"
        >
          {{ action.label }}
        </button>
      </div>
    </header>
    <slot />
  </section>
</template>
