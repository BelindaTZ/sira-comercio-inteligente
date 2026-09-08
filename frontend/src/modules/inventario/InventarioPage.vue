<script setup>
/**
 * Gestión de Inventario & Alertas FIFO (001, US2/US3). Arquetipo "Gestión" de
 * `docs/diseno-ui/.../sira_inventario_y_alertas_fifo_header_verde_abisal/`:
 * page header + fila de KPIs + barra de filtros con pills + data-grid + panels
 * de trabajo (ajuste, merma, stock máximo, verificación de anaquel) en modales.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useSesion } from '@/stores/sesion'
import { inventarioApi } from '@/services/inventarioApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import FormularioAjuste from './components/FormularioAjuste.vue'
import FormularioMerma from './components/FormularioMerma.vue'
import FormularioStockMaximo from './components/FormularioStockMaximo.vue'
import FormularioVerificacionAnaquel from './components/FormularioVerificacionAnaquel.vue'

const sesion = useSesion()
const tiendaManual = ref(null)
const tiendaId = computed(() => sesion.tiendaId ?? tiendaManual.value ?? null)
const empleadoId = computed(() => sesion.empleadoId ?? 1)

const tab = ref('lotes') // 'lotes' | 'alertas'
const busqueda = ref('')
const pill = ref('todos')
const page = ref(1)
const size = ref(25)

const rows = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const modal = ref(null) // 'ajuste' | 'merma' | 'stock-max' | 'anaquel'

// contadores para KPIs / pills
const kpi = ref({ lotes: 0, reposicion: 0, vencimiento: 0, porVencer: 0 })

const pillsLotes = computed(() => [
  { value: 'todos', label: 'Todos', count: kpi.value.lotes, tipo: 'neutral' },
  { value: 'por-vencer', label: 'Próximos a vencer', count: kpi.value.porVencer, tipo: 'fifo' },
])
const pillsAlertas = computed(() => [
  {
    value: 'todos',
    label: 'Todas',
    count: kpi.value.reposicion + kpi.value.vencimiento,
    tipo: 'neutral',
  },
  { value: 'reposicion', label: 'Reposición', count: kpi.value.reposicion, tipo: 'quiebre' },
  { value: 'vencimiento', label: 'Vencimiento', count: kpi.value.vencimiento, tipo: 'fifo' },
])

const columnasLotes = [
  { key: 'lote_id', label: 'Lote', width: '80px' },
  { key: 'product_id', label: 'Producto' },
  { key: 'codigo_lote_proveedor', label: 'Cód. proveedor' },
  { key: 'cantidad_disponible', label: 'Disponible', align: 'right' },
  { key: 'cantidad_recibida', label: 'Recibido', align: 'right' },
  { key: 'fecha_vencimiento', label: 'Vence' },
  { key: 'dias_para_vencer', label: 'Días', align: 'right' },
]
const columnasAlertas = [
  { key: 'alerta_id', label: 'Alerta', width: '80px' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'product_id', label: 'Producto' },
  { key: 'fecha_generada', label: 'Generada', formatter: (v) => new Date(v).toLocaleString() },
  { key: 'estado', label: 'Estado' },
  { key: 'acciones', label: '' },
]

async function cargarKpis() {
  if (!tiendaId.value) return
  try {
    const [lotes, rep, ven, pv] = await Promise.all([
      inventarioApi.lotes({ tiendaId: tiendaId.value, size: 1 }),
      inventarioApi.alertas({
        tiendaId: tiendaId.value,
        tipo: 'reposicion',
        estado: 'pendiente',
        size: 1,
      }),
      inventarioApi.alertas({
        tiendaId: tiendaId.value,
        tipo: 'vencimiento',
        estado: 'pendiente',
        size: 1,
      }),
      inventarioApi.lotes({ tiendaId: tiendaId.value, proximosAVencer: true, dias: 7, size: 1 }),
    ])
    kpi.value = {
      lotes: lotes.total,
      reposicion: rep.total,
      vencimiento: ven.total,
      porVencer: pv.total,
    }
  } catch {
    /* KPIs son informativos; no bloquean la tabla */
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
    const productId = /^\d+$/.test(busqueda.value.trim())
      ? Number(busqueda.value.trim())
      : undefined
    let data
    if (tab.value === 'lotes') {
      data = await inventarioApi.lotes({
        tiendaId: tiendaId.value,
        productId,
        proximosAVencer: pill.value === 'por-vencer',
        dias: 7,
        page: page.value,
        size: size.value,
      })
    } else {
      data = await inventarioApi.alertas({
        tiendaId: tiendaId.value,
        tipo: pill.value === 'todos' ? undefined : pill.value,
        estado: 'pendiente',
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

function tras() {
  modal.value = null
  return Promise.all([cargar(), cargarKpis()])
}

watch([tab, pill], () => {
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
      subtitulo="Stock por lote priorizando FEFO, alertas de reposición y vencimiento, y control físico de góndola."
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
          label="Lotes en stock"
          :valor="kpi.lotes"
          variant="emerald"
          microcopy="Inventario por lote de la tienda"
          pie-label="Cobertura"
          :pie-valor="tab === 'lotes' ? 'FEFO activo' : '—'"
        />
        <KpiTile
          label="Reposición inmediata"
          :valor="kpi.reposicion"
          :estado="kpi.reposicion ? 'crítico' : 'al día'"
          :estado-tipo="kpi.reposicion ? 'quiebre' : 'ok'"
          microcopy="Bajo stock de seguridad"
          pie-label="Origen"
          pie-valor="Job diario"
        >
          <template #icono><Icon name="alert" :size="16" /></template>
        </KpiTile>
        <KpiTile
          label="Alertas de vencimiento"
          :valor="kpi.vencimiento"
          :estado="kpi.vencimiento ? 'revisar' : 'al día'"
          :estado-tipo="kpi.vencimiento ? 'fifo' : 'ok'"
          microcopy="Pendientes de atención"
          pie-label="Origen"
          pie-valor="Job diario"
        >
          <template #icono><Icon name="clock" :size="16" /></template>
        </KpiTile>
        <KpiTile
          label="Lotes por vencer (7 d)"
          :valor="kpi.porVencer"
          :estado="kpi.porVencer ? 'ventana FEFO' : 'sin próximos'"
          :estado-tipo="kpi.porVencer ? 'fifo' : 'ok'"
          microcopy="Vencen en ≤ 7 días"
          pie-label="Acción"
          pie-valor="Rotar a góndola"
        >
          <template #icono><Icon name="cube" :size="16" /></template>
        </KpiTile>
      </section>

      <div
        class="mb-4 inline-flex items-center gap-1 rounded-xl border border-brand-200/80 bg-brand-100/60 p-1 shadow-inner"
      >
        <button
          v-for="t in [
            { v: 'lotes', l: 'Lotes en stock' },
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
        v-if="tab === 'lotes'"
        titulo="Lotes en stock"
        subtitulo="Priorizados por fecha de vencimiento más próxima (FEFO)."
        :columns="columnasLotes"
        :rows="rows"
        row-key="lote_id"
        :loading="cargando"
        :page="page"
        :size="size"
        :total="total"
        :search="busqueda"
        search-placeholder="Filtrar por id de producto…"
        :pills="pillsLotes"
        :pill-activa="pill"
        empty-text="Sin lotes para este filtro"
        @update:page="page = $event"
        @update:size="((size = $event), (page = 1))"
        @update:search="busqueda = $event"
        @pill="pill = $event"
      >
        <template #cell:fecha_vencimiento="{ value }">
          {{ value || '—' }}
        </template>
        <template #cell:dias_para_vencer="{ value }">
          <SemanticChip v-if="value != null && value <= 7" tipo="fifo">{{ value }} d</SemanticChip>
          <span v-else-if="value != null" class="tabular-nums text-on-surface-variant"
            >{{ value }} d</span
          >
          <span v-else class="text-on-surface-variant">—</span>
        </template>
        <template #cell:codigo_lote_proveedor="{ value }">{{ value || '—' }}</template>
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
        search-placeholder="Filtrar por id de producto…"
        :pills="pillsAlertas"
        :pill-activa="pill"
        empty-text="Sin alertas pendientes"
        @update:page="page = $event"
        @update:size="((size = $event), (page = 1))"
        @update:search="busqueda = $event"
        @pill="pill = $event"
      >
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
  </div>
</template>
