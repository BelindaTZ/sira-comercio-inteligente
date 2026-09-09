<script setup>
/**
 * Pronóstico de Demanda & Planificación Predictiva (feature 004, US1 + US3).
 * Arquetipo "Dashboard/BI" del kit. Todo lo que se muestra viene del backend:
 *  - modelos entrenados y su WAPE de validación (`/forecasting/modelos`),
 *  - historial de precisión semanal del modelo vigente (`/modelos/{id}/monitoreo`),
 *  - alertas de degradación (`/monitoreo/alertas`),
 *  - umbrales de gobernanza (`/configuracion`).
 * El Jefe de TI aprueba o rechaza modelos (SC-002); la Gerencia audita en lectura.
 * La consulta puntual de pronóstico por SKU (US2) usa `/productos/{id}/tiendas/{id}/pronostico`.
 */
import { computed, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useSesion } from '@/stores/sesion'
import { forecastingApi } from '@/services/forecastingApi'
import { prompt } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, MarkLineComponent])

const sesion = useSesion()
const puedeDecidir = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('TI', 'modelo_demanda'),
)

const modelos = ref([])
const vigente = ref(null)
const detalleVigente = ref(null)
const monitoreo = ref([])
const alertas = ref([])
const config = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const pct = (v) => (v == null ? '—' : `${(Number(v) * 100).toFixed(1)}%`)
const fechaCorta = (s) => (s ? String(s).slice(0, 10) : '—')

const umbralDegradacion = computed(() => {
  const f = config.value.find((c) => c.clave === 'umbral_degradacion_semanal_pct')
  return f ? Number(f.valor) : 0.45
})
const precisionMinima = computed(() => {
  const f = config.value.find((c) => c.clave === 'precision_minima_aprobacion')
  return f ? Number(f.valor) : 0.35
})
const historialMinimo = computed(() => {
  const f = config.value.find((c) => c.clave === 'historial_minimo_semanas')
  return f ? Number(f.valor) : 12
})

const pendientes = computed(() => modelos.value.filter((m) => m.estado === 'pendiente'))

const monitoreoOrdenado = computed(() =>
  [...monitoreo.value].sort((a, b) => a.anio - b.anio || a.semana - b.semana),
)
const ultimaMedicion = computed(
  () => monitoreoOrdenado.value[monitoreoOrdenado.value.length - 1] || null,
)
const tendencia = computed(() => {
  const serie = monitoreoOrdenado.value
  if (serie.length < 2) return null
  const previo = serie[Math.max(0, serie.length - 5)]
  return Number(ultimaMedicion.value.metrica_precision) - Number(previo.metrica_precision)
})

const kpiEstadoUltima = computed(() => {
  if (!ultimaMedicion.value) return 'neutral'
  return ultimaMedicion.value.supero_umbral_alerta ? 'quiebre' : 'ok'
})

const opcionesGrafico = computed(() => {
  const serie = monitoreoOrdenado.value
  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v) => `${(v * 100).toFixed(1)}%`,
    },
    grid: { left: 44, right: 20, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: serie.map((m) => `S${m.semana}·${String(m.anio).slice(2)}`),
      axisLabel: { fontSize: 11, color: '#64748b' },
    },
    yAxis: {
      type: 'value',
      name: 'WAPE',
      min: 0,
      axisLabel: { formatter: (v) => `${(v * 100).toFixed(0)}%`, fontSize: 11, color: '#64748b' },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [
      {
        name: 'WAPE semanal',
        type: 'line',
        smooth: true,
        symbolSize: 7,
        data: serie.map((m) => Number(m.metrica_precision)),
        itemStyle: { color: '#0f766e' },
        lineStyle: { width: 3, color: '#0f766e' },
        areaStyle: { color: 'rgba(15,118,110,0.08)' },
        markLine: {
          symbol: 'none',
          data: [{ yAxis: umbralDegradacion.value }],
          lineStyle: { type: 'dashed', color: '#be123c', width: 2 },
          label: {
            formatter: `Umbral de degradación · ${(umbralDegradacion.value * 100).toFixed(0)}%`,
            color: '#be123c',
            fontSize: 11,
            position: 'insideEndTop',
          },
        },
      },
    ],
  }
})

function msg(e) {
  return e.response?.data?.error?.message || e.message || 'No se pudo cargar el pronóstico.'
}

