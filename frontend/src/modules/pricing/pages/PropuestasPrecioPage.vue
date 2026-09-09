<script setup>
/**
 * Propuestas de ajuste de precio (FR-005, FR-006). El sistema las genera cada
 * semana; ninguna se publica sin que el Jefe Comercial la apruebe aquí (SC-002).
 * Aprobar cambia `precio_base` y escribe el historial de vigencias.
 * Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'
import { useSesion } from '@/stores/sesion'
import { money } from '@/shared/currency'
import { prompt } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const puedeVer = computed(() => sesion.puedeLeerTabla('Comercial', 'propuesta_ajuste_precio'))
const puedeResolver = computed(() =>
  sesion.puedeEditarTabla('Comercial', 'propuesta_ajuste_precio'),
)

const items = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const aviso = ref('')
const trabajando = ref(null)

const pill = ref('pendiente')
const page = ref(1)
const size = ref(15)

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo completar la operación.'
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await pricingApi.propuestas({
      estado: pill.value || undefined,
      page: page.value,
      size: size.value,
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

const ESTADO = {
  pendiente: { tipo: 'fifo', txt: 'Pendiente' },
  aprobada: { tipo: 'ok', txt: 'Aprobada' },
  rechazada: { tipo: 'quiebre', txt: 'Rechazada' },
}

const pills = [
  { value: 'pendiente', label: 'Pendientes' },
  { value: 'aprobada', label: 'Aprobadas' },
  { value: 'rechazada', label: 'Rechazadas' },
  { value: '', label: 'Todas' },
]

const columnas = [
  { key: 'producto', label: 'Producto', width: '140px' },
  { key: 'actual', label: 'Precio actual', align: 'right', width: '130px' },
  { key: 'propuesto', label: 'Precio propuesto', align: 'right', width: '150px' },
  { key: 'delta', label: 'Variación', align: 'right', width: '110px' },
  { key: 'margen', label: 'Margen esperado', align: 'right', width: '140px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '120px' },
  { key: 'acciones', label: '', align: 'right', width: '170px' },
]

function delta(p) {
  const a = Number(p.precio_actual || 0)
  const b = Number(p.precio_propuesto || 0)
  if (!a) return null
  return Math.round(((b - a) / a) * 1000) / 10
}

async function aprobar(p) {
  trabajando.value = p.propuesta_id
  error.value = ''
  aviso.value = ''
  try {
    await pricingApi.aprobarPropuesta(p.propuesta_id)
    aviso.value = `Propuesta #${p.propuesta_id} aprobada: el precio base del producto ${p.product_id} se actualizó.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    trabajando.value = null
  }
}

async function rechazar(p) {
  const motivo = await prompt({
    title: `Rechazar propuesta #${p.propuesta_id}`,
    message: `Producto ${p.product_id}: ${money(p.precio_actual, { showCode: false })} → ${money(p.precio_propuesto, { showCode: false })}.`,
    label: 'Motivo del rechazo',
    placeholder: 'Ej.: el competidor bajó su precio, se mantiene el actual.',
    confirmText: 'Rechazar',
    tone: 'danger',
  })
  if (motivo === null) return
  trabajando.value = p.propuesta_id
  error.value = ''
  try {
    await pricingApi.rechazarPropuesta(p.propuesta_id, motivo)
    aviso.value = `Propuesta #${p.propuesta_id} rechazada.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    trabajando.value = null
  }
}

const kpi = computed(() => ({
  total: total.value,
  suben: items.value.filter((p) => (delta(p) ?? 0) > 0).length,
  bajan: items.value.filter((p) => (delta(p) ?? 0) < 0).length,
}))

onMounted(() => {
  if (puedeVer.value) cargar()
})
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Propuestas de precio"
      subtitulo="El motor calcula un ajuste semanal por producto a partir del margen objetivo, el factor de sensibilidad y la competencia. Ninguna se publica sin aprobación."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.total > 0 && pill === 'pendiente' ? 'fifo' : 'ok'">
          {{ pill === 'pendiente' && kpi.total > 0 ? `${kpi.total} por revisar` : 'Al día' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn variant="ghost" @click="$router.push('/pricing')">
          <Icon name="chevron" :size="14" class="rotate-90" /> Márgenes
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

    <div
      v-if="!puedeVer"
      class="satin-card grid place-items-center rounded-2xl p-12 text-center shadow-card-subtle"
    >
      <div>
        <Icon name="shield" :size="28" class="mx-auto mb-3 text-brand-300" />
        <p class="text-[14px] font-bold text-slate-800">Sin acceso a las propuestas de precio</p>
        <p class="mt-1 text-[12px] text-slate-500">
          Este listado es del Jefe Comercial y la Gerencia General.
        </p>
      </div>
    </div>

    <template v-else>
    <section class="mb-6 grid gap-4 sm:grid-cols-3">
      <KpiTile
        label="Propuestas en el filtro"
        :valor="kpi.total.toLocaleString('es-EC')"
        variant="emerald"
        :microcopy="`Estado: ${pills.find((p) => p.value === pill)?.label.toLowerCase()}`"
      />
      <KpiTile
        label="Suben de precio (esta página)"
        :valor="kpi.suben.toLocaleString('es-EC')"
        estado-tipo="ok"
        microcopy="Recuperan margen frente al objetivo"
      >
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Bajan de precio (esta página)"
        :valor="kpi.bajan.toLocaleString('es-EC')"
        estado-tipo="fifo"
        microcopy="Alinean con la competencia o la elasticidad"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      titulo="Cola de propuestas"
      :columns="columnas"
      :rows="items"
      row-key="propuesta_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="total"
      :pills="pills"
      :pill-activa="pill"
      empty-text="Sin propuestas para este filtro"
      @update:page="((page = $event), cargar())"
      @update:size="((size = $event), (page = 1), cargar())"
      @pill="((pill = $event), (page = 1), cargar())"
    >
      <template #cell:producto="{ row }">
        <span class="font-mono text-[12px] text-slate-700">#{{ row.product_id }}</span>
      </template>
      <template #cell:actual="{ row }">
        <span class="tabular-nums text-[13px] text-slate-500">{{ money(row.precio_actual, { showCode: false }) }}</span>
      </template>
      <template #cell:propuesto="{ row }">
        <span class="tabular-nums text-[13px] font-bold text-brand-900">{{ money(row.precio_propuesto, { showCode: false }) }}</span>
      </template>
      <template #cell:delta="{ row }">
        <span
          class="tabular-nums text-[12px] font-semibold"
          :class="(delta(row) ?? 0) > 0 ? 'text-emerald-700' : (delta(row) ?? 0) < 0 ? 'text-crimson-ruby' : 'text-slate-400'"
        >
          {{ delta(row) == null ? '—' : `${delta(row) > 0 ? '+' : ''}${delta(row)}%` }}
        </span>
      </template>
      <template #cell:margen="{ row }">
        <span class="tabular-nums text-[13px] text-slate-700">{{ row.margen_esperado_pct }}%</span>
      </template>
      <template #cell:estado="{ row }">
        <SemanticChip :tipo="ESTADO[row.estado]?.tipo || 'neutral'">
          {{ ESTADO[row.estado]?.txt || row.estado }}
        </SemanticChip>
      </template>
      <template #cell:acciones="{ row }">
        <div v-if="row.estado === 'pendiente' && puedeResolver" class="flex items-center justify-end gap-1">
          <Btn
            variant="primary"
            class="!px-2.5 !py-1 !text-[12px]"
            :disabled="trabajando === row.propuesta_id"
            @click="aprobar(row)"
          >
            <Icon name="check" :size="13" /> Aprobar
          </Btn>
          <Btn
            variant="danger"
            class="!px-2.5 !py-1 !text-[12px]"
            :disabled="trabajando === row.propuesta_id"
            @click="rechazar(row)"
          >
            Rechazar
          </Btn>
        </div>
        <span v-else class="text-[11px] text-slate-400">—</span>
      </template>
    </DataTable>
    </template>
  </div>
</template>
