<script setup>
/**
 * Datáfonos & Gestión de Firmware — feature 006 US2 (FR-006 a FR-008) + feature
 * 007 US1 (FR-001 a FR-003). Estructura de
 * `docs/diseno-ui/.../sira_gesti_n_de_dat_fonos_y_firmware/`: page header, fila de
 * KPI de flota, tarjeta del estándar de seguridad vigente y data-grid del
 * inventario con estado de conformidad y acciones.
 *
 * Alcance = spec: el inventario sólo trae modelo, firmware, fecha de última
 * actualización y estado de conformidad (data-model 006). La telemetría del
 * mockup (batería, señal, latencia, rollout OTA, repositorio de firmware) NO
 * está en la feature y no se implementa.
 */
import { computed, onMounted, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const puedeEditar = computed(() => sesion.puedeEditarTabla('Finanzas', 'datafonos'))
const puedeEditarEstandar = computed(() =>
  sesion.puedeEditarTabla('Finanzas', 'configuracion_seguridad_pagos'),
)

const datafonos = ref([])
const estandar = ref(null)
const cargando = ref(false)
const error = ref('')

const busqueda = ref('')
const pill = ref('') // '' | 'activo' | 'requiere_actualizacion' | 'fuera_servicio'
const page = ref(1)
const size = ref(15)

const modal = ref(null) // 'estandar' | fila (registrar actualización)
const nuevaVersion = ref('')
const guardando = ref(false)

const ESTADO = {
  activo: { tipo: 'ok', txt: 'Conforme' },
  requiere_actualizacion: { tipo: 'fifo', txt: 'No conforme' },
  fuera_servicio: { tipo: 'quiebre', txt: 'Fuera de servicio' },
}

const kpi = computed(() => {
  const d = datafonos.value
  const por = (e) => d.filter((x) => x.estado === e).length
  return {
    total: d.length,
    activos: por('activo'),
    noConformes: por('requiere_actualizacion'),
    fueraServicio: por('fuera_servicio'),
  }
})

const conformidadPct = computed(() => {
  const evaluables = kpi.value.total - kpi.value.fueraServicio
  return evaluables ? Math.round((kpi.value.activos / evaluables) * 100) : null
})

const pills = computed(() => [
  { value: '', label: 'Todos', count: kpi.value.total },
  { value: 'activo', label: 'Conformes', count: kpi.value.activos },
  { value: 'requiere_actualizacion', label: 'No conformes', count: kpi.value.noConformes },
  { value: 'fuera_servicio', label: 'Fuera de servicio', count: kpi.value.fueraServicio },
])

const columnas = [
  { key: 'terminal', label: 'Terminal / Caja', width: '150px' },
  { key: 'modelo', label: 'Modelo de hardware' },
  { key: 'firmware', label: 'Firmware actual', align: 'center', width: '150px' },
  { key: 'actualizacion', label: 'Últ. actualización', align: 'right', width: '140px' },
  { key: 'estado', label: 'Conformidad', align: 'center', width: '150px' },
  { key: 'acciones', label: '', align: 'right', width: '190px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return datafonos.value.filter((d) => {
    if (pill.value && d.estado !== pill.value) return false
    if (!q) return true
    return (
      String(d.datafono_id).includes(q) ||
      String(d.caja_id).includes(q) ||
      (d.modelo || '').toLowerCase().includes(q) ||
      (d.version_firmware || '').toLowerCase().includes(q)
    )
  })
})
const filas = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    datafonos.value = await cajaApi.datafonos()
    estandar.value = await cajaApi.configuracionSeguridad().catch(() => null)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

function abrirActualizacion(row) {
  nuevaVersion.value = estandar.value?.version_minima_firmware || ''
  modal.value = row
}

async function registrarActualizacion() {
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.actualizarDatafono(modal.value.datafono_id, nuevaVersion.value.trim())
    modal.value = null
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    guardando.value = false
  }
}

async function definirEstandar() {
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.definirEstandarSeguridad(nuevaVersion.value.trim())
    modal.value = null
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    guardando.value = false
  }
}

