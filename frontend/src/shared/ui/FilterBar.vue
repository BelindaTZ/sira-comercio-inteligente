<script setup>
/**
 * Barra de filtros de una pantalla de gestión (Principio XII: filtros reactivos,
 * sin botón "Buscar"). Réplica de `docs/diseno-ui/.../sira_inventario_y_alertas_fifo/`:
 * fila de buscador + dropdowns (slot), y debajo pills segmentadas con contador.
 *
 * `pills`: [{ value, label, count?, tipo? }]  — `tipo`: fifo | quiebre | ok | ia | neutral
 */
import Icon from './Icon.vue'

defineProps({
  modelValue: { type: String, default: '' }, // texto del buscador
  placeholder: { type: String, default: 'Buscar…' },
  pills: { type: Array, default: () => [] },
  pillActiva: { type: [String, Number, null], default: null },
})
const emit = defineEmits(['update:modelValue', 'pill'])

const PILL_INACTIVA = {
  fifo: 'border-amber-300 text-[#b45309] hover:bg-amber-50',
  quiebre: 'border-rose-300 text-[#be123c] hover:bg-rose-50',
  ok: 'border-emerald-300 text-[#047857] hover:bg-emerald-50',
  ia: 'border-amethyst-300 text-amethyst-800 hover:bg-amethyst-50',
  neutral: 'border-brand-200 text-slate-600 hover:bg-brand-50',
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex flex-wrap items-center gap-2">
      <div class="relative min-w-[16rem] flex-1">
        <Icon
          name="search"
          :size="16"
          class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant"
        />
        <input
          :value="modelValue"
          type="text"
          :placeholder="placeholder"
          class="h-10 w-full rounded-xl border border-brand-300 bg-white pl-9 pr-3 text-[13px] text-slate-800 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          @input="emit('update:modelValue', $event.target.value)"
        />
      </div>
      <slot name="dropdowns" />
    </div>

    <div v-if="pills.length" class="flex flex-wrap items-center gap-2 text-[12px]">
      <button
        v-for="p in pills"
        :key="p.value"
        type="button"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 font-bold shadow-2xs transition"
        :class="
          pillActiva === p.value
            ? 'border-brand-800 bg-brand-800 text-white ring-1 ring-brand-800/30'
            : `bg-white ${PILL_INACTIVA[p.tipo] || PILL_INACTIVA.neutral}`
        "
        @click="emit('pill', p.value)"
      >
        {{ p.label }}
        <span
          v-if="p.count != null"
          class="rounded-full px-1.5 text-[11px] font-extrabold tabular-nums"
          :class="pillActiva === p.value ? 'bg-white/20' : 'bg-brand-50 text-brand-900'"
        >
          {{ p.count }}
        </span>
      </button>
    </div>
  </div>
</template>
