<script setup>
/**
 * Seguimiento y auditoría de merma (feature 006, FR-017 a FR-019 + registro/
 * validación de 001). Libro oficial de bajas de inventario con causa raíz real,
 * destino físico de las unidades y gobernanza de umbrales por categoría.
 * Todos los números salen del backend; no hay datos de relleno.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useSesion } from '@/stores/sesion'
import { cajaApi } from '@/services/cajaApi'
import { inventarioApi } from '@/services/inventarioApi'
import { money } from '@/shared/currency'
import { opcionesExportacion } from '@/shared/exportar'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Modal from '@/shared/ui/Modal.vue'
import Icon from '@/shared/ui/Icon.vue'
import FormularioMerma from '@/modules/inventario/components/FormularioMerma.vue'

const sesion = useSesion()
const tiendaId = computed(
  () => sesion.tiendaId ?? (Number(localStorage.getItem('sira_tienda_id')) || 1),
)
const empleadoId = computed(
  () => sesion.empleadoId ?? (Number(localStorage.getItem('sira_empleado_id')) || 1),
)
const puedeEditarUmbrales = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Finanzas', 'umbral_merma_categoria'),
)
// Visar / rechazar una merma es del Encargado o Reponedor; la Gerencia sólo consulta.
const puedeValidar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Operaciones', 'mermas'),
)

const CAUSAS = {
  caducidad: { texto: 'Vencimiento / FEFO', chip: 'quiebre', barra: 'bg-amber-500', punto: 'text-amber-700' },
  rotura: { texto: 'Rotura / manipulación', chip: 'quiebre', barra: 'bg-rose-500', punto: 'text-rose-700' },
  robo: { texto: 'Hurto / pérdida', chip: 'quiebre', barra: 'bg-amethyst-500', punto: 'text-amethyst-700' },
  error_humano: { texto: 'Desmedro operativo', chip: 'fifo', barra: 'bg-slate-400', punto: 'text-slate-600' },
}
const causaMeta = (c) => CAUSAS[c] || { texto: c, chip: 'neutral', barra: 'bg-slate-300', punto: 'text-slate-500' }

const DESTINOS = {
  donacion: { texto: 'Donación a red de alimentos', aprovecha: true },
  devolucion: { texto: 'Devolución a proveedor (nota de crédito)', aprovecha: true },
  destruccion: { texto: 'Destrucción in situ', aprovecha: false },
  cuarentena: { texto: 'Jaula de cuarentena', aprovecha: false },
}
const destinoTexto = (d) => DESTINOS[d]?.texto || d || '—'
const incidentes = (n) => `${n} ${n === 1 ? 'incidente' : 'incidentes'}`

const cargando = ref(false)
const error = ref('')
const exito = ref('')

const kpis = ref({
  merma_acumulada_mes: 0,
  tasa_merma_pct: 0,
  venta_mes: 0,
  skus_criticos_count: 0,
  tasa_recuperacion_pct: 0,
  recuperacion_monto: 0,
  pendientes_count: 0,
  causas_desglose: {},
})

const mermas = ref([])
const filtroCausa = ref('todas')
const filtroEstado = ref('todos')
const busqueda = ref('')

// Desglose de causa raíz: 100 % derivado de causas_desglose del backend.
const causasCatalogo = computed(() => {
  const d = kpis.value.causas_desglose || {}
  const total = Object.values(d).reduce((s, x) => s + Number(x.valor || 0), 0)
  return Object.keys(CAUSAS)
    .map((id) => {
      const valor = Number(d[id]?.valor ?? 0)
      return {
        id,
        nombre: CAUSAS[id].texto,
        barra: CAUSAS[id].barra,
        punto: CAUSAS[id].punto,
        monto: valor,
        incidentes: Number(d[id]?.cantidad ?? 0),
        pct: total > 0 ? Math.round((valor / total) * 100) : 0,
      }
    })
    .filter((c) => c.monto > 0 || c.incidentes > 0)
})
const hayCausas = computed(() => causasCatalogo.value.length > 0)

// Desglose por destino físico de las unidades (real, de la lista de incidentes).
const destinoCatalogo = computed(() => {
  const acc = {}
  for (const m of mermas.value) {
    const key = m.destino || 'sin_destino'
    acc[key] = acc[key] || { destino: key, monto: 0, incidentes: 0 }
    acc[key].monto += Number(m.valor || 0)
    acc[key].incidentes += 1
  }
  return Object.values(acc).sort((a, b) => b.monto - a.monto)
})

const modalDeclarar = ref(false)
const modalActa = ref(false)
const mermaSeleccionada = ref(null)
const modalUmbrales = ref(false)
const umbrales = ref([])
const seguimientoSemanal = ref([])
const nuevoUmbral = reactive({ product_category: '', porcentaje_umbral: '' })
const guardandoUmbral = ref(false)

watch(tiendaId, cargarDatos)

async function cargarDatos() {
  cargando.value = true
  error.value = ''
  try {
    const [kpisData, mermasData] = await Promise.all([
      inventarioApi.kpisMermas(tiendaId.value).catch(() => null),
      inventarioApi.listarMermas({ tiendaId: tiendaId.value, limit: 100 }).catch(() => []),
    ])
    if (kpisData) {
      kpis.value = {
        merma_acumulada_mes: Number(kpisData.merma_acumulada_mes ?? 0),
        tasa_merma_pct: Number(kpisData.tasa_merma_pct ?? 0),
        venta_mes: Number(kpisData.venta_mes ?? 0),
        skus_criticos_count: Number(kpisData.skus_criticos_count ?? 0),
        tasa_recuperacion_pct: Number(kpisData.tasa_recuperacion_pct ?? 0),
        recuperacion_monto: Number(kpisData.recuperacion_monto ?? 0),
        pendientes_count: Number(kpisData.pendientes_count ?? 0),
        causas_desglose: kpisData.causas_desglose || {},
      }
    }
    mermas.value = Array.isArray(mermasData) ? mermasData : []
  } catch (e) {
    error.value = e.message || 'No se pudieron cargar los incidentes de merma.'
  } finally {
    cargando.value = false
  }
}

async function cargarUmbrales() {
  try {
    umbrales.value = await cajaApi.umbralesMerma()
    const d = new Date()
    const day = (d.getUTCDay() + 6) % 7
    d.setUTCDate(d.getUTCDate() - day + 3)
    const primerJueves = new Date(Date.UTC(d.getUTCFullYear(), 0, 4))
    const semana = 1 + Math.round((d - primerJueves) / 604800000)
    seguimientoSemanal.value = await cajaApi.seguimientoMermaSemanal(tiendaId.value, {
      semana,
      anio: d.getUTCFullYear(),
    })
  } catch (e) {
    error.value = e.message || 'No se pudo cargar el seguimiento de umbrales.'
  }
}

async function guardarUmbral() {
  if (!nuevoUmbral.product_category || !nuevoUmbral.porcentaje_umbral) return
  guardandoUmbral.value = true
  error.value = ''
  try {
    await cajaApi.definirUmbralMerma(
      nuevoUmbral.product_category.trim(),
      Number(nuevoUmbral.porcentaje_umbral),
    )
    nuevoUmbral.product_category = ''
    nuevoUmbral.porcentaje_umbral = ''
    await cargarUmbrales()
  } catch (e) {
    error.value = e.message
  } finally {
    guardandoUmbral.value = false
  }
}

async function procesarValidacion(merma, decision) {
  error.value = ''
  try {
    await inventarioApi.validarMerma(merma.merma_id, { empleadoId: empleadoId.value, decision })
    exito.value = `Merma #${merma.merma_id} marcada como ${decision}.`
    setTimeout(() => (exito.value = ''), 4000)
    await cargarDatos()
  } catch (e) {
    error.value = `No se pudo procesar la merma: ${e.message}`
  }
}

const mermasFiltradas = computed(() =>
  mermas.value.filter((m) => {
    if (filtroCausa.value !== 'todas' && m.causa !== filtroCausa.value) return false
    if (filtroEstado.value === 'pendientes' && m.estado_validacion !== 'pendiente') return false
    if (filtroEstado.value === 'validadas' && m.estado_validacion !== 'validada') return false
    if (filtroEstado.value === 'rechazadas' && m.estado_validacion !== 'rechazada') return false
    if (busqueda.value.trim()) {
      const q = busqueda.value.toLowerCase().trim()
      const campos = [
        `#${m.merma_id}`,
        m.product_nombre,
        m.product_sku,
        m.lote_numero,
        m.observaciones,
      ]
      if (!campos.some((c) => c && String(c).toLowerCase().includes(q))) return false
    }
    return true
  }),
)

const cuentaPorEstado = (estado) =>
  mermas.value.filter((m) => m.estado_validacion === estado).length

function folio(m) {
  const anio = m.fecha ? String(m.fecha).slice(0, 4) : new Date().getFullYear()
  return `MRM-${anio}-${m.merma_id}`
}

function abrirActa(m) {
  mermaSeleccionada.value = m
  modalActa.value = true
}

const menuExport = ref(false)
const filasExport = computed(() => [
  ['Folio', 'Producto', 'SKU', 'Lote', 'Cantidad', 'Costo unit. USD', 'Total USD', 'Causa', 'Destino', 'Estado', 'Fecha'],
  ...mermasFiltradas.value.map((m) => [
    folio(m),
    m.product_nombre,
    m.product_sku || m.product_id,
    m.lote_numero || '—',
    m.cantidad,
    m.costo_unitario,
    m.valor,
    causaMeta(m.causa).texto,
    destinoTexto(m.destino),
    m.estado_validacion,
    m.fecha,
  ]),
])
const opcionesExport = computed(() =>
  opcionesExportacion(
    `Auditoría de mermas — tienda ${tiendaId.value}`,
    `auditoria_mermas_tienda_${tiendaId.value}_${new Date().toISOString().slice(0, 10)}`,
    filasExport.value,
  ),
)
function exportar(opt) {
  menuExport.value = false
  opt.fn()
}

onMounted(cargarDatos)
</script>

<template>
  <div class="mx-auto max-w-[1500px] space-y-6 px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Seguimiento y auditoría de merma"
      subtitulo="Libro oficial de bajas de inventario con trazabilidad por lote y ubicación, causa raíz del desmedro, destino físico de las unidades y validación contable (FR-017 a FR-019)."
    >
      <template #badge>
        <SemanticChip :tipo="kpis.pendientes_count > 0 ? 'fifo' : 'ok'">
          {{ kpis.pendientes_count > 0 ? `${kpis.pendientes_count} por validar` : 'Al día' }}
        </SemanticChip>
      </template>
      <template #acciones>
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
              @click="exportar(opt)"
            >
              <Icon name="download" :size="13" class="text-slate-400" /> {{ opt.label }}
            </button>
          </div>
        </div>
        <Btn
          variant="ghost"
          @click="
            () => {
              cargarUmbrales()
              modalUmbrales = true
            }
          "
        >
          <Icon name="cog" :size="16" /> Umbrales por categoría
        </Btn>
        <Btn v-if="puedeValidar" variant="primary" @click="modalDeclarar = true">
          <Icon name="alert" :size="16" /> Declarar merma
        </Btn>
      </template>
    </PageHeader>

    <p
      v-if="exito"
      class="flex items-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      <Icon name="check" :size="16" /> {{ exito }}
    </p>
    <p v-if="error" class="rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>

    <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Merma acumulada del mes"
        :valor="money(kpis.merma_acumulada_mes)"
        variant="emerald"
        :microcopy="
          kpis.venta_mes > 0
            ? `${kpis.tasa_merma_pct}% sobre venta confirmada del mes`
            : 'Sin venta confirmada del mes para el ratio'
        "
      />
      <KpiTile
        label="SKUs con merma este mes"
        :valor="kpis.skus_criticos_count.toLocaleString('es-EC')"
        :estado-tipo="kpis.skus_criticos_count > 0 ? 'fifo' : 'ok'"
      >
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Valor recuperado / aprovechado"
        :valor="money(kpis.recuperacion_monto)"
        :microcopy="`${kpis.tasa_recuperacion_pct}% del valor de merma (donación o devolución)`"
        :estado-tipo="kpis.tasa_recuperacion_pct > 0 ? 'ok' : 'neutral'"
      >
        <template #icono><Icon name="truck" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Incidentes por validar"
        :valor="kpis.pendientes_count.toLocaleString('es-EC')"
        :estado="kpis.pendientes_count > 0 ? 'Requiere visado del Encargado' : 'Al día'"
        :estado-tipo="kpis.pendientes_count > 0 ? 'quiebre' : 'ok'"
      >
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="grid gap-6 lg:grid-cols-3">
      <!-- Causa raíz -->
      <section class="satin-card rounded-2xl p-5 shadow-card-subtle lg:col-span-2">
        <div class="flex items-center justify-between border-b border-brand-100 pb-3">
          <h2 class="font-display text-[14px] font-bold text-brand-950">Desglose de causa raíz</h2>
          <span class="text-[11px] text-slate-400">Mes en curso · tienda {{ tiendaId }}</span>
        </div>

        <p v-if="!hayCausas" class="py-10 text-center text-[13px] text-slate-400">
          Sin mermas registradas este mes en esta tienda.
        </p>

        <template v-else>
          <div class="my-4 flex h-3 w-full gap-0.5 overflow-hidden rounded-full bg-brand-50 p-0.5">
            <div
              v-for="c in causasCatalogo"
              :key="c.id"
              class="h-full cursor-pointer rounded-full transition-all"
              :class="c.barra"
              :style="{ width: `${c.pct}%` }"
              :title="`${c.nombre}: ${c.pct}%`"
              @click="filtroCausa = filtroCausa === c.id ? 'todas' : c.id"
            />
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <button
              v-for="c in causasCatalogo"
              :key="c.id"
              type="button"
              class="rounded-xl border p-3.5 text-left transition-all hover:shadow-card-subtle"
              :class="filtroCausa === c.id ? 'border-brand-400 bg-brand-50/60' : 'border-brand-100 bg-white'"
              @click="filtroCausa = filtroCausa === c.id ? 'todas' : c.id"
            >
              <div class="flex items-center justify-between">
                <span class="flex items-center gap-2 text-[12px] font-bold text-slate-800">
                  <span class="h-2.5 w-2.5 rounded-full" :class="c.barra" /> {{ c.nombre }}
                </span>
                <span class="text-[12px] font-bold" :class="c.punto">{{ c.pct }}%</span>
              </div>
              <div class="mt-2 flex items-baseline justify-between">
                <span class="font-mono text-[15px] font-bold text-slate-900">{{ money(c.monto) }}</span>
                <span class="text-[11px] font-semibold text-slate-500">{{ incidentes(c.incidentes) }}</span>
              </div>
            </button>
          </div>

          <div v-if="filtroCausa !== 'todas'" class="pt-3 text-right">
            <button
              class="text-[11px] font-semibold text-brand-600 underline"
              @click="filtroCausa = 'todas'"
            >
              Quitar filtro de causa
            </button>
          </div>
        </template>
      </section>

      <!-- Destino físico -->
      <section class="satin-card rounded-2xl p-5 shadow-card-subtle">
        <div class="flex items-center gap-2 border-b border-brand-100 pb-3">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg border border-brand-200 bg-brand-50 text-brand-700">
            <Icon name="truck" :size="16" />
          </div>
          <div>
            <h2 class="font-display text-[14px] font-bold text-brand-950">Destino de las unidades</h2>
            <span class="text-[11px] text-slate-400">Sobre los {{ mermas.length }} incidentes cargados</span>
          </div>
        </div>

        <p v-if="!destinoCatalogo.length" class="py-8 text-center text-[13px] text-slate-400">
          Sin incidentes cargados.
        </p>
        <ul v-else class="mt-3 space-y-2.5">
          <li
            v-for="d in destinoCatalogo"
            :key="d.destino"
            class="rounded-xl border border-brand-100 bg-white p-3"
          >
            <div class="flex items-center justify-between">
              <span class="text-[12px] font-bold text-slate-800">{{ destinoTexto(d.destino === 'sin_destino' ? null : d.destino) }}</span>
              <SemanticChip :tipo="DESTINOS[d.destino]?.aprovecha ? 'ok' : 'neutral'">
                {{ DESTINOS[d.destino]?.aprovecha ? 'Aprovecha' : 'No recupera' }}
              </SemanticChip>
            </div>
            <div class="mt-1.5 flex items-baseline justify-between">
              <span class="font-mono text-[14px] font-bold text-slate-900">{{ money(d.monto) }}</span>
              <span class="text-[11px] font-semibold text-slate-500">{{ incidentes(d.incidentes) }}</span>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <!-- Libro de incidentes -->
    <section class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <div class="flex flex-col gap-4 border-b border-brand-100 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="font-display text-[14px] font-bold text-brand-950">
            Libro de incidentes de merma
            <span class="ml-1 text-[12px] font-semibold text-slate-400">{{ mermasFiltradas.length }} registros</span>
          </h2>
          <p class="text-[12px] text-slate-500">Bajas físicas con trazabilidad por lote y ubicación en sala.</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <div class="relative">
            <input
              v-model="busqueda"
              type="text"
              placeholder="Folio, SKU, lote…"
              class="h-9 w-56 rounded-lg border border-brand-200 bg-white pl-3 pr-8 text-[12px] focus:border-brand-500 focus:outline-none"
            />
            <button
              v-if="busqueda"
              class="absolute right-2 top-2 text-slate-400 hover:text-slate-600"
              @click="busqueda = ''"
            >
              <Icon name="x" :size="14" />
            </button>
          </div>
          <div class="flex items-center gap-1 rounded-xl border border-brand-200 bg-white p-1 text-[12px]">
            <button
              v-for="f in [
                { v: 'todos', t: 'Todos' },
                { v: 'pendientes', t: `Pendientes (${cuentaPorEstado('pendiente')})` },
                { v: 'validadas', t: 'Validadas' },
                { v: 'rechazadas', t: 'Rechazadas' },
              ]"
              :key="f.v"
              class="rounded-lg px-2.5 py-1 font-semibold transition-colors"
              :class="filtroEstado === f.v ? 'bg-brand-800 text-white' : 'text-slate-500 hover:bg-brand-50'"
              @click="filtroEstado = f.v"
            >
              {{ f.t }}
            </button>
          </div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-[12px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-4 py-3">Folio / fecha</th>
              <th class="px-4 py-3">Producto</th>
              <th class="px-4 py-3">Lote / vencimiento</th>
              <th class="px-4 py-3">Ubicación</th>
              <th class="px-4 py-3 text-right">Cant.</th>
              <th class="px-4 py-3 text-right">Costo unit.</th>
              <th class="px-4 py-3 text-right">Pérdida</th>
              <th class="px-4 py-3">Causa</th>
              <th class="px-4 py-3">Destino</th>
              <th class="px-4 py-3 text-center">Estado</th>
              <th class="px-4 py-3 text-center">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="cargando">
              <td colspan="11" class="px-4 py-10 text-center text-slate-400">Cargando…</td>
            </tr>
            <tr v-else-if="!mermasFiltradas.length">
              <td colspan="11" class="px-4 py-10 text-center text-slate-400">
                Sin incidentes de merma para los filtros seleccionados.
              </td>
            </tr>
            <tr v-for="m in mermasFiltradas" :key="m.merma_id" class="hover:bg-brand-50/70">
              <td class="px-4 py-3">
                <div class="font-mono font-bold text-slate-800">#{{ folio(m) }}</div>
                <div class="text-[11px] text-slate-400">{{ m.fecha }}</div>
              </td>
              <td class="px-4 py-3">
                <div class="font-semibold text-slate-800">{{ m.product_nombre }}</div>
                <div class="font-mono text-[11px] text-slate-400">
                  {{ m.product_sku || `#${m.product_id}` }}<template v-if="m.product_categoria"> · {{ m.product_categoria }}</template>
                </div>
              </td>
              <td class="px-4 py-3 font-mono">
                <span class="text-slate-700">{{ m.lote_numero || '—' }}</span>
                <div v-if="m.lote_vencimiento" class="text-[11px] font-semibold text-crimson-ruby">
                  Venc: {{ m.lote_vencimiento }}
                </div>
              </td>
              <td class="px-4 py-3 text-slate-600">{{ m.ubicacion_sala || '—' }}</td>
              <td class="px-4 py-3 text-right font-mono font-bold text-slate-800">{{ m.cantidad }}</td>
              <td class="px-4 py-3 text-right font-mono text-slate-500">{{ money(m.costo_unitario) }}</td>
              <td class="px-4 py-3 text-right font-mono font-bold text-slate-800">{{ money(m.valor) }}</td>
              <td class="px-4 py-3">
                <SemanticChip :tipo="causaMeta(m.causa).chip">{{ causaMeta(m.causa).texto }}</SemanticChip>
              </td>
              <td class="px-4 py-3 text-slate-600">{{ destinoTexto(m.destino) }}</td>
              <td class="px-4 py-3 text-center">
                <SemanticChip
                  :tipo="
                    m.estado_validacion === 'validada'
                      ? 'ok'
                      : m.estado_validacion === 'pendiente'
                        ? 'fifo'
                        : 'quiebre'
                  "
                >
                  {{
                    m.estado_validacion === 'validada'
                      ? 'Validada'
                      : m.estado_validacion === 'pendiente'
                        ? 'Pendiente'
                        : 'Rechazada'
                  }}
                </SemanticChip>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-center gap-1">
                  <template v-if="m.estado_validacion === 'pendiente' && puedeValidar">
                    <button
                      class="rounded-lg bg-brand-700 px-2 py-1 text-[10px] font-bold text-white hover:bg-brand-600"
                      @click="procesarValidacion(m, 'validada')"
                    >
                      Aprobar
                    </button>
                    <button
                      class="rounded-lg border border-brand-200 px-2 py-1 text-[10px] font-bold text-slate-600 hover:bg-brand-50"
                      @click="procesarValidacion(m, 'rechazada')"
                    >
                      Rechazar
                    </button>
                  </template>
                  <button
                    class="rounded-lg p-1.5 text-brand-700 hover:bg-brand-50"
                    title="Ver acta de la merma"
                    @click="abrirActa(m)"
                  >
                    <Icon name="download" :size="15" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Modal: declarar merma -->
    <Modal
      v-if="modalDeclarar"
      titulo="Declarar baja de merma de inventario"
      size="lg"
      @cerrar="modalDeclarar = false"
    >
      <FormularioMerma
        :tienda-id="tiendaId"
        :empleado-id="empleadoId"
        @registrada="
          () => {
            modalDeclarar = false
            cargarDatos()
            exito = 'Merma registrada; queda pendiente de visado.'
          }
        "
        @cerrar="modalDeclarar = false"
      />
    </Modal>

    <!-- Modal: acta de la merma -->
    <Modal
      v-if="modalActa && mermaSeleccionada"
      titulo="Acta de baja de merma"
      size="md"
      @cerrar="modalActa = false"
    >
      <div class="space-y-4 text-[12px]">
        <div class="flex items-center justify-between rounded-xl border border-brand-200 bg-brand-50/60 p-4">
          <span class="font-mono text-[14px] font-bold text-brand-900">#{{ folio(mermaSeleccionada) }}</span>
          <SemanticChip :tipo="mermaSeleccionada.estado_validacion === 'validada' ? 'ok' : mermaSeleccionada.estado_validacion === 'pendiente' ? 'fifo' : 'quiebre'">
            {{ mermaSeleccionada.estado_validacion }}
          </SemanticChip>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-lg border border-brand-100 bg-white p-3">
            <span class="block text-[11px] text-slate-400">Producto</span>
            <span class="font-semibold text-slate-800">{{ mermaSeleccionada.product_nombre }}</span>
            <div class="font-mono text-[11px] text-slate-500">{{ mermaSeleccionada.product_sku || `#${mermaSeleccionada.product_id}` }}</div>
          </div>
          <div class="rounded-lg border border-brand-100 bg-white p-3">
            <span class="block text-[11px] text-slate-400">Lote / vencimiento</span>
            <span class="font-mono font-semibold text-slate-800">{{ mermaSeleccionada.lote_numero || '—' }}</span>
            <div class="text-[11px] text-slate-500">{{ mermaSeleccionada.lote_vencimiento || 'Sin fecha de vencimiento' }}</div>
          </div>
          <div class="rounded-lg border border-brand-100 bg-white p-3">
            <span class="block text-[11px] text-slate-400">Cantidad</span>
            <span class="font-mono text-[14px] font-bold text-slate-800">{{ mermaSeleccionada.cantidad }} u.</span>
          </div>
          <div class="rounded-lg border border-brand-100 bg-white p-3">
            <span class="block text-[11px] text-slate-400">Pérdida total</span>
            <span class="font-mono text-[14px] font-bold text-crimson-ruby">{{ money(mermaSeleccionada.valor) }}</span>
          </div>
        </div>

        <div class="rounded-lg border border-brand-100 bg-white p-3">
          <span class="block text-[11px] text-slate-400">Causa y destino</span>
          <div class="font-semibold text-slate-800">
            {{ causaMeta(mermaSeleccionada.causa).texto }} → {{ destinoTexto(mermaSeleccionada.destino) }}
          </div>
          <p v-if="mermaSeleccionada.observaciones" class="mt-1 italic text-slate-600">
            "{{ mermaSeleccionada.observaciones }}"
          </p>
        </div>

        <div class="rounded-lg border border-brand-100 bg-brand-50/50 p-3 text-slate-700">
          Registrada por
          <strong>{{ mermaSeleccionada.empleado_nombre || `empleado #${mermaSeleccionada.empleado_id}` }}</strong>
          el {{ mermaSeleccionada.fecha }}<span v-if="mermaSeleccionada.fecha_validacion"> · validada el {{ String(mermaSeleccionada.fecha_validacion).slice(0, 10) }}</span>.
        </div>

        <div class="flex justify-end gap-2 border-t border-brand-100 pt-3">
          <Btn variant="ghost" @click="modalActa = false">Cerrar</Btn>
          <Btn variant="primary" @click="() => window.print()">
            <Icon name="download" :size="15" /> Imprimir
          </Btn>
        </div>
      </div>
    </Modal>

    <!-- Modal: umbrales por categoría -->
    <Modal
      v-if="modalUmbrales"
      titulo="Umbrales de merma por categoría"
      size="lg"
      @cerrar="modalUmbrales = false"
    >
      <div class="space-y-4 text-[12px]">
        <p class="text-slate-600">
          El Jefe de Operaciones define el umbral aceptable de merma semanal por categoría (FR-017),
          vigente para toda la red. Superarlo genera una alerta de gestión pero nunca bloquea la
          operativa (FR-019).
        </p>

        <div
          v-if="!puedeEditarUmbrales"
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 p-3 text-slate-600"
        >
          <Icon name="shield" :size="16" class="shrink-0 text-brand-700" />
          <span>Vista de consulta. La definición de umbrales está asignada a la Jefatura de Operaciones.</span>
        </div>

        <form
          v-else
          class="flex flex-wrap items-end gap-3 rounded-xl border border-brand-200 bg-brand-50/50 p-4"
          @submit.prevent="guardarUmbral"
        >
          <div class="min-w-[160px] flex-1">
            <label class="mb-1 block text-[11px] font-semibold text-slate-700">Categoría</label>
            <input
              v-model="nuevoUmbral.product_category"
              required
              placeholder="p. ej. BEVERAGE, REFRIGERATED…"
              class="h-8 w-full rounded-lg border border-brand-300 bg-white px-2.5 text-[12px]"
            />
          </div>
          <div class="w-28">
            <label class="mb-1 block text-[11px] font-semibold text-slate-700">Umbral (%)</label>
            <input
              v-model="nuevoUmbral.porcentaje_umbral"
              type="number"
              step="0.1"
              min="0.1"
              max="100"
              required
              placeholder="1.5"
              class="h-8 w-full rounded-lg border border-brand-300 bg-white px-2.5 font-mono text-[12px]"
            />
          </div>
          <Btn type="submit" variant="primary" :disabled="guardandoUmbral">
            {{ guardandoUmbral ? 'Guardando…' : 'Fijar umbral' }}
          </Btn>
        </form>

        <div class="overflow-hidden rounded-xl border border-brand-200">
          <table class="w-full text-left text-[12px]">
            <thead>
              <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
                <th class="px-3 py-2.5">Categoría</th>
                <th class="px-3 py-2.5 text-right">Merma acumulada semanal</th>
                <th class="px-3 py-2.5 text-right">Umbral</th>
                <th class="px-3 py-2.5 text-center">Estado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-brand-100/90 bg-white/80">
              <tr v-if="!seguimientoSemanal.length">
                <td colspan="4" class="px-3 py-6 text-center text-slate-400">
                  Sin umbrales definidos o sin mermas de esas categorías esta semana.
                </td>
              </tr>
              <tr v-for="s in seguimientoSemanal" :key="s.product_category" class="hover:bg-brand-50/70">
                <td class="px-3 py-2 font-semibold text-slate-800">{{ s.product_category }}</td>
                <td class="px-3 py-2 text-right font-mono">
                  {{ s.porcentaje_merma_acumulado == null ? '—' : `${s.porcentaje_merma_acumulado}%` }}
                </td>
                <td class="px-3 py-2 text-right font-mono font-semibold">{{ s.porcentaje_umbral }}%</td>
                <td class="px-3 py-2 text-center">
                  <SemanticChip :tipo="s.supera_umbral ? 'quiebre' : 'ok'">
                    {{ s.supera_umbral ? 'Sobre umbral' : 'Dentro de rango' }}
                  </SemanticChip>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex justify-end pt-1">
          <Btn variant="ghost" @click="modalUmbrales = false">Cerrar</Btn>
        </div>
      </div>
    </Modal>
  </div>
</template>
