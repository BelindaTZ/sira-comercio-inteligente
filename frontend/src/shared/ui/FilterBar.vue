<script setup>
/**
 * Barra de filtros reactiva (Principio XII: sin botón "Buscar"). Markup EXACTO de
 * `docs/diseno-ui/.../sira_inventario_y_alertas_fifo…/code.html` → tarjeta propia
 * (`.satin-card`) SEPARADA de la tabla: fila de buscador + dropdowns (slot), y
 * debajo pills segmentadas con contador.
 *
 * `pills`: [{ value, label, count?, tipo? }] — `tipo`: fifo | quiebre | ok | ia | neutral
 */
import Icon from './Icon.vue'

defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Buscar…' },
  pills: { type: Array, default: () => [] },
  pillActiva: { type: [String, Number, null], default: null },
})
const emit = defineEmits(['update:modelValue', 'pill'])

const PILL_INACTIVA = {
  fifo: 'border-amber-300 text-damask-amber hover:bg-amber-50',
  quiebre: 'border-rose-300 text-crimson-ruby hover:bg-rose-50',
  ok: 'border-emerald-300 text-emerald-700 hover:bg-emerald-50',
  ia: 'border-amethyst-300 text-amethyst-800 hover:bg-amethyst-50',
  neutral: 'border-surface-border text-on-surface-variant hover:bg-brand-50',
}
</script>

<template>
  <div class="satin-card flex flex-col gap-3.5 rounded-2xl p-4">
    <div class="flex flex-col items-stretch justify-between gap-3 lg:flex-row lg:items-center">
      <div class="relative max-w-lg flex-1">
        <Icon
          name="search"
          :size="17"
          class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant"
        />
        <input
          :value="modelValue"
          type="text"
          :placeholder="placeholder"
          class="h-10 w-full rounded-xl border border-surface-border bg-surface-canvas pl-9 pr-3 text-[13px] text-on-surface transition-all placeholder:text-outline focus:border-primary focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/15"
          @input="emit('update:modelValue', $event.target.value)"
        />
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <slot name="dropdowns" />
      </div>
    </div>

    <div
      v-if="pills.length"
      class="no-scrollbar flex items-center gap-2 overflow-x-auto pb-0.5 text-[12px]"
    >
      <button
        v-for="p in pills"
        :key="p.value"
        type="button"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 font-bold shadow-2xs transition"
        :class="
          pillActiva === p.value
            ? 'border-primary bg-primary text-on-primary ring-1 ring-primary/30'
            : `bg-surface-canvas ${PILL_INACTIVA[p.tipo] || PILL_INACTIVA.neutral}`
        "
        @click="emit('pill', p.value)"
      >
        {{ p.label }}
        <span
          v-if="p.count != null"
          class="rounded-full px-1.5 text-[11px] font-extrabold tabular-nums"
          :class="pillActiva === p.value ? 'bg-white/20 text-white' : 'bg-white/70'"
        >
          {{ p.count }}
        </span>
      </button>
    </div>
  </div>
</template>
