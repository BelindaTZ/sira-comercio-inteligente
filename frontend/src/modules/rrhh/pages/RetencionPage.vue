<script setup>
/**
 * Acciones de retención (feature 011, US1 / FR-002). El Jefe de RRHH registra una
 * acción (fecha, descripción) para un empleado y ve su historial. Sólo los
 * empleados en puestos críticos alimentan el KPI de OT-8.1. Arquetipo "Gestión".
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'

const sesion = useSesion()
const puedeEditar = computed(() => !sesion.esGerente && sesion.rol === 'Jefe_RRHH')

const empleados = ref([])
const seleccionado = ref('')
const acciones = ref([])
const error = ref('')
const aviso = ref('')
const cargando = ref(false)
const nueva = reactive({ fecha: new Date().toISOString().slice(0, 10), descripcion: '' })

const activos = computed(() => empleados.value.filter((e) => e.activo))
const empActual = computed(() => empleados.value.find((e) => e.empleado_id === Number(seleccionado.value)))
const kpi = computed(() => ({
  enCriticos: activos.value.filter((e) => e.puesto_critico).length,
  conAccion: seleccionado.value ? acciones.value.length : null,
}))

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    empleados.value = await rrhhApi.listarEmpleados({ activo: true })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function verAcciones() {
  if (!seleccionado.value) {
    acciones.value = []
    return
  }
  try {
    acciones.value = await rrhhApi.accionesRetencion(Number(seleccionado.value))
  } catch (e) {
    error.value = e.message
    acciones.value = []
  }
}

async function registrar() {
  if (!seleccionado.value || !nueva.descripcion.trim()) return
  error.value = ''
  try {
    await rrhhApi.registrarAccionRetencion({
      empleadoId: Number(seleccionado.value),
      fecha: nueva.fecha,
      descripcion: nueva.descripcion.trim(),
    })
    nueva.descripcion = ''
    aviso.value = 'Acción de retención registrada.'
    await verAcciones()
  } catch (e) {
    error.value = e.message
  }
}

watch(seleccionado, verAcciones)
onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1100px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Acciones de retención"
      subtitulo="Seguimiento por empleado de las acciones de retención (conversaciones, ajustes, planes). Las de empleados en puestos críticos alimentan el KPI de OT-8.1 (FR-002)."
    >
      <template #badge>
        <SemanticChip tipo="fifo">{{ kpi.enCriticos }} personas en puestos críticos</SemanticChip>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-4 flex items-center justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      <span>{{ aviso }}</span>
      <button class="text-brand-600 hover:text-brand-900" @click="aviso = ''"><Icon name="x" :size="14" /></button>
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-3">
      <KpiTile
        label="Empleado seleccionado"
        :valor="empActual ? empActual.nombre : '—'"
        variant="emerald"
        :microcopy="empActual ? `${empActual.puesto_nombre || ''}${empActual.puesto_critico ? ' · crítico' : ''}` : 'Elegí un empleado'"
      />
      <KpiTile
        label="Acciones registradas"
        :valor="kpi.conAccion == null ? '—' : kpi.conAccion.toLocaleString('es-EC')"
        estado-tipo="neutral"
      >
        <template #icono><Icon name="pencil" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Personas en puestos críticos" :valor="kpi.enCriticos.toLocaleString('es-EC')" estado-tipo="fifo">
        <template #icono><Icon name="shield" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="satin-card rounded-2xl p-5 shadow-card-subtle">
      <label class="block text-[12px] font-semibold text-slate-600">
        Empleado
        <select
          v-model="seleccionado"
          class="mt-1 block w-full max-w-md rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
        >
          <option value="">Elegí un empleado…</option>
          <option v-for="e in activos" :key="e.empleado_id" :value="e.empleado_id">
            {{ e.nombre }} — {{ e.puesto_nombre }}{{ e.puesto_critico ? ' (crítico)' : '' }}
          </option>
        </select>
      </label>

      <template v-if="seleccionado">
        <form
          v-if="puedeEditar"
          class="mt-4 flex flex-wrap items-end gap-3 border-t border-brand-100 pt-4"
          @submit.prevent="registrar"
        >
          <label class="text-[12px] font-semibold text-slate-600">
            Fecha
            <input v-model="nueva.fecha" type="date" required class="mt-1 block rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="min-w-[240px] flex-1 text-[12px] font-semibold text-slate-600">
            Descripción de la acción
            <input v-model="nueva.descripcion" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <Btn variant="primary" type="submit"><Icon name="plus" :size="15" /> Registrar</Btn>
        </form>

        <ul class="mt-4 space-y-2">
          <li
            v-for="a in acciones"
            :key="a.accion_id"
            class="flex gap-3 rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-[13px]"
          >
            <span class="shrink-0 font-mono text-[11px] font-semibold text-slate-400">{{ a.fecha }}</span>
            <span class="text-slate-700">{{ a.descripcion }}</span>
          </li>
          <li v-if="!acciones.length" class="text-[12px] text-slate-400">
            Este empleado todavía no tiene acciones de retención registradas.
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
