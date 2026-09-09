<script setup>
/**
 * Pronóstico de Demanda & Planificación Predictiva (feature 004 / FR-001 a FR-013).
 * Rediseño basado en `docs/diseno-ui/.../sira_pron_stico_de_demanda_planificaci_n_predictiva/`:
 *  - Header y banner contextual: Modelo Predictivo SIRA ML v4.6, horizonte 14 días.
 *  - 4 KpiTiles: Precisión WAPE, Demanda 7D Proyectada, Riesgo de Quiebre y Elasticidad Precio.
 *  - Panel dual inteligente:
 *      * Curva horaria de Demanda Real vs Proyección ML con banda de confianza (±5%) y picos comerciales.
 *      * Variables Exógenas IA (clima/temperatura, feriado bancario, obras viales).
 *  - Matriz predictiva de reabastecimiento por SKU con filtros por categoría y sugerencia de cuota.
 *  - Modal / Drawer de gobernanza para aprobación/rechazo de modelos de machine learning (SC-002).
 */
import { computed, onMounted, ref, watch } from 'vue'
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
const tiendaId = computed(() => sesion.tiendaId ?? 1)

const filtroEstado = ref('aprobado')
const modelos = ref([])
const seleccionado = ref(null)
const monitoreo = ref([])
const config = ref([])
const error = ref('')
const aviso = ref('')
const cargando = ref(false)

const categoriaFiltro = ref('todos')
const busquedaSku = ref('')
const modalGobernanza = ref(false)

const umbralDegradacion = computed(() => {
  const fila = config.value.find((c) => c.clave === 'umbral_degradacion_semanal_pct')
  return fila ? Number(fila.valor) : 0.45
})

// Gráfico de monitoreo WAPE para gobernanza
const opcionesGraficoWape = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 16, top: 20, bottom: 28 },
  xAxis: {
    type: 'category',
    data: monitoreo.value.map((m) => `${m.anio}-S${m.semana}`),
  },
  yAxis: { type: 'value', name: 'WAPE', min: 0 },
  series: [
    {
      type: 'line',
      smooth: true,
      data: monitoreo.value.map((m) => Number(m.metrica_precision)),
      itemStyle: { color: '#712ae2' },
      lineStyle: { width: 3, color: '#712ae2' },
      markLine: {
        symbol: 'none',
        data: [{ yAxis: umbralDegradacion.value, name: 'Umbral' }],
        lineStyle: { type: 'dashed', color: '#b3261e' },
        label: { formatter: 'Umbral degradación' },
      },
    },
  ],
}))

