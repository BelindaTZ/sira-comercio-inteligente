<script setup>
/**
 * Candidatos a liquidación & venta estratégica de stock — feature 005 (FR-011 a
 * FR-014). Arquetipo "Gestión" del kit ya implementado.
 *
 * El sistema clasifica semanalmente los SKU de baja rotación (categoría C) y
 * sugiere una rebaja; el Encargado de Tienda autoriza la liquidación producto a
 * producto o en lote, y ésta se propaga al POS. Alcance = spec + backend: las
 * "políticas locales" y la matriz de niveles del mockup no tienen respaldo y no
 * se implementan.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useSesion } from '@/stores/sesion'
import { promocionesApi } from '@/services/promocionesApi'
import { confirm } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import { money } from '@/shared/currency'

const sesion = useSesion()
const tiendaId = computed(() => sesion.tiendaId ?? 1)
const puedeEjecutar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Operaciones', 'candidato_liquidacion'),
)
const puedeConfigurar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Operaciones', 'configuracion_promociones'),
)
const puedeVerAbc = computed(() => sesion.puedeLeerTabla('Operaciones', 'cambio_clasificacion_abc'))

const candidatos = ref([])
const cambiosAbc = ref([])
const regla = reactive({ rotacion_minima_liquidacion_semanal: '', descuento_liquidacion_pct: '' })
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const busqueda = ref('')
const pill = ref('')
const page = ref(1)
const size = ref(15)
const seleccion = ref(new Set())

const modalRegla = ref(false)
const modalAbc = ref(false)
const guardando = ref(false)

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo completar la operación.'
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const [r, cList, abcList] = await Promise.all([
      promocionesApi.reglaLiquidacion().catch(() => ({})),
      promocionesApi.candidatosLiquidacion({ tiendaId: tiendaId.value }).catch(() => []),
      puedeVerAbc.value ? promocionesApi.cambiosAbc().catch(() => []) : Promise.resolve([]),
    ])
    regla.rotacion_minima_liquidacion_semanal = r.rotacion_minima_liquidacion_semanal ?? ''
    regla.descuento_liquidacion_pct = r.descuento_liquidacion_pct ?? ''
    candidatos.value = cList || []
    cambiosAbc.value = abcList || []
    seleccion.value = new Set()
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

const pendientes = computed(() => candidatos.value.filter((c) => c.estado === 'candidato'))
const kpi = computed(() => {
  const enRiesgo = pendientes.value.reduce((s, c) => s + Number(c.precio_base || 0), 0)
  const recup = pendientes.value.reduce((s, c) => s + Number(c.precio_liquidacion || 0), 0)
  return {
    total: candidatos.value.length,
    pendientes: pendientes.value.length,
    ejecutados: candidatos.value.filter((c) => c.estado === 'ejecutado').length,
    enRiesgo,
    recuperacion: recup,
    recuperacionPct: enRiesgo ? Math.round((recup / enRiesgo) * 100) : null,
  }
})

const pills = computed(() => [
  { value: '', label: 'Todos', count: kpi.value.total },
  { value: 'candidato', label: 'Por autorizar', count: kpi.value.pendientes },
  { value: 'ejecutado', label: 'En liquidación', count: kpi.value.ejecutados },
])

const columnas = [
  { key: 'sel', label: '', width: '36px' },
  { key: 'producto', label: 'Producto' },
  { key: 'rotacion', label: 'Rotación', align: 'right', width: '110px' },
  { key: 'precio', label: 'Normal → liquidación', align: 'right', width: '190px' },
  { key: 'descuento', label: 'Descuento', align: 'center', width: '100px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '130px' },
  { key: 'acciones', label: '', align: 'right', width: '130px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return candidatos.value.filter((c) => {
    if (pill.value && c.estado !== pill.value) return false
    if (!q) return true
    return (
      (c.product_nombre || '').toLowerCase().includes(q) ||
      String(c.product_id).includes(q) ||
      (c.product_category || '').toLowerCase().includes(q)
    )
  })
})
const filas = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

function toggle(id) {
  const s = new Set(seleccion.value)
  s.has(id) ? s.delete(id) : s.add(id)
  seleccion.value = s
}
const seleccionables = computed(() => filtrados.value.filter((c) => c.estado === 'candidato'))
function toggleTodos() {
  seleccion.value =
    seleccion.value.size === seleccionables.value.length
      ? new Set()
      : new Set(seleccionables.value.map((c) => c.candidato_id))
}

async function ejecutar(c) {
  error.value = ''
  aviso.value = ''
  try {
    await promocionesApi.ejecutarCandidato(c.candidato_id)
    aviso.value = `Liquidación de "${c.product_nombre}" activada en el POS.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  }
}

async function ejecutarSeleccion() {
  const ids = [...seleccion.value]
  if (!ids.length) return
  const ok = await confirm({
    title: 'Autorizar liquidación en lote',
    message: `Se activará la rebaja en el POS para ${ids.length} producto(s). Esta acción se propaga a todas las cajas.`,
    confirmText: 'Autorizar',
  })
  if (!ok) return
  let n = 0
  const fallos = []
  for (const id of ids) {
    try {
      await promocionesApi.ejecutarCandidato(id)
      n++
    } catch {
      fallos.push(id)
    }
  }
  aviso.value = `${n} liquidación(es) activada(s) en POS${fallos.length ? ` · ${fallos.length} con error` : ''}.`
  await cargar()
}

async function guardarRegla() {
  guardando.value = true
  error.value = ''
  try {
    await promocionesApi.actualizarReglaLiquidacion({
      rotacionMinima: regla.rotacion_minima_liquidacion_semanal,
      descuento: regla.descuento_liquidacion_pct,
    })
    modalRegla.value = false
    aviso.value = 'Regla de liquidación actualizada. Se aplicará en el próximo cálculo semanal.'
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardando.value = false
  }
}

async function recalcular() {
  aviso.value = ''
  error.value = ''
  try {
    if (puedeVerAbc.value) await promocionesApi.forzarClasificacionAbc().catch(() => {})
    await promocionesApi.forzarCandidatos()
    aviso.value = 'Clasificación ABC y candidatos recalculados.'
    await cargar()
  } catch (e) {
    error.value = msg(e)
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Candidatos a liquidación"
      subtitulo="SKU de baja rotación con rebaja sugerida por el sistema. Autoriza la liquidación para rescatar margen antes de que el stock caiga en merma."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.pendientes > 0 ? 'fifo' : 'ok'">
          {{ kpi.pendientes > 0 ? `${kpi.pendientes} por autorizar` : 'Sin pendientes' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeEjecutar" variant="ghost" @click="recalcular">
          <Icon name="cog" :size="16" /> Recalcular candidatos
        </Btn>
        <Btn v-if="puedeVerAbc" variant="ghost" @click="modalAbc = true">
          <Icon name="chart" :size="16" /> Auditoría ABC ({{ cambiosAbc.length }})
        </Btn>
        <Btn v-if="puedeConfigurar" variant="primary" @click="modalRegla = true">
          <Icon name="tag" :size="16" /> Configurar regla
        </Btn>
        <span
          v-if="!puedeEjecutar && !puedeConfigurar"
          class="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600"
        >
          <Icon name="shield" :size="14" /> Solo lectura
        </span>
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
        label="Valor en riesgo"
        :valor="money(kpi.enRiesgo)"
        variant="emerald"
        microcopy="Precio normal del stock candidato aún no liquidado"
        pie-label="SKU candidatos"
        :pie-valor="`${kpi.pendientes} por autorizar`"
      />
      <KpiTile
        label="Recuperación proyectada"
        :valor="money(kpi.recuperacion)"
        :estado="kpi.recuperacionPct != null ? `${kpi.recuperacionPct}% del valor` : ''"
        estado-tipo="ok"
        microcopy="Ingreso estimado si se autoriza toda la liquidación sugerida"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="SKU candidatos activos"
        :valor="kpi.pendientes.toLocaleString('es-EC')"
        :estado-tipo="kpi.pendientes > 0 ? 'fifo' : 'ok'"
        microcopy="Elegibles según la rotación mínima semanal configurada"
      >
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="En liquidación"
        :valor="kpi.ejecutados.toLocaleString('es-EC')"
        estado-tipo="neutral"
        microcopy="Rebaja ya propagada a las cajas POS"
      >
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
    </section>

    <div
      v-if="seleccion.size"
      class="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-brand-300 bg-brand-50 px-4 py-2.5"
    >
      <span class="text-[13px] font-semibold text-brand-900">
        {{ seleccion.size }} producto(s) seleccionado(s)
      </span>
      <div class="flex gap-2">
        <Btn variant="ghost" class="!py-1 !text-[12px]" @click="seleccion = new Set()">
          Limpiar
        </Btn>
        <Btn variant="primary" class="!py-1 !text-[12px]" @click="ejecutarSeleccion">
          <Icon name="bolt" :size="13" /> Autorizar liquidación ({{ seleccion.size }})
        </Btn>
      </div>
    </div>

    <DataTable
      titulo="Productos candidatos"
      subtitulo="Selección múltiple para autorizar en lote, o ejecución individual."
      :columns="columnas"
      :rows="filas"
      row-key="candidato_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Producto o categoría…"
      :pills="pills"
      :pill-activa="pill"
      empty-text="Sin candidatos a liquidación esta semana"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
      @pill="((pill = $event), (page = 1))"
    >
      <template #acciones-cabecera>
        <button
          v-if="seleccionables.length && puedeEjecutar"
          type="button"
          class="rounded-lg border border-brand-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-brand-800 hover:bg-brand-50"
          @click="toggleTodos"
        >
          {{ seleccion.size === seleccionables.length ? 'Deseleccionar' : 'Seleccionar todos' }}
        </button>
      </template>

      <template #cell:sel="{ row }">
        <input
          v-if="row.estado === 'candidato' && puedeEjecutar"
          type="checkbox"
          class="accent-brand-700"
          :checked="seleccion.has(row.candidato_id)"
          @change="toggle(row.candidato_id)"
        />
      </template>

      <template #cell:producto="{ row }">
        <div class="flex items-center gap-2">
          <img
            v-if="row.imagen_url"
            :src="row.imagen_url"
            alt=""
            class="h-8 w-8 shrink-0 rounded-lg border border-brand-100 object-cover"
          />
          <div class="leading-tight">
            <div class="text-[12px] font-semibold text-slate-800">
              {{ row.product_nombre || `Producto ${row.product_id}` }}
            </div>
            <div class="text-[10px] text-slate-400">
              {{ row.product_category || 'General' }} · ID {{ row.product_id }}
            </div>
          </div>
        </div>
      </template>

      <template #cell:rotacion="{ row }">
        <span class="tabular-nums text-[12px] font-semibold text-crimson-ruby">
          {{ Number(row.rotacion_reciente_calculada).toFixed(1) }}
        </span>
        <span class="text-[10px] text-slate-400"> u/sem</span>
      </template>

      <template #cell:precio="{ row }">
        <span class="text-[12px] text-slate-400 line-through">{{ money(row.precio_base) }}</span>
        <span class="mx-1 text-slate-300">→</span>
        <span class="text-[13px] font-bold text-brand-900">{{ money(row.precio_liquidacion) }}</span>
      </template>

      <template #cell:descuento="{ row }">
        <SemanticChip tipo="quiebre">−{{ Math.round(Number(row.descuento_sugerido_pct)) }}%</SemanticChip>
      </template>

      <template #cell:estado="{ row }">
        <SemanticChip :tipo="row.estado === 'ejecutado' ? 'ok' : 'fifo'">
          {{ row.estado === 'ejecutado' ? 'En liquidación' : 'Por autorizar' }}
        </SemanticChip>
      </template>

      <template #cell:acciones="{ row }">
        <Btn
          v-if="row.estado === 'candidato' && puedeEjecutar"
          variant="primary"
          class="!px-2.5 !py-1 !text-[12px]"
          @click="ejecutar(row)"
        >
          <Icon name="bolt" :size="13" /> Autorizar
        </Btn>
        <span v-else-if="row.estado === 'ejecutado'" class="text-[11px] font-semibold text-emerald-700">
          Aplicado
        </span>
        <span v-else class="text-[11px] text-slate-400">—</span>
      </template>
    </DataTable>

    <Modal
      v-if="modalRegla"
      titulo="Regla de liquidación (categoría C)"
      @cerrar="modalRegla = false"
    >
      <p class="mb-4 text-[13px] text-slate-600">
        El sistema evalúa cada semana los productos de baja rotación y sugiere su liquidación antes de
        que caigan en merma.
      </p>
      <form class="space-y-4" @submit.prevent="guardarRegla">
        <label class="block text-[12px] font-semibold text-slate-600">
          Rotación mínima aceptable (u/semana) <span class="text-crimson-ruby">*</span>
          <input
            v-model="regla.rotacion_minima_liquidacion_semanal"
            type="number"
            step="0.1"
            min="0"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
          <span class="mt-1 block text-[11px] text-slate-500">
            Por debajo de este valor el SKU se marca como candidato.
          </span>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Descuento de liquidación sugerido (%) <span class="text-crimson-ruby">*</span>
          <input
            v-model="regla.descuento_liquidacion_pct"
            type="number"
            step="1"
            min="1"
            max="90"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" @click="modalRegla = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Guardando…' : 'Guardar regla' }}
          </Btn>
        </div>
      </form>
    </Modal>

    <Modal
      v-if="modalAbc"
      titulo="Auditoría de reclasificación ABC"
      size="lg"
      @cerrar="modalAbc = false"
    >
      <p class="mb-3 text-[13px] text-slate-600">
        Cambios de clasificación (principio de Pareto 80/15/5) del período.
      </p>
      <div class="max-h-80 overflow-y-auto rounded-xl border border-brand-200">
        <table class="w-full text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-100 text-[11px] uppercase text-slate-400">
              <th class="px-3 py-2">Producto</th>
              <th class="px-3 py-2 text-center">Antes</th>
              <th class="px-3 py-2 text-center">Ahora</th>
              <th class="px-3 py-2 text-right">Fecha</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100">
            <tr v-if="!cambiosAbc.length">
              <td colspan="4" class="px-3 py-6 text-center text-slate-400">
                Sin reclasificaciones en el período.
              </td>
            </tr>
            <tr v-for="(c, i) in cambiosAbc" :key="i">
              <td class="px-3 py-1.5 font-medium text-slate-700">Producto #{{ c.product_id }}</td>
              <td class="px-3 py-1.5 text-center font-mono">{{ c.clasificacion_anterior || '—' }}</td>
              <td class="px-3 py-1.5 text-center font-mono font-bold text-brand-800">
                {{ c.clasificacion_nueva }}
              </td>
              <td class="px-3 py-1.5 text-right text-slate-500">
                {{ (c.fecha_calculo || '').slice(0, 10) || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex justify-end pt-3">
        <Btn variant="ghost" @click="modalAbc = false">Cerrar</Btn>
      </div>
    </Modal>
  </div>
</template>
