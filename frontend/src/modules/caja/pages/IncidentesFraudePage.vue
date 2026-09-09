<script setup>
/**
 * Incidentes de fraude interno de caja (feature 006, FR-011 a FR-016). Ciclo de
 * vida: abierto → (Encargado aplica el protocolo, registra acciones) → en_revisión
 * → (Jefe de Finanzas cierra con resultado) → cerrado. Un incidente sigue su curso
 * aunque el empleado esté dado de baja (FR-016). Distinto de los incidentes de
 * seguridad de pago (007).
 *
 * Alcance = spec: la telemetría del mockup (hash, BIN, monto, riesgo %, motor
 * SIRA, mapa de calor POS, reglas heurísticas) NO está en la entidad ni en la
 * feature y no se implementa.
 */
import { computed, onMounted, ref } from 'vue'
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
// registrar y aplicar protocolo: Encargado (detecta en su tienda) + Jefe de Finanzas.
// Cerrar el caso como fraude confirmado/descartado es sólo del Jefe de Finanzas.
const puedeRegistrar = computed(() => sesion.puedeEditarTabla('Finanzas', 'incidentes_fraude'))
const puedeCerrar = computed(() => sesion.rol === 'Jefe_Finanzas')
const puedeAplicar = computed(() => sesion.puedeEditarTabla('Finanzas', 'incidentes_fraude'))

const filas = ref([])
const cargando = ref(false)
const error = ref('')
const pill = ref('')
const page = ref(1)
const size = ref(15)

const modal = ref(null) // 'nuevo' | { tipo: 'cerrar', row }
const nuevo = ref({ empleadoId: null, descripcion: '' })
const guardando = ref(false)
const empleados = ref([])

async function abrirNuevo() {
  nuevo.value = { empleadoId: null, descripcion: '' }
  modal.value = 'nuevo'
  if (!empleados.value.length) {
    try {
      empleados.value = await cajaApi.empleados()
    } catch (e) {
      error.value = e.response?.data?.error?.message || e.message
    }
  }
}

const ESTADO = {
  abierto: { tipo: 'quiebre', txt: 'Abierto' },
  en_revision: { tipo: 'fifo', txt: 'En revisión' },
  cerrado: { tipo: 'ok', txt: 'Cerrado' },
}
const RESULTADO = {
  fraude_confirmado: { tipo: 'quiebre', txt: 'Fraude confirmado' },
  descartado: { tipo: 'ok', txt: 'Descartado' },
}

const kpi = computed(() => {
  const por = (e) => filas.value.filter((i) => i.estado === e).length
  return {
    abiertos: por('abierto'),
    revision: por('en_revision'),
    cerrados: por('cerrado'),
    confirmados: filas.value.filter((i) => i.resultado === 'fraude_confirmado').length,
  }
})

const pills = computed(() => [
  { value: '', label: 'Todos', count: filas.value.length },
  { value: 'abierto', label: 'Abiertos', count: kpi.value.abiertos },
  { value: 'en_revision', label: 'En revisión', count: kpi.value.revision },
  { value: 'cerrado', label: 'Cerrados', count: kpi.value.cerrados },
])

const visibles = computed(() => filas.value.filter((i) => !pill.value || i.estado === pill.value))
const pagina = computed(() =>
  visibles.value.slice((page.value - 1) * size.value, page.value * size.value),
)

const columnas = [
  { key: 'incidente', label: 'Incidente', width: '132px' },
  { key: 'empleado', label: 'Empleado involucrado', width: '190px' },
  { key: 'origen', label: 'Origen', width: '120px' },
  { key: 'detalle', label: 'Evidencia & acciones' },
  { key: 'estado', label: 'Estado', align: 'center', width: '128px' },
  { key: 'acciones', label: '', align: 'right', width: '210px' },
]

const fmtFecha = (s) =>
  s ? new Date(s).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
const origenDe = (i) =>
  i.cierre_id ? `Cuadre #${i.cierre_id}` : i.ajuste_id ? `Ajuste #${i.ajuste_id}` : 'Directo'

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    filas.value = await cajaApi.incidentes()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