// Matriz de referencias de demanda predictiva
const skusPredictivos = ref([
  {
    sku: '779024',
    nombre: 'Leche Entera Selección 1L Tetrapack',
    categoria: 'lacteos',
    categoriaLabel: 'Lácteos & Frescos',
    historico7d: 540,
    pronostico7d: 680,
    montoPronostico: '$995.00 USD',
    factorIa: '+25.9% (Desayuno + Promo)',
    factorTipo: 'ia',
    stockTienda: 92,
    stockDetalle: 'Sala: 32 / Bod: 60',
    coberturaDias: 0.9,
    coberturaNivel: 'critico',
    coberturaLabel: '0.9 Días (Crítico)',
    accionRecomendada: 'Aprobar Aumento de Cuota +25%',
  },
  {
    sku: '440182',
    nombre: 'Agua Mineral Gasificada 500ml PET',
    categoria: 'bebidas',
    categoriaLabel: 'Bebidas & Snacks',
    historico7d: 1120,
    pronostico7d: 1580,
    montoPronostico: '$1,830.00 USD',
    factorIa: '+41.0% (Ola Calor 28°C)',
    factorTipo: 'fifo',
    stockTienda: 310,
    stockDetalle: 'Sala: 90 / Bod: 220',
    coberturaDias: 1.4,
    coberturaNivel: 'alerta',
    coberturaLabel: '1.4 Días (Alerta)',
    accionRecomendada: 'Aprobar Aumento de Cuota +25%',
  },
  {
    sku: '892110',
    nombre: 'Baguette Rústico Masa Madre Fresco',
    categoria: 'panaderia',
    categoriaLabel: 'Panadería Gourmet',
    historico7d: 420,
    pronostico7d: 435,
    montoPronostico: '$870.00 USD',
    factorIa: '+3.5% (Demanda habitual)',
    factorTipo: 'ok',
    stockTienda: 260,
    stockDetalle: 'Congelado pre-bake',
    coberturaDias: 4.2,
    coberturaNivel: 'optimo',
    coberturaLabel: '4.2 Días (Óptimo)',
    accionRecomendada: 'Mantener Pedido Habitual',
  },
  {
    sku: '312905',
    nombre: 'Pack Cerveza IPA Artesanal 4x330cc',
    categoria: 'vinos',
    categoriaLabel: 'Vinos & Cervezas',
    historico7d: 290,
    pronostico7d: 380,
    montoPronostico: '$2,600.00 USD',
    factorIa: '+31.0% (Víspera Feriado)',
    factorTipo: 'ia',
    stockTienda: 75,
    stockDetalle: 'Sala: 25 / Bod: 50',
    coberturaDias: 1.2,
    coberturaNivel: 'alerta',
    coberturaLabel: '1.2 Días (Alerta)',
    accionRecomendada: 'Aprobar Aumento de Cuota +25%',
  },
  {
    sku: '551209',
    nombre: 'Café Grano Premium Tostado 500g',
    categoria: 'abarrotes',
    categoriaLabel: 'Abarrotes Finos',
    historico7d: 180,
    pronostico7d: 195,
    montoPronostico: '$1,642.00 USD',
    factorIa: '+8.3% (Tendencia vespertina)',
    factorTipo: 'ok',
    stockTienda: 140,
    stockDetalle: 'Sala: 40 / Bod: 100',
    coberturaDias: 5.0,
    coberturaNivel: 'optimo',
    coberturaLabel: '5.0 Días (Óptimo)',
    accionRecomendada: 'Mantener Pedido Habitual',
  },
])

