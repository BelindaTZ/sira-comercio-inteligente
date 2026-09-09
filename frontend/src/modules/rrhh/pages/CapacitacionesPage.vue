<script setup>
/**
 * Gestión de Capacitaciones & Cumplimiento — feature 011 US2 (FR-003 a FR-005).
 * Estructura de `docs/diseno-ui/.../Recuersos humano_Capacitacion/`: page header
 * con alcance de tienda, fila de KPI de cumplimiento, tarjetas de módulos
 * formativos con su avance y matriz de estado por colaborador.
 *
 * Alcance = spec + backend: el Jefe de RRHH programa por rol (fan-out) y registra
 * finalizaciones; el Encargado de Tienda consulta el cumplimiento de su personal
 * (solo lectura, FR-005). Las micro-sesiones en sala, el ranking regional y la
 * exportación del mockup no están en la feature y no se implementan.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const puedeProgramar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('RRHH', 'capacitaciones'),
)
const puedeRegistrar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('RRHH', 'empleado_capacitacion'),
)
const esEncargado = computed(() => sesion.rol === 'Encargado_Tienda')

const tiendas = ref([])
const tiendaId = ref(sesion.tiendaId ?? null)
const catalogo = ref([])
const matriz = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo completar la operación.'
}

const tiendaNombre = computed(
  () => tiendas.value.find((t) => t.tienda_id === tiendaId.value)?.nombre || sesion.tiendaNombre || '—',
)

async function cargar() {
  if (tiendaId.value == null) return
  cargando.value = true
  error.value = ''
  try {
    const [cat, mat] = await Promise.all([
      rrhhApi.capacitaciones(tiendaId.value),
      rrhhApi.cumplimientoCapacitacionTienda(tiendaId.value),
    ])
    catalogo.value = cat
    matriz.value = mat
  } catch (e) {
    error.value = msg(e)
    catalogo.value = []
    matriz.value = []
  } finally {
    cargando.value = false
  }
}

onMounted(async () => {
  try {
    if (!esEncargado.value) {
      tiendas.value = await rrhhApi.tiendas()
      if (tiendaId.value == null && tiendas.value.length) tiendaId.value = tiendas.value[0].tienda_id
    }
  } catch {
    /* el Encargado no necesita el selector */
  }
  await cargar()
})
watch(tiendaId, cargar)

// ---- agregación por colaborador ------------------------------------------
const HOY = new Date()
function esReciente(fecha) {
  if (!fecha) return false
  return (HOY - new Date(fecha)) / 86400000 <= 30
}

const colaboradores = computed(() => {
  const porEmpleado = new Map()
  for (const fila of matriz.value) {
    if (!porEmpleado.has(fila.empleado_id)) {
      porEmpleado.set(fila.empleado_id, {
        empleado_id: fila.empleado_id,
        nombre: fila.nombre,
        puesto: fila.puesto,
        fecha_contratacion: fila.fecha_contratacion,
        modulos: [],
      })
    }
    porEmpleado.get(fila.empleado_id).modulos.push({
      capacitacion_id: fila.capacitacion_id,
      nombre: fila.nombre_capacitacion,
      completado: Boolean(fila.fecha_completado),
      fecha_completado: fila.fecha_completado,
    })
  }
  return [...porEmpleado.values()].map((c) => {
    const total = c.modulos.length
    const hechos = c.modulos.filter((m) => m.completado).length
    const pendientes = c.modulos.filter((m) => !m.completado)
    let estado
    if (total === 0) estado = { txt: 'Sin asignaciones', tipo: 'neutral' }
    else if (hechos === total) estado = { txt: 'Al día', tipo: 'ok' }
    else if (hechos === 0 && esReciente(c.fecha_contratacion))
      estado = { txt: 'Onboarding', tipo: 'ia' }
    else if (hechos === 0) estado = { txt: 'Pendiente', tipo: 'quiebre' }
    else estado = { txt: 'En progreso', tipo: 'fifo' }
    return { ...c, total, hechos, pendientes, estado, pct: total ? Math.round((hechos / total) * 100) : 0 }
  })
})

const kpi = computed(() => {
  const cs = colaboradores.value
  const asignaciones = matriz.value.length
  const completadas = matriz.value.filter((f) => f.fecha_completado).length
  const alDia = cs.filter((c) => c.total > 0 && c.hechos === c.total).length
  return {
    empleados: cs.length,
    alDia,
    pendientes: asignaciones - completadas,
    cumplimientoPct: asignaciones ? Math.round((completadas / asignaciones) * 100) : null,
    modulos: catalogo.value.length,
  }
})