async function aplicarProtocolo(row) {
  const acciones = await prompt({
    title: `Aplicar protocolo — incidente #${row.incidente_id}`,
    message: `Empleado ${row.empleado_nombre || `#${row.empleado_id}`}. Registrá las acciones tomadas según el protocolo vigente; el incidente pasa a "en revisión".`,
    label: 'Acciones tomadas',
    required: true,
    confirmText: 'Registrar y pasar a revisión',
  })
  if (!acciones) return
  try {
    await cajaApi.aplicarProtocolo(row.incidente_id, acciones)
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

async function cerrar(resultado) {
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.cerrarIncidente(modal.value.row.incidente_id, resultado)
    modal.value = null
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    guardando.value = false
  }
}

async function registrar() {
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.abrirIncidente({
      empleadoId: Number(nuevo.value.empleadoId),
      descripcion: nuevo.value.descripcion.trim(),
    })
    modal.value = null
    nuevo.value = { empleadoId: null, descripcion: '' }
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Incidentes de Fraude"
      subtitulo="Casos de fraude interno de caja escalados desde el reporte de diferencias o registrados directamente. Cada incidente sigue su ciclo hasta cerrarse, sin acusar al empleado si la investigación no lo confirma."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.abiertos > 0 ? 'quiebre' : 'ok'">
          {{ kpi.abiertos > 0 ? `${kpi.abiertos} abiertos` : 'Sin abiertos' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <RouterLink
          to="/caja/protocolo"
          class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50/70"
        >
          <Icon name="academic" :size="16" /> Protocolo de escalamiento
        </RouterLink>
        <Btn
          v-if="puedeRegistrar"
          variant="primary"
          @click="abrirNuevo"
        >
          <Icon name="plus" :size="17" /> Registrar incidente
        </Btn>
      </template>
    </PageHeader>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Incidentes abiertos"
        :valor="kpi.abiertos.toLocaleString('es-CL')"
        variant="emerald"
        microcopy="Esperan que el Encargado aplique el protocolo"
        pie-label="En revisión"
        :pie-valor="`${kpi.revision} en investigación`"
      />
      <KpiTile
        label="En revisión"
        :valor="kpi.revision.toLocaleString('es-CL')"
        :estado="kpi.revision > 0 ? 'pendiente de cierre' : 'al día'"
        :estado-tipo="kpi.revision > 0 ? 'fifo' : 'ok'"
        microcopy="Protocolo aplicado, a la espera del cierre del Jefe de Finanzas"
      >
        <template #icono><Icon name="clock" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Cerrados"
        :valor="kpi.cerrados.toLocaleString('es-CL')"
        microcopy="Ciclo completo con resultado registrado"
      >
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Cerrados como fraude"
        :valor="kpi.confirmados.toLocaleString('es-CL')"
        :estado="kpi.confirmados > 0 ? 'confirmados' : 'ninguno'"
        :estado-tipo="kpi.confirmados > 0 ? 'quiebre' : 'ok'"
        microcopy="El resto se cerró como descartado (no fraude)"
      >
        <template #icono><Icon name="shield" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
      {{ error }}
    </p>

    <DataTable
      titulo="Registro de incidentes"
      subtitulo="Ordenados por más reciente. El ciclo abierto → en revisión → cerrado deja constancia de quién y cuándo lo cambió (FR-015)."
      :columns="columnas"
      :rows="pagina"
      row-key="incidente_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="visibles.length"
      :pills="pills"
      :pill-activa="pill"
      empty-text="Sin incidentes de fraude"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @pill="((pill = $event), (page = 1))"
    >
      <template #cell:incidente="{ row }">
        <div class="leading-tight">
          <div class="font-mono text-[12px] font-bold text-brand-800">#{{ row.incidente_id }}</div>
          <div class="text-[10px] text-slate-400">{{ fmtFecha(row.fecha_hora) }}</div>
        </div>
      </template>

      <template #cell:empleado="{ row }">
        <div class="flex items-center gap-2">
          <span
            class="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand-100 font-display text-[10px] font-bold text-brand-800"
          >
            {{ (row.empleado_nombre || '?').split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase() }}
          </span>
          <div class="min-w-0">
            <div class="truncate text-[12px] font-semibold text-slate-800">
              {{ row.empleado_nombre || 'Empleado sin nombre' }}
            </div>
            <div class="font-mono text-[10px] text-slate-400">#{{ row.empleado_id }}</div>
          </div>
        </div>
      </template>

      <template #cell:origen="{ row }">
        <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
          {{ origenDe(row) }}
        </span>
      </template>

      <template #cell:detalle="{ row }">
        <p class="text-[11px] text-slate-600">{{ row.descripcion }}</p>
        <p v-if="row.acciones_tomadas" class="mt-1 text-[11px] text-slate-500">
          <span class="font-semibold text-slate-600">Acciones:</span> {{ row.acciones_tomadas }}
        </p>
        <div v-if="row.resultado" class="mt-1">
          <SemanticChip :tipo="RESULTADO[row.resultado]?.tipo || 'neutral'">
            {{ RESULTADO[row.resultado]?.txt || row.resultado }}
          </SemanticChip>
        </div>
        <p v-if="row.fecha_actualizacion" class="mt-1 text-[10px] text-slate-400">
          Últ. cambio por #{{ row.actualizado_por }} · {{ fmtFecha(row.fecha_actualizacion) }}
        </p>
      </template>

      <template #cell:estado="{ row }">
        <SemanticChip :tipo="ESTADO[row.estado]?.tipo || 'neutral'">
          {{ ESTADO[row.estado]?.txt || row.estado }}
        </SemanticChip>
      </template>

      <template #cell:acciones="{ row }">
        <div class="flex items-center justify-end gap-1 whitespace-nowrap">
          <Btn
            v-if="row.estado === 'abierto' && puedeAplicar"
            variant="primary"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="aplicarProtocolo(row)"
          >
            <Icon name="academic" :size="14" /> Aplicar protocolo
          </Btn>
          <Btn
            v-else-if="row.estado === 'en_revision' && puedeCerrar"
            variant="ghost"
            class="!px-2.5 !py-1 !text-[12px]"
            @click="modal = { tipo: 'cerrar', row }"
          >
            <Icon name="check" :size="14" /> Cerrar incidente
          </Btn>
          <span v-else class="text-[11px] text-slate-400">—</span>
        </div>
      </template>
    </DataTable>

    <Modal v-if="modal === 'nuevo'" titulo="Registrar incidente de fraude" @cerrar="modal = null">
      <p class="mb-3 text-[13px] text-slate-600">
        Abre un incidente sobre el empleado involucrado con la evidencia que lo originó (FR-011).
        Queda en estado "abierto".
      </p>
      <form class="space-y-3" @submit.prevent="registrar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Empleado involucrado
          <select
            v-model.number="nuevo.empleadoId"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option :value="null" disabled>Selecciona un empleado…</option>
            <option v-for="e in empleados" :key="e.empleado_id" :value="e.empleado_id">
              {{ e.nombre || `Empleado ${e.empleado_id}` }}{{ e.puesto ? ` · ${e.puesto}` : '' }}
            </option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Evidencia / descripción del patrón
          <textarea
            v-model="nuevo.descripcion"
            rows="4"
            required
            placeholder="Qué se detectó y por qué se escala"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <button
          type="submit"
          :disabled="guardando || !nuevo.empleadoId || !nuevo.descripcion.trim()"
          class="w-full rounded-xl bg-brand-800 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-40"
        >
          {{ guardando ? 'Registrando…' : 'Registrar incidente' }}
        </button>
      </form>
    </Modal>

    <Modal
      v-else-if="modal && modal.tipo === 'cerrar'"
      :titulo="`Cerrar incidente #${modal.row.incidente_id}`"
      @cerrar="modal = null"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Dejá constancia del resultado de la investigación. Cerrar como "descartado" no implica una
        sanción contra el empleado (FR-015).
      </p>
      <div class="grid grid-cols-2 gap-2.5">
        <button
          type="button"
          :disabled="guardando"
          class="flex flex-col items-center gap-1.5 rounded-xl border border-rose-300 bg-white p-4 text-center hover:bg-rose-50 disabled:opacity-50"
          @click="cerrar('fraude_confirmado')"
        >
          <Icon name="shield" :size="22" class="text-crimson-ruby" />
          <span class="text-[13px] font-bold text-slate-800">Fraude confirmado</span>
        </button>
        <button
          type="button"
          :disabled="guardando"
          class="flex flex-col items-center gap-1.5 rounded-xl border border-emerald-300 bg-white p-4 text-center hover:bg-emerald-50 disabled:opacity-50"
          @click="cerrar('descartado')"
        >
          <Icon name="check" :size="22" class="text-emerald-700" />
          <span class="text-[13px] font-bold text-slate-800">Descartado</span>
        </button>
      </div>
    </Modal>
  </div>
</template>
