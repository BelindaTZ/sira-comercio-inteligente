<script setup>
/**
 * Gestión de Inventario & Alertas FIFO (001, US2/US3). Arquetipo "Gestión" de
 * `docs/diseno-ui/.../sira_inventario_y_alertas_fifo_header_verde_abisal/`:
 * page header + fila de KPIs + panel con buscador + pills + data-grid.
 *
 * Pestaña "Stock por SKU" → `GET /inventario/stock` (una fila por producto con
 * ubicación en sala, stock vs. mínimo, lote más urgente y estado derivado).
 * Pestaña "Alertas" → `GET /inventario/alertas`.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useSesion } from '@/stores/sesion'
import { inventarioApi } from '@/services/inventarioApi'
import { catalogoApi } from '@/services/catalogoApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import CategoriaPicker from '@/shared/ui/CategoriaPicker.vue'
import FormularioAjuste from './components/FormularioAjuste.vue'
import FormularioMerma from './components/FormularioMerma.vue'
import FormularioStockMaximo from './components/FormularioStockMaximo.vue'
import FormularioVerificacionAnaquel from './components/FormularioVerificacionAnaquel.vue'
import FormularioUbicacion from './components/FormularioUbicacion.vue'

const sesion = useSesion()
const tiendaManual = ref(null)
const tiendaId = computed(() => sesion.tiendaId ?? tiendaManual.value ?? null)
const empleadoId = computed(() => sesion.empleadoId ?? 1)
const puedeEditar = computed(() => sesion.puedeEditarTabla('Operaciones', 'ubicacion_producto'))

const tab = ref('stock') // 'stock' | 'alertas'
const busqueda = ref('')
const categoria = ref('')
const pill = ref('todos')
const page = ref(1)
const size = ref(25)

const rows = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const modal = ref(null) // 'ajuste' | 'merma' | 'stock-max' | 'anaquel' | fila-de-ubicacion

const kpi = ref({ skus: 0, quiebre: 0, porVencer: 0, sobreStock: 0 })

const pillsStock = computed(() => [
  { value: 'todos', label: 'Todos', count: kpi.value.skus },
  { value: 'quiebre', label: 'Quiebre de stock', count: kpi.value.quiebre },
  { value: 'por_vencer', label: 'Próximos a vencer FIFO', count: kpi.value.porVencer },
  { value: 'sobre_stock', label: 'Sobre stock', count: kpi.value.sobreStock },
  { value: 'normal', label: 'Stock normal' },
])
const pillsAlertas = computed(() => [
  { value: 'todos', label: 'Todas', count: kpi.value.quiebre + kpi.value.porVencer },
  { value: 'reposicion', label: 'Reposición', count: kpi.value.quiebre },
  { value: 'vencimiento', label: 'Vencimiento', count: kpi.value.porVencer },
])

const columnasStock = [
  { key: 'producto', label: 'Producto' },
  { key: 'product_category', label: 'Categoría' },
  { key: 'ubicacion', label: 'Ubicación' },
  { key: 'stock', label: 'Stock físico vs. mín', align: 'center' },
  { key: 'lote', label: 'Lote & vencimiento FIFO' },
  { key: 'precio', label: 'Costo / PVP (Mg %)', align: 'right' },
  { key: 'estado', label: 'Estado', align: 'center' },
  { key: 'acciones', label: '', align: 'right' },
]
const columnasAlertas = [
  { key: 'alerta_id', label: 'Alerta', width: '72px' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'producto', label: 'Producto' },
  { key: 'fecha_generada', label: 'Generada', formatter: (v) => new Date(v).toLocaleString() },
  { key: 'estado', label: 'Estado' },
  { key: 'acciones', label: '' },
]

const money = (v) => (v == null ? '—' : `$${Math.round(Number(v)).toLocaleString('es-CL')}`)

async function cargarKpis() {
  if (!tiendaId.value) return
  try {
    const q = { tiendaId: tiendaId.value, size: 1 }
    const [t, quiebre, pv, sobre] = await Promise.all([
      inventarioApi.stock(q),
      inventarioApi.stock({ ...q, estado: 'quiebre' }),
      inventarioApi.stock({ ...q, estado: 'por_vencer' }),
      inventarioApi.stock({ ...q, estado: 'sobre_stock' }),
    ])
    kpi.value = {
      skus: t.total,
      quiebre: quiebre.total,
      porVencer: pv.total,
      sobreStock: sobre.total,
    }
  } catch {
    /* KPIs informativos; no bloquean la tabla */
  }
}

