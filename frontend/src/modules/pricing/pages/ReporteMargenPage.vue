<script setup>
/**
 * FR-013 — reporte mensual de margen real vs. objetivo por categoría, listo para
 * presentar a Dirección General. Reutiliza íntegramente `GET /api/pricing/
 * reportes/margen` de US1 con el rango del mes seleccionado (Principio VIII, DRY).
 */
import { computed, onMounted, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'

const hoy = new Date()
const mes = ref(`${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`)
const filas = ref([])
const cargando = ref(false)
const error = ref('')

const rango = computed(() => {
  const [y, m] = mes.value.split('-').map(Number)
  const desde = `${y}-${String(m).padStart(2, '0')}-01`
  const finMes = new Date(y, m, 0).getDate()
  const hasta = `${y}-${String(m).padStart(2, '0')}-${finMes}`
  return { desde, hasta }
})

function moneda(v) {
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(
    Number(v || 0)
  )
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await pricingApi.reporteMargen({
      fechaDesde: rango.value.desde,
      fechaHasta: rango.value.hasta,
    })
    filas.value = data.filas
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Reporte de margen</h1>
      <RouterLink
        to="/pricing"
        class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
      >
        ← Márgenes
      </RouterLink>
    </div>

    <div class="mb-4 flex items-center gap-3">
      <input
        v-model="mes"
        type="month"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
        @change="cargar"
      />
      <button
        type="button"
        class="rounded-lg bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container"
        @click="cargar"
      >
        Generar
      </button>
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
            <th class="px-4 py-2 font-semibold">Categoría</th>
            <th class="px-4 py-2 text-right font-semibold">Unidades</th>
            <th class="px-4 py-2 text-right font-semibold">Ingreso</th>
            <th class="px-4 py-2 text-right font-semibold">Margen objetivo</th>
            <th class="px-4 py-2 text-right font-semibold">Margen real</th>
            <th class="px-4 py-2 text-right font-semibold">Δ</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!filas.length">
            <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">
              Sin ventas confirmadas en el mes
            </td>
          </tr>
          <tr
            v-for="f in filas"
            :key="f.product_category"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-4 py-2">{{ f.product_category }}</td>
            <td class="px-4 py-2 text-right tabular-nums">{{ f.unidades_vendidas }}</td>
            <td class="px-4 py-2 text-right tabular-nums">{{ moneda(f.ingreso_total) }}</td>
            <td class="px-4 py-2 text-right tabular-nums">
              {{ f.margen_objetivo_pct == null ? '—' : `${f.margen_objetivo_pct}%` }}
            </td>
            <td class="px-4 py-2 text-right font-semibold tabular-nums">
              {{ f.margen_real_pct == null ? '—' : `${f.margen_real_pct}%` }}
            </td>
            <td
              class="px-4 py-2 text-right tabular-nums"
              :class="
                f.margen_objetivo_pct != null &&
                f.margen_real_pct != null &&
                Number(f.margen_real_pct) < Number(f.margen_objetivo_pct)
                  ? 'text-error'
                  : 'text-tertiary'
              "
            >
              <template v-if="f.margen_objetivo_pct != null && f.margen_real_pct != null">
                {{ (Number(f.margen_real_pct) - Number(f.margen_objetivo_pct)).toFixed(2) }}
              </template>
              <template v-else>—</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