// ---- matriz (DataTable) --------------------------------------------------
const busqueda = ref('')
const pill = ref('')
const page = ref(1)
const size = ref(15)

const pills = computed(() => [
  { value: '', label: 'Todos', count: colaboradores.value.length },
  {
    value: 'ok',
    label: 'Al día',
    count: colaboradores.value.filter((c) => c.estado.tipo === 'ok').length,
  },
  {
    value: 'fifo',
    label: 'En progreso',
    count: colaboradores.value.filter((c) => c.estado.tipo === 'fifo').length,
  },
  {
    value: 'pend',
    label: 'Pendientes / onboarding',
    count: colaboradores.value.filter((c) => ['quiebre', 'ia'].includes(c.estado.tipo)).length,
  },
])

const columnas = [
  { key: 'colaborador', label: 'Colaborador' },
  { key: 'avance', label: 'Cursos aprobados', width: '190px' },
  { key: 'pendientes', label: 'Módulos pendientes' },
  { key: 'estado', label: 'Estado', align: 'center', width: '140px' },
  { key: 'acciones', label: '', align: 'right', width: '160px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return colaboradores.value.filter((c) => {
    if (pill.value === 'pend' && !['quiebre', 'ia'].includes(c.estado.tipo)) return false
    else if (pill.value && pill.value !== 'pend' && c.estado.tipo !== pill.value) return false
    if (!q) return true
    return (
      c.nombre.toLowerCase().includes(q) ||
      (c.puesto || '').toLowerCase().includes(q) ||
      String(c.empleado_id).includes(q)
    )
  })
})
const filas = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

// ---- modal: programar capacitación -------------------------------------
const modalProgramar = ref(false)
const roles = ref([])
const formProg = reactive({ nombre: '', descripcion: '', roleIds: [] })
const guardando = ref(false)

async function abrirProgramar() {
  error.value = ''
  Object.assign(formProg, { nombre: '', descripcion: '', roleIds: [] })
  if (!roles.value.length) {
    try {
      roles.value = await rrhhApi.rolesSistema()
    } catch (e) {
      error.value = msg(e)
    }
  }
  modalProgramar.value = true
}

