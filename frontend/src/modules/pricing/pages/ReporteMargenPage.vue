<script setup>
/**
 * FR-013 — reporte mensual de margen real vs. objetivo por categoría, para
 * presentar a Dirección. Reutiliza `GET /api/pricing/reportes/margen` de US1 con
 * el rango del mes elegido (Principio VIII, DRY). Arquetipo "Dashboard/BI".
 */
import { computed, onMounted, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'
import { money as moneyUsd } from '@/shared/currency'
import { opcionesExportacion } from '@/shared/exportar'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import DataTable from '@/shared/DataTable.vue'

const hoy = new Date()
const mes = ref(`${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`)
const filas = ref([])
const cargando = ref(false)
const error = ref('')
const busqueda = ref('')
const page = ref(1)
const size = ref(20)
const menuExport = ref(false)

const money = (v) => moneyUsd(v, { decimals: 0, showCode: false })
const rango = computed(() => {
  const [y, m] = mes.value.split('-').map(Number)
  const fin = new Date(y, m, 0).getDate()
  return {
    desde: `${y}-${String(m).padStart(2, '0')}-01`,
    hasta: `${y}-${String(m).padStart(2, '0')}-${fin}`,
  }
})

const delta = (f) =>
  f.margen_objetivo_pct != null && f.margen_real_pct != null
    ? Number(f.margen_real_pct) - Number(f.margen_objetivo_pct)
    : null

const kpi = computed(() => {
  const conObj = filas.value.filter((f) => delta(f) != null)
  const bajoObjetivo = conObj.filter((f) => delta(f) < 0)
  return {
    ingreso: filas.value.reduce((a, f) => a + Number(f.ingreso_total || 0), 0),
    unidades: filas.value.reduce((a, f) => a + Number(f.unidades_vendidas || 0), 0),
    categorias: filas.value.length,
    bajoObjetivo: bajoObjetivo.length,
    faltanteUds: bajoObjetivo.reduce((a, f) => a + Math.abs(delta(f)), 0),
  }
})

const columnas = [
  { key: 'categoria', label: 'Categoría' },
  { key: 'unidades', label: 'Unidades', align: 'right', width: '110px' },
  { key: 'ingreso', label: 'Ingreso', align: 'right', width: '130px' },
  { key: 'objetivo', label: 'Margen objetivo', align: 'right', width: '140px' },
  { key: 'real', label: 'Margen real', align: 'right', width: '130px' },
  { key: 'delta', label: 'Δ pp', align: 'right', width: '100px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return q
    ? filas.value.filter((f) => (f.product_category || '').toLowerCase().includes(q))
    : filas.value
})
const pagina = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

const opcionesExport = computed(() =>
  opcionesExportacion(
    `Reporte de margen — ${mes.value}`,
    `reporte_margen_${mes.value}`,
    [
      ['Categoría', 'Unidades', 'Ingreso USD', 'Margen objetivo %', 'Margen real %', 'Δ pp'],
      ...filas.value.map((f) => [
        f.product_category,
        f.unidades_vendidas,
        Number(f.ingreso_total || 0).toFixed(2),
        f.margen_objetivo_pct ?? '',
        f.margen_real_pct ?? '',
        delta(f) == null ? '' : delta(f).toFixed(2),
      ]),
    ],
  ),
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await pricingApi.reporteMargen({
      fechaDesde: rango.value.desde,
      fechaHasta: rango.value.hasta,
    })
    filas.value = data.filas
    page.value = 1
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Reporte de margen por categoría"
      subtitulo="Margen real de las ventas confirmadas del mes frente al objetivo de cada categoría (FR-013). Listo para presentar a Dirección."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.bajoObjetivo > 0 ? 'quiebre' : 'ok'">
          {{ kpi.bajoObjetivo > 0 ? `${kpi.bajoObjetivo} categorías bajo objetivo` : 'Todas en o sobre objetivo' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="clock" :size="14" class="text-brand-700" />
          <input v-model="mes" type="month" class="bg-transparent text-slate-800 focus:outline-none" @change="cargar" />
        </label>
        <div class="relative">
          <Btn variant="ghost" @click="menuExport = !menuExport">
            <Icon name="download" :size="16" /> Exportar
            <Icon name="chevron" :size="12" :class="menuExport ? '-rotate-180' : ''" />
          </Btn>
          <div
            v-if="menuExport"
            class="absolute right-0 z-20 mt-1 w-44 rounded-xl border border-brand-200 bg-white py-1 shadow-card-hover"
          >
            <button
              v-for="opt in opcionesExport"
              :key="opt.id"
              type="button"
              class="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-brand-50"
              @click="((menuExport = false), opt.fn())"
            >
              <Icon name="download" :size="13" class="text-slate-400" /> {{ opt.label }}
            </button>
          </div>
        </div>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Ingreso del mes"
        :valor="money(kpi.ingreso)"
        variant="emerald"
        :microcopy="`${kpi.categorias} categorías con venta`"
      />
      <KpiTile label="Unidades vendidas" :valor="kpi.unidades.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Categorías bajo objetivo"
        :valor="kpi.bajoObjetivo.toLocaleString('es-EC')"
        :estado-tipo="kpi.bajoObjetivo > 0 ? 'quiebre' : 'ok'"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Brecha acumulada"
        :valor="`${kpi.faltanteUds.toFixed(1)} pp`"
        estado-tipo="fifo"
        microcopy="Suma de puntos porcentuales por debajo del objetivo"
      >
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      titulo="Detalle por categoría"
      :columns="columnas"
      :rows="pagina"
      row-key="product_category"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Buscar categoría…"
      empty-text="Sin ventas confirmadas en el mes seleccionado"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
    >
      <template #cell:categoria="{ row }">
        <span class="font-semibold text-slate-800">{{ row.product_category }}</span>
      </template>
      <template #cell:unidades="{ row }">
        <span class="tabular-nums text-[13px] text-slate-600">{{ row.unidades_vendidas }}</span>
      </template>
      <template #cell:ingreso="{ row }">
        <span class="tabular-nums text-[13px] text-slate-800">{{ money(row.ingreso_total) }}</span>
      </template>
      <template #cell:objetivo="{ row }">
        <span class="tabular-nums text-[13px] text-slate-500">
          {{ row.margen_objetivo_pct == null ? '—' : `${row.margen_objetivo_pct}%` }}
        </span>
      </template>
      <template #cell:real="{ row }">
        <span class="tabular-nums text-[13px] font-bold text-slate-800">
          {{ row.margen_real_pct == null ? '—' : `${row.margen_real_pct}%` }}
        </span>
      </template>
      <template #cell:delta="{ row }">
        <SemanticChip v-if="delta(row) != null" :tipo="delta(row) < 0 ? 'quiebre' : 'ok'">
          {{ delta(row) > 0 ? '+' : '' }}{{ delta(row).toFixed(1) }}
        </SemanticChip>
        <span v-else class="text-[12px] text-slate-400">—</span>
      </template>
    </DataTable>
  </div>
</template>
