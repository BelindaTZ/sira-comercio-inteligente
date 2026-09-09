<script setup>
/**
 * US2 / FR-004..FR-006 — el Encargado de la tienda origen aprueba (descuenta y
 * despacha) o rechaza las solicitudes de traslado dirigidas a su tienda. Si el
 * stock ya no alcanza al momento de aprobar, el backend responde 409 con el
 * stock real disponible (FR-005).
 */
import { onMounted, ref } from 'vue'
import { trasladosApi } from '@/services/trasladosApi'
import { prompt } from '@/shared/ui/dialogs'

const pendientes = ref([])
const error = ref('')
const aviso = ref('')

async function cargar() {
  error.value = ''
  try {
    pendientes.value = await trasladosApi.listar({ estado: 'solicitado' })
  } catch (e) {
    error.value = e.message
  }
}

async function resolver(traslado, decision) {
  error.value = ''
  aviso.value = ''
  let motivo = null
  if (decision === 'rechazar') {
    motivo = await prompt({
      title: 'Rechazar el traslado',
      label: 'Motivo (opcional)',
      confirmText: 'Rechazar',
      tone: 'danger',
    })
    if (motivo === null) return
    motivo = motivo || null
  }
  try {
    const r = await trasladosApi.resolver(traslado.traslado_id, decision, motivo)
    aviso.value = `Traslado #${r.traslado_id}: ${r.estado}`
    await cargar()
  } catch (e) {
    const d = e.response?.data?.error?.details
    error.value = d
      ? `Stock insuficiente: hay ${d.stock_disponible}, se piden ${d.cantidad_solicitada}`
      : e.message
  }
}

onMounted(cargar)
</script>

<template>
  <section>
    <div class="mb-2 flex items-center justify-between">
      <h2 class="text-sm font-semibold text-on-surface">Solicitudes pendientes de resolución</h2>
      <button type="button" class="text-xs font-semibold text-primary-container" @click="cargar">
        Recargar
      </button>
    </div>
    <p
      v-if="error"
      class="mb-3 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>
    <p v-if="aviso" class="mb-3 text-xs text-tertiary">{{ aviso }}</p>

    <p v-if="!pendientes.length" class="text-sm text-on-surface-variant">
      Sin solicitudes pendientes
    </p>
    <ul class="space-y-2">
      <li
        v-for="t in pendientes"
        :key="t.traslado_id"
        class="flex items-center justify-between rounded-xl border border-outline-variant bg-surface-container-lowest p-3 text-sm"
      >
        <span class="text-on-surface">
          #{{ t.traslado_id }} · producto {{ t.product_id }} · {{ t.cantidad }} u · tienda
          {{ t.tienda_origen_id }} → {{ t.tienda_destino_id }}
        </span>
        <span class="flex gap-2">
          <button
            type="button"
            class="rounded-lg bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
            @click="resolver(t, 'aprobar')"
          >
            Aprobar y despachar
          </button>
          <button
            type="button"
            class="rounded-lg bg-error-container px-3 py-1.5 text-xs font-semibold text-on-error-container"
            @click="resolver(t, 'rechazar')"
          >
            Rechazar
          </button>
        </span>
      </li>
    </ul>
  </section>
</template>