async function programar() {
  if (!formProg.nombre.trim() || !formProg.roleIds.length) return
  guardando.value = true
  error.value = ''
  try {
    const r = await rrhhApi.programarCapacitacion({
      nombre: formProg.nombre.trim(),
      descripcion: formProg.descripcion.trim() || null,
      roleIds: formProg.roleIds,
    })
    modalProgramar.value = false
    aviso.value = `Capacitación "${r.nombre}" programada — ${r.empleados_asignados} colaborador(es) asignado(s) en la red.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardando.value = false
  }
}

// ---- modal: registrar finalización ------------------------------------
const modalFin = ref(false)
const finColaborador = ref(null)
const formFin = reactive({ capacitacionId: null, fecha: new Date().toISOString().slice(0, 10) })

function abrirFinalizacion(colaborador) {
  finColaborador.value = colaborador
  formFin.capacitacionId = colaborador.pendientes[0]?.capacitacion_id ?? null
  formFin.fecha = new Date().toISOString().slice(0, 10)
  error.value = ''
  modalFin.value = true
}

async function registrarFinalizacion() {
  if (!formFin.capacitacionId || !formFin.fecha) return
  guardando.value = true
  error.value = ''
  try {
    await rrhhApi.completarCapacitacion(
      finColaborador.value.empleado_id,
      formFin.capacitacionId,
      formFin.fecha,
    )
    modalFin.value = false
    aviso.value = `Finalización registrada para ${finColaborador.value.nombre}.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Gestión de capacitaciones y cumplimiento"
      subtitulo="Programación de capacitaciones por rol (fan-out automático) y seguimiento del cumplimiento del personal de cada tienda."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.pendientes > 0 ? 'fifo' : 'ok'">
          {{ kpi.pendientes > 0 ? `${kpi.pendientes} pendientes` : 'Todo al día' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <label
          v-if="!esEncargado && tiendas.length"
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="pin" :size="14" class="text-brand-700" />
          <select v-model.number="tiendaId" class="bg-transparent text-slate-800 focus:outline-none">
            <option v-for="t in tiendas" :key="t.tienda_id" :value="t.tienda_id">{{ t.nombre }}</option>
          </select>
        </label>
        <span
          v-else
          class="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600"
        >
          <Icon name="pin" :size="14" class="text-brand-700" /> {{ tiendaNombre }}
        </span>
        <Btn v-if="puedeProgramar" variant="primary" @click="abrirProgramar">
          <Icon name="plus" :size="17" /> Programar capacitación
        </Btn>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-4 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      {{ aviso }}
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Cumplimiento de la tienda"
        :valor="kpi.cumplimientoPct != null ? `${kpi.cumplimientoPct}%` : null"
        variant="emerald"
        :microcopy="`${tiendaNombre} — capacitaciones completadas sobre asignadas`"
        pie-label="Colaboradores al día"
        :pie-valor="`${kpi.alDia} / ${kpi.empleados}`"
      />
      <KpiTile
        label="Colaboradores al día"
        :valor="`${kpi.alDia} / ${kpi.empleados}`"
        :estado-tipo="kpi.alDia === kpi.empleados && kpi.empleados ? 'ok' : 'fifo'"
        microcopy="Sin ningún módulo formativo pendiente"
      >
        <template #icono><Icon name="users" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Módulos formativos activos"
        :valor="kpi.modulos.toLocaleString('es-EC')"
        estado-tipo="neutral"
        microcopy="Capacitaciones programadas en el sistema"
      >
        <template #icono><Icon name="academic" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Asignaciones pendientes"
        :valor="kpi.pendientes.toLocaleString('es-EC')"
        :estado-tipo="kpi.pendientes > 0 ? 'quiebre' : 'ok'"
        microcopy="Registros empleado-capacitación sin fecha de finalización"
      >
        <template #icono><Icon name="clock" :size="16" /></template>
      </KpiTile>
    </section>

    <!-- Módulos formativos -->
    <section class="mb-6">
      <h2 class="mb-1 font-display text-base font-bold text-brand-950">Módulos formativos</h2>
      <p class="mb-3 text-[12px] text-slate-600">Avance de {{ tiendaNombre }} por capacitación.</p>
      <div v-if="!catalogo.length" class="rounded-xl border border-brand-200 bg-white p-6 text-center text-[13px] text-slate-500">
        Aún no hay capacitaciones programadas.
      </div>
      <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="c in catalogo"
          :key="c.capacitacion_id"
          class="satin-card rounded-2xl p-4 shadow-card-subtle"
        >
          <div class="flex items-start justify-between gap-2">
            <h3 class="text-[13px] font-bold text-slate-900">{{ c.nombre }}</h3>
            <SemanticChip :tipo="c.asignados && c.completados === c.asignados ? 'ok' : 'fifo'">
              {{ c.asignados ? Math.round((c.completados / c.asignados) * 100) : 0 }}%
            </SemanticChip>
          </div>
          <p v-if="c.descripcion" class="mt-1 line-clamp-2 text-[11px] text-slate-500">
            {{ c.descripcion }}
          </p>
          <div class="mt-3">
            <div class="h-1.5 w-full overflow-hidden rounded-full bg-brand-100">
              <div
                class="h-full rounded-full bg-brand-600"
                :style="{ width: `${c.asignados ? (c.completados / c.asignados) * 100 : 0}%` }"
              />
            </div>
            <p class="mt-1 text-[11px] font-medium text-slate-500">
              {{ c.completados }} / {{ c.asignados }} en esta tienda
            </p>
          </div>
        </article>
      </div>
    </section>

    <DataTable
      titulo="Matriz de estado formativo por colaborador"
      subtitulo="Cursos aprobados, módulos pendientes y estado de cada colaborador de la tienda."
      :columns="columnas"
      :rows="filas"
      row-key="empleado_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Colaborador o puesto…"
      :pills="pills"
      :pill-activa="pill"
      empty-text="Sin registros de capacitación en esta tienda"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
      @pill="((pill = $event), (page = 1))"
    >
      <template #cell:colaborador="{ row }">
        <div class="leading-tight">
          <div class="text-[12px] font-semibold text-slate-800">{{ row.nombre }}</div>
          <div class="text-[10px] text-slate-400">
            {{ row.puesto || 'Sin puesto' }} · #{{ row.empleado_id }}
          </div>
        </div>
      </template>

      <template #cell:avance="{ row }">
        <div class="flex items-center gap-2">
          <div class="h-1.5 w-20 overflow-hidden rounded-full bg-brand-100">
            <div
              class="h-full rounded-full"
              :class="row.hechos === row.total ? 'bg-brand-600' : 'bg-amber-500'"
              :style="{ width: `${row.pct}%` }"
            />
          </div>
          <span class="tabular-nums text-[12px] font-medium text-slate-600">
            {{ row.hechos }} / {{ row.total }}
          </span>
        </div>
      </template>

      <template #cell:pendientes="{ row }">
        <span v-if="!row.pendientes.length" class="text-[12px] text-slate-400">Ninguno</span>
        <div v-else class="flex flex-wrap gap-1">
          <span
            v-for="m in row.pendientes.slice(0, 3)"
            :key="m.capacitacion_id"
            class="rounded-md bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700"
          >
            {{ m.nombre }}
          </span>
          <span v-if="row.pendientes.length > 3" class="text-[10px] text-slate-400">
            +{{ row.pendientes.length - 3 }}
          </span>
        </div>
      </template>

      <template #cell:estado="{ row }">
        <SemanticChip :tipo="row.estado.tipo">{{ row.estado.txt }}</SemanticChip>
      </template>

      <template #cell:acciones="{ row }">
        <Btn
          v-if="puedeRegistrar && row.pendientes.length"
          variant="ghost"
          class="!px-2.5 !py-1 !text-[12px]"
          @click="abrirFinalizacion(row)"
        >
          <Icon name="check" :size="14" /> Registrar finalización
        </Btn>
        <span v-else class="text-[11px] text-slate-400">—</span>
      </template>
    </DataTable>

    <Modal
      v-if="modalProgramar"
      titulo="Programar capacitación"
      size="lg"
      @cerrar="modalProgramar = false"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Al guardar, el sistema asigna la capacitación a todos los colaboradores con cuenta activa en
        los roles seleccionados, en todas las tiendas (FR-003 / FR-004).
      </p>
      <form class="space-y-4" @submit.prevent="programar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Nombre <span class="text-crimson-ruby">*</span>
          <input
            v-model="formProg.nombre"
            type="text"
            maxlength="150"
            required
            placeholder="Ej.: Prevención de fraude y ciberseguridad POS"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Descripción
          <textarea
            v-model="formProg.descripcion"
            rows="2"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div>
          <p class="mb-1.5 text-[12px] font-semibold text-slate-600">
            Roles objetivo <span class="text-crimson-ruby">*</span>
          </p>
          <div class="grid max-h-52 gap-1.5 overflow-y-auto rounded-xl border border-brand-200 p-3 sm:grid-cols-2">
            <label
              v-for="r in roles"
              :key="r.role_id"
              class="flex items-center gap-2 text-[12px] text-slate-700"
            >
              <input v-model="formProg.roleIds" type="checkbox" :value="r.role_id" class="accent-brand-700" />
              {{ r.nombre }}
            </label>
          </div>
        </div>
        <div class="flex justify-end gap-2.5 pt-2">
          <Btn variant="ghost" @click="modalProgramar = false">Cancelar</Btn>
          <Btn
            variant="primary"
            type="submit"
            :disabled="guardando || !formProg.nombre.trim() || !formProg.roleIds.length"
          >
            {{ guardando ? 'Programando…' : 'Programar' }}
          </Btn>
        </div>
      </form>
    </Modal>

    <Modal
      v-if="modalFin"
      :titulo="`Registrar finalización — ${finColaborador?.nombre}`"
      @cerrar="modalFin = false"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        Registra la fecha en que el colaborador completó una de sus capacitaciones pendientes
        (FR-004).
      </p>
      <form class="space-y-4" @submit.prevent="registrarFinalizacion">
        <label class="block text-[12px] font-semibold text-slate-600">
          Capacitación <span class="text-crimson-ruby">*</span>
          <select
            v-model.number="formFin.capacitacionId"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option v-for="m in finColaborador?.pendientes || []" :key="m.capacitacion_id" :value="m.capacitacion_id">
              {{ m.nombre }}
            </option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Fecha de finalización <span class="text-crimson-ruby">*</span>
          <input
            v-model="formFin.fecha"
            type="date"
            required
            :max="new Date().toISOString().slice(0, 10)"
            class="mt-1 block w-48 rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div class="flex justify-end gap-2.5 pt-2">
          <Btn variant="ghost" @click="modalFin = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando || !formFin.capacitacionId">
            {{ guardando ? 'Registrando…' : 'Confirmar finalización' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
