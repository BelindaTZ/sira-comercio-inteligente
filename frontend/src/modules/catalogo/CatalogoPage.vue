<script setup>
/**
 * Catálogo de productos (001, US4). Arquetipo "Gestión" de `docs/diseno-ui/`:
 * page header + acciones, KPI tiles, barra de filtros con pills, data-grid con
 * chips ABC / estado, alta y edición en modales.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import FilterBar from '@/shared/ui/FilterBar.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import FormularioProducto from './components/FormularioProducto.vue'

const busqueda = ref('')
const pill = ref('activos') // 'todos' | 'activos' | 'baja'
const page = ref(1)
const size = ref(25)

const rows = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const modal = ref(null) // 'nuevo' | producto (edición)
const edicion = ref({ precio_base: null, costo: null })

const kpi = ref({ total: 0, activos: 0, perecederos: 0, claseA: 0 })

const pills = computed(() => [
  { value: 'todos', label: 'Todos', count: kpi.value.total, tipo: 'neutral' },
  { value: 'activos', label: 'Activos', count: kpi.value.activos, tipo: 'ok' },
  {
    value: 'baja',
    label: 'Dados de baja',
    count: kpi.value.total - kpi.value.activos,
    tipo: 'quiebre',
  },
])

const fmtMoneda = (v) => (v == null ? '—' : `$${Number(v).toLocaleString('es-CL')}`)
const margen = (row) =>
  row.costo && row.precio_base && Number(row.precio_base) > 0
    ? `${(((row.precio_base - row.costo) / row.precio_base) * 100).toFixed(1)}%`
    : '—'

const columnas = [
  { key: 'product_id', label: 'ID', width: '72px' },
  { key: 'nombre', label: 'Producto' },
  { key: 'marca', label: 'Marca' },
  { key: 'product_category', label: 'Categoría' },
  { key: 'costo', label: 'Costo', align: 'right', formatter: fmtMoneda },
  { key: 'precio_base', label: 'Precio', align: 'right', formatter: fmtMoneda },
  { key: 'margen', label: 'Margen', align: 'right', formatter: (_, r) => margen(r) },
  { key: 'clasificacion_abc', label: 'ABC' },
  { key: 'activo', label: 'Estado' },
]

function activoParam() {
  return pill.value === 'activos' ? true : pill.value === 'baja' ? false : undefined
}

async function cargarKpis() {
  try {
    const [t, a] = await Promise.all([
      catalogoApi.listar({ size: 1 }),
      catalogoApi.listar({ size: 1, activo: true }),
    ])
    kpi.value = { ...kpi.value, total: t.total, activos: a.total }
  } catch {
    /* informativo */
  }
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await catalogoApi.listar({
      search: busqueda.value.trim() || undefined,
      activo: activoParam(),
      page: page.value,
      size: size.value,
    })
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function guardarEdicion() {
  try {
    const patch = {}
    if (edicion.value.precio_base != null) patch.precio_base = Number(edicion.value.precio_base)
    if (edicion.value.costo != null) patch.costo = Number(edicion.value.costo)
    await catalogoApi.actualizar(modal.value.product_id, patch)
    modal.value = null
    await Promise.all([cargar(), cargarKpis()])
  } catch (e) {
    error.value = e.message
  }
}

async function darDeBaja(row) {
  if (!window.confirm(`¿Dar de baja "${row.nombre || row.product_id}"?`)) return
  try {
    await catalogoApi.darDeBaja(row.product_id)
    await Promise.all([cargar(), cargarKpis()])
  } catch (e) {
    error.value = e.message
  }
}

function abrirEdicion(row) {
  edicion.value = { precio_base: row.precio_base, costo: row.costo }
  modal.value = row
}

function trasAlta() {
  modal.value = null
  return Promise.all([cargar(), cargarKpis()])
}

watch(pill, () => {
  page.value = 1
  cargar()
})
watch([page, size], cargar)
let deb
watch(busqueda, () => {
  clearTimeout(deb)
  deb = setTimeout(() => {
    page.value = 1
    cargar()
  }, 300)
})
onMounted(() => {
  cargar()
  cargarKpis()
})
</script>

