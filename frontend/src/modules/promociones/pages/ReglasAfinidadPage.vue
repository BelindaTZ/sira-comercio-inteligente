<script setup>
/**
 * Reglas de asociación de canasta (FR-001, FR-002) + tasa de redención de cupones
 * de afinidad (FR-008). El sistema calcula las reglas mensualmente; el Jefe de
 * Marketing desactiva las que no considera accionables.
 */
import { onMounted, ref } from 'vue'
import { promocionesApi } from '@/services/promocionesApi'

const filtroEstado = ref('vigente')
const reglas = ref([])
const tasa = ref(null)
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    reglas.value = await promocionesApi.reglasAfinidad(filtroEstado.value || undefined)
    tasa.value = await promocionesApi.tasaRedencionAfinidad()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function calcular() {
  try {
    await promocionesApi.forzarCalculoAfinidad()
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function desactivar(regla) {
  const motivo = window.prompt('Motivo de la desactivación (opcional):') || ''
  try {
    await promocionesApi.desactivarRegla(regla.regla_id, motivo)
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
      <h1 class="text-2xl font-bold text-primary-container">Reglas de afinidad</h1>
      <div class="flex gap-2">
        <RouterLink
          to="/promociones/liquidacion"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
        >
          Liquidación →
        </RouterLink>
        <RouterLink
          to="/promociones/colocacion"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
        >
          Colocación →
        </RouterLink>
        <button
          type="button"
          class="rounded-lg bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container"
          @click="calcular"
        >
          Recalcular (dev)
        </button>
      </div>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div
      v-if="tasa"
      class="mb-4 rounded-xl border border-outline-variant bg-surface-container-high p-4 text-sm"
    >
      Cupones de afinidad — enviados: <strong>{{ tasa.enviados }}</strong> · redimidos:
      <strong>{{ tasa.redimidos }}</strong> · tasa: <strong>{{ tasa.tasa_pct }}%</strong>
      <span class="text-on-surface-variant"> (separada de los cupones por hito de 002)</span>
    </div>

    <div class="mb-4">
      <select
        v-model="filtroEstado"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
        @change="cargar"
      >
        <option value="vigente">Vigentes</option>
        <option value="desactivada">Desactivadas</option>
        <option value="reemplazada">Reemplazadas</option>
        <option value="">Todas</option>
      </select>
    </div>

    <div
      class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
    >
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-4 py-2 font-semibold">Antecedente → Consecuente</th>
            <th class="px-4 py-2 text-right font-semibold">Soporte</th>
            <th class="px-4 py-2 text-right font-semibold">Confianza</th>
            <th class="px-4 py-2 text-right font-semibold">Lift</th>
            <th class="px-4 py-2 font-semibold">Estado</th>
            <th class="px-4 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!reglas.length">
            <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Sin reglas</td>
          </tr>
          <tr
            v-for="r in reglas"
            :key="r.regla_id"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-4 py-2 tabular-nums">
              #{{ r.product_id_antecedente }} → #{{ r.product_id_consecuente }}
            </td>
            <td class="px-4 py-2 text-right tabular-nums">{{ Number(r.soporte).toFixed(3) }}</td>
            <td class="px-4 py-2 text-right font-semibold tabular-nums">
              {{ Number(r.confianza).toFixed(3) }}
            </td>
            <td class="px-4 py-2 text-right tabular-nums">
              {{ r.lift == null ? '—' : Number(r.lift).toFixed(2) }}
            </td>
            <td class="px-4 py-2">
              <span
                class="rounded-full px-2 py-0.5 text-xs font-semibold"
                :class="{
                  'bg-tertiary-container text-on-tertiary-container': r.estado === 'vigente',
                  'bg-error-container text-on-error-container': r.estado === 'desactivada',
                  'bg-surface-container-high text-on-surface-variant': r.estado === 'reemplazada',
                }"
              >
                {{ r.estado }}
              </span>
            </td>
            <td class="px-4 py-2 text-right">
              <button
                v-if="r.estado === 'vigente'"
                type="button"
                class="text-xs font-semibold text-error hover:underline"
                @click="desactivar(r)"
              >
                Desactivar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
