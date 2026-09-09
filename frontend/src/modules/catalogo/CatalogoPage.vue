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
const puedeCanales = computed(() => sesion.puedeEditarTabla('Comercial', 'regla_recargo_canal'))

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
})

const CANAL_CORTO = { fisico: 'Físico', delivery_app: 'Delivery', ecommerce: 'E‑Commerce' }

const canales = ref([])
const canalSel = ref('delivery_app')
const modal = ref(null) // 'nuevo' | 'canales' | fila (edición precio)
const edicion = ref({ precio_base: null, costo: null })
const seleccion = ref(null) // fila para el simulador

const money = (v) => (v == null ? '—' : `$${Math.round(Number(v)).toLocaleString('es-CL')}`)
const pct = (v) => (v == null ? '—' : `${Number(v).toFixed(1)}%`)

const eanPct = computed(() =>
  kpi.value.total ? Math.round((kpi.value.con_ean / kpi.value.total) * 100) : 0,
)
const metaMargen = 32
const margenSobreMeta = computed(() => (kpi.value.margen_bruto_ponderado_pct ?? 0) >= metaMargen)

const canalActual = computed(() => canales.value.find((c) => c.canal === canalSel.value) || null)
const markupActual = computed(() => Number(canalActual.value?.markup_pct ?? 0))
const pvpCanal = (row) =>
  row.precio_base == null ? null : Number(row.precio_base) * (1 + markupActual.value / 100)

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

