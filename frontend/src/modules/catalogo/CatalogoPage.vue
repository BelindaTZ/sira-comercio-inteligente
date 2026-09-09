<script setup>
/**
 * Catálogo Maestro de Productos & Matriz de Precios (001, US4).
 * Estructura de `docs/diseno-ui/.../sira_cat_logo_maestro_de_productos_precios/`:
 * page header + acciones, 4 KPI tiles (incl. elasticidad IA), barra de filtros
 * (categoría · banda de margen · canal), data-grid con PVP por canal y estado de
 * margen, y panel lateral con el simulador de impacto + reglas de recargo por
 * canal. Los componentes (KpiTile / DataTable / Btn / SemanticChip) son los
 * mismos de la pantalla de Inventario.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'
import { useSesion } from '@/stores/sesion'
import { confirm } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import CategoriaPicker from '@/shared/ui/CategoriaPicker.vue'
import FormularioProducto from './components/FormularioProducto.vue'
import SimuladorPrecio from './components/SimuladorPrecio.vue'

const sesion = useSesion()
const puedeEditar = computed(() => sesion.puedeEditarTabla('Comercial', 'productos'))

const busqueda = ref('')
const categoria = ref('')
const bandaMargen = ref('')
const pill = ref('activos') // 'todos' | 'activos' | 'baja'
const page = ref(1)
const size = ref(25)

const rows = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')

const kpi = ref({
  total_activos: 0,
  nuevos_30d: 0,
  con_ean: 0,
  total: 0,
  skus_con_elasticidad: 0,
  promos_vigentes: 0,
  skus_bajo_margen: 0,
  margen_bruto_ponderado_pct: null,
  calculado_at: null,
})

const modal = ref(null) // 'nuevo' | fila (edición precio)
const edicion = ref({ precio_base: null, costo: null })
const seleccion = ref(null) // fila para el simulador

const money = (v) =>
  v == null ? '—' : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const pct = (v) => (v == null ? '—' : `${Number(v).toFixed(1)}%`)

const eanPct = computed(() =>
  kpi.value.total ? Math.round((kpi.value.con_ean / kpi.value.total) * 100) : 0,
)
const metaMargen = 32
const margenSobreMeta = computed(() => (kpi.value.margen_bruto_ponderado_pct ?? 0) >= metaMargen)

const actualizadoHace = computed(() => {
  if (!kpi.value.calculado_at) return null
  const min = Math.round((Date.now() - new Date(kpi.value.calculado_at)) / 60000)
  if (min < 1) return 'hace instantes'
  if (min < 60) return `hace ${min} min`
  const h = Math.round(min / 60)
  return h < 24 ? `hace ${h} h` : `hace ${Math.round(h / 24)} d`
})

const pills = computed(() => [
  { value: 'todos', label: 'Todos', count: kpi.value.total },
  { value: 'activos', label: 'Activos', count: kpi.value.total_activos },
  { value: 'baja', label: 'Dados de baja', count: kpi.value.total - kpi.value.total_activos },
])

const ESTADO = {
  optimo: { tipo: 'ok', txt: 'Margen óptimo' },
  ajustado: { tipo: 'fifo', txt: 'Margen ajustado' },
  bajo: { tipo: 'quiebre', txt: 'Bajo margen' },
  sin_precio: { tipo: 'neutral', txt: 'Sin precio' },
}

const columnas = [
  { key: 'sku', label: 'SKU / EAN-13', width: '128px' },
  { key: 'producto', label: 'Producto & formato' },
  { key: 'categoria', label: 'Categoría' },
  { key: 'costo', label: 'Costo adquisición', align: 'right', width: '120px' },
  { key: 'margen', label: 'Margen real / obj.', align: 'right', width: '120px' },
  { key: 'pvp', label: 'PVP Final / Neto', align: 'right', width: '145px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '140px' },
  { key: 'acciones', label: '', align: 'center', width: '96px' },
]

function activoParam() {
  return pill.value === 'activos' ? true : pill.value === 'baja' ? false : undefined
}

async function cargarKpis() {
  try {
    kpi.value = await catalogoApi.resumen()
  } catch {
    /* informativo */
  }
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await catalogoApi.matrizPrecios({
      search: busqueda.value.trim() || undefined,
      categoria: categoria.value || undefined,
      margen: bandaMargen.value || undefined,
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

function abrirEdicion(row) {
  if (!puedeEditar.value) {
    seleccion.value = row
    return
  }
  edicion.value = { precio_base: row.precio_base, costo: row.costo }
  modal.value = row
}

async function guardarEdicion() {
  try {
    const patch = {}
    if (edicion.value.precio_base != null) patch.precio_base = Number(edicion.value.precio_base)
    if (edicion.value.costo != null) patch.costo = Number(edicion.value.costo)
    await catalogoApi.actualizar(modal.value.product_id, patch)
    modal.value = null
    await refrescar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

async function darDeBaja(row) {
  const ok = await confirm({
    title: 'Dar de baja el producto',
    message: `"${row.nombre || row.product_id}" dejará de aparecer en el catálogo activo. No afecta ventas ya registradas.`,
    confirmText: 'Dar de baja',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await catalogoApi.darDeBaja(row.product_id)
    await refrescar()
  } catch (e) {
    error.value = e.message
  }
}

function refrescar() {
  return Promise.all([cargar(), cargarKpis()])
}
function trasAlta() {
  modal.value = null
  return refrescar()
}

const descargando = ref('')
async function descargar(formato) {
  descargando.value = formato
  try {
    const blob = await catalogoApi.exportarPrecios(formato, {
      search: busqueda.value.trim(),
      categoria: categoria.value,
      margen: bandaMargen.value,
    })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `catalogo-precios.${formato}`
    a.click()
    URL.revokeObjectURL(a.href)
    modal.value = null
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    descargando.value = ''
  }
}

watch([pill, categoria, bandaMargen], () => {
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
      titulo="Catálogo Maestro de Productos & Precios"
      subtitulo="Gestión centralizada de SKU, márgenes reales vs. objetivo y simulación de sensibilidad de precio a la demanda."
    >
      <template #badge>
        <span
          v-if="actualizadoHace"
          class="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-800"
        >
          <span class="live-indicator h-1.5 w-1.5 rounded-full bg-emerald-500" /> KPIs {{ actualizadoHace }}
        </span>
      </template>
      <template #acciones>
        <Btn variant="ghost" @click="modal = 'export'"><Icon name="download" :size="16" /> Exportar</Btn>
        <Btn v-if="puedeEditar" variant="primary" @click="modal = 'nuevo'">
          <Icon name="plus" :size="17" /> Nuevo producto
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
        label="Total SKUs activos"
        :valor="kpi.total_activos.toLocaleString('es-CL')"
        variant="emerald"
        :microcopy="`${kpi.total.toLocaleString('es-CL')} en el catálogo maestro`"
        pie-label="Código EAN validado"
        :pie-valor="`${eanPct}% · ${kpi.con_ean.toLocaleString('es-CL')} SKUs`"
      />
      <KpiTile
        label="Margen bruto ponderado"
        :valor="kpi.margen_bruto_ponderado_pct != null ? kpi.margen_bruto_ponderado_pct.toFixed(1) + '%' : null"
        :estado="margenSobreMeta ? 'sobre meta' : 'bajo meta'"
        :estado-tipo="margenSobreMeta ? 'ok' : 'quiebre'"
        :microcopy="`Meta de tienda: > ${metaMargen}.0%`"
      >
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Elasticidad de precios IA"
        :valor="kpi.skus_con_elasticidad.toLocaleString('es-CL')"
        unidad="SKUs"
        variant="ia"
        estado="motor activo"
        estado-tipo="ia"
        microcopy="Bajo optimización dinámica de PVP"
        pie-label="Origen"
        pie-valor="Factor de sensibilidad por categoría"
      >
        <template #icono><Icon name="bolt" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="SKUs bajo margen objetivo"
        :valor="kpi.skus_bajo_margen.toLocaleString('es-CL')"
        :estado="kpi.skus_bajo_margen > 0 ? 'revisar PVP' : 'al día'"
        :estado-tipo="kpi.skus_bajo_margen > 0 ? 'quiebre' : 'ok'"
        microcopy="Margen real > 5 pp bajo el objetivo de su categoría"
        pie-label="Con historial promocional"
        :pie-valor="`${kpi.promos_vigentes.toLocaleString('es-CL')} SKUs`"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
      {{ error }}
    </p>

    <div class="grid items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]">
      <DataTable
        titulo="Productos"
        subtitulo="Margen real vs. objetivo de su categoría. El PVP por canal se calcula sobre el precio físico."
        :columns="columnas"
        :rows="rows"
        row-key="product_id"
        :loading="cargando"
        densa
        :page="page"
        :size="size"
        :total="total"
        :search="busqueda"
        search-placeholder="SKU, EAN-13, nombre o marca…"
        :pills="pills"
        :pill-activa="pill"
        empty-text="Sin productos para este filtro"
        @update:page="page = $event"
        @update:size="((size = $event), (page = 1))"
        @update:search="busqueda = $event"
        @pill="pill = $event"
        @row-click="((seleccion = $event))"
      >
        <template #acciones-cabecera>
          <div class="w-40"><CategoriaPicker v-model="categoria" label="" placeholder="Todas las categorías" /></div>
          <select
            v-model="bandaMargen"
            class="h-9 rounded-lg border border-brand-300 bg-white px-2 text-[12px] text-slate-700"
          >
            <option value="">Margen: todos</option>
            <option value="bajo">&lt; 20% (bajo)</option>
            <option value="normal">20–35% (normal)</option>
            <option value="premium">&gt; 35% (premium)</option>
          </select>
        </template>

        <template #cell:sku="{ row }">
          <div class="font-mono text-[11px] leading-tight">
            <div class="font-bold text-brand-800">{{ row.product_id }}</div>
            <div class="text-slate-400">{{ row.codigo_barras || '—' }}</div>
          </div>
        </template>

        <template #cell:producto="{ row }">
          <div class="flex items-center gap-2.5">
            <img
              v-if="row.imagen_url && row.imagen_url.startsWith('http')"
              :src="row.imagen_url"
              alt=""
              class="h-9 w-9 shrink-0 rounded-md border border-brand-200 bg-brand-50 object-cover"
            />
            <span
              v-else
              class="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-brand-200 bg-brand-50 text-brand-300"
            >
              <Icon name="image" :size="16" />
            </span>
            <div class="min-w-0">
              <div class="truncate text-[12px] font-semibold text-slate-800">
                {{ row.nombre || '(sin nombre)' }}
              </div>
              <div class="truncate text-[10px] text-slate-500">
                {{ row.marca || 'Sin marca' }}<template v-if="row.package_size"> · {{ row.package_size }}</template>
              </div>
            </div>
          </div>
        </template>

        <template #cell:categoria="{ row }">
          <div class="flex flex-wrap items-center gap-1">
            <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-700">
              {{ row.product_category || '—' }}
            </span>
            <SemanticChip v-if="row.clasificacion_abc === 'A'" tipo="ok">A</SemanticChip>
            <SemanticChip v-else-if="row.clasificacion_abc === 'C'" tipo="quiebre">C</SemanticChip>
            <SemanticChip v-if="row.es_ancla" tipo="ia">Ancla</SemanticChip>
          </div>
        </template>

        <template #cell:costo="{ row }">
          <div class="font-medium tabular-nums text-slate-700">{{ money(row.costo) }}</div>
          <div class="text-[10px] text-slate-400">adquisición</div>
        </template>

        <template #cell:margen="{ row }">
          <div
            class="font-bold tabular-nums"
            :class="
              row.estado_margen === 'optimo'
                ? 'text-emerald-700'
                : row.estado_margen === 'ajustado'
                  ? 'text-amber-700'
                  : row.estado_margen === 'bajo'
                    ? 'text-crimson-ruby'
                    : 'text-slate-400'
            "
          >
            {{ pct(row.margen_pct) }}
          </div>
          <div class="text-[10px] font-medium text-slate-400">obj {{ pct(row.margen_objetivo_pct) }}</div>
        </template>

        <template #cell:pvp="{ row }">
          <div class="font-bold tabular-nums text-slate-900">{{ money(row.precio_base) }}</div>
          <div class="text-[10px] font-medium text-slate-500">
            neto {{ money(row.precio_neto ?? (row.precio_base != null ? row.precio_base / 1.15 : null)) }}
            <span class="text-slate-400">(IVA 15%)</span>
          </div>
        </template>

        <template #cell:estado="{ row }">
          <SemanticChip :tipo="ESTADO[row.estado_margen].tipo">{{ ESTADO[row.estado_margen].txt }}</SemanticChip>
        </template>

        <template #cell:acciones="{ row }">
          <div class="flex items-center justify-center gap-0.5">
            <button
              type="button"
              class="rounded-md p-1.5 text-slate-400 hover:bg-amethyst-50 hover:text-amethyst-700"
              :class="seleccion?.product_id === row.product_id ? 'bg-amethyst-100 text-amethyst-700' : ''"
              title="Simular impacto de precio"
              @click.stop="seleccion = row"
            >
              <Icon name="chart" :size="15" />
            </button>
            <button
              v-if="puedeEditar"
              type="button"
              class="rounded-md p-1.5 text-slate-400 hover:bg-brand-50 hover:text-brand-800"
              title="Editar precio / costo"
              @click.stop="abrirEdicion(row)"
            >
              <Icon name="pencil" :size="15" />
            </button>
            <button
              v-if="row.activo && puedeEditar"
              type="button"
              class="rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-crimson-ruby"
              title="Dar de baja"
              @click.stop="darDeBaja(row)"
            >
              <Icon name="trash" :size="15" />
            </button>
          </div>
        </template>
      </DataTable>

      <div class="space-y-4">
        <SimuladorPrecio :producto="seleccion" :puede-editar="puedeEditar" @aplicado="refrescar" />
      </div>
    </div>

    <Modal v-if="modal === 'nuevo'" titulo="Nuevo producto" @cerrar="modal = null">
      <FormularioProducto @creado="trasAlta" />
    </Modal>

    <Modal v-if="modal === 'export'" titulo="Exportar matriz de precios" @cerrar="modal = null">
      <p class="mb-3 text-[13px] text-slate-600">
        Se exporta el listado con los filtros activos ({{ total.toLocaleString('es-CL') }} productos,
        hasta 5.000 filas). Elegí el formato:
      </p>
      <div class="grid grid-cols-3 gap-2.5">
        <button
          v-for="f in [
            { v: 'csv', t: 'CSV', d: 'Texto plano', icon: 'filter' },
            { v: 'xlsx', t: 'Excel', d: '.xlsx con formato', icon: 'chart' },
            { v: 'pdf', t: 'PDF', d: 'Reporte para imprimir', icon: 'image' },
          ]"
          :key="f.v"
          type="button"
          :disabled="descargando"
          class="flex flex-col items-center gap-1.5 rounded-xl border border-brand-200 bg-white p-4 text-center transition hover:border-brand-500 hover:bg-brand-50/60 disabled:opacity-50"
          @click="descargar(f.v)"
        >
          <Icon :name="f.icon" :size="22" class="text-brand-700" />
          <span class="text-[13px] font-bold text-slate-800">
            {{ descargando === f.v ? 'Generando…' : f.t }}
          </span>
          <span class="text-[10px] text-slate-500">{{ f.d }}</span>
        </button>
      </div>
    </Modal>

    <Modal
      v-else-if="modal && typeof modal === 'object'"
      :titulo="`Editar precio — ${modal.nombre || modal.product_id}`"
      @cerrar="modal = null"
    >
      <form class="space-y-3" @submit.prevent="guardarEdicion">
        <label class="block text-[12px] font-semibold text-slate-600">
          Costo adquisición
          <input
            v-model="edicion.costo"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          PVP final (con IVA 15% incluido)
          <input
            v-model="edicion.precio_base"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div v-if="edicion.precio_base != null && edicion.precio_base > 0" class="flex items-center justify-between rounded-lg bg-brand-50/70 p-2.5 text-xs text-brand-900 border border-brand-200/60">
          <span class="text-slate-600 font-medium">Equivalente neto (sin IVA):</span>
          <span class="font-bold tabular-nums text-brand-800">{{ money(Number(edicion.precio_base) / 1.15) }}</span>
        </div>
        <button
          type="submit"
          class="w-full rounded-xl bg-brand-800 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
        >
          Guardar
        </button>
      </form>
    </Modal>
  </div>
</template>
