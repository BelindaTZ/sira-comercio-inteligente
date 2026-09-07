<script setup>
/** Resumen mensual de cuentas por pagar para Finanzas (FR-041, Ronda 10). */
import { onMounted, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'

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

const moneda = (v) =>
  new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(Number(v || 0))
</script>

<template>
  <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
    <h3 class="mb-3 text-sm font-semibold text-on-surface">Cuentas por pagar</h3>
    <div class="mb-3 flex gap-2">
      <input
        v-model="desde"
        type="date"
        class="rounded-lg border border-outline-variant bg-surface px-2 py-1 text-sm"
        @change="cargar"
      />
      <input
        v-model="hasta"
        type="date"
        class="rounded-lg border border-outline-variant bg-surface px-2 py-1 text-sm"
        @change="cargar"
      />
    </div>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
    <template v-if="resumen">
      <p class="text-3xl font-bold text-primary-container">
        {{ moneda(resumen.total_por_pagar) }}
      </p>
      <p class="text-sm text-on-surface-variant">
        {{ resumen.facturas_abiertas }} factura(s) abiertas
      </p>
    </template>
  </div>
</template>
