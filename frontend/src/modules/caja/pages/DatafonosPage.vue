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
import { computed, onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { useSesion } from '@/stores/sesion'
import { prompt } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
// FR-006 (registrar/editar el inventario) es del Jefe de TI; fuera de servicio /
// restablecer (007 US1) los hace también el Encargado (permiso UPDATE).
const puedeGestionar = computed(() => sesion.esGerente || sesion.rol === 'Jefe_TI')
const puedeEditar = computed(() => sesion.puedeEditarTabla('Finanzas', 'datafonos'))
const puedeEditarEstandar = computed(() =>
  sesion.puedeEditarTabla('Finanzas', 'configuracion_seguridad_pagos'),
)

const datafonos = ref([])
const cajas = ref([])
const estandar = ref(null)
const cargando = ref(false)
const error = ref('')

const busqueda = ref('')
const pill = ref('') // '' | 'activo' | 'requiere_actualizacion' | 'fuera_servicio'
const page = ref(1)
const size = ref(15)

const modal = ref(null) // 'estandar' | 'nuevo' | 'actualizar' | 'editar'
const filaActiva = ref(null)
const nuevaVersion = ref('')
const form = reactive({ cajaId: null, modelo: '', versionFirmware: '', fechaUltimaActualizacion: '' })
const guardando = ref(false)

const cajasById = computed(() => Object.fromEntries(cajas.value.map((c) => [c.caja_id, c])))
function etiquetaCaja(cajaId) {
  const c = cajasById.value[cajaId]
  return c ? c.nombre : `Caja ${cajaId}`
}

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
    cajas.value = await cajaApi.cajas().catch(() => [])
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

function abrirNuevo() {
  Object.assign(form, {
    cajaId: cajas.value[0]?.caja_id ?? null,
    modelo: '',
    versionFirmware: estandar.value?.version_minima_firmware || '',
    fechaUltimaActualizacion: '',
  })
  modal.value = 'nuevo'
}

function abrirEditar(row) {
  filaActiva.value = row
  Object.assign(form, {
    cajaId: row.caja_id,
    modelo: row.modelo || '',
    versionFirmware: row.version_firmware || '',
    fechaUltimaActualizacion: row.fecha_ultima_actualizacion || '',
  })
  modal.value = 'editar'
}

async function crearDatafono() {
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.crearDatafono({
      cajaId: form.cajaId,
      modelo: form.modelo.trim(),
      versionFirmware: form.versionFirmware.trim(),
      fechaUltimaActualizacion: form.fechaUltimaActualizacion || null,
    })
    modal.value = null
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    guardando.value = false
  }
}

async function guardarEdicion() {
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.editarDatafono(filaActiva.value.datafono_id, {
      modelo: form.modelo.trim(),
      versionFirmware: form.versionFirmware.trim(),
      fechaUltimaActualizacion: form.fechaUltimaActualizacion || null,
    })
    modal.value = null
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    guardando.value = false
  }
}

function abrirActualizacion(row) {
  filaActiva.value = row
  nuevaVersion.value = estandar.value?.version_minima_firmware || ''
  modal.value = 'actualizar'
}

