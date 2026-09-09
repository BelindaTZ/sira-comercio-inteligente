<script setup>
/**
 * Gestión y Mitigación de Riesgo de Fuga (churn) — feature 002 US3.
 * Estructura de `docs/diseno-ui/.../sira_gesti_n_y_mitigaci_n_de_riesgo_de_fuga_de_clientes/`:
 * 3 KPI de diagnóstico, cohorte enriquecida (LTV, frecuencia, sucursal, nivel)
 * y acción de retención (crear campaña de reactivación con el segmento). El
 * backend calcula el ciclo individual y la severidad (SC-005, FR-011).
 */
import { computed, onMounted, ref, watch } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import FormularioCampana from './components/FormularioCampana.vue'

const sesion = useSesion()
const puedeVer = computed(() => sesion.puedeLeerTabla('Marketing_CRM', 'churn_score'))

const severidad = ref('') // '' | 'en_riesgo' | 'inactivo'
const page = ref(1)
const size = ref(25)
const rows = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const modal = ref(null) // 'export' | 'campana'
const descargando = ref('')

const kpi = ref({
  clientes_riesgo: 0,
  prob_abandono_media: null,
  ltv_en_riesgo: 0,
  categorias_afectadas: [],
})

const money = (v) => `$${Math.round(Number(v || 0)).toLocaleString('es-CL')}`

const pills = computed(() => [
  { value: '', label: 'Toda la cohorte', count: kpi.value.clientes_riesgo },
  { value: 'en_riesgo', label: 'En riesgo', tipo: 'fifo' },
  { value: 'inactivo', label: 'Inactivo', tipo: 'quiebre' },
])

const columnas = [
  { key: 'cliente', label: 'Cliente & RUT' },
  { key: 'visita', label: 'Última visita • frecuencia', width: '170px' },
  { key: 'ltv', label: 'LTV histórico', align: 'right', width: '128px' },
  { key: 'causal', label: 'Causal probable' },
  { key: 'riesgo', label: 'Nivel de riesgo', align: 'center', width: '132px' },
]

function causal(r) {
  const d = r.dias_desde_ultima_compra
  const c = r.ciclo_compra_dias
  if (d == null || c == null) return 'Sin patrón de compra establecido'
  if (d > 3 * c) return `Quiebre severo del ciclo — ${d} d sin compra (habitual ${c} d)`
  return `Desaceleración del ciclo — ${d} d vs. ${c} d habitual`
}

