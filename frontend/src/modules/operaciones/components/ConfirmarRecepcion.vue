<script setup>
/**
 * US3 / FR-007..FR-010, FR-012 — el Encargado de la tienda destino confirma la
 * recepción de un traslado despachado (`en_transito`); el Jefe de Operaciones ve
 * el listado semanal con los que quedaron pendientes de confirmar.
 */
import { onMounted, reactive, ref } from 'vue'
import { trasladosApi } from '@/services/trasladosApi'

const hoy = new Date().toISOString().slice(0, 10)
const semanaAtras = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10)

const periodo = reactive({ desde: semanaAtras, hasta: hoy })
const reporte = ref([])
const err = ref('')
const aviso = ref('')

async function cargarReporte() {
  err.value = ''
  try {
    reporte.value = await trasladosApi.reporteSemanal({
      desde: periodo.desde,
      hasta: periodo.hasta,
    })
  } catch (e) {
    err.value = e.message
  }
}

async function confirmar(traslado) {
  err.value = ''
  aviso.value = ''
  try {
    const r = await trasladosApi.confirmarRecepcion(traslado.traslado_id)
    aviso.value = `Traslado #${r.traslado_id}: ${r.estado}`
    await cargarReporte()
  } catch (e) {
    err.value = e.message
  }
}

async function cancelar(traslado) {
  err.value = ''
  try {
    await trasladosApi.cancelar(traslado.traslado_id)
    await cargarReporte()
  } catch (e) {
    err.value = e.message
  }
}

onMounted(cargarReporte)
</script>

<template>
  <section>
    <h2 class="mb-2 text-sm font-semibold text-on-surface">Recepción y listado semanal</h2>
    <p
      v-if="err"
      class="mb-3 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ err }}
    </p>
    <p v-if="aviso" class="mb-3 text-xs text-tertiary">{{ aviso }}</p>

    <form class="mb-3 flex items-end gap-3" @submit.prevent="cargarReporte">
      <label class="text-xs text-on-surface-variant">
        Desde
        <input
          v-model="periodo.desde"
          type="date"
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Hasta
        <input
          v-model="periodo.hasta"
          type="date"
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Ver periodo
      </button>
    </form>

    <p v-if="!reporte.length" class="text-sm text-on-surface-variant">
      Sin traslados en el periodo
    </p>
    <ul class="space-y-2">
      <li
        v-for="t in reporte"
        :key="t.traslado_id"
        class="flex items-center justify-between rounded-xl border border-outline-variant bg-surface-container-lowest p-3 text-sm"
      >
        <span class="text-on-surface">
          #{{ t.traslado_id }} · producto {{ t.product_id }} · {{ t.cantidad }} u ·
          {{ t.tienda_origen_id }} → {{ t.tienda_destino_id }}
          <span
            v-if="t.pendiente_confirmacion"
            class="ml-2 rounded-md bg-secondary-container px-2 py-0.5 text-xs font-semibold text-on-secondary-container"
          >
            pendiente de confirmar
          </span>
          <span v-else class="ml-2 text-xs text-on-surface-variant">{{ t.estado }}</span>
        </span>
        <span class="flex gap-2">
          <button
            v-if="t.estado === 'en_transito'"
            type="button"
            class="rounded-lg bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
            @click="confirmar(t)"
          >
            Confirmar recepción
          </button>
          <button
            v-if="t.estado === 'solicitado'"
            type="button"
            class="rounded-lg bg-error-container px-3 py-1.5 text-xs font-semibold text-on-error-container"
            @click="cancelar(t)"
          >
            Cancelar
          </button>
        </span>
      </li>
    </ul>
  </section>
</template>
