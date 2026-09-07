<script setup>
/**
 * Tabla de clientes en riesgo de fuga (US3, feature 002). Sólo presenta lo que
 * el backend ya calculó: `ciclo_compra_dias` y `dias_desde_ultima_compra` vienen
 * resueltos por cada fila — el Jefe de Marketing nunca los deriva a mano (SC-005).
 */
defineProps({
  filas: { type: Array, default: () => [] },
  cargando: { type: Boolean, default: false },
})

const ETIQUETA_SEVERIDAD = {
  en_riesgo: { texto: 'En riesgo', clase: 'bg-tertiary-container text-on-tertiary-container' },
  inactivo: { texto: 'Inactivo', clase: 'bg-error-container text-on-error-container' },
}
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-outline-variant text-left text-on-surface-variant">
          <th class="px-4 py-2 font-semibold">ID</th>
          <th class="px-4 py-2 font-semibold">Nombre</th>
          <th class="px-4 py-2 font-semibold">Cédula</th>
          <th class="px-4 py-2 font-semibold">Severidad</th>
          <th class="px-4 py-2 text-right font-semibold">Score</th>
          <th class="px-4 py-2 text-right font-semibold">Ciclo (días)</th>
          <th class="px-4 py-2 text-right font-semibold">Días sin comprar</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="cargando">
          <td colspan="7" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
        </tr>
        <tr v-else-if="!filas.length">
          <td colspan="7" class="px-4 py-6 text-center text-on-surface-variant">
            Sin clientes en riesgo
          </td>
        </tr>
        <tr
          v-for="f in filas"
          :key="f.household_id"
          class="border-b border-outline-variant last:border-0 hover:bg-surface-container-low"
        >
          <td class="px-4 py-2 tabular-nums">{{ f.household_id }}</td>
          <td class="px-4 py-2">{{ f.nombre }}</td>
          <td class="px-4 py-2 text-on-surface-variant">{{ f.documento_identidad || '—' }}</td>
          <td class="px-4 py-2">
            <span
              class="rounded-full px-2 py-0.5 text-xs font-semibold"
              :class="ETIQUETA_SEVERIDAD[f.severidad]?.clase"
            >
              {{ ETIQUETA_SEVERIDAD[f.severidad]?.texto || f.severidad }}
            </span>
          </td>
          <td class="px-4 py-2 text-right tabular-nums">{{ f.score }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ f.ciclo_compra_dias ?? '—' }}</td>
          <td class="px-4 py-2 text-right tabular-nums">{{ f.dias_desde_ultima_compra ?? '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
