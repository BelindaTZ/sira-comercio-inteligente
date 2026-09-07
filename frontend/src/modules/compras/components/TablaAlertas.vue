<script setup>
/** Alertas de inventario (reposición / vencimiento / exceso). Botón "Atender" (FR-021). */
defineProps({
  alertas: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['atender'])

const claseTipo = {
  reposicion: 'bg-error-container text-on-error-container',
  vencimiento: 'bg-error-container text-on-error-container',
  exceso_stock: 'bg-surface-container-high text-on-surface',
}
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-outline-variant text-left text-on-surface-variant">
          <th class="px-4 py-2 font-semibold">Tipo</th>
          <th class="px-4 py-2 font-semibold">Producto</th>
          <th class="px-4 py-2 font-semibold">Lote</th>
          <th class="px-4 py-2 font-semibold">Generada</th>
          <th class="px-4 py-2" />
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td colspan="5" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
        </tr>
        <tr v-else-if="!alertas.length">
          <td colspan="5" class="px-4 py-6 text-center text-on-surface-variant">
            Sin alertas pendientes
          </td>
        </tr>
        <tr
          v-for="a in alertas"
          :key="a.alerta_id"
          class="border-b border-outline-variant last:border-0"
        >
          <td class="px-4 py-2">
            <span class="rounded-full px-2 py-0.5 text-xs font-semibold" :class="claseTipo[a.tipo]">
              {{ a.tipo.replace('_', ' ') }}
            </span>
          </td>
          <td class="px-4 py-2">#{{ a.product_id }}</td>
          <td class="px-4 py-2 text-on-surface-variant">{{ a.lote_id ?? '—' }}</td>
          <td class="px-4 py-2 text-on-surface-variant">
            {{ new Date(a.fecha_generada).toLocaleString('es-EC') }}
          </td>
          <td class="px-4 py-2 text-right">
            <button
              type="button"
              class="text-xs font-semibold text-primary-container hover:underline"
              @click="emit('atender', a.alerta_id)"
            >
              Atender
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