async function cargar() {
  if (!tiendaId.value) {
    rows.value = []
    total.value = 0
    return
  }
  cargando.value = true
  error.value = ''
  try {
    const search = busqueda.value.trim() || undefined
    let data
    if (tab.value === 'stock') {
      data = await inventarioApi.stock({
        tiendaId: tiendaId.value,
        search,
        categoria: categoria.value || undefined,
        estado: pill.value === 'todos' ? undefined : pill.value,
        page: page.value,
        size: size.value,
      })
    } else {
      data = await inventarioApi.alertas({
        tiendaId: tiendaId.value,
        tipo: pill.value === 'todos' ? undefined : pill.value,
        estado: 'pendiente',
        search,
        page: page.value,
        size: size.value,
      })
    }
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function atender(alerta) {
  try {
    await inventarioApi.atenderAlerta(alerta.alerta_id, empleadoId.value)
    await Promise.all([cargar(), cargarKpis()])
  } catch (e) {
    error.value = e.message
  }
}

async function buscarImagen(row) {
  try {
    const p = await catalogoApi.imagenAuto(row.product_id)
    row.imagen_url = p.imagen_url
  } catch (e) {
    error.value = e.message
  }
}

function tras() {
  modal.value = null
  return Promise.all([cargar(), cargarKpis()])
}

watch(tab, () => {
  pill.value = 'todos'
  page.value = 1
  cargar()
})
watch([pill, categoria], () => {
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
watch(tiendaId, () => {
  cargar()
  cargarKpis()
})
onMounted(() => {
  cargar()
  cargarKpis()
})
</script>

<template>
  <div class="mx-auto max-w-[1720px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Gestión de Inventario & Alertas FIFO"
      subtitulo="Stock por SKU con ubicación en sala, rotación FEFO y control de vencimientos y merma."
    >
      <template #acciones>
        <Btn variant="primary" @click="modal = 'ajuste'">
          <Icon name="plus" :size="17" /> Ajuste de conteo
        </Btn>
        <Btn variant="ghost" @click="modal = 'anaquel'">Verificar anaquel</Btn>
        <Btn variant="ghost" @click="modal = 'stock-max'">Stock máx.</Btn>
        <Btn variant="danger" @click="modal = 'merma'">
          <Icon name="alert" :size="17" /> Declarar merma
        </Btn>
      </template>
    </PageHeader>

    <p
      v-if="!tiendaId"
      class="mb-6 flex flex-wrap items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-lowest p-4 text-sm text-on-surface-variant"
    >
      Tu cuenta no tiene tienda asignada. Indicá una para consultar su inventario:
      <input
        v-model.number="tiendaManual"
        type="number"
        placeholder="id de tienda"
        class="w-32 rounded-md border border-outline-variant bg-white px-2 py-1 text-sm text-on-surface"
      />
    </p>

    <template v-else>
      <section class="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="SKUs en catálogo activo"
          :valor="kpi.skus"
          variant="emerald"
          microcopy="Productos con stock en esta tienda"
          pie-label="Rotación"
          pie-valor="FEFO activo"
        />
        <KpiTile
          label="Reposición inmediata"
          :valor="kpi.quiebre"
          :estado="kpi.quiebre ? 'crítico' : 'al día'"
          :estado-tipo="kpi.quiebre ? 'quiebre' : 'ok'"
          microcopy="Disponible ≤ stock de seguridad"
        >
          <template #icono><Icon name="alert" :size="16" /></template>
        </KpiTile>
        <KpiTile
          label="Vencimiento FIFO < 7 d"
          :valor="kpi.porVencer"
          :estado="kpi.porVencer ? 'revisar' : 'al día'"
          :estado-tipo="kpi.porVencer ? 'fifo' : 'ok'"
          microcopy="Lote más próximo a vencer"
        >
          <template #icono><Icon name="clock" :size="16" /></template>
        </KpiTile>
        <KpiTile
          label="Sobre stock"
          :valor="kpi.sobreStock"
          :estado="kpi.sobreStock ? 'exceso' : 'ok'"
          :estado-tipo="kpi.sobreStock ? 'fifo' : 'ok'"
          microcopy="Disponible > máximo de categoría"
        >
          <template #icono><Icon name="cube" :size="16" /></template>
        </KpiTile>
      </section>

      <div
        class="mb-4 inline-flex items-center gap-1 rounded-xl border border-brand-200/80 bg-brand-100/60 p-1 shadow-inner"
      >
        <button
          v-for="t in [
            { v: 'stock', l: 'Stock por SKU' },
            { v: 'alertas', l: 'Alertas pendientes' },
          ]"
          :key="t.v"
          type="button"
          class="rounded-lg px-3 py-1.5 text-[12px] font-semibold transition-all"
          :class="
            tab === t.v
              ? 'border border-brand-900 bg-brand-800 text-white shadow-xs'
              : 'text-slate-600 hover:bg-white/60 hover:text-brand-900'
          "
          @click="tab = t.v"
        >
          {{ t.l }}
        </button>
      </div>

      <p
        v-if="error"
        class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
      >
        {{ error }}
      </p>

      <DataTable
        v-if="tab === 'stock'"
        titulo="Stock por SKU"
        subtitulo="Una fila por producto: ubicación en sala, stock vs. mínimo y lote más próximo a vencer."
        :columns="columnasStock"
        :rows="rows"
        row-key="product_id"
        :loading="cargando"
        :page="page"
        :size="size"
        :total="total"
        :search="busqueda"
        search-placeholder="Buscar por nombre o ID de producto…"
        :pills="pillsStock"
        :pill-activa="pill"
        empty-text="Sin productos para este filtro"
        @update:page="page = $event"
        @update:size="((size = $event), (page = 1))"
        @update:search="busqueda = $event"
        @pill="pill = $event"
      >
        <template #acciones-cabecera>
          <div class="w-56">
            <CategoriaPicker v-model="categoria" label="" placeholder="Todas las categorías" />
          </div>
        </template>

        <template #cell:producto="{ row }">
          <div class="flex items-center gap-3">
            <img
              v-if="row.imagen_url && row.imagen_url.startsWith('http')"
              :src="row.imagen_url"
              alt=""
              class="h-10 w-10 shrink-0 rounded-xl border border-brand-200 object-cover"
            />
            <span
              v-else
              class="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-brand-200 bg-brand-50 text-brand-400"
            >
              <Icon name="image" :size="18" />
            </span>
            <div class="min-w-0">
              <div class="truncate font-semibold text-slate-900">
                {{ row.nombre || 'Producto sin nombre' }}
              </div>
              <div class="text-[11px] text-slate-500">
                {{ row.marca || '—' }}
                <span v-if="row.codigo_barras" class="tabular-nums">
                  · EAN {{ row.codigo_barras }}</span
                >
              </div>
            </div>
          </div>
        </template>

        <template #cell:product_category="{ value }">
          <span
            v-if="value"
            class="rounded-md border border-brand-200 bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-900"
            >{{ value }}</span
          >
          <span v-else class="text-slate-400">—</span>
        </template>

        <template #cell:ubicacion="{ row }">
          <button
            v-if="puedeEditar"
            type="button"
            class="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border px-2 py-1 text-[11px] font-semibold transition"
            :class="
              row.pasillo
                ? 'border-brand-200 bg-white text-slate-700 hover:border-brand-400'
                : 'border-dashed border-brand-300 text-brand-600 hover:bg-brand-50'
            "
            @click.stop="modal = row"
          >
            <Icon name="pin" :size="13" />
            <span v-if="row.pasillo"
              >{{ row.pasillo
              }}<span v-if="row.gondola" class="text-slate-400"> · {{ row.gondola }}</span></span
            >
            <span v-else>Ubicar</span>
          </button>
          <span v-else class="text-[12px] text-slate-600">
            <template v-if="row.pasillo"
              >{{ row.pasillo }}<span v-if="row.gondola"> · {{ row.gondola }}</span></template
            >
            <template v-else>—</template>
          </span>
        </template>

        <template #cell:stock="{ row }">
          <div class="mx-auto flex w-40 flex-col gap-1">
            <div class="flex items-center justify-between text-[11px]">
              <span
                class="font-bold"
                :class="
                  row.cantidad_disponible <= row.cantidad_minima
                    ? 'text-crimson-ruby'
                    : 'text-slate-800'
                "
                >{{ row.cantidad_disponible }} un.</span
              >
              <span class="text-slate-400">mín {{ row.cantidad_minima }}</span>
            </div>
            <div class="h-1.5 w-full overflow-hidden rounded-full bg-brand-100">
              <div
                class="h-full rounded-full"
                :class="
                  row.cantidad_disponible <= row.cantidad_minima
                    ? 'bg-crimson-ruby'
                    : row.estado === 'sobre_stock'
                      ? 'bg-damask-amber'
                      : 'bg-emerald-500'
                "
                :style="{
                  width:
                    Math.min(
                      100,
                      Math.round((row.cantidad_disponible / Math.max(1, row.cantidad_minima)) * 50)
                    ) + '%',
                }"
              />
            </div>
          </div>
        </template>

        <template #cell:lote="{ row }">
          <div v-if="row.lote_urgente" class="flex flex-col gap-1">
            <span class="font-mono text-[11px] text-slate-700">{{ row.lote_urgente }}</span>
            <span class="text-[11px]">
              <SemanticChip
                v-if="row.dias_para_vencer != null && row.dias_para_vencer < 0"
                tipo="quiebre"
                >Vencido</SemanticChip
              >
              <SemanticChip
                v-else-if="row.dias_para_vencer != null && row.dias_para_vencer <= 7"
                tipo="fifo"
                >Vence en {{ row.dias_para_vencer }} d</SemanticChip
              >
              <span v-else-if="row.fecha_vencimiento" class="text-slate-500"
                >Cad. {{ new Date(row.fecha_vencimiento).toLocaleDateString('es-CL') }}</span
              >
              <span v-else class="text-slate-400">No perecedero</span>
            </span>
          </div>
          <span v-else class="text-slate-400">Sin lote</span>
        </template>

        <template #cell:precio="{ row }">
          <div class="font-bold text-slate-900">
            {{ money(row.costo) }} / {{ money(row.precio_base) }}
          </div>
          <div class="text-[11px] font-semibold text-emerald-700">
            Mg {{ row.margen_pct != null ? row.margen_pct + '%' : '—' }}
          </div>
        </template>

        <template #cell:estado="{ value }">
          <SemanticChip
            :tipo="
              value === 'quiebre'
                ? 'quiebre'
                : value === 'por_vencer'
                  ? 'fifo'
                  : value === 'sobre_stock'
                    ? 'fifo'
                    : 'ok'
            "
          >
            {{
              {
                quiebre: 'Quiebre crítico',
                por_vencer: 'Próximo a vencer',
                sobre_stock: 'Sobre stock',
                normal: 'Suficiente',
              }[value]
            }}
          </SemanticChip>
        </template>

        <template #cell:acciones="{ row }">
          <button
            v-if="puedeEditar && !(row.imagen_url && row.imagen_url.startsWith('http'))"
            type="button"
            title="Buscar imagen genérica"
            class="rounded-lg border border-brand-200 p-1.5 text-brand-600 hover:bg-brand-50"
            @click.stop="buscarImagen(row)"
          >
            <Icon name="image" :size="15" />
          </button>
        </template>
      </DataTable>

      <DataTable
        v-else
        titulo="Alertas pendientes"
        subtitulo="Reposición y vencimiento generadas por los jobs diarios."
        :columns="columnasAlertas"
        :rows="rows"
        row-key="alerta_id"
        :loading="cargando"
        :page="page"
        :size="size"
        :total="total"
        :search="busqueda"
        search-placeholder="Buscar por nombre o ID de producto…"
        :pills="pillsAlertas"
        :pill-activa="pill"
        empty-text="Sin alertas pendientes"
        @update:page="page = $event"
        @update:size="((size = $event), (page = 1))"
        @update:search="busqueda = $event"
        @pill="pill = $event"
      >
        <template #cell:producto="{ row }">
          <div class="font-medium text-slate-900">
            {{ row.producto_nombre || 'Producto sin nombre' }}
          </div>
          <div class="text-[11px] text-slate-500 tabular-nums">ID {{ row.product_id }}</div>
        </template>
        <template #cell:tipo="{ value }">
          <SemanticChip :tipo="value === 'reposicion' ? 'quiebre' : 'fifo'">
            {{ value }}
          </SemanticChip>
        </template>
        <template #cell:estado="{ value }">
          <SemanticChip :tipo="value === 'pendiente' ? 'neutral' : 'ok'">{{ value }}</SemanticChip>
        </template>
        <template #cell:acciones="{ row }">
          <button
            v-if="row.estado === 'pendiente'"
            type="button"
            class="rounded-md border border-primary/30 px-2.5 py-1 text-[12px] font-semibold text-primary hover:bg-primary/5"
            @click.stop="atender(row)"
          >
            Atender
          </button>
        </template>
      </DataTable>
    </template>

    <Modal v-if="modal === 'ajuste'" titulo="Ajuste de conteo físico" @cerrar="modal = null">
      <FormularioAjuste :tienda-id="tiendaId" :empleado-id="empleadoId" @ajustado="tras" />
    </Modal>
    <Modal v-if="modal === 'merma'" titulo="Declarar merma" @cerrar="modal = null">
      <FormularioMerma :tienda-id="tiendaId" :empleado-id="empleadoId" @registrada="tras" />
    </Modal>
    <Modal v-if="modal === 'stock-max'" titulo="Stock máximo por categoría" @cerrar="modal = null">
      <FormularioStockMaximo :tienda-id="tiendaId" :empleado-id="empleadoId" @definido="tras" />
    </Modal>
    <Modal v-if="modal === 'anaquel'" titulo="Verificación de anaquel" @cerrar="modal = null">
      <FormularioVerificacionAnaquel
        :tienda-id="tiendaId"
        :empleado-id="empleadoId"
        @registrada="tras"
      />
    </Modal>
    <Modal
      v-if="modal && typeof modal === 'object'"
      titulo="Ubicación en sala"
      @cerrar="modal = null"
    >
      <FormularioUbicacion
        :producto="modal"
        :tienda-id="tiendaId"
        :empleado-id="empleadoId"
        @guardada="tras"
      />
    </Modal>
  </div>
</template>
