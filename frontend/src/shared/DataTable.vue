<script setup>
/**
 * Tabla de datos genérica y reutilizable (Principio XII: una sola implementación
 * de listado en toda la app). Recibe columnas + filas ya paginadas por el
 * backend; emite eventos de paginación, no pagina en cliente.
 */
import { computed } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true }, // [{ key, label, align?, formatter? }]
  rows: { type: Array, default: () => [] },
  rowKey: { type: [String, Function], default: 'id' },
  loading: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  pages: { type: Number, default: 1 },
  total: { type: Number, default: 0 },
  emptyText: { type: String, default: 'Sin resultados' },
})

const emit = defineEmits(['update:page', 'row-click'])

const keyFor = (row, idx) =>
  typeof props.rowKey === 'function' ? props.rowKey(row) : (row[props.rowKey] ?? idx)

const cell = (row, col) => (col.formatter ? col.formatter(row[col.key], row) : row[col.key])

const canPrev = computed(() => props.page > 1)
const canNext = computed(() => props.page < props.pages)
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
    <div class="overflow-x-auto">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="border-b border-outline-variant bg-surface-container-low">
            <th
              v-for="col in columns"
              :key="col.key"
              scope="col"
              class="px-4 py-3 font-semibold text-on-surface-variant"
              :class="col.align === 'right' ? 'text-right' : 'text-left'"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="columns.length" class="px-4 py-8 text-center text-on-surface-variant">
              Cargando…
            </td>
          </tr>
          <tr v-else-if="!rows.length">
            <td :colspan="columns.length" class="px-4 py-8 text-center text-on-surface-variant">
              {{ emptyText }}
            </td>
          </tr>
          <tr
            v-for="(row, idx) in rows"
            v-else
            :key="keyFor(row, idx)"
            class="border-b border-outline-variant last:border-0 hover:bg-surface-container-low"
            @click="emit('row-click', row)"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              class="px-4 py-3 text-on-surface"
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
      class="flex items-center justify-between gap-4 border-t border-outline-variant px-4 py-3 text-sm text-on-surface-variant"
    >
      <span>{{ total }} registro(s)</span>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 font-medium text-primary-container disabled:opacity-40"
          :disabled="!canPrev"
          @click="emit('update:page', page - 1)"
        >
          Anterior
        </button>
        <span>Página {{ page }} / {{ Math.max(pages, 1) }}</span>
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 font-medium text-primary-container disabled:opacity-40"
          :disabled="!canNext"
          @click="emit('update:page', page + 1)"
        >
          Siguiente
        </button>
      </div>
    </div>
  </div>
</template>
