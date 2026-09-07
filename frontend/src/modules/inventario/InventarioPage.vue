<script setup>
/**
 * Inventario & FIFO (US2). Lista los lotes priorizando los próximos a vencer
 * (FR-015), permite ajustes por conteo físico (FR-017) y registro de mermas
 * (FR-018). Toda regla vive en el backend.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import TablaLotes from './components/TablaLotes.vue'
import FormularioAjuste from './components/FormularioAjuste.vue'
import FormularioMerma from './components/FormularioMerma.vue'
import FormularioStockMaximo from './components/FormularioStockMaximo.vue'
import FormularioVerificacionAnaquel from './components/FormularioVerificacionAnaquel.vue'

const sesion = {
  tiendaId: Number(localStorage.getItem('sira_tienda_id')) || 1,
  empleadoId: Number(localStorage.getItem('sira_empleado_id')) || 1,
}

const filtros = reactive({ productId: null, proximosAVencer: false, dias: 7 })
const lotes = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await inventarioApi.lotes({
      tiendaId: sesion.tiendaId,
      productId: filtros.productId || undefined,
      proximosAVencer: filtros.proximosAVencer,
      dias: filtros.dias,
    })
    lotes.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

// Filtros reactivos (Principio XII): recargan solos al cambiar.
watch(filtros, cargar, { deep: true })
onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Inventario &amp; FIFO</h1>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div class="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <section class="space-y-4">
        <div
          class="flex flex-wrap items-center gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-3"
        >
          <input
            v-model.number="filtros.productId"
            type="number"
            placeholder="Filtrar por producto"
            class="rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
          />
          <label class="flex items-center gap-2 text-sm text-on-surface-variant">
            <input v-model="filtros.proximosAVencer" type="checkbox" />
            Sólo próximos a vencer
          </label>
          <input
            v-if="filtros.proximosAVencer"
            v-model.number="filtros.dias"
            type="number"
            min="1"
            class="w-20 rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
          />
          <span class="ml-auto text-sm text-on-surface-variant">{{ total }} lote(s)</span>
        </div>
        <TablaLotes :lotes="lotes" :loading="cargando" />
      </section>

      <aside class="space-y-4">
        <FormularioAjuste
          :tienda-id="sesion.tiendaId"
          :empleado-id="sesion.empleadoId"
          @ajustado="cargar"
        />
        <FormularioMerma
          :tienda-id="sesion.tiendaId"
          :empleado-id="sesion.empleadoId"
          @registrada="cargar"
        />
        <FormularioStockMaximo :tienda-id="sesion.tiendaId" :empleado-id="sesion.empleadoId" />
        <FormularioVerificacionAnaquel
          :tienda-id="sesion.tiendaId"
          :empleado-id="sesion.empleadoId"
        />
      </aside>
    </div>
  </main>
</template>