<template>
  <div class="mx-auto max-w-[1720px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Catálogo de productos"
      subtitulo="Alta con autocompletado, edición de precio/costo y baja lógica. Toda regla en el backend."
    >
      <template #acciones>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-[13px] font-semibold text-white transition hover:bg-primary-hover"
          @click="modal = 'nuevo'"
        >
          <Icon name="plus" :size="16" /> Nuevo producto
        </button>
      </template>
    </PageHeader>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <KpiTile
        label="Productos en catálogo"
        :valor="kpi.total.toLocaleString('es-CL')"
        variant="emerald"
      />
      <KpiTile label="Activos" :valor="kpi.activos.toLocaleString('es-CL')" variant="mint" />
      <KpiTile
        label="Dados de baja"
        :valor="(kpi.total - kpi.activos).toLocaleString('es-CL')"
        variant="plain"
      />
    </section>

    <FilterBar
      v-model="busqueda"
      placeholder="Buscar por nombre, marca o código de barras…"
      :pills="pills"
      :pill-activa="pill"
      class="mb-4"
      @pill="pill = $event"
    />

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <DataTable
      titulo="Productos"
      subtitulo="Catálogo maestro de la red — alta, edición de precio/costo y baja lógica."
      :columns="columnas"
      :rows="rows"
      row-key="product_id"
      :loading="cargando"
      :page="page"
      :size="size"
      :total="total"
      empty-text="Sin productos para este filtro"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @row-click="abrirEdicion"
    >
      <template #cell:nombre="{ row }">
        <span class="font-medium text-on-surface">{{ row.nombre || '(sin nombre)' }}</span>
        <SemanticChip v-if="row.es_perecedero" tipo="fifo" class="ml-2">Perecedero</SemanticChip>
        <SemanticChip v-if="row.es_ancla" tipo="ia" class="ml-1">Ancla</SemanticChip>
      </template>
      <template #cell:marca="{ value }">{{ value || '—' }}</template>
      <template #cell:product_category="{ value }">{{ value || '—' }}</template>
      <template #cell:clasificacion_abc="{ value }">
        <SemanticChip
          v-if="value"
          :tipo="value === 'A' ? 'ok' : value === 'C' ? 'quiebre' : 'neutral'"
        >
          {{ value }}
        </SemanticChip>
        <span v-else class="text-on-surface-variant">—</span>
      </template>
      <template #cell:activo="{ row }">
        <div class="flex items-center gap-2">
          <SemanticChip :tipo="row.activo ? 'ok' : 'quiebre'">
            {{ row.activo ? 'Activo' : 'Baja' }}
          </SemanticChip>
          <button
            v-if="row.activo"
            type="button"
            class="rounded-md border border-crimson-ruby/30 px-2 py-0.5 text-[11px] font-semibold text-crimson-ruby hover:bg-[#ffe4e6]"
            @click.stop="darDeBaja(row)"
          >
            Baja
          </button>
        </div>
      </template>
    </DataTable>

    <Modal v-if="modal === 'nuevo'" titulo="Nuevo producto" @cerrar="modal = null">
      <FormularioProducto @creado="trasAlta" />
    </Modal>

    <Modal
      v-else-if="modal && typeof modal === 'object'"
      :titulo="`Editar — ${modal.nombre || modal.product_id}`"
      @cerrar="modal = null"
    >
      <form class="space-y-3" @submit.prevent="guardarEdicion">
        <label class="block text-xs text-on-surface-variant">
          Costo
          <input
            v-model="edicion.costo"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-md border border-outline-variant bg-white px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="block text-xs text-on-surface-variant">
          Precio base
          <input
            v-model="edicion.precio_base"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-md border border-outline-variant bg-white px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <button
          type="submit"
          class="w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white"
        >
          Guardar
        </button>
      </form>
    </Modal>
  </div>
</template>
