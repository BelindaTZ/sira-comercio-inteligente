<script setup>
/**
 * Encabezado de página del design-system / referencia: headline (Plus Jakarta) +
 * subtítulo + cluster de acciones a la derecha. Mismo bloque en `screen.png` de
 * Dashboard Ejecutivo e Inventario & FIFO.
 */
defineProps({
  titulo: { type: String, required: true },
  subtitulo: { type: String, default: '' },
})
</script>

<template>
  <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
    <div class="max-w-2xl">
      <h1 class="font-display text-[30px] font-bold leading-9 tracking-tight text-on-surface">
        {{ titulo }}
      </h1>
      <p v-if="subtitulo" class="mt-1.5 text-sm text-on-surface-variant">{{ subtitulo }}</p>
    </div>
    <div v-if="$slots.acciones" class="flex flex-wrap items-center gap-2">
      <slot name="acciones" />
    </div>
  </header>
</template>
