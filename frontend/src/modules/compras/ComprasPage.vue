<script setup>
/**
 * Compras & Reposición (US3). Reúne las alertas de inventario, la creación de
 * órdenes desde la sugerencia semanal, y el ciclo de cuentas por pagar
 * (factura + pago con doble autorización). Toda regla vive en el backend.
 */
import { onMounted, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import TablaAlertas from './components/TablaAlertas.vue'
import FormularioOrdenCompra from './components/FormularioOrdenCompra.vue'
import FormularioFacturaProveedor from './components/FormularioFacturaProveedor.vue'
import FormularioPagoProveedor from './components/FormularioPagoProveedor.vue'
import ResumenCuentasPorPagar from './components/ResumenCuentasPorPagar.vue'
import ReporteComprasAutomaticoManual from './components/ReporteComprasAutomaticoManual.vue'
import HistorialProveedorProducto from './components/HistorialProveedorProducto.vue'

const sesion = {
  tiendaId: Number(localStorage.getItem('sira_tienda_id')) || 1,
  empleadoId: Number(localStorage.getItem('sira_empleado_id')) || 1,
}

const alertas = ref([])
const cargandoAlertas = ref(false)
const aviso = ref('')
const error = ref('')

async function cargarAlertas() {
  cargandoAlertas.value = true
  try {
    const data = await inventarioApi.alertas({ tiendaId: sesion.tiendaId })
    alertas.value = data.items
  } catch (e) {
    error.value = e.message
  } finally {
    cargandoAlertas.value = false
  }
}

async function atender(alertaId) {
  try {
    await inventarioApi.atenderAlerta(alertaId, sesion.empleadoId)
    await cargarAlertas()
  } catch (e) {
    error.value = e.message
  }
}

async function correrJobs() {
  aviso.value = ''
  try {
    const r = await inventarioApi.jobReposicion(sesion.tiendaId)
    const v = await inventarioApi.jobVencimiento(sesion.tiendaId)
    aviso.value = `Job reposición: ${r.alertas_generadas.length} · vencimiento: ${v.alertas_generadas.length}`
    await cargarAlertas()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargarAlertas)
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Compras &amp; Reposición</h1>
      <button
        type="button"
        class="rounded-lg border border-outline-variant px-3 py-2 text-sm font-medium text-on-surface"
        @click="correrJobs"
      >
        Ejecutar jobs de alertas
      </button>
    </div>

    <p
      v-if="aviso"
      class="mb-3 rounded-lg bg-surface-container-high px-4 py-2 text-sm text-on-surface"
    >
      {{ aviso }}
    </p>
    <p
      v-if="error"
      class="mb-3 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <section class="mb-6">
      <h2 class="mb-2 text-sm font-semibold text-on-surface-variant">Alertas de inventario</h2>
      <TablaAlertas :alertas="alertas" :loading="cargandoAlertas" @atender="atender" />
    </section>

    <div class="grid gap-6 lg:grid-cols-2">
      <FormularioOrdenCompra
        :tienda-id="sesion.tiendaId"
        :empleado-id="sesion.empleadoId"
        @creada="cargarAlertas"
      />
      <div class="space-y-6">
        <ResumenCuentasPorPagar />
        <ReporteComprasAutomaticoManual />
        <HistorialProveedorProducto />
      </div>
      <FormularioFacturaProveedor :empleado-id="sesion.empleadoId" />
      <FormularioPagoProveedor :empleado-autoriza-id="sesion.empleadoId" />
    </div>
  </main>
</template>
