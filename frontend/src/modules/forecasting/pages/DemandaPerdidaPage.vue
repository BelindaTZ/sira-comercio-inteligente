<script setup>
/**
 * Auditoría y análisis de demanda perdida (Stock-Out) — feature 004 US4 (FR-014).
 * Arquetipo "Gestión" del kit. Los datos vienen de `eventos_quiebre_stock`
 * (registrados por el Encargado cuando un producto se agota antes de reponerse):
 * agregados por SKU y por categoría. Cada SKU afectado ofrece la acción concreta
 * de solicitar su reposición (abre "órdenes de compra" con el pedido casi listo).
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { forecastingApi } from '@/services/forecastingApi'
import { inventarioApi } from '@/services/inventarioApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const router = useRouter()
const tiendaId = computed(() => sesion.tiendaId ?? 1)
const puedeSolicitar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Operaciones', 'ordenes_compra'),
)

const hoy = new Date()
const mes = ref(`${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`)
const porProducto = ref([])
const porCategoria = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')
const solicitando = ref(null)

const rango = computed(() => {
  const [y, m] = mes.value.split('-').map(Number)
  const fin = new Date(y, m, 0).getDate()
  return {
    desde: `${y}-${String(m).padStart(2, '0')}-01`,
    hasta: `${y}-${String(m).padStart(2, '0')}-${fin}`,
  }
})

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo cargar el reporte.'
}

async function cargar(conAviso = false) {
  cargando.value = true
  error.value = ''
  try {
    const params = {
      fechaDesde: rango.value.desde,
      fechaHasta: rango.value.hasta,
      tiendaId: tiendaId.value,
    }
    const [prod, cat] = await Promise.all([
      forecastingApi.demandaPerdidaPorProducto(params),
      forecastingApi.demandaPerdida(params),
    ])
    porProducto.value = prod
    porCategoria.value = cat
    if (conAviso) aviso.value = `Reporte actualizado — ${prod.length} SKU con demanda perdida en el período.`
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

const kpi = computed(() => {
  const unidades = porProducto.value.reduce((a, x) => a + Number(x.demanda_estimada_no_satisfecha || 0), 0)
  const eventos = porProducto.value.reduce((a, x) => a + Number(x.cantidad_eventos || 0), 0)
  const topCat = [...porCategoria.value].sort(
    (a, b) => b.demanda_estimada_no_satisfecha - a.demanda_estimada_no_satisfecha,
  )[0]
  return {
    unidades,
    eventos,
    skus: porProducto.value.length,
    topCat: topCat ? topCat.product_category : '—',
    topCatUds: topCat ? topCat.demanda_estimada_no_satisfecha : 0,
  }
})

// ---- DataTable por SKU --------------------------------------------------
const busqueda = ref('')
const page = ref(1)
const size = ref(15)

const columnas = [
  { key: 'producto', label: 'Producto' },
  { key: 'categoria', label: 'Categoría', width: '170px' },
  { key: 'eventos', label: 'Eventos', align: 'right', width: '90px' },
  { key: 'unidades', label: 'Unidades no satisfechas', align: 'right', width: '180px' },
  { key: 'ultimo', label: 'Último evento', align: 'right', width: '130px' },
  { key: 'acciones', label: '', align: 'right', width: '170px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return q
    ? porProducto.value.filter(
        (x) =>
          (x.producto_nombre || '').toLowerCase().includes(q) ||
          String(x.product_id).includes(q) ||
          (x.product_category || '').toLowerCase().includes(q),
      )
    : porProducto.value
})
const filas = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

async function solicitarReposicion(row) {
  solicitando.value = row.product_id
  error.value = ''
  try {
    // deja la alerta de reposición y abre "órdenes de compra" con el producto cargado
    await inventarioApi
      .solicitarReposicion({
        productId: row.product_id,
        tiendaId: tiendaId.value,
        empleadoId: sesion.empleadoId,
      })
      .catch(() => {})
    router.push({ name: 'compras', query: { nuevaOrden: row.product_id } })
  } finally {
    solicitando.value = null
  }
}

onMounted(() => cargar())
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Auditoría y análisis de demanda perdida (Stock-Out)"
      subtitulo="Ventas no concretadas por quiebre de stock en sala, a partir de los eventos que el Encargado registra cuando un producto se agota antes de reponerse (FR-014)."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.eventos > 0 ? 'quiebre' : 'ok'">
          {{ kpi.eventos > 0 ? `${kpi.eventos} eventos en el período` : 'Sin quiebres registrados' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="clock" :size="14" class="text-brand-700" />
          <input v-model="mes" type="month" class="bg-transparent text-slate-800 focus:outline-none" @change="cargar()" />
        </label>
        <Btn variant="ghost" @click="cargar(true)">
          <Icon name="chart" :size="16" /> Actualizar
        </Btn>
        <Btn variant="ghost" @click="$router.push('/forecasting')">
          <Icon name="chevron" :size="14" class="rotate-90" /> Pronóstico
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
      <KpiTile
        label="Unidades no satisfechas"
        :valor="kpi.unidades.toLocaleString('es-EC')"
        variant="emerald"
        :microcopy="`${rango.desde} al ${rango.hasta}`"
        pie-label="SKU afectados"
        :pie-valor="`${kpi.skus}`"
      />
      <KpiTile
        label="Eventos de quiebre"
        :valor="kpi.eventos.toLocaleString('es-EC')"
        :estado-tipo="kpi.eventos > 0 ? 'quiebre' : 'ok'"
        microcopy="Cada evento = un producto agotado en góndola antes de reponerse"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="SKU con demanda perdida"
        :valor="kpi.skus.toLocaleString('es-EC')"
        estado-tipo="fifo"
        microcopy="Productos distintos con al menos un evento de quiebre"
      >
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Categoría más impactada"
        :valor="kpi.topCat"
        estado-tipo="neutral"
        :microcopy="`${kpi.topCatUds} unidades no satisfechas`"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      titulo="Demanda perdida por SKU"
      subtitulo="Ordenado por unidades no satisfechas. La acción deja la alerta de reposición y abre la orden de compra."
      :columns="columnas"
      :rows="filas"
      row-key="product_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Producto, categoría o ID…"
      empty-text="Sin eventos de quiebre de stock en el período seleccionado"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
    >
      <template #cell:producto="{ row }">
        <div class="flex items-center gap-2">
          <Icon name="cube" :size="15" class="shrink-0 text-slate-400" />
          <div class="leading-tight">
            <div class="text-[12px] font-semibold text-slate-800">
              {{ row.producto_nombre || `Producto ${row.product_id}` }}
            </div>
            <div class="flex items-center gap-1.5">
              <span class="font-mono text-[10px] text-slate-400">ID {{ row.product_id }}</span>
              <SemanticChip v-if="row.alta_demanda" tipo="ia">alta demanda</SemanticChip>
            </div>
          </div>
        </div>
      </template>
      <template #cell:categoria="{ row }">
        <span class="text-[12px] text-slate-600">{{ row.product_category }}</span>
      </template>
      <template #cell:eventos="{ row }">
        <span class="tabular-nums text-[13px] text-slate-700">{{ row.cantidad_eventos }}</span>
      </template>
      <template #cell:unidades="{ row }">
        <span class="tabular-nums text-[13px] font-bold text-crimson-ruby">
          {{ row.demanda_estimada_no_satisfecha }}
        </span>
      </template>
      <template #cell:ultimo="{ row }">
        <span class="tabular-nums text-[12px] text-slate-500">
          {{ (row.ultimo_evento || '').slice(0, 10) || '—' }}
        </span>
      </template>
      <template #cell:acciones="{ row }">
        <Btn
          v-if="puedeSolicitar"
          variant="primary"
          class="!px-2.5 !py-1 !text-[12px]"
          :disabled="solicitando === row.product_id"
          @click="solicitarReposicion(row)"
        >
          <Icon name="truck" :size="13" />
          {{ solicitando === row.product_id ? 'Abriendo…' : 'Solicitar reposición' }}
        </Btn>
        <span v-else class="text-[11px] text-slate-400">—</span>
      </template>
    </DataTable>

    <section v-if="porCategoria.length" class="mt-6">
      <h2 class="mb-1 font-display text-base font-bold text-brand-950">Consolidado por categoría</h2>
      <p class="mb-3 text-[12px] text-slate-600">Mismo período, agregado por familia de producto.</p>
      <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
        <table class="w-full text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[11px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-4 py-3">Categoría</th>
              <th class="px-4 py-3 text-right">Eventos</th>
              <th class="px-4 py-3 text-right">Unidades no satisfechas</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-for="c in porCategoria" :key="c.product_category" class="hover:bg-brand-50/70">
              <td class="px-4 py-2.5 font-medium text-slate-700">{{ c.product_category }}</td>
              <td class="px-4 py-2.5 text-right tabular-nums text-slate-600">{{ c.cantidad_eventos }}</td>
              <td class="px-4 py-2.5 text-right font-bold tabular-nums text-crimson-ruby">
                {{ c.demanda_estimada_no_satisfecha }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
