<script setup>
/**
 * Tabla de datos genérica (Principio XII: una sola implementación de listado).
 * Réplica del data-grid de `docs/diseno-ui/.../sira_inventario_y_alertas_fifo/`:
 * header oscuro, filas de 44px, valores numéricos `tabular-nums` a la derecha,
 * footer con "Mostrando X–Y de N", filas por página y números de página.
 *
 * Recibe filas ya paginadas por el backend; emite eventos, no pagina en cliente.
 */
import { computed } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true }, // [{ key, label, align?, formatter?, width? }]
  rows: { type: Array, default: () => [] },
  rowKey: { type: [String, Function], default: 'id' },
  loading: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  size: { type: Number, default: 25 },
  total: { type: Number, default: 0 },
  emptyText: { type: String, default: 'Sin resultados' },
  sizeOptions: { type: Array, default: () => [15, 25, 50, 100] },
})

const emit = defineEmits(['update:page', 'update:size', 'row-click'])

const keyFor = (row, idx) =>
  typeof props.rowKey === 'function' ? props.rowKey(row) : (row[props.rowKey] ?? idx)
const cell = (row, col) => (col.formatter ? col.formatter(row[col.key], row) : row[col.key])

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))
const desde = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.size + 1))
const hasta = computed(() => Math.min(props.page * props.size, props.total))

// Ventana de números de página (máx 5) alrededor de la actual.
const numeros = computed(() => {
  const t = pages.value
  if (t <= 7) return Array.from({ length: t }, (_, i) => i + 1)
  const p = props.page
  const out = [1]
  const lo = Math.max(2, p - 1)
  const hi = Math.min(t - 1, p + 1)
  if (lo > 2) out.push('…')
  for (let i = lo; i <= hi; i++) out.push(i)
  if (hi < t - 1) out.push('…')
  out.push(t)
  return out
})
</script>

<template>
  <div
    class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-tier-1"
  >
    <div class="overflow-x-auto">
      <table class="w-full border-collapse text-[13px]">
        <thead>
          <tr class="bg-primary text-white">
            <th
              v-for="col in columns"
              :key="col.key"
              scope="col"
              class="whitespace-nowrap px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.04em]"
              :class="col.align === 'right' ? 'text-right' : 'text-left'"
              :style="col.width ? { width: col.width } : null"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="columns.length" class="px-4 py-10 text-center text-on-surface-variant">
              Cargando…
            </td>
          </tr>
          <tr v-else-if="!rows.length">
            <td :colspan="columns.length" class="px-4 py-10 text-center text-on-surface-variant">
              {{ emptyText }}
            </td>
          </tr>
          <tr
            v-for="(row, idx) in rows"
            v-else
            :key="keyFor(row, idx)"
            class="border-b border-[rgba(15,23,42,0.05)] transition-colors last:border-0 hover:bg-[rgba(10,54,50,0.03)]"
            @click="emit('row-click', row)"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              class="h-11 px-4 text-on-surface"
              :class="col.align === 'right' ? 'text-right tabular-nums' : 'text-left'"
            >
              <slot :name="`cell:${col.key}`" :row="row" :value="row[col.key]">
                {{ cell(row, col) }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      class="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant px-4 py-2.5 text-[12px] text-on-surface-variant"
    >
      <div class="flex items-center gap-3">
        <span
          >Mostrando <b class="tabular-nums text-on-surface">{{ desde }}–{{ hasta }}</b> de
          <b class="tabular-nums text-on-surface">{{ total }}</b></span
        >
        <label class="flex items-center gap-1.5">
          Filas
          <select
            :value="size"
            class="rounded-md border border-outline-variant bg-white px-1.5 py-0.5 text-[12px] text-on-surface"
            @change="emit('update:size', Number($event.target.value))"
          >
            <option v-for="s in sizeOptions" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
      </div>
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="rounded-md px-2 py-1 font-medium text-on-surface-variant hover:bg-surface-container disabled:opacity-30"
          :disabled="page <= 1"
          @click="emit('update:page', page - 1)"
        >
          ‹
        </button>
        <template v-for="(n, i) in numeros" :key="i">
          <span v-if="n === '…'" class="px-1.5 text-on-surface-variant">…</span>
          <button
            v-else
            type="button"
            class="min-w-[26px] rounded-md px-1.5 py-1 text-center font-semibold transition"
            :class="
              n === page
                ? 'bg-primary text-white'
                : 'text-on-surface-variant hover:bg-surface-container'
            "
            @click="emit('update:page', n)"
          >
            {{ n }}
          </button>
        </template>
        <button
          type="button"
          class="rounded-md px-2 py-1 font-medium text-on-surface-variant hover:bg-surface-container disabled:opacity-30"
          :disabled="page >= pages"
          @click="emit('update:page', page + 1)"
        >
          ›
        </button>
      </div>
    </div>
  </div>
</template>
