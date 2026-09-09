<script setup>
/**
 * Propuestas de ajuste de precio (FR-005, FR-006). El sistema las genera
 * semanalmente; ninguna se publica sin que Jefe_Comercial la apruebe aquí
 * (SC-002). Aprobar cambia `precio_base` y escribe el historial de vigencias.
 */
import { onMounted, reactive, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'
import { prompt } from '@/shared/ui/dialogs'

const filtros = reactive({ estado: 'pendiente' })
const items = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')

function moneda(v) {
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(
    Number(v || 0)
  )
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await pricingApi.propuestas({ estado: filtros.estado || undefined })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function aprobar(p) {
  try {
    await pricingApi.aprobarPropuesta(p.propuesta_id)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function rechazar(p) {
  const motivo = await prompt({
    title: 'Rechazar la propuesta de precio',
    label: 'Motivo (opcional)',
    confirmText: 'Rechazar',
    tone: 'danger',
  })
  if (motivo === null) return
  try {
    await pricingApi.rechazarPropuesta(p.propuesta_id, motivo)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Propuestas de precio</h1>
      <RouterLink
        to="/pricing"
        class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
      >
        ← Márgenes
      </RouterLink>
    </div>

    <div class="mb-4 flex items-center gap-3">
      <select
        v-model="filtros.estado"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
        @change="cargar"
      >
        <option value="pendiente">Pendientes</option>
        <option value="aprobada">Aprobadas</option>
        <option value="rechazada">Rechazadas</option>
        <option value="">Todas</option>
      </select>
      <span class="text-sm text-on-surface-variant">{{ total }}</span>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div
      class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
    >
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-4 py-2 font-semibold">Producto</th>
            <th class="px-4 py-2 text-right font-semibold">Precio actual</th>
            <th class="px-4 py-2 text-right font-semibold">Precio propuesto</th>
            <th class="px-4 py-2 text-right font-semibold">Margen esperado</th>
            <th class="px-4 py-2 font-semibold">Estado</th>
            <th class="px-4 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">
              Sin propuestas
            </td>
          </tr>
          <tr
            v-for="p in items"
            :key="p.propuesta_id"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-4 py-2 tabular-nums">#{{ p.product_id }}</td>
            <td class="px-4 py-2 text-right tabular-nums">{{ moneda(p.precio_actual) }}</td>
            <td class="px-4 py-2 text-right font-semibold tabular-nums">
              {{ moneda(p.precio_propuesto) }}
            </td>
            <td class="px-4 py-2 text-right tabular-nums">{{ p.margen_esperado_pct }}%</td>
            <td class="px-4 py-2">
              <span
                class="rounded-full px-2 py-0.5 text-xs font-semibold"
                :class="{
                  'bg-secondary-container text-on-secondary-container': p.estado === 'pendiente',
                  'bg-tertiary-container text-on-tertiary-container': p.estado === 'aprobada',
                  'bg-error-container text-on-error-container': p.estado === 'rechazada',
                }"
              >
                {{ p.estado }}
              </span>
            </td>
            <td class="px-4 py-2 text-right">
              <div v-if="p.estado === 'pendiente'" class="flex justify-end gap-2">
                <button
                  type="button"
                  class="rounded-lg bg-primary-container px-2 py-1 text-xs font-semibold text-on-primary-container"
                  @click="aprobar(p)"
                >
                  Aprobar
                </button>
                <button
                  type="button"
                  class="rounded-lg border border-outline-variant px-2 py-1 text-xs font-semibold text-error"
                  @click="rechazar(p)"
                >
                  Rechazar
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
