<script setup>
/**
 * Data-grid — markup EXACTO del panel "Rendimiento Operacional por Sucursal" de
 * `docs/diseno-ui/.../sira_dashboard_ejecutivo…/code.html` (líneas 844-1060):
 *
 *  - `.satin-card` con cabecera de panel (gradiente sage): título + badge de
 *    conteo + subtítulo a la izquierda; **buscador + iconos a la derecha**
 *    (el buscador vive AQUÍ, no en una tarjeta aparte).
 *  - fila opcional de pills segmentadas (Principio XII) bajo la cabecera.
 *  - `<thead>` en gradiente verde abisal, filas `divide-y`, celdas `py-3.5 px-6`.
 *  - footer de paginación estandarizado.
 *
 * Recibe filas ya paginadas por el backend; emite eventos, no pagina en cliente.
 */
import { computed } from 'vue'
import Icon from './ui/Icon.vue'

const props = defineProps({
  columns: { type: Array, required: true }, // [{ key, label, align?, formatter?, width? }]
  rows: { type: Array, default: () => [] },
  rowKey: { type: [String, Function], default: 'id' },
  loading: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  size: { type: Number, default: 25 },
  total: { type: Number, default: 0 },
  titulo: { type: String, default: '' },
  subtitulo: { type: String, default: '' },
  // buscador embebido en la cabecera del panel
  search: { type: String, default: null }, // null → sin buscador
  searchPlaceholder: { type: String, default: 'Filtrar por nombre o ID…' },
  // pills segmentadas (Principio XII: filtros reactivos, sin botón "Buscar")
  pills: { type: Array, default: () => [] }, // [{ value, label, count? }]
  pillActiva: { type: [String, Number, null], default: null },
  emptyText: { type: String, default: 'Sin resultados' },
  sizeOptions: { type: Array, default: () => [15, 25, 50, 100] },
})
const emit = defineEmits(['update:page', 'update:size', 'update:search', 'pill', 'row-click'])

const conCabecera = computed(
  () => Boolean(props.titulo) || props.search !== null || props.pills.length > 0
)

const keyFor = (row, idx) =>
  typeof props.rowKey === 'function' ? props.rowKey(row) : (row[props.rowKey] ?? idx)
