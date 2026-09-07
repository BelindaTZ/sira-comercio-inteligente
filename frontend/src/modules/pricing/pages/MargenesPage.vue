<script setup>
/**
 * Márgenes objetivo por categoría (FR-001) + regla de ajuste (FR-004) y el
 * listado consolidado de descuentos bajo margen mínimo (FR-011/FR-012).
 * Toda la regla vive en el backend.
 */
import { onMounted, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'
import FormularioReglaAjuste from '../components/FormularioReglaAjuste.vue'
import TablaMargenBajo from '../components/TablaMargenBajo.vue'

const margenes = ref([])
const seleccionada = ref(null)
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    margenes.value = await pricingApi.margenes()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

function onGuardado() {
  seleccionada.value = null
  cargar()
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Márgenes y pricing</h1>
      <div class="flex gap-2 text-sm">
        <RouterLink
          to="/pricing/propuestas"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-on-surface hover:bg-surface-container-low"
        >
          Propuestas de precio →
        </RouterLink>
        <RouterLink
          to="/pricing/reporte"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-on-surface hover:bg-surface-container-low"
        >
          Reporte de margen →
        </RouterLink>
        <RouterLink
          to="/pricing/competencia"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-on-surface hover:bg-surface-container-low"
        >
          Competencia →
        </RouterLink>
      </div>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div class="grid gap-6 lg:grid-cols-[1fr_22rem]">
      <section class="space-y-6">
        <div
          class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-4 py-2 font-semibold">Categoría</th>
                <th class="px-4 py-2 text-right font-semibold">Margen objetivo</th>
                <th class="px-4 py-2 text-right font-semibold">Factor sensib.</th>
                <th class="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
              </tr>
              <tr v-else-if="!margenes.length">
                <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">
                  Sin categorías con margen objetivo definido
                </td>
              </tr>
              <tr
                v-for="m in margenes"
                :key="m.product_category"
                class="cursor-pointer border-b border-outline-variant last:border-0 hover:bg-surface-container-low"
                :class="{
                  'bg-surface-container-low': seleccionada?.product_category === m.product_category,
                }"
                @click="seleccionada = m"
              >
                <td class="px-4 py-2">{{ m.product_category }}</td>
                <td class="px-4 py-2 text-right tabular-nums">{{ m.margen_objetivo_pct }}%</td>
                <td class="px-4 py-2 text-right tabular-nums">
                  {{ m.factor_sensibilidad ?? '—' }}
                </td>
                <td class="px-4 py-2 text-right text-xs text-primary-container">Editar</td>
              </tr>
            </tbody>
          </table>
        </div>

        <TablaMargenBajo />
      </section>

      <aside>
        <FormularioReglaAjuste :margen="seleccionada" @guardado="onGuardado" />
        <p v-if="!seleccionada" class="mt-3 text-sm text-on-surface-variant">
          Selecciona una categoría para editar su margen objetivo y su factor de sensibilidad.
        </p>
      </aside>
    </div>
  </main>
</template>