async function registrarActualizacion() {
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.actualizarDatafono(filaActiva.value.datafono_id, nuevaVersion.value.trim())
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
  const motivo = await prompt({
    title: `Marcar fuera de servicio — datáfono #${row.datafono_id}`,
    message: `${etiquetaCaja(row.caja_id)} quedará no disponible para cobro con tarjeta.`,
    label: 'Motivo',
    placeholder: 'Ej.: no lee chip, sin conexión, daño físico…',
    required: true,
    tone: 'danger',
    confirmText: 'Marcar fuera de servicio',
  })
  if (!motivo) return
  try {
    await cajaApi.datafonoFueraServicio(row.datafono_id, motivo)
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
        <Btn v-if="puedeEditarEstandar" variant="ghost" @click="abrirModalEstandar">
          <Icon name="shield" :size="16" /> Estándar de seguridad
        </Btn>
        <Btn v-if="puedeGestionar" variant="primary" :disabled="!cajas.length" @click="abrirNuevo">
          <Icon name="plus" :size="17" /> Registrar datáfono
        </Btn>
        <span
          v-if="!puedeGestionar && !puedeEditar"
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
        <div class="leading-tight">
          <div class="text-[12px] font-semibold text-slate-800">{{ etiquetaCaja(row.caja_id) }}</div>
          <div class="font-mono text-[10px] text-slate-400">
            {{ `#${row.datafono_id}${cajasById[row.caja_id] ? ` · Tienda ${cajasById[row.caja_id].tienda_id}` : ''}` }}
          </div>
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
        <div
          v-if="row.estado === 'fuera_servicio' && row.motivo_fuera_servicio"
          class="mt-1 text-[10px] leading-tight text-slate-500"
          :title="row.motivo_fuera_servicio"
        >
          {{ row.motivo_fuera_servicio }}
        </div>
      </template>

      <template #cell:acciones="{ row }">
        <div class="flex items-center justify-end gap-1 whitespace-nowrap">
          <Btn
            v-if="row.estado === 'requiere_actualizacion' && puedeGestionar"
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
            v-if="puedeGestionar"
            type="button"
            class="rounded-md p-1.5 text-slate-400 hover:bg-brand-50 hover:text-brand-800"
            title="Editar datos de inventario"
            @click="abrirEditar(row)"
          >
            <Icon name="pencil" :size="15" />
          </button>
          <button
            v-if="row.estado !== 'fuera_servicio' && puedeEditar"
            type="button"
            class="rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-crimson-ruby"
            title="Marcar fuera de servicio"
            @click="fueraServicio(row)"
          >
            <Icon name="alert" :size="15" />
          </button>
          <span v-if="!puedeGestionar && !puedeEditar" class="text-[11px] text-slate-400">—</span>
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
      v-else-if="modal === 'nuevo' || modal === 'editar'"
      :titulo="
        modal === 'nuevo'
          ? 'Registrar datáfono'
          : `Editar datáfono #${filaActiva?.datafono_id}`
      "
      @cerrar="modal = null"
    >
      <p class="mb-3 text-[13px] text-slate-600">
        Datos de inventario del terminal (FR-006). El estado de conformidad lo calcula el sistema
        contra el estándar de seguridad vigente.
      </p>
      <form class="space-y-3" @submit.prevent="modal === 'nuevo' ? crearDatafono() : guardarEdicion()">
        <label class="block text-[12px] font-semibold text-slate-600">
          Caja asignada
          <select
            v-model.number="form.cajaId"
            :disabled="modal === 'editar'"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:bg-slate-50 disabled:text-slate-500"
          >
            <option v-for="c in cajas" :key="c.caja_id" :value="c.caja_id">
              {{ c.nombre }} — Tienda {{ c.tienda_id }}
            </option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Modelo de hardware
          <input
            v-model="form.modelo"
            type="text"
            maxlength="60"
            placeholder="Ingenico Move 5000"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-[12px] font-semibold text-slate-600">
            Versión de firmware
            <input
              v-model="form.versionFirmware"
              type="text"
              maxlength="30"
              placeholder="4.8.0"
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Última actualización
            <input
              v-model="form.fechaUltimaActualizacion"
              type="date"
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            />
          </label>
        </div>
        <button
          type="submit"
          :disabled="guardando"
          class="w-full rounded-xl bg-brand-800 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {{ guardando ? 'Guardando…' : modal === 'nuevo' ? 'Registrar datáfono' : 'Guardar cambios' }}
        </button>
      </form>
    </Modal>

    <Modal
      v-else-if="modal === 'actualizar'"
      :titulo="`Registrar actualización — datáfono #${filaActiva?.datafono_id}`"
      @cerrar="modal = null"
    >
      <p class="mb-3 text-[13px] text-slate-600">
        Registra la actualización o reemplazo del datáfono no conforme de
        {{ etiquetaCaja(filaActiva?.caja_id) }} (FR-008). Queda con la fecha de resolución de hoy.
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
