<script setup>
/**
 * Campañas (feature 002).
 *  - US4: tasa de redención de los cupones automáticos por hito (FR-014).
 *  - US5: campañas de reactivación con grupo de control obligatorio y uplift
 *    real al cierre (FR-016..FR-019). Toda regla vive en el backend.
 */
import { onMounted, ref } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import FormularioCampana from './components/FormularioCampana.vue'

const ETIQUETA_HITO = {
  cumpleanos: 'Cumpleaños',
  aniversario_registro: 'Aniversario de registro',
}

const hito = ref([])
const campanas = ref([])
const detalle = ref(null)
const cargando = ref(false)
const error = ref('')

function pct(v) {
  return v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)} %`
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    hito.value = await clientesApi.tasaRedencion()
    campanas.value = (await clientesApi.listarCampanas('reactivacion')).items
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

async function abrir(id) {
  try {
    detalle.value = await clientesApi.detalleCampana(id)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

async function accion(fn, id) {
  error.value = ''
  try {
    await fn(id)
    await cargar()
    await abrir(id)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

function onCreada(c) {
  cargar()
  abrir(c.campaign_id)
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Campañas</h1>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <section class="mb-10">
      <h2 class="mb-2 text-lg font-semibold text-on-surface">Cupones por hito</h2>
      <p class="mb-3 text-sm text-on-surface-variant">
        Tasa de redención de los cupones automáticos de cumpleaños y aniversario.
      </p>
      <div
        class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
      >
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-outline-variant text-left text-on-surface-variant">
              <th class="px-4 py-2 font-semibold">Tipo de hito</th>
              <th class="px-4 py-2 text-right font-semibold">Enviados</th>
              <th class="px-4 py-2 text-right font-semibold">Redimidos</th>
              <th class="px-4 py-2 text-right font-semibold">Tasa</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!hito.length">
              <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">
                Aún no se han enviado cupones por hito
              </td>
            </tr>
            <tr
              v-for="f in hito"
              :key="f.tipo_evento"
              class="border-b border-outline-variant last:border-0"
            >
              <td class="px-4 py-2">{{ ETIQUETA_HITO[f.tipo_evento] || f.tipo_evento }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ f.enviados }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ f.redimidos }}</td>
              <td class="px-4 py-2 text-right font-semibold tabular-nums">{{ pct(f.tasa) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <div class="space-y-4">
        <h2 class="text-lg font-semibold text-on-surface">Reactivación (uplift)</h2>
        <div
          class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-4 py-2 font-semibold">ID</th>
                <th class="px-4 py-2 font-semibold">Periodo</th>
                <th class="px-4 py-2 text-right font-semibold">Uplift</th>
                <th class="px-4 py-2 font-semibold">Decisión</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!campanas.length">
                <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">
                  Sin campañas de reactivación
                </td>
              </tr>
              <tr
                v-for="c in campanas"
                :key="c.campaign_id"
                class="cursor-pointer border-b border-outline-variant last:border-0 hover:bg-surface-container-low"
                @click="abrir(c.campaign_id)"
              >
                <td class="px-4 py-2 tabular-nums">{{ c.campaign_id }}</td>
                <td class="px-4 py-2 text-on-surface-variant">
                  {{ c.start_date }} → {{ c.end_date }}
                </td>
                <td class="px-4 py-2 text-right tabular-nums">—</td>
                <td class="px-4 py-2 text-on-surface-variant">—</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="detalle"
          class="rounded-xl border border-outline-variant bg-surface-container-high p-4 text-sm"
        >
          <p class="font-semibold text-on-surface">
            Campaña #{{ detalle.campaign_id }}
            <span class="ml-2 text-xs text-on-surface-variant">
              {{ detalle.enviada ? 'enviada' : 'sin enviar' }}
            </span>
          </p>
          <p class="mt-1 text-on-surface-variant">
            {{ detalle.miembros.filter((m) => m.grupo === 'tratado').length }} tratados ·
            {{ detalle.miembros.filter((m) => m.grupo === 'control').length }} control
          </p>

          <div v-if="detalle.resultado" class="mt-3 space-y-1">
            <p>
              Retorno tratado:
              <strong>{{ pct(detalle.resultado.tasa_retorno_tratado) }}</strong>
              · control: <strong>{{ pct(detalle.resultado.tasa_retorno_control) }}</strong>
            </p>
            <p class="text-base font-semibold text-primary-container">
              Uplift: {{ pct(detalle.resultado.uplift) }}
            </p>
            <p v-if="detalle.resultado.decision" class="text-on-surface-variant">
              Decisión: {{ detalle.resultado.decision }}
            </p>
          </div>

          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-if="!detalle.enviada"
              type="button"
              class="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-on-primary"
              @click="accion(clientesApi.enviarCampana, detalle.campaign_id)"
            >
              Enviar
            </button>
            <button
              v-if="detalle.enviada && !detalle.resultado"
              type="button"
              class="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-on-primary"
              @click="accion(clientesApi.cerrarCampana, detalle.campaign_id)"
            >
              Cerrar y medir uplift
            </button>
            <template v-if="detalle.resultado && !detalle.resultado.decision">
              <button
                type="button"
                class="rounded-lg border border-outline-variant px-3 py-1.5 text-xs font-semibold text-on-surface"
                @click="
                  accion(
                    (id) => clientesApi.decidirCampana(id, 'aprobada_escalar'),
                    detalle.campaign_id
                  )
                "
              >
                Aprobar escalar
              </button>
              <button
                type="button"
                class="rounded-lg border border-outline-variant px-3 py-1.5 text-xs font-semibold text-on-surface"
                @click="
                  accion((id) => clientesApi.decidirCampana(id, 'descartada'), detalle.campaign_id)
                "
              >
                Descartar
              </button>
            </template>
          </div>
        </div>
      </div>

      <FormularioCampana @creada="onCreada" />
    </section>
  </main>
</template>
