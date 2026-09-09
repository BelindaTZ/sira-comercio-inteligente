<script setup>
/**
 * Catálogo de empleados (feature 008, FR-005/FR-006/FR-014). Alta, actualización
 * y baja — el Jefe de RRHH. Al dar de baja, un trigger de PostgreSQL inhabilita
 * la cuenta asociada (research.md Decisión 4). Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { confirm } from '@/shared/ui/dialogs'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const puedeEditar = computed(() => !sesion.esGerente && sesion.rol === 'Jefe_RRHH')

const empleados = ref([])
const puestos = ref([])
const tiendas = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')
const busqueda = ref('')
const pill = ref('activos')
const page = ref(1)
const size = ref(15)
const modal = ref(false)
const guardando = ref(false)

const nuevo = reactive({
  nombre: '',
  puestoId: '',
  tiendaId: '',
  email: '',
  telefono: '',
  fechaContratacion: new Date().toISOString().slice(0, 10),
})

const kpi = computed(() => ({
  total: empleados.value.length,
  activos: empleados.value.filter((e) => e.activo).length,
  conCuenta: empleados.value.filter((e) => e.tiene_cuenta).length,
  criticos: empleados.value.filter((e) => e.activo && e.puesto_critico).length,
}))

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return empleados.value.filter((e) => {
    if (pill.value === 'activos' && !e.activo) return false
    if (pill.value === 'baja' && e.activo) return false
    if (q && !`${e.nombre} ${e.email || ''} ${e.empleado_id}`.toLowerCase().includes(q)) return false
    return true
  })
})
const pagina = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)
const pills = computed(() => [
  { value: 'activos', label: 'Activos', count: kpi.value.activos },
  { value: 'baja', label: 'Dados de baja', count: kpi.value.total - kpi.value.activos },
  { value: 'todos', label: 'Todos', count: kpi.value.total },
])

const columnas = [
  { key: 'empleado', label: 'Empleado' },
  { key: 'puesto', label: 'Puesto', width: '150px' },
  { key: 'tienda', label: 'Tienda', width: '160px' },
  { key: 'contratacion', label: 'Ingreso', align: 'right', width: '110px' },
  { key: 'cuenta', label: 'Cuenta', align: 'center', width: '90px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '120px' },
  { key: 'acciones', label: '', align: 'right', width: '110px' },
]

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    ;[empleados.value, puestos.value] = await Promise.all([
      rrhhApi.listarEmpleados(),
      puestos.value.length ? Promise.resolve(puestos.value) : rrhhApi.listarPuestos(),
    ])
    if (!tiendas.value.length) tiendas.value = await rrhhApi.tiendas().catch(() => [])
    page.value = 1
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function crear() {
  if (!nuevo.nombre.trim() || !nuevo.puestoId) return
  guardando.value = true
  error.value = ''
  try {
    const e = await rrhhApi.crearEmpleado({
      nombre: nuevo.nombre.trim(),
      puestoId: Number(nuevo.puestoId),
      tiendaId: nuevo.tiendaId ? Number(nuevo.tiendaId) : null,
      email: nuevo.email || null,
      telefono: nuevo.telefono || null,
      fechaContratacion: nuevo.fechaContratacion,
    })
    modal.value = false
    Object.assign(nuevo, {
      nombre: '',
      puestoId: '',
      tiendaId: '',
      email: '',
      telefono: '',
      fechaContratacion: new Date().toISOString().slice(0, 10),
    })
    aviso.value = `Empleado #${e.empleado_id} registrado.`
    await cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

async function darBaja(emp) {
  const ok = await confirm({
    title: `Dar de baja a ${emp.nombre}`,
    message: 'La baja inhabilita también su cuenta de usuario. Queda registrada con la fecha de hoy.',
    confirmText: 'Dar de baja',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await rrhhApi.darBajaEmpleado(emp.empleado_id, new Date().toISOString().slice(0, 10))
    aviso.value = `${emp.nombre} dado de baja.`
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

const fechaCorta = (s) => (s ? String(s).slice(0, 10) : '—')

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1500px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Empleados"
      subtitulo="Directorio del personal de la red con su puesto, tienda y estado de cuenta. El alta y la baja las gestiona el Jefe de RRHH (FR-005/FR-006/FR-014)."
    >
      <template #badge>
        <SemanticChip tipo="ok">{{ kpi.activos }} activos</SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeEditar" variant="primary" @click="modal = true">
          <Icon name="plus" :size="15" /> Alta de empleado
        </Btn>
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

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile label="Empleados en la red" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" :microcopy="`${kpi.activos} activos`" />
      <KpiTile label="Con cuenta de usuario" :valor="kpi.conCuenta.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="id" :size="16" /></template>
      </KpiTile>
      <KpiTile label="En puesto crítico" :valor="kpi.criticos.toLocaleString('es-EC')" estado-tipo="fifo">
        <template #icono><Icon name="shield" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Dados de baja" :valor="(kpi.total - kpi.activos).toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="users" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      titulo="Directorio de empleados"
      :columns="columnas"
      :rows="pagina"
      row-key="empleado_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Nombre, correo o ID…"
      :pills="pills"
      :pill-activa="pill"
      empty-text="Sin empleados que coincidan"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
      @pill="((pill = $event), (page = 1))"
    >
      <template #cell:empleado="{ row }">
        <div class="leading-tight">
          <div class="text-[12px] font-semibold text-slate-800">{{ row.nombre }}</div>
          <div class="text-[11px] text-slate-400">
            ID {{ row.empleado_id }}<template v-if="row.email"> · {{ row.email }}</template>
          </div>
        </div>
      </template>
      <template #cell:puesto="{ row }">
        <span class="flex items-center gap-1 text-[12px] text-slate-700">
          {{ row.puesto_nombre || '—' }}
          <SemanticChip v-if="row.puesto_critico" tipo="fifo">crítico</SemanticChip>
        </span>
      </template>
      <template #cell:tienda="{ row }">
        <span class="text-[12px] text-slate-600">{{ row.tienda_nombre || 'Sin tienda' }}</span>
      </template>
      <template #cell:contratacion="{ row }">
        <span class="tabular-nums text-[12px] text-slate-500">{{ fechaCorta(row.fecha_contratacion) }}</span>
      </template>
      <template #cell:cuenta="{ row }">
        <Icon
          :name="row.tiene_cuenta ? 'check' : 'x'"
          :size="14"
          :class="row.tiene_cuenta ? 'text-emerald-600' : 'text-slate-300'"
        />
      </template>
      <template #cell:estado="{ row }">
        <SemanticChip :tipo="row.activo ? 'ok' : 'quiebre'">
          {{ row.activo ? 'Activo' : `Baja ${fechaCorta(row.fecha_baja)}` }}
        </SemanticChip>
      </template>
      <template #cell:acciones="{ row }">
        <Btn
          v-if="puedeEditar && row.activo"
          variant="danger"
          class="!px-2.5 !py-1 !text-[12px]"
          @click="darBaja(row)"
        >
          Dar de baja
        </Btn>
        <span v-else class="text-[11px] text-slate-400">—</span>
      </template>
    </DataTable>

    <Modal v-if="modal" titulo="Alta de empleado" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="crear">
        <label class="block text-[12px] font-semibold text-slate-600">
          Nombre completo
          <input v-model="nuevo.nombre" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-[12px] font-semibold text-slate-600">
            Puesto
            <select v-model="nuevo.puestoId" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
              <option value="" disabled>Elegí un puesto…</option>
              <option v-for="p in puestos" :key="p.puesto_id" :value="p.puesto_id">{{ p.nombre }}</option>
            </select>
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Tienda (opcional)
            <select v-model="nuevo.tiendaId" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
              <option value="">Sin tienda asignada</option>
              <option v-for="t in tiendas" :key="t.tienda_id" :value="t.tienda_id">{{ t.nombre }}</option>
            </select>
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Correo (opcional)
            <input v-model="nuevo.email" type="email" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Teléfono (opcional)
            <input v-model="nuevo.telefono" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="col-span-2 block text-[12px] font-semibold text-slate-600">
            Fecha de contratación
            <input v-model="nuevo.fechaContratacion" type="date" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
        </div>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Registrando…' : 'Registrar empleado' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
