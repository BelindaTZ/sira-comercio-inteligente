<script setup>
/** Resumen mensual de cuentas por pagar para Finanzas (FR-041, Ronda 10). */
import { onMounted, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'
import { money } from '@/shared/currency'

const hoy = new Date()
const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1).toISOString().slice(0, 10)
const ultimoDia = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0).toISOString().slice(0, 10)

const desde = ref(primerDia)
const hasta = ref(ultimoDia)
const resumen = ref(null)
const error = ref('')

async function cargar() {
  error.value = ''
  try {
    resumen.value = await comprasApi.resumenCuentasPorPagar(desde.value, hasta.value)
  } catch (e) {
    error.value = e.message
  }
}
onMounted(cargar)

const inputClass = 'rounded-lg border border-brand-300 bg-white px-2 py-1 text-[12px] text-slate-800'
</script>

<template>
  <div class="rounded-xl border border-brand-200 bg-white p-4">
    <h3 class="mb-3 text-[13px] font-bold text-brand-950">Cuentas por pagar</h3>
    <div class="mb-3 flex gap-2">
      <input v-model="desde" type="date" :class="inputClass" @change="cargar" />
      <input v-model="hasta" type="date" :class="inputClass" @change="cargar" />
    </div>
    <p v-if="error" class="text-sm text-crimson-ruby">{{ error }}</p>
    <template v-if="resumen">
      <p class="font-mono text-2xl font-bold text-brand-900">{{ money(resumen.total_por_pagar) }}</p>
      <p class="text-[12px] text-slate-500">{{ resumen.facturas_abiertas }} factura(s) abiertas</p>
    </template>
  </div>
</template>
