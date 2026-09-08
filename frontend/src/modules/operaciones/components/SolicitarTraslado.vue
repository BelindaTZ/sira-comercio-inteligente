<script setup>
/**
 * US2 / FR-003 — un Encargado de Tienda registra una solicitud de traslado desde
 * otra sucursal. La solicitud queda en estado `solicitado` hasta que la tienda
 * origen la resuelve.
 */
import { reactive, ref } from 'vue'
import { trasladosApi } from '@/services/trasladosApi'

const emit = defineEmits(['creado'])

const form = reactive({
  product_id: '',
  tienda_origen_id: '',
  tienda_destino_id: '',
  cantidad: '',
})
const ultimo = ref(null)
const error = ref('')

async function solicitar() {
  error.value = ''
  try {
    ultimo.value = await trasladosApi.solicitar({
      productId: Number(form.product_id),
      tiendaOrigenId: Number(form.tienda_origen_id),
      tiendaDestinoId: Number(form.tienda_destino_id),
      cantidad: Number(form.cantidad),
    })
    form.cantidad = ''
    emit('creado', ultimo.value)
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <section>
    <h2 class="mb-2 text-sm font-semibold text-on-surface">Solicitar traslado</h2>
    <p
      v-if="error"
      class="mb-3 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>
    <form
      class="grid gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 sm:grid-cols-2"
      @submit.prevent="solicitar"
    >
      <label class="text-xs text-on-surface-variant">
        Producto (id)
        <input
          v-model="form.product_id"
          type="number"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Cantidad
        <input
          v-model="form.cantidad"
          type="number"
          min="1"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Tienda origen (id)
        <input
          v-model="form.tienda_origen_id"
          type="number"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Tienda destino (id)
        <input
          v-model="form.tienda_destino_id"
          type="number"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="col-span-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Registrar solicitud
      </button>
      <p v-if="ultimo" class="col-span-full text-xs text-tertiary">
        Traslado #{{ ultimo.traslado_id }} — {{ ultimo.estado }}.
      </p>
    </form>
  </section>
</template>
