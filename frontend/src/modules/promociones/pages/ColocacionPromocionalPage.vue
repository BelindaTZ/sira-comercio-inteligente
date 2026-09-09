<script setup>
/**
 * Registro de colocación en anaquel destacado / mailer promocional (FR-015) y
 * consulta de su efecto en ventas frente a un periodo de referencia (FR-016), sin
 * atribución causal automática — la lectura la hace el usuario.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { promocionesApi } from '@/services/promocionesApi'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
const puedeRegistrar = computed(() => sesion.puedeEditarTabla('Marketing_CRM', 'promociones'))

const hoy = new Date()
const form = reactive({
  productId: '',
  tiendaId: Number(localStorage.getItem('sira_tienda_id')) || 1,
  displayLocation: '',
  mailerLocation: '',
  semana: 1,
  anio: hoy.getFullYear(),
})
const colocaciones = ref([])
const efectoPorId = reactive({})
const error = ref('')

async function cargar() {
  error.value = ''
  try {
    colocaciones.value = await promocionesApi.colocaciones({ tiendaId: form.tiendaId })
  } catch (e) {
    error.value = e.message
  }
}

async function registrar() {
  error.value = ''
  try {
    await promocionesApi.registrarColocacion({
      productId: Number(form.productId),
      tiendaId: form.tiendaId,
      displayLocation: form.displayLocation || null,
      mailerLocation: form.mailerLocation || null,
      semana: form.semana,
      anio: form.anio,
    })
    form.productId = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function verEfecto(c) {
  try {
    efectoPorId[c.promocion_id] = await promocionesApi.efectoColocacion(c.promocion_id)
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Colocación promocional</h1>
      <RouterLink
        to="/promociones"
        class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
      >
        ← Reglas de afinidad
      </RouterLink>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <form
      v-if="puedeRegistrar"
      class="mb-6 grid gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 sm:grid-cols-3"
      @submit.prevent="registrar"
    >
      <input
        v-model="form.productId"
        type="number"
        placeholder="ID producto"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <input
        v-model.number="form.tiendaId"
        type="number"
        placeholder="ID tienda"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <input
        v-model="form.displayLocation"
        placeholder="Ubicación anaquel (código)"
        maxlength="2"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <input
        v-model="form.mailerLocation"
        placeholder="Ubicación mailer (código)"
        maxlength="2"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <input
        v-model.number="form.semana"
        type="number"
        min="1"
        max="53"
        placeholder="Semana"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <input
        v-model.number="form.anio"
        type="number"
        placeholder="Año"
        class="rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container sm:col-span-3"
      >
        Registrar colocación
      </button>
    </form>

    <div
      class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
    >
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-4 py-2 font-semibold">Producto</th>
            <th class="px-4 py-2 font-semibold">Anaquel / Mailer</th>
            <th class="px-4 py-2 font-semibold">Semana</th>
            <th class="px-4 py-2 font-semibold">Efecto (colocación vs. referencia)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!colocaciones.length">
            <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">
              Sin colocaciones registradas
            </td>
          </tr>
          <tr
            v-for="c in colocaciones"
            :key="c.promocion_id"
            class="border-b border-outline-variant last:border-0"
          >
            <td class="px-4 py-2 tabular-nums">#{{ c.product_id }}</td>
            <td class="px-4 py-2 text-on-surface-variant">
              {{ c.display_location || '—' }} / {{ c.mailer_location || '—' }}
            </td>
            <td class="px-4 py-2 tabular-nums">{{ c.anio }}-S{{ c.semana }}</td>
            <td class="px-4 py-2">
              <template v-if="efectoPorId[c.promocion_id]">
                <strong>{{ efectoPorId[c.promocion_id].ventas_semana_colocacion }}</strong>
                vs. {{ efectoPorId[c.promocion_id].ventas_semana_referencia }} uds
              </template>
              <button
                v-else
                type="button"
                class="text-xs font-semibold text-primary-container hover:underline"
                @click="verEfecto(c)"
              >
                Ver efecto
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