const columnas = computed(() => [
  { key: 'sku', label: 'SKU / EAN-13', width: '128px' },
  { key: 'producto', label: 'Producto & formato' },
  { key: 'categoria', label: 'Categoría' },
  { key: 'costo', label: 'Costo neto', align: 'right', width: '104px' },
  { key: 'margen', label: 'Margen obj.', align: 'right', width: '104px' },
  { key: 'pvp', label: 'PVP actual', align: 'right', width: '116px' },
  { key: 'pvp_canal', label: `PVP ${CANAL_CORTO[canalSel.value] || 'canal'}`, align: 'right', width: '116px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '132px' },
  { key: 'acciones', label: '', align: 'center', width: '84px' },
])

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

async function cargarCanales() {
  try {
    canales.value = await catalogoApi.canales()
  } catch {
    canales.value = []
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
  if (!window.confirm(`¿Dar de baja "${row.nombre || row.product_id}"?`)) return
  try {
    await catalogoApi.darDeBaja(row.product_id)
    await refrescar()
  } catch (e) {
    error.value = e.message
  }
}

async function guardarCanal(canal, markup) {
  try {
    const actualizado = await catalogoApi.actualizarCanal(canal, { markupPct: Number(markup) })
    canales.value = canales.value.map((c) => (c.canal === canal ? actualizado : c))
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

function refrescar() {
  return Promise.all([cargar(), cargarKpis()])
}
function trasAlta() {
  modal.value = null
  return refrescar()
}

function exportarCsv() {
  const cab = ['product_id', 'ean', 'nombre', 'marca', 'categoria', 'costo', 'precio_base', 'margen_pct', 'estado']
  const lineas = rows.value.map((r) =>
    [r.product_id, r.codigo_barras, r.nombre, r.marca, r.product_category, r.costo, r.precio_base, r.margen_pct, r.estado_margen]
      .map((v) => `"${(v ?? '').toString().replace(/"/g, '""')}"`)
      .join(','),
  )
  const blob = new Blob([[cab.join(','), ...lineas].join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `catalogo-precios-p${page.value}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
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
  cargarCanales()
})
</script>

<template>
  <div class="mx-auto max-w-[1720px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Catálogo Maestro de Productos & Matriz de Precios"
      subtitulo="Gestión centralizada de SKU, márgenes brutos y PVP regulado por canal, con simulación de sensibilidad a la demanda."
    >
      <template #badge>
        <span
          class="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-800"
        >
          <span class="live-indicator h-1.5 w-1.5 rounded-full bg-emerald-500" /> Sync omnicanal
        </span>
      </template>
      <template #acciones>
        <Btn variant="ghost" @click="exportarCsv"><Icon name="download" :size="16" /> Exportar</Btn>
        <Btn variant="ia" @click="modal = 'canales'">
          <Icon name="cog" :size="16" /> Reglas de precio por canal
        </Btn>
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
          <select
            v-model="canalSel"
            class="h-9 rounded-lg border border-amethyst-300 bg-amethyst-50 px-2 text-[12px] font-semibold text-amethyst-800"
          >
            <option v-for="c in canales" :key="c.canal" :value="c.canal">{{ c.nombre }}</option>
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

        <template #cell:costo="{ row }">{{ money(row.costo) }}</template>

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
          <div v-if="row.costo != null" class="text-[10px] text-slate-400">neto {{ money(row.costo) }}</div>
        </template>

        <template #cell:pvp_canal="{ row }">
          <span class="font-bold tabular-nums" :class="markupActual > 0 ? 'text-amethyst-700' : 'text-slate-700'">
            {{ money(pvpCanal(row)) }}
          </span>
          <div v-if="markupActual > 0" class="text-[10px] text-amethyst-500">+{{ markupActual }}%</div>
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

        <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
          <div class="flex items-center justify-between">
            <h4 class="font-display text-[11px] font-bold uppercase tracking-wider text-brand-900">
              Reglas de recargo por canal
            </h4>
            <Icon name="cog" :size="14" class="text-slate-400" />
          </div>
          <ul class="mt-2.5 space-y-1.5">
            <li
              v-for="c in canales"
              :key="c.canal"
              class="flex items-center justify-between rounded-lg bg-brand-50/60 px-2.5 py-2 text-[12px]"
            >
              <span class="flex items-center gap-2 text-slate-700">
                <span
                  class="h-2 w-2 rounded-full"
                  :class="c.canal === 'delivery_app' ? 'bg-amethyst-500' : c.canal === 'ecommerce' ? 'bg-sky-500' : 'bg-emerald-500'"
                />
                {{ c.nombre }}
              </span>
              <span class="font-bold tabular-nums" :class="Number(c.markup_pct) > 0 ? 'text-amethyst-700' : 'text-brand-900'">
                {{ Number(c.markup_pct) > 0 ? '+' : '' }}{{ Number(c.markup_pct).toFixed(1) }}%
              </span>
            </li>
          </ul>
          <p class="mt-2 text-[10px] leading-tight text-slate-500">
            Los canales digitales cubren automáticamente la comisión de pasarela y el packaging.
          </p>
        </div>
      </div>
    </div>

    <Modal v-if="modal === 'nuevo'" titulo="Nuevo producto" @cerrar="modal = null">
      <FormularioProducto @creado="trasAlta" />
    </Modal>

    <Modal
      v-if="modal === 'canales'"
      titulo="Reglas de recargo por canal"
      size="lg"
      @cerrar="modal = null"
    >
      <p class="mb-3 text-[13px] text-slate-600">
        El recargo se aplica sobre el PVP físico para calcular el precio de cada canal digital.
        El canal físico es siempre la base (0%).
      </p>
      <div class="space-y-2.5">
        <div
          v-for="c in canales"
          :key="c.canal"
          class="rounded-xl border border-brand-200 p-3"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[13px] font-bold text-slate-800">{{ c.nombre }}</p>
              <p class="text-[11px] text-slate-500">{{ c.descripcion }}</p>
            </div>
            <label class="flex items-center gap-1.5 text-[13px] font-semibold text-slate-700">
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                :value="c.markup_pct"
                :disabled="c.canal === 'fisico' || !puedeCanales"
                class="w-20 rounded-lg border border-brand-300 bg-white py-1 text-center tabular-nums disabled:bg-slate-100"
                @change="guardarCanal(c.canal, $event.target.value)"
              />
              % markup
            </label>
          </div>
        </div>
      </div>
      <p v-if="!puedeCanales" class="mt-3 text-[11px] text-slate-400">
        Solo el Jefe Comercial / de Operaciones puede editar estas reglas.
      </p>
    </Modal>

    <Modal
      v-else-if="modal && typeof modal === 'object'"
      :titulo="`Editar precio — ${modal.nombre || modal.product_id}`"
      @cerrar="modal = null"
    >
      <form class="space-y-3" @submit.prevent="guardarEdicion">
        <label class="block text-[12px] font-semibold text-slate-600">
          Costo neto
          <input
            v-model="edicion.costo"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          PVP físico (base)
          <input
            v-model="edicion.precio_base"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
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
