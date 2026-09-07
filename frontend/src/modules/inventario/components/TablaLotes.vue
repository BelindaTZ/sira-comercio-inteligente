<script setup>
/**
 * Lista de lotes priorizando visualmente los próximos a vencer (FR-015).
 * El backend ya devuelve el orden FEFO; aquí sólo se resalta el estado.
 */
defineProps({
  lotes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

function claseVencimiento(dias) {
  if (dias == null) return 'text-on-surface-variant'
  if (dias < 0) return 'font-bold text-on-error-container'
  if (dias <= 7) return 'font-semibold text-error'
  if (dias <= 30) return 'font-medium text-on-surface'
  return 'text-on-surface-variant'
}

function etiquetaVencimiento(lote) {
  if (lote.fecha_vencimiento == null) return 'Sin vencimiento'
  const d = lote.dias_para_vencer
  if (d < 0) return `Vencido (${lote.fecha_vencimiento})`
  return `${lote.fecha_vencimiento} · ${d} d`
}
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-outline-variant text-left text-on-surface-variant">
          <th class="px-4 py-2 font-semibold">Lote</th>
          <th class="px-4 py-2 font-semibold">Producto</th>
          <th class="px-4 py-2 text-right font-semibold">Disponible</th>
          <th class="px-4 py-2 text-right font-semibold">Recibido</th>
          <th class="px-4 py-2 font-semibold">Vencimiento</th>
          <th class="px-4 py-2 font-semibold">Cód. proveedor</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
        </tr>
        <tr v-else-if="!lotes.length">
          <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Sin lotes</td>
        </tr>
        <tr
          v-for="lote in lotes"
          :key="lote.lote_id"
          class="border-b border-outline-variant last:border-0"
          :class="
            lote.dias_para_vencer != null && lote.dias_para_vencer <= 7
              ? 'bg-error-container/30'
              : ''
          "
        >
          <td class="px-4 py-2 tabular-nums">#{{ lote.lote_id }}</td>
          <td class="px-4 py-2">#{{ lote.product_id }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ lote.cantidad_disponible }}</td>
          <td class="px-4 py-2 text-right tabular-nums text-on-surface-variant">
            {{ lote.cantidad_recibida }}
          </td>
          <td class="px-4 py-2" :class="claseVencimiento(lote.dias_para_vencer)">
            {{ etiquetaVencimiento(lote) }}
          </td>
          <td class="px-4 py-2 text-on-surface-variant">{{ lote.codigo_lote_proveedor || '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
