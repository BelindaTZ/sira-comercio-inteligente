<script setup>
/** % de órdenes por sugerencia vs. pedido especial del mes (FR-039, Ronda 10). */
import { onMounted, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'

const mes = ref(new Date().toISOString().slice(0, 7))
const reporte = ref(null)
const error = ref('')

async function cargar() {
  error.value = ''
  try {
    reporte.value = await comprasApi.reporteAutomaticoManual(mes.value)
  } catch (e) {
    error.value = e.message
  }
}
onMounted(cargar)
</script>

<template>
  <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
    <div class="mb-3 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-on-surface">Compras automáticas vs. manuales</h3>
      <input
        v-model="mes"
        type="month"
        class="rounded-lg border border-outline-variant bg-surface px-2 py-1 text-sm"
        @change="cargar"
      />
    </div>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
    <template v-if="reporte">
      <p class="text-3xl font-bold text-tertiary-container">{{ reporte.pct_programadas }}%</p>
      <p class="text-sm text-on-surface-variant">
        {{ reporte.programadas }} programadas / {{ reporte.especiales }} especiales ({{
          reporte.total
        }}
        en total)
      </p>
    </template>
  </div>
</template>
