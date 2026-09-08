<script setup>
/**
 * Encabezado de página — markup EXACTO de la "Executive Title & Action Toolbar"
 * de `docs/diseno-ui/.../sira_dashboard_ejecutivo/code.html`.
 */
defineProps({
  titulo: { type: String, required: true },
  subtitulo: { type: String, default: '' },
})
</script>

<template>
  <section class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-center">
    <div>
      <div class="flex flex-wrap items-center gap-3">
        <h1
          class="font-display text-2xl font-extrabold tracking-tight text-brand-950 lg:text-[27px]"
        >
          {{ titulo }}
        </h1>
        <slot name="badge" />
      </div>
      <p v-if="subtitulo" class="mt-1 text-[13px] font-medium text-slate-600">{{ subtitulo }}</p>
    </div>
    <div v-if="$slots.acciones" class="flex flex-wrap items-center gap-2.5">
      <slot name="acciones" />
    </div>
  </section>
</template>
