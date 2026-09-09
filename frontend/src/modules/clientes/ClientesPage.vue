<script setup>
/**
 * Gestión de Clientes & Programa de Lealtad "Club Marzú" (feature 002, US1).
 * Estructura de `docs/diseno-ui/.../sira_crm_clientes_programa_fidelizaci_n_club_marz/`:
 * page header + acciones, 4 KPI tiles, directorio enriquecido (LTV, frecuencia,
 * puntos, nivel) con pills de segmentación por tier, y panel derecho con la
 * ficha 360° del cliente. Kit visual compartido con Inventario / Catálogo.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import { useSesion } from '@/stores/sesion'
import { confirm } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import FormularioCliente from './components/FormularioCliente.vue'
import FichaCliente360 from './components/FichaCliente360.vue'

const sesion = useSesion()
const puedeEditar = computed(() => sesion.puedeEditarTabla('Marketing_CRM', 'clientes'))
const puedeChurn = computed(() => sesion.puedeLeerTabla('Marketing_CRM', 'churn_score'))
const puedeCampanas = computed(() => sesion.puedeLeerTabla('Marketing_CRM', 'campanas'))
const puedeCrearCampana = computed(() => sesion.puedeEditarTabla('Marketing_CRM', 'campanas'))

const busqueda = ref('')
const nivel = ref('') // '' | nivel_id
const pillEstado = ref('activos') // 'todos' | 'activos'
const page = ref(1)
const size = ref(25)

const rows = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')

const kpi = ref({
  base_activos: 0,
  ticket_club: null,
  ticket_no_club: null,
  uplift_pct: null,
  tasa_redencion_pct: null,
  redimidos: 0,
  con_clv: 0,
  niveles: [],
})

const seleccion = ref(null)
const modal = ref(null) // 'nuevo' | 'editar'
const tituloPagina = 'Gestión de Clientes & Programa de Lealtad "Club Marzú"'

const money = (v) =>
  v == null ? '—' : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const fmtFecha = (d) =>
  d ? new Date(d).toLocaleDateString('es-CL', { day: '2-digit', month: 'short' }) : '—'

const TIER_DOT = { Bronce: 'bg-amber-700', Plata: 'bg-slate-400', Oro: 'bg-amber-500', Platino: 'bg-amethyst-500' }

const altoValor = computed(() =>
  kpi.value.niveles
    .filter((n) => n.nombre === 'Oro' || n.nombre === 'Platino')
    .reduce((a, n) => a + n.clientes, 0),
)

const pills = computed(() => [
  { value: '', label: 'Todos', count: kpi.value.base_activos },
  ...kpi.value.niveles.map((n) => ({ value: String(n.nivel_id), label: n.nombre, count: n.clientes })),
])

const columnas = [
  { key: 'cliente', label: 'Cliente & RUT' },
  { key: 'nivel', label: 'Nivel Club', width: '128px' },
  { key: 'puntos', label: 'Puntos', align: 'right', width: '96px' },
  { key: 'frecuencia', label: 'Frecuencia', align: 'center', width: '96px' },
  { key: 'sucursal', label: 'Sucursal habitual', width: '150px' },
  { key: 'ultima', label: 'Última compra', width: '116px' },
  { key: 'ltv', label: 'LTV histórico', align: 'right', width: '128px' },
  { key: 'ir', label: '', align: 'center', width: '40px' },
]

async function cargarKpis() {
  try {
    kpi.value = await clientesApi.resumenCrm()
  } catch {
    /* informativo */
  }
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await clientesApi.directorio({
      search: busqueda.value.trim() || undefined,
      nivelId: nivel.value || undefined,
      activo: pillEstado.value === 'activos' ? true : undefined,
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

function refrescar() {
  modal.value = null
  return Promise.all([cargar(), cargarKpis()])
}

async function darDeBaja(row) {
  const ok = await confirm({
    title: 'Anonimizar y dar de baja',
    message: `Se eliminarán los datos personales de "${row.nombre}" y quedará inactivo. Esta acción es irreversible.`,
    confirmText: 'Anonimizar',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await clientesApi.darDeBaja(row.household_id)
    if (seleccion.value?.household_id === row.household_id) seleccion.value = null
    await refrescar()
  } catch (e) {
    error.value = e.message
  }
}

watch([nivel, pillEstado], () => {
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
      :titulo="tituloPagina"
      subtitulo="Directorio con LTV, frecuencia y puntos del Club, segmentación por nivel y ficha 360° del cliente."
    >
      <template #badge>
        <SemanticChip tipo="ia">Fidelización activa</SemanticChip>
      </template>
      <template #acciones>
        <RouterLink
          v-if="puedeCampanas"
          to="/clientes/campanas"
          class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 shadow-2xs hover:bg-brand-50/70"
        >
          <Icon name="megaphone" :size="16" /> Campañas de cupones
        </RouterLink>
        <RouterLink
          v-if="puedeChurn"
          to="/clientes/riesgo-fuga"
          class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 shadow-2xs hover:bg-brand-50/70"
        >
          <Icon name="alert" :size="16" /> Riesgo de fuga
        </RouterLink>
        <Btn v-if="puedeEditar" variant="primary" @click="((seleccion = null), (modal = 'nuevo'))">
          <Icon name="plus" :size="17" /> Registrar cliente
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
        label="Base de clientes activos"
        :valor="kpi.base_activos.toLocaleString('es-CL')"
        variant="emerald"
        :microcopy="`${kpi.con_clv.toLocaleString('es-CL')} con CLV calculado`"
        pie-label="Segmentados"
        :pie-valor="`${kpi.niveles.reduce((a, n) => a + n.clientes, 0).toLocaleString('es-CL')} en un nivel del Club`"
      />
      <KpiTile
        label="Ticket promedio Club Marzú"
        :valor="money(kpi.ticket_club)"
        :estado="kpi.uplift_pct != null ? `+${kpi.uplift_pct}% uplift` : 'sin base'"
        :estado-tipo="kpi.uplift_pct != null ? 'ia' : 'neutral'"
        :microcopy="kpi.ticket_no_club != null ? `vs. ${money(kpi.ticket_no_club)} no inscritos` : 'Compra media del cliente inscrito'"
      >
        <template #icono><Icon name="cart" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Tasa de redención de cupones"
        :valor="kpi.tasa_redencion_pct != null ? kpi.tasa_redencion_pct + '%' : null"
        estado-tipo="ok"
        :estado="`${kpi.redimidos.toLocaleString('es-CL')} canjes`"
        microcopy="Clientes que canjearon al menos un cupón asignado"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Clientes de alto valor"
        :valor="altoValor.toLocaleString('es-CL')"
        unidad="Oro + Platino"
        variant="ia"
        estado="foco retención"
        estado-tipo="ia"
        microcopy="Tiers superiores del Club — mayor LTV y frecuencia"
        pie-label="Del total con nivel"
        :pie-valor="`${kpi.niveles.reduce((a, n) => a + n.clientes, 0).toLocaleString('es-CL')} clientes`"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
      {{ error }}
    </p>

    <div class="grid items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_384px]">
      <div class="space-y-4">
        <DataTable
          titulo="Directorio de clientes"
          subtitulo="Ordenado por LTV histórico. El nivel del Club sale del CLV más reciente."
          :columns="columnas"
          :rows="rows"
          row-key="household_id"
          :loading="cargando"
          densa
          :page="page"
          :size="size"
          :total="total"
          :search="busqueda"
          search-placeholder="RUT, nombre, email o teléfono…"
          :pills="pills"
          :pill-activa="nivel"
          empty-text="Sin clientes para este filtro"
          @update:page="page = $event"
          @update:size="((size = $event), (page = 1))"
          @update:search="busqueda = $event"
          @pill="nivel = $event"
          @row-click="seleccion = $event"
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
                <div class="truncate font-mono text-[10px] text-slate-500">
                  {{ row.documento_identidad || '—' }}<template v-if="row.email"> · {{ row.email }}</template>
                </div>
              </div>
            </div>
          </template>

          <template #cell:nivel="{ row }">
            <span
              v-if="row.nivel_nombre"
              class="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-700"
            >
              <span class="h-2 w-2 rounded-full" :class="TIER_DOT[row.nivel_nombre] || 'bg-slate-300'" />
              {{ row.nivel_nombre }}
            </span>
            <span v-else class="text-[11px] text-slate-400">Sin nivel</span>
          </template>

          <template #cell:puntos="{ row }">
            <span class="font-bold tabular-nums text-amethyst-700">
              {{ row.puntos.toLocaleString('es-CL') }}
            </span>
          </template>

          <template #cell:frecuencia="{ row }">
            <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-semibold text-slate-700">
              {{ Number(row.frecuencia_sem).toFixed(1) }} v/sem
            </span>
          </template>

          <template #cell:sucursal="{ row }">
            <span class="truncate text-[11px] text-slate-600">{{ row.sucursal || '—' }}</span>
          </template>

          <template #cell:ultima="{ row }">
            <div class="text-[11px] text-slate-600">{{ fmtFecha(row.ultima_compra) }}</div>
            <div v-if="row.ultimo_ticket" class="text-[10px] text-slate-400">#{{ row.ultimo_ticket }}</div>
          </template>

          <template #cell:ltv="{ row }">
            <span class="font-bold tabular-nums text-slate-900">{{ money(row.ltv) }}</span>
          </template>

          <template #cell:ir="{ row }">
            <Icon
              name="chevron"
              :size="15"
              class="-rotate-90"
              :class="seleccion?.household_id === row.household_id ? 'text-amethyst-600' : 'text-slate-300'"
            />
          </template>
        </DataTable>

        <div
          v-if="puedeCampanas"
          class="flex items-center justify-between gap-3 rounded-2xl border border-amethyst-200 bg-amethyst-50/50 p-4"
        >
          <div class="flex items-center gap-3">
            <span class="grid h-10 w-10 place-items-center rounded-lg bg-amethyst-600 text-white">
              <Icon name="bolt" :size="18" />
            </span>
            <div>
              <p class="text-[13px] font-bold text-slate-800">Motor predictivo de recompra Marzú</p>
              <p class="text-[12px] text-slate-600">
                {{ kpi.niveles.reduce((a, n) => (n.nombre === 'Oro' || n.nombre === 'Platino' ? a + n.clientes : a), 0) }}
                clientes Oro/Platino con probabilidad de visita este fin de semana.
              </p>
            </div>
          </div>
          <RouterLink
            to="/clientes/campanas"
            class="inline-flex items-center gap-1.5 rounded-lg bg-amethyst-600 px-3 py-1.5 text-[12px] font-bold text-white hover:bg-amethyst-500"
          >
            {{ puedeCrearCampana ? 'Crear campaña' : 'Ver campañas' }}
            <Icon name="chevron" :size="12" class="-rotate-90" />
          </RouterLink>
        </div>
      </div>

      <FichaCliente360
        :cliente="seleccion"
        :niveles="kpi.niveles"
        :puede-cupon="puedeCampanas"
        @editar="((seleccion = $event), (modal = 'editar'))"
        @asignar-cupon="() => $router.push('/clientes/campanas')"
      />
    </div>

    <Modal
      v-if="modal === 'nuevo'"
      titulo="Registrar cliente"
      @cerrar="modal = null"
    >
      <FormularioCliente :cliente="null" @guardado="refrescar" />
    </Modal>
    <Modal
      v-else-if="modal === 'editar' && seleccion"
      :titulo="`Editar — ${seleccion.nombre}`"
      @cerrar="modal = null"
    >
      <FormularioCliente :cliente="seleccion" @guardado="refrescar" />
      <button
        type="button"
        class="mt-3 w-full rounded-xl border border-rose-300 px-3 py-2 text-[12px] font-semibold text-crimson-ruby hover:bg-rose-50"
        @click="darDeBaja(seleccion)"
      >
        Anonimizar y dar de baja
      </button>
    </Modal>
  </div>
</template>