async function fueraServicio(row) {
  if (!window.confirm(`¿Marcar el datáfono #${row.datafono_id} (Caja ${row.caja_id}) fuera de servicio?`))
    return
  try {
    await cajaApi.datafonoFueraServicio(row.datafono_id)
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

async function restablecer(row) {
  try {
    await cajaApi.datafonoRestablecer(row.datafono_id)
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

function abrirModalEstandar() {
  nuevaVersion.value = estandar.value?.version_minima_firmware || ''
  modal.value = 'estandar'
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Datáfonos & Gestión de Firmware"
      subtitulo="Inventario de terminales de pago por caja, conformidad automática frente al estándar de seguridad vigente y registro de su actualización o reemplazo."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.noConformes > 0 ? 'fifo' : 'ok'">
          {{ kpi.noConformes > 0 ? `${kpi.noConformes} no conformes` : 'Flota conforme' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeEditarEstandar" variant="primary" @click="abrirModalEstandar">
          <Icon name="shield" :size="16" /> Definir estándar de seguridad
        </Btn>
        <span
          v-else
          class="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600"
        >
          <Icon name="shield" :size="14" /> Solo lectura
        </span>
      </template>
    </PageHeader>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Terminales en inventario"
        :valor="kpi.total.toLocaleString('es-CL')"
        variant="emerald"
        :microcopy="`${kpi.activos} operativos · ${kpi.fueraServicio} fuera de servicio`"
        pie-label="Conformidad de firmware"
        :pie-valor="conformidadPct != null ? `${conformidadPct}% al día` : 'Sin estándar vigente'"
      />
      <KpiTile
        label="No conformes al estándar"
        :valor="kpi.noConformes.toLocaleString('es-CL')"
        :estado="kpi.noConformes > 0 ? 'coordinar actualización' : 'al día'"
        :estado-tipo="kpi.noConformes > 0 ? 'fifo' : 'ok'"
        microcopy="Firmware por debajo de la versión mínima vigente (FR-007)"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Fuera de servicio"
        :valor="kpi.fueraServicio.toLocaleString('es-CL')"
        :estado="kpi.fueraServicio > 0 ? 'no disponible para cobro' : 'todos en línea'"
        :estado-tipo="kpi.fueraServicio > 0 ? 'quiebre' : 'ok'"
        microcopy="Marcados por el Encargado de Tienda en la verificación diaria"
      >
        <template #icono><Icon name="cog" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Estándar de seguridad vigente"
        :valor="estandar ? `firmware ≥ ${estandar.version_minima_firmware}` : 'Sin definir'"
        variant="ia"
        estado="PCI"
        estado-tipo="ia"
        :microcopy="
          estandar
            ? `Vigente desde ${estandar.vigente_desde}`
            : 'Defina la versión mínima para evaluar la flota'
        "
      >
        <template #icono><Icon name="key" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
      {{ error }}
    </p>

    <DataTable
      titulo="Inventario de datáfonos"
      subtitulo="Un datáfono por caja. El estado de conformidad se recalcula solo al cambiar el estándar de seguridad."
      :columns="columnas"
      :rows="filas"
      row-key="datafono_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Terminal, caja, modelo o firmware…"
      :pills="pills"
      :pill-activa="pill"
      empty-text="No hay datáfonos en el inventario"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
      @pill="((pill = $event), (page = 1))"
    >
      <template #cell:terminal="{ row }">
        <div class="font-mono text-[11px] leading-tight">
          <div class="font-bold text-brand-800">#{{ row.datafono_id }}</div>
          <div class="text-slate-400">Caja {{ row.caja_id }}</div>
        </div>
      </template>

      <template #cell:modelo="{ row }">
        <div class="flex items-center gap-2">
          <Icon name="cube" :size="15" class="shrink-0 text-slate-400" />
          <span class="text-[12px] font-medium text-slate-800">{{ row.modelo || '—' }}</span>
        </div>
      </template>

      <template #cell:firmware="{ row }">
        <SemanticChip :tipo="ESTADO[row.estado]?.tipo || 'neutral'">
          {{ row.version_firmware || 'sin declarar' }}
        </SemanticChip>
      </template>

      <template #cell:actualizacion="{ row }">
        <span class="tabular-nums text-[12px] text-slate-600">
          {{ row.fecha_ultima_actualizacion || '—' }}
        </span>
      </template>

      <template #cell:estado="{ row }">
        <SemanticChip :tipo="ESTADO[row.estado]?.tipo || 'neutral'">
          {{ ESTADO[row.estado]?.txt || row.estado }}
        </SemanticChip>
      </template>

      <template #cell:acciones="{ row }">
        <div class="flex items-center justify-end gap-1 whitespace-nowrap">
          <Btn
            v-if="row.estado === 'requiere_actualizacion' && puedeEditar"
            variant="primary"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="abrirActualizacion(row)"
          >
            <Icon name="check" :size="14" /> Actualizar
          </Btn>
          <Btn
            v-else-if="row.estado === 'fuera_servicio' && puedeEditar"
            variant="ghost"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="restablecer(row)"
          >
            <Icon name="check" :size="14" /> Restablecer
          </Btn>
          <button
            v-if="row.estado !== 'fuera_servicio' && puedeEditar"
            type="button"
            class="rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-crimson-ruby"
            title="Marcar fuera de servicio"
            @click="fueraServicio(row)"
          >
            <Icon name="alert" :size="15" />
          </button>
          <span v-if="!puedeEditar" class="text-[11px] text-slate-400">—</span>
        </div>
      </template>
    </DataTable>

    <Modal
      v-if="modal === 'estandar'"
      titulo="Definir estándar de seguridad de pagos"
      @cerrar="modal = null"
    >
      <p class="mb-3 text-[13px] text-slate-600">
        La nueva versión mínima de firmware queda vigente de inmediato y el sistema recalcula la
        conformidad de todos los datáfonos (FR-007).
      </p>
      <form class="space-y-3" @submit.prevent="definirEstandar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Versión mínima de firmware
          <input
            v-model="nuevaVersion"
            type="text"
            required
            placeholder="4.8.0"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <button
          type="submit"
          :disabled="guardando"
          class="w-full rounded-xl bg-brand-800 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {{ guardando ? 'Guardando…' : 'Definir estándar' }}
        </button>
      </form>
    </Modal>

    <Modal
      v-else-if="modal && typeof modal === 'object'"
      :titulo="`Registrar actualización — datáfono #${modal.datafono_id}`"
      @cerrar="modal = null"
    >
      <p class="mb-3 text-[13px] text-slate-600">
        Registra la actualización o reemplazo del datáfono no conforme de la Caja
        {{ modal.caja_id }} (FR-008). Queda con la fecha de resolución de hoy.
      </p>
      <form class="space-y-3" @submit.prevent="registrarActualizacion">
        <label class="block text-[12px] font-semibold text-slate-600">
          Nueva versión de firmware instalada
          <input
            v-model="nuevaVersion"
            type="text"
            required
            placeholder="4.8.0"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <button
          type="submit"
          :disabled="guardando"
          class="w-full rounded-xl bg-brand-800 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {{ guardando ? 'Guardando…' : 'Registrar actualización' }}
        </button>
      </form>
    </Modal>
  </div>
</template>
