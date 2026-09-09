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
  <div class="rounded-xl border border-brand-200 bg-white p-4">
    <div class="mb-3 flex items-center justify-between gap-2">
      <h3 class="text-[13px] font-bold text-brand-950">Compras automáticas vs. manuales</h3>
      <input
        v-model="mes"
        type="month"
        class="rounded-lg border border-brand-300 bg-white px-2 py-1 text-[12px] text-slate-800"
        @change="cargar"
      />
    </div>
    <p v-if="error" class="text-sm text-crimson-ruby">{{ error }}</p>
    <template v-if="reporte">
      <p class="font-mono text-2xl font-bold text-brand-900">{{ reporte.pct_programadas }}%</p>
      <p class="text-[12px] text-slate-500">
        {{ reporte.programadas }} programadas / {{ reporte.especiales }} especiales
        ({{ reporte.total }} en total)
      </p>
    </template>
  </div>
</template>
