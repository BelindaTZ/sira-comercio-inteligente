<script setup>
/**
 * Márgenes objetivo por categoría (FR-001) + regla de ajuste (FR-004) y el
 * listado consolidado de descuentos bajo el margen mínimo (FR-011/FR-012).
 * Arquetipo "Gestión" del kit ya implementado. Toda la regla vive en el backend.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'
import { useSesion } from '@/stores/sesion'
import { money } from '@/shared/currency'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
// El Encargado sólo tiene la lectura de `revision_margen_bajo`; los márgenes
// objetivo y su regla son de Jefe Comercial / Gerencia.
const puedeVerMargenes = computed(() => sesion.puedeLeerTabla('Comercial', 'margenes_objetivo'))
const puedeVerBajoMargen = computed(() =>
  sesion.puedeLeerTabla('Comercial', 'revision_margen_bajo'),
)
const puedeEditarRegla = computed(() => sesion.puedeEditarTabla('Comercial', 'margenes_objetivo'))
const puedeRevisar = computed(() => sesion.puedeEditarTabla('Comercial', 'revision_margen_bajo'))

const margenes = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo completar la operación.'
}

async function cargarMargenes() {
  cargando.value = true
  error.value = ''
  try {
    margenes.value = await pricingApi.margenes()
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

const kpi = computed(() => {
  const m = margenes.value
  const conRegla = m.filter((x) => x.factor_sensibilidad != null).length
  const prom = m.length
    ? Math.round(m.reduce((a, x) => a + Number(x.margen_objetivo_pct || 0), 0) / m.length)
    : null
  return { categorias: m.length, conRegla, prom }
})

// ---- márgenes objetivo (DataTable) ----------------------------------------
const busqueda = ref('')
const page = ref(1)
const size = ref(15)

const columnas = [
  { key: 'categoria', label: 'Categoría' },
  { key: 'objetivo', label: 'Margen objetivo', align: 'right', width: '150px' },
  { key: 'factor', label: 'Factor de sensibilidad', align: 'right', width: '180px' },
  { key: 'acciones', label: '', align: 'right', width: '110px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return q
    ? margenes.value.filter((m) => (m.product_category || '').toLowerCase().includes(q))
    : margenes.value
})
const filas = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

// ---- modal: editar regla ------------------------------------------------
const modal = ref(null)
const form = reactive({ margenObjetivoPct: '', factorSensibilidad: '' })
const guardando = ref(false)

function abrirEdicion(m) {
  modal.value = m
  form.margenObjetivoPct = m.margen_objetivo_pct ?? ''
  form.factorSensibilidad = m.factor_sensibilidad ?? ''
  error.value = ''
}

async function guardarRegla() {
  guardando.value = true
  error.value = ''
  try {
    await pricingApi.actualizarMargen(modal.value.product_category, {
      margenObjetivoPct: form.margenObjetivoPct === '' ? undefined : form.margenObjetivoPct,
      factorSensibilidad: form.factorSensibilidad === '' ? undefined : form.factorSensibilidad,
    })
    modal.value = null
    aviso.value = 'Regla de ajuste actualizada. El motor la usará en el próximo cálculo semanal.'
    await cargarMargenes()
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardando.value = false
  }
}

// ---- descuentos bajo margen (FR-011/FR-012) -----------------------------
const bajoMargen = ref([])
const bajoTotal = ref(0)
const bajoRevisado = ref(false)
const bajoCargando = ref(false)
const borrador = reactive({})

async function cargarBajoMargen() {
  bajoCargando.value = true
  try {
    const data = await pricingApi.margenBajo({
      tiendaId: sesion.tiendaId ?? undefined,
      revisado: bajoRevisado.value,
    })
    bajoMargen.value = data.items
    bajoTotal.value = data.total
  } catch (e) {
    error.value = msg(e)
  } finally {
    bajoCargando.value = false
  }
}

async function registrarRevision(it) {
  const texto = (borrador[it.venta_detalle_id] || '').trim()
  if (!texto) return
  try {
    await pricingApi.registrarRevision(it.venta_detalle_id, texto)
    delete borrador[it.venta_detalle_id]
    aviso.value = `Revisión registrada para la línea #${it.venta_detalle_id}.`
    await cargarBajoMargen()
  } catch (e) {
    error.value = msg(e)
  }
}

const colsBajo = [
  { key: 'ref', label: 'Venta / línea', width: '130px' },
  { key: 'producto', label: 'Producto' },
  { key: 'aplicado', label: 'P. aplicado', align: 'right', width: '120px' },
  { key: 'margen', label: 'Margen real', align: 'right', width: '110px' },
  { key: 'motivo', label: 'Motivo del descuento' },
  { key: 'accion', label: 'Acción correctiva' },
]

onMounted(() => {
  if (puedeVerMargenes.value) cargarMargenes()
  if (puedeVerBajoMargen.value) cargarBajoMargen()
})
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Márgenes y pricing"
      subtitulo="Margen objetivo y factor de sensibilidad por categoría (insumo del motor de propuestas semanales) y seguimiento de los descuentos que quedaron bajo el mínimo."
    >
      <template v-if="puedeVerMargenes" #acciones>
        <Btn variant="ghost" @click="$router.push('/pricing/propuestas')">
          <Icon name="tag" :size="16" /> Propuestas de precio
        </Btn>
        <Btn variant="ghost" @click="$router.push('/pricing/reporte')">
          <Icon name="chart" :size="16" /> Reporte de margen
        </Btn>
        <Btn variant="ghost" @click="$router.push('/pricing/competencia')">
          <Icon name="megaphone" :size="16" /> Competencia
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

    <section v-if="puedeVerMargenes" class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Categorías con margen objetivo"
        :valor="kpi.categorias.toLocaleString('es-EC')"
        variant="emerald"
        :microcopy="`${kpi.conRegla} con regla de ajuste activa`"
        pie-label="Margen objetivo promedio"
        :pie-valor="kpi.prom != null ? `${kpi.prom}%` : '—'"
      />
      <KpiTile
        label="Regla de ajuste activa"
        :valor="kpi.conRegla.toLocaleString('es-EC')"
        estado-tipo="neutral"
        microcopy="Categorías con factor de sensibilidad definido (el motor las incluye)"
      >
        <template #icono><Icon name="cog" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Descuentos bajo margen"
        :valor="bajoTotal.toLocaleString('es-EC')"
        :estado-tipo="bajoTotal > 0 ? 'quiebre' : 'ok'"
        :microcopy="bajoRevisado ? 'Ya revisados' : 'Pendientes de acción correctiva'"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Margen objetivo promedio"
        :valor="kpi.prom != null ? `${kpi.prom}%` : null"
        estado-tipo="neutral"
        microcopy="Media simple de todas las categorías configuradas"
      >
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      v-if="puedeVerMargenes"
      titulo="Márgenes objetivo por categoría"
      subtitulo="El factor de sensibilidad (0–1) es la elasticidad con la que el motor calcula las propuestas; sin él, la categoría no genera propuestas."
      :columns="columnas"
      :rows="filas"
      row-key="product_category"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Categoría…"
      empty-text="Sin categorías con margen objetivo definido"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
    >
      <template #cell:categoria="{ row }">
        <span class="text-[13px] font-semibold text-slate-800">{{ row.product_category }}</span>
      </template>
      <template #cell:objetivo="{ row }">
        <span class="tabular-nums text-[13px] font-bold text-brand-900">{{ row.margen_objetivo_pct }}%</span>
      </template>
      <template #cell:factor="{ row }">
        <SemanticChip v-if="row.factor_sensibilidad != null" tipo="ia">
          {{ row.factor_sensibilidad }}
        </SemanticChip>
        <span v-else class="text-[12px] text-slate-400">sin regla</span>
      </template>
      <template #cell:acciones="{ row }">
        <Btn
          v-if="puedeEditarRegla"
          variant="ghost"
          class="!px-2.5 !py-1 !text-[12px]"
          @click="abrirEdicion(row)"
        >
          <Icon name="pencil" :size="13" /> Editar
        </Btn>
        <span v-else class="text-[11px] text-slate-400">—</span>
      </template>
    </DataTable>

    <section v-if="puedeVerBajoMargen" class="mt-6">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 class="font-display text-base font-bold text-brand-950">Descuentos bajo margen mínimo</h2>
          <p class="text-[12px] text-slate-600">
            Líneas de venta con descuento manual autorizado cuyo margen real quedó bajo el objetivo
            efectivo (FR-011).
          </p>
        </div>
        <label class="flex items-center gap-2 text-[12px] font-semibold text-slate-600">
          <input
            type="checkbox"
            class="accent-brand-700"
            :checked="bajoRevisado"
            @change="((bajoRevisado = $event.target.checked), cargarBajoMargen())"
          />
          Ver ya revisados
        </label>
      </div>

      <DataTable
        :columns="colsBajo"
        :rows="bajoMargen"
        row-key="venta_detalle_id"
        :loading="bajoCargando"
        densa
        :page="1"
        :size="bajoMargen.length || 1"
        :total="bajoMargen.length"
        empty-text="Sin descuentos bajo margen para este filtro"
      >
        <template #cell:ref="{ row }">
          <span class="font-mono text-[11px] text-slate-600">#{{ row.venta_id }} / {{ row.venta_detalle_id }}</span>
        </template>
        <template #cell:producto="{ row }">
          <span class="text-[12px] text-slate-700">Producto {{ row.product_id }} · ×{{ row.cantidad }}</span>
        </template>
        <template #cell:aplicado="{ row }">
          <span class="tabular-nums text-[13px] text-slate-800">{{ money(row.precio_aplicado, { showCode: false }) }}</span>
        </template>
        <template #cell:margen="{ row }">
          <span class="tabular-nums text-[13px] font-bold text-crimson-ruby">
            {{ row.margen_real == null ? '—' : `${row.margen_real}%` }}
          </span>
        </template>
        <template #cell:motivo="{ row }">
          <span class="text-[12px] text-slate-500">{{ row.motivo_descuento || '—' }}</span>
        </template>
        <template #cell:accion="{ row }">
          <span v-if="row.revisado" class="text-[12px] text-emerald-700">{{ row.accion_correctiva }}</span>
          <div v-else-if="puedeRevisar" class="flex gap-1.5">
            <input
              v-model="borrador[row.venta_detalle_id]"
              placeholder="Acción tomada…"
              class="w-40 rounded-lg border border-brand-300 bg-white px-2 py-1 text-[12px] text-slate-800"
            />
            <Btn variant="primary" class="!px-2 !py-1 !text-[11px]" @click="registrarRevision(row)">
              Registrar
            </Btn>
          </div>
          <span v-else class="text-[12px] text-slate-400">pendiente de revisión</span>
        </template>
      </DataTable>
    </section>

    <Modal
      v-if="modal"
      :titulo="`Regla de ajuste — ${modal.product_category}`"
      @cerrar="modal = null"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        El margen objetivo y el factor de sensibilidad son el insumo del motor que genera las
        propuestas de precio cada semana (FR-004).
      </p>
      <form class="space-y-4" @submit.prevent="guardarRegla">
        <label class="block text-[12px] font-semibold text-slate-600">
          Margen objetivo (%)
          <input
            v-model="form.margenObjetivoPct"
            type="number"
            min="0"
            max="100"
            step="0.01"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Factor de sensibilidad (0–1)
          <input
            v-model="form.factorSensibilidad"
            type="number"
            min="0"
            max="1"
            step="0.05"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
          <span class="mt-1 block text-[11px] text-slate-500">
            Vacío = sin regla activa; el motor omite la categoría.
          </span>
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" @click="modal = null">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Guardando…' : 'Guardar regla' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