async function cargarKpis() {
  try {
    kpi.value = await clientesApi.riesgoFugaResumen(severidad.value)
  } catch {
    /* informativo */
  }
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await clientesApi.riesgoFugaDirectorio({
      severidad: severidad.value || undefined,
      page: page.value,
      size: size.value,
    })
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

async function descargar(formato) {
  descargando.value = formato
  try {
    const blob = await clientesApi.exportarRiesgoFuga(formato, severidad.value)
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `riesgo-fuga.${formato}`
    a.click()
    URL.revokeObjectURL(a.href)
    modal.value = null
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    descargando.value = ''
  }
}

const segmentoSugerido = computed(() =>
  severidad.value === 'inactivo'
    ? 'riesgo_alto_general'
    : severidad.value === 'en_riesgo'
      ? 'en_riesgo_reciente'
      : 'tier_alto_desaceleracion',
)

function trasCampana() {
  modal.value = null
}

watch(severidad, () => {
  if (!puedeVer.value) return
  page.value = 1
  cargar()
  cargarKpis()
})
watch([page, size], () => puedeVer.value && cargar())
onMounted(() => {
  if (!puedeVer.value) return
  cargar()
  cargarKpis()
})
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Gestión y Mitigación de Riesgo de Fuga"
      subtitulo="Cohortes de clientes en riesgo de abandono, quiebre del ciclo de compra y plan de retención personalizado."
    >
      <template #badge>
        <SemanticChip tipo="ia">Algoritmo predictivo</SemanticChip>
      </template>
      <template #acciones>
        <RouterLink
          to="/clientes"
          class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50/70"
        >
          <Icon name="users" :size="16" /> Directorio
        </RouterLink>
        <Btn variant="ghost" @click="modal = 'export'"><Icon name="download" :size="16" /> Exportar lista</Btn>
        <Btn variant="primary" @click="modal = 'campana'">
          <Icon name="bolt" :size="16" /> Ejecutar estrategia de retención
        </Btn>
      </template>
    </PageHeader>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <KpiTile
        label="Clientes en riesgo crítico"
        :valor="kpi.clientes_riesgo.toLocaleString('es-CL')"
        variant="emerald"
        :microcopy="`Probabilidad media de abandono ${kpi.prob_abandono_media != null ? kpi.prob_abandono_media.toFixed(0) : '—'}%`"
        pie-label="Ventana"
        pie-valor="Severidad relativa al ciclo propio"
      />
      <KpiTile
        label="LTV en riesgo directo"
        :valor="money(kpi.ltv_en_riesgo)"
        estado="exposición alta"
        estado-tipo="quiebre"
        microcopy="Gasto histórico ponderado en peligro de pérdida"
      >
        <template #icono><Icon name="bank" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Categorías más afectadas"
        :valor="kpi.categorias_afectadas[0] || '—'"
        variant="ia"
        :microcopy="kpi.categorias_afectadas.slice(1).join(' · ') || 'Sin datos suficientes'"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
    </section>

    <div
      v-if="!puedeVer"
      class="satin-card grid place-items-center rounded-2xl p-12 text-center shadow-card-subtle"
    >
      <div class="max-w-sm">
        <Icon name="shield" :size="28" class="mx-auto mb-3 text-brand-300" />
        <p class="text-[14px] font-bold text-slate-800">Sección exclusiva del Jefe de Marketing</p>
        <p class="mt-1 text-[12px] text-slate-500">
          El análisis de riesgo de fuga y el plan de retención los gestiona el equipo de
          Marketing / CRM (feature 002, US3).
        </p>
        <RouterLink
          to="/clientes"
          class="mt-4 inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
        >
          <Icon name="users" :size="15" /> Volver al directorio
        </RouterLink>
      </div>
    </div>

    <template v-else>
      <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
        {{ error }}
      </p>

      <DataTable
      titulo="Cohorte en observación algorítmica"
      subtitulo="Ordenada por probabilidad de abandono. El causal se deriva del quiebre del ciclo de compra."
      :columns="columnas"
      :rows="rows"
      row-key="household_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="total"
      :pills="pills"
      :pill-activa="severidad"
      empty-text="Sin clientes en esta severidad"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @pill="severidad = $event"
    >
      <template #cell:cliente="{ row }">
        <div class="flex items-center gap-2.5">
          <span
            class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-100 font-display text-[11px] font-bold text-brand-800"
          >
            {{ (row.nombre || '?').split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase() }}
          </span>
          <div class="min-w-0">
            <div class="truncate text-[12px] font-semibold text-slate-800">
              {{ row.nombre || `Cliente ${row.household_id}` }}
            </div>
            <div class="flex items-center gap-1.5 text-[10px] text-slate-500">
              <span v-if="row.nivel_nombre" class="rounded bg-slate-100 px-1 py-0.5 font-medium text-slate-600">
                {{ row.nivel_nombre }}
              </span>
              <span class="truncate font-mono">{{ row.documento_identidad || '—' }}</span>
              <span v-if="row.sucursal">· {{ row.sucursal }}</span>
            </div>
          </div>
        </div>
      </template>

      <template #cell:visita="{ row }">
        <div
          class="text-[12px] font-semibold"
          :class="row.severidad === 'inactivo' ? 'text-crimson-ruby' : 'text-amber-700'"
        >
          <Icon name="clock" :size="12" class="mr-1 inline" />
          {{ row.dias_desde_ultima_compra != null ? `Hace ${row.dias_desde_ultima_compra} d` : '—' }}
        </div>
        <div class="text-[10px] text-slate-500">
          {{ Number(row.frecuencia_sem).toFixed(1) }} vis/sem habitual
        </div>
      </template>

      <template #cell:ltv="{ row }">
        <span class="font-bold tabular-nums text-slate-900">{{ money(row.ltv) }}</span>
      </template>

      <template #cell:causal="{ row }">
        <span class="text-[11px] text-slate-600">{{ causal(row) }}</span>
      </template>

      <template #cell:riesgo="{ row }">
        <SemanticChip :tipo="row.severidad === 'inactivo' ? 'quiebre' : 'fifo'">
          {{ row.severidad === 'inactivo' ? 'Alto' : 'Medio' }} {{ Math.round(Number(row.score) * 100) }}%
        </SemanticChip>
      </template>
    </DataTable>

    <Modal v-if="modal === 'export'" titulo="Exportar cohorte de riesgo" @cerrar="modal = null">
      <p class="mb-3 text-[13px] text-slate-600">
        Lista de la severidad seleccionada (hasta 5.000 filas), lista para el Call Center.
      </p>
      <div class="grid grid-cols-3 gap-2.5">
        <button
          v-for="f in [
            { v: 'csv', t: 'CSV', d: 'Texto plano', icon: 'filter' },
            { v: 'xlsx', t: 'Excel', d: '.xlsx con formato', icon: 'chart' },
            { v: 'pdf', t: 'PDF', d: 'Para imprimir', icon: 'image' },
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
        v-if="modal === 'campana'"
        size="lg"
        titulo="Ejecutar estrategia de retención"
        @cerrar="modal = null"
      >
        <FormularioCampana :segmento-inicial="segmentoSugerido" @creada="trasCampana" />
      </Modal>
    </template>
  </div>
</template>