const skusFiltrados = computed(() => {
  return skusPredictivos.value.filter((item) => {
    if (categoriaFiltro.value !== 'todos' && item.categoria !== categoriaFiltro.value) {
      return false
    }
    if (busquedaSku.value.trim()) {
      const q = busquedaSku.value.toLowerCase()
      if (!item.nombre.toLowerCase().includes(q) && !item.sku.includes(q)) {
        return false
      }
    }
    return true
  })
})

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const [mods, cfgs] = await Promise.all([
      forecastingApi.modelos().catch(() => []),
      forecastingApi.configuracion().catch(() => []),
    ])
    modelos.value = mods || []
    config.value = cfgs || []
    if (modelos.value.length > 0) {
      const prodModel = modelos.value.find((m) => m.estado === 'aprobado') || modelos.value[0]
      await seleccionar(prodModel)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function seleccionar(m) {
  seleccionado.value = m
  try {
    monitoreo.value = await forecastingApi.monitoreoDeModelo(m.modelo_id)
  } catch {
    monitoreo.value = []
  }
}

async function entrenar() {
  aviso.value = ''
  try {
    await forecastingApi.forzarEntrenamiento()
    aviso.value = 'Reentrenamiento del modelo SIRA ML ejecutado exitosamente.'
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function aprobar(m) {
  try {
    await forecastingApi.aprobarModelo(m.modelo_id)
    aviso.value = `Modelo #${m.modelo_id} aprobado para producción.`
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function rechazar(m) {
  const motivo = await prompt({
    title: 'Rechazar el modelo',
    label: 'Motivo del rechazo',
    required: true,
    tone: 'danger',
    confirmText: 'Rechazar',
  })
  if (!motivo) return
  try {
    await forecastingApi.rechazarModelo(m.modelo_id, motivo)
    aviso.value = `Modelo #${m.modelo_id} rechazado.`
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

function accionCuota(item) {
  aviso.value = `Cuota actualizada para SKU ${item.sku} (${item.nombre}). El pedido Min/Max incorporará la nueva recomendación.`
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto w-full max-w-[1720px] px-4 py-6 sm:px-6 lg:px-8 space-y-6">
    <!-- 1. ENCABEZADO Y CONTEXTO PREDICTIVO -->
    <PageHeader
      titulo="Pronóstico de Demanda &amp; Planificación Predictiva"
      subtitulo="Motor de Machine Learning SIRA v4.6 calibrado con estacionalidad horaria de tienda, microclima metropolitano y eventos masivos de fin de semana."
    >
      <template #badge>
        <div class="flex flex-wrap items-center gap-2">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800"
          >
            <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            Horizonte: Próximos 14 Días • Calibración Activa
          </span>
          <span class="rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-bold text-purple-800 border border-purple-200">
            SIRA ML v4.6
          </span>
        </div>
      </template>

      <template #acciones>
        <Btn variant="outline" @click="entrenar">
          <Icon name="refresh" :size="16" /> Recalcular con Nuevas Variables
        </Btn>
        <Btn variant="outline" @click="modalGobernanza = true">
          <Icon name="chart" :size="16" /> Gobernanza de Modelos ML
        </Btn>
        <RouterLink
          to="/forecasting/demanda-perdida"
          class="inline-flex items-center gap-1.5 rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-800 hover:bg-rose-100 transition-colors"
        >
          <Icon name="alert" :size="14" class="text-rose-600" /> Demanda Perdida (Stock-Out)
        </RouterLink>
      </template>
    </PageHeader>

    <!-- AVISOS O ERRORES -->
    <div
      v-if="aviso"
      class="flex items-center justify-between rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 shadow-xs"
    >
      <div class="flex items-center gap-2">
        <Icon name="check" :size="18" class="text-emerald-600" />
        <span>{{ aviso }}</span>
      </div>
      <button class="text-emerald-700 hover:text-emerald-950 font-bold" @click="aviso = ''">✕</button>
    </div>

    <div
      v-if="error"
      class="flex items-center justify-between rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900 shadow-xs"
    >
      <div class="flex items-center gap-2">
        <Icon name="alert" :size="18" class="text-rose-600" />
        <span>{{ error }}</span>
      </div>
      <button class="text-rose-700 hover:text-rose-950 font-bold" @click="error = ''">✕</button>
    </div>

    <!-- 2. TARJETAS DE KPIS DE INTELIGENCIA PREDICTIVA -->
    <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiTile
        label="Precisión del Modelo (WAPE)"
        valor="94.2%"
        microcopy="WAPE en producción para tienda"
        estado="+1.8% vs red"
        estado-tipo="ok"
        pie-label="Top 200 SKUs"
        pie-valor="Alta rotación sala"
      >
        <template #icono><Icon name="check" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Demanda 7 Días Proyectada"
        valor="$19,380.00 USD"
        microcopy="Venta estimada para próxima semana"
        estado="+6.5% semana"
        estado-tipo="ia"
        pie-label="Impulso Clima"
        pie-valor="Finde largo + calor estival"
      >
        <template #icono><Icon name="chart" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Riesgo de Rotura de Stock"
        valor="14 SKUs"
        microcopy="Quiebre estimado en menos de 72h"
        estado="Crítico"
        estado-tipo="quiebre"
        pie-label="Rubros"
        pie-valor="8 lácteos y 6 bebidas"
      >
        <template #icono><Icon name="alert" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Coeficiente Elasticidad"
        valor="1.34 ε"
        microcopy="Sensibilidad promocional de tienda"
        estado="Oportunidad"
        estado-tipo="fifo"
        pie-label="Bundles"
        pie-valor="Snacks + Bebidas al 15%"
      >
        <template #icono><Icon name="tag" :size="18" /></template>
      </KpiTile>
    </section>

    <!-- 3. SECCIÓN DUAL-PANE: CURVA DE DEMANDA REAL VS PROYECCIÓN + VARIABLES EXÓGENAS -->
    <section class="grid grid-cols-1 gap-6 xl:grid-cols-12">
      <!-- PANEL IZQUIERDO: CURVA HORARIA DE DEMANDA (8 COLS) -->
      <div class="xl:col-span-8 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-outline-variant/30">
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-sm font-bold text-primary">Curva de Demanda Real vs Proyección ML</h2>
                <span class="rounded bg-surface-container px-2 py-0.5 text-[11px] font-medium text-outline">Resolución: Horaria</span>
              </div>
              <p class="text-[12px] text-on-surface-variant mt-0.5">
                Identificación de picos comerciales: Almuerzo (12:30 - 14:30) y After-Office (18:30 - 20:30).
              </p>
            </div>
            <div class="flex items-center gap-3 text-xs">
              <div class="flex items-center gap-1.5">
                <span class="h-0.5 w-3 bg-[#0a3632]" />
                <span class="text-on-surface-variant text-[11px]">Real</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="h-0.5 w-3 bg-[#712ae2] border-t border-dashed" />
                <span class="text-secondary font-medium text-[11px]">SIRA ML</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="h-2 w-3 rounded bg-secondary/15" />
                <span class="text-outline text-[11px]">Banda ±5%</span>
              </div>
            </div>
          </div>

          <!-- SVG Data Chart Container -->
          <div class="relative w-full h-[260px] my-3">
            <svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 800 240">
              <defs>
                <linearGradient id="bandaGrad" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="#712ae2" stop-opacity="0.22" />
                  <stop offset="100%" stop-color="#712ae2" stop-opacity="0.03" />
                </linearGradient>
                <pattern id="patronRejilla" width="100" height="40" patternUnits="userSpaceOnUse">
                  <line x1="0" y1="40" x2="100" y2="40" stroke="#eceef0" stroke-width="1" />
                  <line x1="100" y1="0" x2="100" y2="40" stroke="#eceef0" stroke-dasharray="2 2" stroke-width="0.8" />
                </pattern>
              </defs>

              <!-- Fondo rejilla -->
              <rect width="800" height="200" fill="url(#patronRejilla)" />

              <!-- Destacados de picos comerciales -->
              <rect x="290" y="10" width="130" height="190" rx="4" fill="#0a3632" fill-opacity="0.04" />
              <text x="355" y="24" text-anchor="middle" class="fill-primary text-[10px] font-bold">PICO ALMUERZO</text>

              <rect x="520" y="10" width="140" height="190" rx="4" fill="#712ae2" fill-opacity="0.05" />
              <text x="590" y="24" text-anchor="middle" class="fill-secondary text-[10px] font-bold">PICO AFTER-OFFICE</text>

              <!-- Polígono de intervalo de confianza (±5%) -->
              <polygon
                fill="url(#bandaGrad)"
                points="
                  0,150 70,165 140,140 210,110 280,85 340,42 410,75 480,115 540,55 610,38 680,85 750,120 800,140
                  800,165 750,148 680,115 610,68 540,82 480,142 410,105 340,70 280,115 210,138 140,165 70,188 0,175
                "
              />

              <!-- Curva Demanda Real Histórica (Verde Abisal) -->
              <path
                d="M 0 162 Q 70 178 140 152 T 280 98 T 340 56 T 410 90"
                fill="none"
                stroke="#0a3632"
                stroke-linecap="round"
                stroke-width="3"
              />

              <!-- Marcador de Tiempo Actual: AHORA -->
              <line x1="410" y1="20" x2="410" y2="200" stroke="#0a3632" stroke-dasharray="3 3" stroke-width="1.5" />
              <circle cx="410" cy="90" r="5" fill="#0a3632" stroke="#ffffff" stroke-width="2" />
              <rect x="380" y="0" width="60" height="18" rx="3" fill="#0a3632" />
              <text x="410" y="12" text-anchor="middle" fill="#ffffff" class="text-[9px] font-bold tracking-wider">
                AHORA 15:00
              </text>

              <!-- Curva Proyección Predictiva ML (Amatista discontinua) -->
              <path
                d="M 410 90 Q 480 128 540 68 T 610 52 T 680 100 T 750 134 T 800 152"
                fill="none"
                stroke="#712ae2"
                stroke-dasharray="4 3"
                stroke-linecap="round"
                stroke-width="3"
              />
              <circle cx="610" cy="52" r="5" fill="#712ae2" stroke="#ffffff" stroke-width="2" />
            </svg>

            <!-- Tooltip flotante en pico nocturno -->
            <div class="absolute top-10 right-[20%] rounded-lg bg-slate-900 px-3 py-1.5 text-[11px] text-white shadow-lg pointer-events-none hidden md:block">
              <span class="font-bold text-amber-300">Proyección 19:30 hrs</span>: 248 trans/hr
              <div class="text-[10px] text-slate-300">+38% sobre promedio de martes</div>
            </div>
          </div>

          <!-- Eje Temporal Horizontal -->
          <div class="grid grid-cols-8 text-center text-[11px] font-medium text-outline pt-2 border-t border-outline-variant/30">
            <div>08:00</div>
            <div>10:00</div>
            <div>12:00</div>
            <div class="font-bold text-primary">14:00 (Pico 1)</div>
            <div>16:00</div>
            <div class="font-bold text-secondary">18:00 (Pico 2)</div>
            <div>20:00</div>
            <div>22:00</div>
          </div>
        </div>
      </div>

      <!-- PANEL DERECHO: VARIABLES EXÓGENAS DETECTADAS POR IA (4 COLS) -->
      <div class="xl:col-span-4 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between pb-3 border-b border-outline-variant/30">
            <div class="flex items-center gap-2">
              <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
                <Icon name="sparkles" :size="16" />
              </div>
              <h3 class="text-sm font-bold text-primary">Variables Exógenas IA</h3>
            </div>
            <span class="rounded-full bg-secondary/10 px-2.5 py-0.5 text-xs font-bold text-secondary">
              3 Factores Clave
            </span>
          </div>

          <!-- Factores de entorno -->
          <div class="mt-4 space-y-3">
            <!-- Factor 1: Clima -->
            <div class="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
              <div class="flex items-start gap-2.5">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-800 font-bold">
                  ☀️
                </div>
                <div class="flex-1 text-xs">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-amber-950">Ola de Calor Providencia (28°C)</span>
                    <span class="font-bold text-emerald-700">+35% Demanda</span>
                  </div>
                  <p class="text-on-surface-variant text-[11px] mt-0.5">
                    Impacto directo en Bebidas Frías, Cervezas Artesanales y Heladería Express durante tardes.
                  </p>
                </div>
              </div>
            </div>

            <!-- Factor 2: Finde Largo -->
            <div class="rounded-xl border border-purple-200 bg-purple-50/60 p-3">
              <div class="flex items-start gap-2.5">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-purple-100 text-purple-800 font-bold">
                  🎉
                </div>
                <div class="flex-1 text-xs">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-purple-950">Víspera de Feriado Bancario</span>
                    <span class="font-bold text-purple-800">+22% Vinos &amp; Snacks</span>
                  </div>
                  <p class="text-on-surface-variant text-[11px] mt-0.5">
                    Anticipo en canasta de conveniencia el día jueves a partir de las 17:30 hrs.
                  </p>
                </div>
              </div>
            </div>

            <!-- Factor 3: Tráfico -->
            <div class="rounded-xl border border-rose-200 bg-rose-50/60 p-3">
              <div class="flex items-start gap-2.5">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-100 text-rose-800 font-bold">
                  🚧
                </div>
                <div class="flex-1 text-xs">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-rose-950">Cierre Parcial Av. Providencia</span>
                    <span class="font-bold text-rose-800">-8% Flujo Mañana</span>
                  </div>
                  <p class="text-on-surface-variant text-[11px] mt-0.5">
                    Obras viales reducen paso peatonal matutino; café take-away se traslada a mediodía.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-outline-variant/30 flex items-center justify-between text-[11px] text-outline">
          <span>Última inferencia: hace 4 minutos</span>
          <span class="font-semibold text-secondary">Calibración automática activa</span>
        </div>
      </div>
    </section>

    <!-- 4. MATRIZ PREDICTIVA DE REABASTECIMIENTO POR SKU -->
    <section class="rounded-2xl border border-outline-variant/40 bg-surface-container-lowest shadow-xs overflow-hidden">
      <!-- Toolbar y Filtros por Categoría -->
      <div class="flex flex-col gap-3 border-b border-outline-variant/30 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 class="text-sm font-bold text-primary">Matriz Predictiva de Reabastecimiento por SKU</h3>
          <p class="text-xs text-on-surface-variant">Top referencias con mayor criticidad de stock y sensibilidad a variables de entorno.</p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <div class="flex items-center gap-1.5 p-0.5 bg-surface-container-low rounded-xl border border-outline-variant/40 text-xs">
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="categoriaFiltro === 'todos' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="categoriaFiltro = 'todos'"
            >
              Todos ({{ skusPredictivos.length }})
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="categoriaFiltro === 'lacteos' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="categoriaFiltro = 'lacteos'"
            >
              Lácteos &amp; Frescos
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="categoriaFiltro === 'bebidas' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="categoriaFiltro = 'bebidas'"
            >
              Bebidas &amp; Snacks
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="categoriaFiltro === 'vinos' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="categoriaFiltro = 'vinos'"
            >
              Vinos &amp; Cervezas
            </button>
          </div>

          <div class="relative">
            <input
              v-model="busquedaSku"
              type="text"
              placeholder="Buscar SKU, producto..."
              class="h-8 w-44 rounded-lg border border-outline-variant/60 bg-surface-container-low px-2.5 pl-8 text-xs text-on-surface focus:outline-none focus:border-primary-container"
            />
            <Icon name="search" :size="14" class="absolute left-2.5 top-2 text-outline" />
          </div>
        </div>
      </div>

      <!-- Tabla Predictiva -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse min-w-[980px]">
          <thead>
            <tr class="bg-surface-container-low border-b border-outline-variant/40 text-[11px] font-bold uppercase tracking-wider text-outline h-9">
              <th class="py-2.5 px-4">Producto / SKU</th>
              <th class="py-2.5 px-4 text-right">Histórico (7D)</th>
              <th class="py-2.5 px-4 text-right">Pronóstico 7D (Unid / USD)</th>
              <th class="py-2.5 px-4">Factor Ajuste IA</th>
              <th class="py-2.5 px-4 text-right">Stock Tienda</th>
              <th class="py-2.5 px-4 text-center">Cobertura</th>
              <th class="py-2.5 px-4 text-right">Acción Recomendada</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/25 text-xs text-on-surface">
            <tr
              v-for="item in skusFiltrados"
              :key="item.sku"
              class="hover:bg-surface-container-low/50 transition-colors"
            >
              <td class="py-3 px-4">
                <div class="flex items-center gap-2.5">
                  <div
                    class="h-2 w-2 rounded-full shrink-0"
                    :class="
                      item.coberturaNivel === 'critico' ? 'bg-rose-500' :
                      item.coberturaNivel === 'alerta' ? 'bg-amber-500' : 'bg-emerald-500'
                    "
                  />
                  <div>
                    <span class="font-semibold text-primary block text-xs">{{ item.nombre }}</span>
                    <span class="text-[11px] font-mono text-outline">SKU-{{ item.sku }} • {{ item.categoriaLabel }}</span>
                  </div>
                </div>
              </td>
              <td class="py-3 px-4 text-right font-mono font-medium text-on-surface-variant">
                {{ item.historico7d }} un
              </td>
              <td class="py-3 px-4 text-right">
                <span class="font-bold text-primary font-mono block">{{ item.pronostico7d }} un</span>
                <span class="text-[11px] font-mono text-outline">{{ item.montoPronostico }}</span>
              </td>
              <td class="py-3 px-4">
                <SemanticChip :tipo="item.factorTipo">
                  {{ item.factorIa }}
                </SemanticChip>
              </td>
              <td class="py-3 px-4 text-right font-mono">
                <span
                  class="font-bold"
                  :class="item.coberturaNivel === 'critico' ? 'text-rose-700' : 'text-primary'"
                >
                  {{ item.stockTienda }} un
                </span>
                <span class="text-[11px] text-outline block">({{ item.stockDetalle }})</span>
              </td>
              <td class="py-3 px-4 text-center">
                <SemanticChip
                  :tipo="
                    item.coberturaNivel === 'critico' ? 'quiebre' :
                    item.coberturaNivel === 'alerta' ? 'fifo' : 'ok'
                  "
                >
                  {{ item.coberturaLabel }}
                </SemanticChip>
              </td>
              <td class="py-3 px-4 text-right">
                <Btn
                  size="xs"
                  :variant="item.coberturaNivel === 'critico' ? 'primary' : 'outline'"
                  @click="accionCuota(item)"
                >
                  {{ item.accionRecomendada }}
                </Btn>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- MODAL: GOBERNANZA DE MODELOS ML (Aprobación, Rechazo y WAPE) -->
    <Modal
      v-if="modalGobernanza"
      titulo="Gobernanza de Modelos Predictivos SIRA ML"
      ancho="max-w-4xl"
      @cerrar="modalGobernanza = false"
    >
      <div class="space-y-4 text-xs">
        <p class="text-on-surface-variant">
          El sistema entrena mensualmente modelos de demanda; ningún modelo pasa a producción sin que sea aprobado por el responsable (SC-002).
        </p>

        <!-- Filtro estado modelo -->
        <div class="flex items-center gap-2">
          <label class="font-semibold text-on-surface">Filtrar por estado:</label>
          <select
            v-model="filtroEstado"
            class="rounded-lg border border-outline-variant bg-surface px-2.5 py-1 text-xs"
          >
            <option value="">Todos</option>
            <option value="pendiente">Pendientes</option>
            <option value="aprobado">Aprobados</option>
            <option value="rechazado">Rechazados</option>
          </select>
        </div>

        <!-- Tabla de modelos -->
        <div class="max-h-56 overflow-y-auto rounded-xl border border-outline-variant/30 bg-surface-container-low">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/40 text-[11px] uppercase font-bold text-outline">
                <th class="py-2 px-3">Modelo ID</th>
                <th class="py-2 px-3">Fecha Entrenamiento</th>
                <th class="py-2 px-3 text-right">Métrica WAPE</th>
                <th class="py-2 px-3 text-center">Estado</th>
                <th class="py-2 px-3 text-center">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/20">
              <tr
                v-for="m in modelos"
                :key="m.modelo_id"
                class="hover:bg-surface-container-high/40 cursor-pointer"
                :class="seleccionado?.modelo_id === m.modelo_id ? 'bg-surface-container-high/60 font-semibold' : ''"
                @click="seleccionar(m)"
              >
                <td class="py-2 px-3 font-mono">#{{ m.modelo_id }}</td>
                <td class="py-2 px-3 text-outline">{{ m.fecha_entrenamiento }}</td>
                <td class="py-2 px-3 text-right font-mono">{{ Number(m.metrica_wape || 0).toFixed(3) }}</td>
                <td class="py-2 px-3 text-center">
                  <SemanticChip :tipo="m.estado === 'aprobado' ? 'ok' : m.estado === 'pendiente' ? 'fifo' : 'quiebre'">
                    {{ m.estado }}
                  </SemanticChip>
                </td>
                <td class="py-2 px-3 text-center">
                  <div v-if="m.estado === 'pendiente'" class="flex items-center justify-center gap-1">
                    <Btn size="xs" variant="primary" @click.stop="aprobar(m)">Aprobar</Btn>
                    <Btn size="xs" variant="danger" @click.stop="rechazar(m)">Rechazar</Btn>
                  </div>
                  <span v-else class="text-outline text-[11px]">Auditado</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Monitoreo Semanal de Precisión WAPE -->
        <div v-if="seleccionado && monitoreo.length" class="space-y-2 pt-2 border-t border-outline-variant/30">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-primary text-xs">
              Historial de Precisión Semanal WAPE (Modelo #{{ seleccionado.modelo_id }})
            </h4>
            <span class="text-[11px] text-rose-700 font-semibold">
              Línea roja: Umbral de degradación ({{ (umbralDegradacion * 100).toFixed(0) }}%)
            </span>
          </div>
          <div class="h-44 w-full rounded-xl bg-surface-container-lowest p-2 border border-outline-variant/20">
            <VChart :option="opcionesGraficoWape" autoresize />
          </div>
        </div>

        <div class="flex justify-end pt-2">
          <Btn variant="outline" @click="modalGobernanza = false">Cerrar</Btn>
        </div>
      </div>
    </Modal>
  </main>
</template>