async function cargar(conAviso = false) {
  cargando.value = true
  error.value = ''
  try {
    const [mods, cfgs, alerts] = await Promise.all([
      forecastingApi.modelos(),
      forecastingApi.configuracion().catch(() => []),
      forecastingApi.alertasMonitoreo().catch(() => []),
    ])
    modelos.value = mods || []
    config.value = cfgs || []
    alertas.value = alerts || []
    vigente.value = modelos.value.find((m) => m.estado === 'aprobado') || null
    if (vigente.value) {
      const [det, mon] = await Promise.all([
        forecastingApi.detalleModelo(vigente.value.modelo_id).catch(() => null),
        forecastingApi.monitoreoDeModelo(vigente.value.modelo_id).catch(() => []),
      ])
      detalleVigente.value = det
      monitoreo.value = mon || []
    } else {
      detalleVigente.value = null
      monitoreo.value = []
    }
    if (conAviso) aviso.value = 'Datos de pronóstico actualizados.'
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

async function entrenar() {
  aviso.value = ''
  error.value = ''
  try {
    const r = await forecastingApi.forzarEntrenamiento()
    aviso.value = r?.entrenado
      ? `Modelo #${r.modelo_id} entrenado (WAPE ${pct(r.wape_validacion)}). Queda pendiente de tu revisión.`
      : `Reentrenamiento ejecutado: ${r?.motivo || 'sin cambios'}.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  }
}

async function aprobar(m) {
  error.value = ''
  try {
    await forecastingApi.aprobarModelo(m.modelo_id)
    aviso.value = `Modelo #${m.modelo_id} aprobado — ahora es el vigente en producción.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  }
}

async function rechazar(m) {
  const motivo = await prompt({
    title: `Rechazar el modelo #${m.modelo_id}`,
    message: 'El modelo vigente actual (si existe) sigue en producción sin interrupción.',
    label: 'Motivo del rechazo',
    required: true,
    tone: 'danger',
    confirmText: 'Rechazar modelo',
  })
  if (!motivo) return
  error.value = ''
  try {
    await forecastingApi.rechazarModelo(m.modelo_id, motivo)
    aviso.value = `Modelo #${m.modelo_id} rechazado.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  }
}

// ---- consulta puntual de pronóstico por SKU (US2) ---------------------
const modalConsulta = ref(false)
const consulta = ref({ tiendaId: sesion.tiendaId ?? '', semana: '', anio: '' })
const consultando = ref(false)
const resultadoConsulta = ref(null)
const errorConsulta = ref('')

// autocompletado de producto + catálogo de tiendas
const tiendasOpc = ref([])
const productoTexto = ref('')
const productoOpciones = ref([])
const productoElegido = ref(null)
const buscandoProducto = ref(false)
let debProducto

function abrirConsulta() {
  const iso = new Date()
  const inicio = new Date(iso.getFullYear(), 0, 1)
  consulta.value = {
    tiendaId: sesion.tiendaId ?? '',
    semana: Math.ceil(((iso - inicio) / 86400000 + inicio.getDay() + 1) / 7),
    anio: iso.getFullYear(),
  }
  productoTexto.value = ''
  productoOpciones.value = []
  productoElegido.value = null
  resultadoConsulta.value = null
  errorConsulta.value = ''
  modalConsulta.value = true
  if (!tiendasOpc.value.length) {
    forecastingApi.tiendasPronostico().then((t) => (tiendasOpc.value = t)).catch(() => {})
  }
}

function buscarProducto() {
  productoElegido.value = null
  clearTimeout(debProducto)
  const q = productoTexto.value.trim()
  if (q.length < 2) {
    productoOpciones.value = []
    return
  }
  debProducto = setTimeout(async () => {
    buscandoProducto.value = true
    try {
      productoOpciones.value = await forecastingApi.opcionesProductoPronostico(q)
    } catch {
      productoOpciones.value = []
    } finally {
      buscandoProducto.value = false
    }
  }, 250)
}

function elegirProducto(p) {
  productoElegido.value = p
  productoTexto.value = `${p.nombre || 'Producto'} · #${p.product_id}`
  productoOpciones.value = []
}

async function ejecutarConsulta() {
  errorConsulta.value = ''
  resultadoConsulta.value = null
  const { tiendaId, semana, anio } = consulta.value
  if (!productoElegido.value || !tiendaId || !semana || !anio) {
    errorConsulta.value = 'Elegí un producto de la lista y completá tienda, semana y año.'
    return
  }
  consultando.value = true
  try {
    resultadoConsulta.value = await forecastingApi.pronostico(
      productoElegido.value.product_id,
      Number(tiendaId),
      { semana: Number(semana), anio: Number(anio) },
    )
  } catch (e) {
    errorConsulta.value = msg(e)
  } finally {
    consultando.value = false
  }
}

onMounted(() => cargar())
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Pronóstico de demanda & planificación predictiva"
      subtitulo="El sistema entrena mensualmente un modelo de demanda por producto y tienda con el historial de ventas, promociones, cambios de precio y quiebres del período. Ningún modelo pasa a producción sin la aprobación del Jefe de TI (SC-002), y su precisión se vigila semana a semana."
    >
      <template #badge>
        <SemanticChip :tipo="vigente ? 'ok' : 'fifo'">
          {{ vigente ? `Modelo vigente #${vigente.modelo_id}` : 'Sin modelo en producción' }}
        </SemanticChip>
        <SemanticChip v-if="pendientes.length" tipo="fifo">
          {{ pendientes.length }} pendiente{{ pendientes.length === 1 ? '' : 's' }} de revisión
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn variant="ghost" @click="abrirConsulta">
          <Icon name="search" :size="16" /> Consultar pronóstico de un SKU
        </Btn>
        <Btn variant="ghost" @click="cargar(true)">
          <Icon name="chart" :size="16" /> Actualizar
        </Btn>
        <Btn v-if="puedeDecidir" variant="ia" @click="entrenar">
          <Icon name="bolt" :size="16" /> Forzar reentrenamiento
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

    <!-- KPIs -->
    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Modelo vigente en producción"
        :valor="vigente ? `#${vigente.modelo_id}` : '—'"
        variant="emerald"
        :microcopy="vigente ? `Entrenado el ${fechaCorta(vigente.fecha_entrenamiento)}` : 'Todos los productos usan el respaldo por rotación reciente'"
        pie-label="WAPE de validación"
        :pie-valor="vigente ? pct(vigente.metrica_precision_validacion) : '—'"
      />
      <KpiTile
        label="Precisión última semana (WAPE)"
        :valor="ultimaMedicion ? pct(ultimaMedicion.metrica_precision) : '—'"
        :estado="ultimaMedicion ? (ultimaMedicion.supero_umbral_alerta ? 'Sobre el umbral' : 'Dentro del umbral') : ''"
        :estado-tipo="kpiEstadoUltima"
        :microcopy="`Umbral de degradación configurado: ${pct(umbralDegradacion)} · menor WAPE = mejor`"
      >
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Tendencia de precisión"
        :valor="tendencia == null ? '—' : `${tendencia > 0 ? '+' : ''}${(tendencia * 100).toFixed(1)} pp`"
        :estado="tendencia == null ? '' : tendencia > 0 ? 'Se degrada' : 'Mejora o estable'"
        :estado-tipo="tendencia == null ? 'neutral' : tendencia > 0.03 ? 'quiebre' : 'ok'"
        microcopy="Cambio del WAPE frente a ~4 semanas atrás"
      >
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Cobertura del pronóstico"
        :valor="detalleVigente ? (detalleVigente.productos_cubiertos || 0).toLocaleString('es-EC') : '—'"
        estado-tipo="neutral"
        :microcopy="`Combinaciones producto/tienda con pronóstico propio · el resto usa rotación reciente (mín. ${historialMinimo} semanas de historial)`"
      >
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
    </section>

    <!-- Curva de precisión semanal -->
    <section class="mb-6 satin-card rounded-2xl p-5 shadow-card-subtle">
      <div class="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 class="font-display text-base font-bold text-brand-950">
          Precisión del modelo en producción — WAPE semanal
        </h2>
        <SemanticChip v-if="alertas.length" tipo="quiebre">
          {{ alertas.length }} semana{{ alertas.length === 1 ? '' : 's' }} sobre el umbral
        </SemanticChip>
      </div>
      <p class="mb-3 text-[12px] text-slate-600">
        Cada semana el sistema compara el pronóstico del modelo vigente contra la demanda ya
        observada (FR-011). Si el error supera el umbral, se levanta una alerta para el Jefe de TI
        (FR-012).
      </p>
      <div v-if="monitoreoOrdenado.length" class="h-[300px] w-full">
        <VChart :option="opcionesGrafico" autoresize />
      </div>
      <p
        v-else
        class="grid h-[220px] place-items-center rounded-xl border border-dashed border-brand-200 text-[13px] text-slate-500"
      >
        {{ vigente ? 'El modelo vigente todavía no tiene semanas cerradas para comparar.' : 'Aprobá un modelo para empezar a medir su precisión en producción.' }}
      </p>
    </section>

    <!-- Gobernanza de modelos -->
    <section class="mb-6 satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-brand-200 px-5 py-3.5">
        <div>
          <h2 class="font-display text-base font-bold text-brand-950">Gobernanza de modelos (SC-002)</h2>
          <p class="text-[12px] text-slate-600">
            WAPE de validación de referencia para aprobar: {{ pct(precisionMinima) }} o mejor.
          </p>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[720px] text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[11px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-5 py-3">Modelo</th>
              <th class="px-4 py-3">Entrenado</th>
              <th class="px-4 py-3 text-right">WAPE validación</th>
              <th class="px-4 py-3 text-center">Estado</th>
              <th class="px-4 py-3">Resolución</th>
              <th class="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="!modelos.length && !cargando">
              <td colspan="6" class="px-5 py-10 text-center text-slate-500">
                Todavía no se ha entrenado ningún modelo de demanda.
              </td>
            </tr>
            <tr v-for="m in modelos" :key="m.modelo_id" class="hover:bg-brand-50/70">
              <td class="px-5 py-3">
                <span class="font-mono font-semibold text-brand-900">#{{ m.modelo_id }}</span>
                <span v-if="m.estado === 'aprobado'" class="ml-2 text-[11px] font-bold text-emerald-700">
                  vigente
                </span>
              </td>
              <td class="px-4 py-3 text-slate-600">{{ fechaCorta(m.fecha_entrenamiento) }}</td>
              <td
                class="px-4 py-3 text-right font-bold tabular-nums"
                :class="
                  m.metrica_precision_validacion == null ? 'text-slate-400'
                  : Number(m.metrica_precision_validacion) <= precisionMinima ? 'text-emerald-700'
                  : 'text-amber-700'
                "
              >
                {{ pct(m.metrica_precision_validacion) }}
              </td>
              <td class="px-4 py-3 text-center">
                <SemanticChip
                  :tipo="
                    m.estado === 'aprobado' ? 'ok'
                    : m.estado === 'pendiente' ? 'fifo'
                    : m.estado === 'rechazado' ? 'quiebre' : 'neutral'
                  "
                >
                  {{ m.estado }}
                </SemanticChip>
              </td>
              <td class="px-4 py-3 text-[12px] text-slate-500">
                <template v-if="m.fecha_resolucion">
                  {{ fechaCorta(m.fecha_resolucion) }}
                  <span v-if="m.observaciones" class="block text-slate-400">{{ m.observaciones }}</span>
                </template>
                <span v-else>—</span>
              </td>
              <td class="px-4 py-3 text-right">
                <div v-if="m.estado === 'pendiente' && puedeDecidir" class="flex justify-end gap-1.5">
                  <Btn variant="primary" class="!px-2.5 !py-1 !text-[12px]" @click="aprobar(m)">
                    Aprobar
                  </Btn>
                  <Btn variant="danger" class="!px-2.5 !py-1 !text-[12px]" @click="rechazar(m)">
                    Rechazar
                  </Btn>
                </div>
                <span v-else class="text-[11px] text-slate-400">
                  {{ m.estado === 'pendiente' ? 'Requiere Jefe de TI' : '—' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Alertas de degradación -->
    <section v-if="alertas.length" class="mb-6">
      <h2 class="mb-1 font-display text-base font-bold text-brand-950">Alertas de degradación abiertas</h2>
      <p class="mb-3 text-[12px] text-slate-600">
        Semanas en que la precisión del modelo vigente cayó por debajo del umbral configurado.
      </p>
      <ul class="space-y-2">
        <li
          v-for="a in alertas"
          :key="`${a.modelo_id}-${a.anio}-${a.semana}`"
          class="flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50/70 px-4 py-2.5 text-[13px]"
        >
          <span class="flex items-center gap-2 text-rose-900">
            <Icon name="alert" :size="15" class="text-rose-600" />
            Modelo #{{ a.modelo_id }} · semana {{ a.semana }} de {{ a.anio }}
          </span>
          <span class="font-bold tabular-nums text-crimson-ruby">WAPE {{ pct(a.metrica_precision) }}</span>
        </li>
      </ul>
    </section>

    <!-- Modal: consulta puntual de pronóstico por SKU -->
    <Modal v-if="modalConsulta" titulo="Consultar pronóstico de un SKU" size="md" @cerrar="modalConsulta = false">
      <p class="mb-4 text-[12px] text-slate-600">
        Devuelve la cantidad pronosticada por el modelo vigente para un producto y tienda en una
        semana dada. Si no hay pronóstico propio, la reposición usa el respaldo por rotación reciente
        (FR-008).
      </p>
      <form class="space-y-3" @submit.prevent="ejecutarConsulta">
        <div class="relative">
          <label class="block text-[12px] font-semibold text-slate-600">
            Producto
            <input
              v-model="productoTexto"
              placeholder="Buscá por nombre o ID…"
              autocomplete="off"
              class="mt-1 block w-full rounded-lg border px-3 py-2 text-sm text-slate-800"
              :class="productoElegido ? 'border-emerald-400 bg-emerald-50/40' : 'border-brand-300 bg-white'"
              @input="buscarProducto"
            />
          </label>
          <ul
            v-if="productoOpciones.length"
            class="absolute z-10 mt-1 max-h-52 w-full overflow-y-auto rounded-lg border border-brand-200 bg-white shadow-tier-2"
          >
            <li
              v-for="p in productoOpciones"
              :key="p.product_id"
              class="cursor-pointer px-3 py-2 text-[13px] hover:bg-brand-50"
              @click="elegirProducto(p)"
            >
              <span class="font-semibold text-slate-800">{{ p.nombre || 'Producto sin nombre' }}</span>
              <span class="ml-1.5 font-mono text-[11px] text-slate-400">#{{ p.product_id }}</span>
              <span v-if="p.product_category" class="block text-[11px] text-slate-400">{{ p.product_category }}</span>
            </li>
          </ul>
          <p
            v-else-if="productoTexto.trim().length >= 2 && !buscandoProducto && !productoElegido"
            class="mt-1 text-[11px] text-slate-400"
          >
            Sin productos con pronóstico que coincidan.
          </p>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <label class="col-span-3 block text-[12px] font-semibold text-slate-600 sm:col-span-1">
            Tienda
            <select
              v-model="consulta.tiendaId"
              required
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            >
              <option value="" disabled>Elegí una tienda…</option>
              <option v-for="t in tiendasOpc" :key="t.tienda_id" :value="t.tienda_id">
                {{ t.nombre }}
              </option>
            </select>
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Semana ISO
            <input
              v-model="consulta.semana"
              type="number"
              min="1"
              max="53"
              required
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Año
            <input
              v-model="consulta.anio"
              type="number"
              required
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            />
          </label>
        </div>
        <p v-if="errorConsulta" class="text-[12px] text-crimson-ruby">{{ errorConsulta }}</p>
        <div
          v-if="resultadoConsulta"
          class="rounded-xl border px-4 py-3 text-[13px]"
          :class="resultadoConsulta.pronostico_disponible ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-amber-200 bg-amber-50 text-amber-900'"
        >
          <template v-if="resultadoConsulta.pronostico_disponible">
            Pronóstico del modelo #{{ resultadoConsulta.modelo_id }}:
            <b class="tabular-nums">{{ Number(resultadoConsulta.cantidad_pronosticada).toFixed(1) }}</b>
            unidades para la semana {{ resultadoConsulta.semana }}/{{ resultadoConsulta.anio }}.
          </template>
          <template v-else>
            Sin pronóstico vigente para ese producto/tienda/semana — la reposición usa el respaldo
            por rotación reciente (FR-008).
          </template>
        </div>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modalConsulta = false">Cerrar</Btn>
          <Btn variant="primary" type="submit" :disabled="consultando">
            {{ consultando ? 'Consultando…' : 'Consultar' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