const cell = (row, col) => (col.formatter ? col.formatter(row[col.key], row) : row[col.key])

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))
const desde = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.size + 1))
const hasta = computed(() => Math.min(props.page * props.size, props.total))

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
  <section class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
    <div
      v-if="conCabecera"
      class="border-b border-brand-200 bg-gradient-to-r from-brand-100/80 via-sage-100 to-brand-50"
    >
      <div class="flex flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center sm:px-6">
        <div v-if="titulo || subtitulo">
          <div class="flex items-center gap-2">
            <h2 class="font-display text-base font-bold text-brand-950">{{ titulo }}</h2>
            <span
              class="rounded-full border border-brand-300 bg-white px-2.5 py-0.5 text-[11px] font-bold text-brand-900 tabular-nums shadow-2xs"
            >
              {{ total.toLocaleString('es-CL') }}
            </span>
          </div>
          <p v-if="subtitulo" class="mt-0.5 text-[12px] text-slate-600">{{ subtitulo }}</p>
        </div>
        <div class="flex items-center gap-2.5">
          <div v-if="search !== null" class="relative">
            <Icon
              name="search"
              :size="16"
              class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-brand-600"
            />
            <input
              :value="search"
              type="text"
              :placeholder="searchPlaceholder"
              class="h-9 w-48 rounded-lg border border-brand-300 bg-white pl-8 pr-3 text-[12px] text-slate-800 transition-all placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20 sm:w-56"
              @input="emit('update:search', $event.target.value)"
            />
          </div>
          <slot name="acciones-cabecera" />
        </div>
      </div>
      <div v-if="pills.length" class="flex flex-wrap items-center gap-2 px-4 pb-3 sm:px-6">
        <button
          v-for="p in pills"
          :key="p.value"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold transition-all"
          :class="
            pillActiva === p.value
              ? 'bg-brand-800 text-white shadow-xs'
              : 'border border-brand-200 bg-white/90 text-slate-600 hover:border-brand-400 hover:text-brand-900'
          "
          @click="emit('pill', p.value)"
        >
          {{ p.label }}
          <span
            v-if="p.count != null"
            class="tabular-nums"
            :class="pillActiva === p.value ? 'text-white/70' : 'text-slate-400'"
            >{{ p.count }}</span
          >
        </button>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full border-collapse text-left">
        <thead>
          <tr
            class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[11px] font-bold uppercase tracking-wider text-brand-100"
          >
            <th
              v-for="col in columns"
              :key="col.key"
              scope="col"
              class="whitespace-nowrap px-6 py-3.5"
              :class="
                col.align === 'right'
                  ? 'text-right'
                  : col.align === 'center'
                    ? 'text-center'
                    : 'text-left'
              "
              :style="col.width ? { width: col.width } : null"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100/90 bg-white/80 text-[13px]">
          <tr v-if="loading">
            <td :colspan="columns.length" class="px-6 py-12 text-center text-slate-500">
              Cargando…
            </td>
          </tr>
          <tr v-else-if="!rows.length">
            <td :colspan="columns.length" class="px-6 py-12 text-center text-slate-500">
              {{ emptyText }}
            </td>
          </tr>
          <tr
            v-for="(row, idx) in rows"
            v-else
            :key="keyFor(row, idx)"
            class="transition-colors hover:bg-brand-50/70"
            @click="emit('row-click', row)"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              class="px-6 py-3.5 text-slate-800"
              :class="
                col.align === 'right'
                  ? 'text-right font-bold tabular-nums text-slate-900'
                  : col.align === 'center'
                    ? 'text-center'
                    : 'text-left'
              "
            >
              <slot :name="`cell:${col.key}`" :row="row" :value="row[col.key]">
                {{ cell(row, col) }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer
      class="flex flex-wrap items-center justify-between gap-3 border-t border-brand-200 bg-white/60 px-6 py-3 text-[12px] text-slate-600"
    >
      <div class="flex items-center gap-3">
        <span>
          Mostrando <b class="tabular-nums text-slate-900">{{ desde }}–{{ hasta }}</b> de
          <b class="tabular-nums text-slate-900">{{ total.toLocaleString('es-CL') }}</b>
        </span>
        <label class="flex items-center gap-1.5">
          Filas
          <select
            :value="size"
            class="rounded-md border border-brand-300 bg-white px-1.5 py-0.5 text-[12px] text-slate-800"
            @change="emit('update:size', Number($event.target.value))"
          >
            <option v-for="s in sizeOptions" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
      </div>
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="rounded-md px-2 py-1 font-medium text-slate-500 hover:bg-brand-50 disabled:opacity-30"
          :disabled="page <= 1"
          @click="emit('update:page', page - 1)"
        >
          ‹
        </button>
        <template v-for="(n, i) in numeros" :key="i">
          <span v-if="n === '…'" class="px-1.5 text-slate-400">…</span>
          <button
            v-else
            type="button"
            class="min-w-[26px] rounded-md px-1.5 py-1 text-center font-semibold transition"
            :class="n === page ? 'bg-brand-800 text-white' : 'text-slate-500 hover:bg-brand-50'"
            @click="emit('update:page', n)"
          >
            {{ n }}
          </button>
        </template>
        <button
          type="button"
          class="rounded-md px-2 py-1 font-medium text-slate-500 hover:bg-brand-50 disabled:opacity-30"
          :disabled="page >= pages"
          @click="emit('update:page', page + 1)"
        >
          ›
        </button>
      </div>
    </footer>
  </section>
</template>
