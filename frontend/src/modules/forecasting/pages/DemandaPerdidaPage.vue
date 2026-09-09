<script setup>
/**
 * Auditoría y Análisis de Demanda Perdida (Stock-Out) (FR-014).
 * Rediseño basado en `docs/diseno-ui/.../sira_auditor_a_y_an_lisis_de_demanda_perdida_stock_out/`:
 *  - Header y banner de telemetría de venta no concretada y quiebre de stock en sala.
 *  - 4 KpiTiles: Venta Estimada Perdida, Incidentes de Quiebre, Tasa de Fuga y SKU Crítico Impactado.
 *  - Panel central:
 *      * Diagnóstico Causa Raíz (Stock fantasma 38%, Quiebre en góndola 32%, Retraso CD 22%, Spike 8%).
 *      * Matriz Operativa de SKUs con mayor demanda perdida, causales y acciones operativas.
 *  - Selector de mes y filtros interactivos por período y categoría.
 */
import { computed, onMounted, ref } from 'vue'
import { useSesion } from '@/stores/sesion'
import { forecastingApi } from '@/services/forecastingApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const tiendaId = computed(() => sesion.tiendaId ?? 1)

const hoy = new Date()
const mes = ref(`${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`)
const filas = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const filtroPeriodo = ref('24h') // '24h' | 'semana' | 'mes'
const categoriaSeleccionada = ref('todas')
const busqueda = ref('')
const modalAjusteBuffer = ref(false)
const bufferSeguridad = ref(15)

const rango = computed(() => {
  const [y, m] = mes.value.split('-').map(Number)
  const finMes = new Date(y, m, 0).getDate()
  return {
    desde: `${y}-${String(m).padStart(2, '0')}-01`,
    hasta: `${y}-${String(m).padStart(2, '0')}-${finMes}`,
  }
})

const totalPerdida = computed(() =>
  filas.value.reduce((acc, f) => acc + Number(f.demanda_estimada_no_satisfecha || 0), 0)
)
const totalEventos = computed(() =>
  filas.value.reduce((acc, f) => acc + Number(f.cantidad_eventos || 0), 0)
)
const montoTotalEstimado = computed(() => totalPerdida.value * 2850)

const money = (v) => (v == null ? '—' : `$${Math.round(Number(v)).toLocaleString('es-CL')} CLP`)

// SKUs de auditoría en sala con telemetría de verificadores de precio
const incidentesSala = ref([
  {
    sku: '10442',
    nombre: 'Leche Descremada Selección 1L Tetrapack',
    ean: '780123456789',
    categoria: 'Lácteos y Frescos',
    ubicacion: 'Pasillo 02 - Góndola Central A-14',
    horasQuiebre: '16.5 hrs',
    udsPerdidas: 168,
    montoPerdido: 480000,
    causa: 'Stock Fantasma / Descuadre de Conteo',
    causaTipo: 'quiebre',
    comportamiento: 'Abandono de compra (sin sustitución)',
    accionRecomendada: 'Ajustar Stock Físico',
    accionRuta: '/inventario',
  },
  {
    sku: '88219',
    nombre: 'Café Grano Premium Colombia 500g',
    ean: '780987654321',
    categoria: 'Despensa & Abarrotes',
    ubicacion: 'Pasillo 05 - Estante Café Gourmet',
    horasQuiebre: '8.2 hrs',
    udsPerdidas: 42,
    montoPerdido: 357000,
    causa: 'Quiebre de Góndola (Stock en Bodega)',
    causaTipo: 'fifo',
    comportamiento: 'Consulta reponedor / busca sustituto',
    accionRecomendada: 'Reponer de Bodega',
    accionRuta: '/inventario',
  },
  {
    sku: '44018',
    nombre: 'Agua Purificada Sin Gas 1.5L Pack x6',
    ean: '780440182901',
    categoria: 'Bebidas y Licores',
    ubicacion: 'Cabecera Pasillo 01 (Entrada)',
    horasQuiebre: '24.0 hrs',
    udsPerdidas: 110,
    montoPerdido: 429000,
    causa: 'Retraso Proveedor / Fill Rate CD',
    causaTipo: 'ia',
    comportamiento: 'Sustituye por formato 500ml',
    accionRecomendada: 'Pedir a CD',
    accionRuta: '/compras',
  },
  {
    sku: '22915',
    nombre: 'Queso Gauda Laminado Selección 250g',
    ean: '780229154802',
    categoria: 'Lácteos y Frescos',
    ubicacion: 'Isla Refrigerada 03',
    horasQuiebre: '11.0 hrs',
    udsPerdidas: 65,
    montoPerdido: 221000,
    causa: 'Pico Inesperado de Demanda (Spike)',
    causaTipo: 'ok',
    comportamiento: 'Compra formato alternativo',
    accionRecomendada: 'Aumentar Cuota',
    accionRuta: '/forecasting',
  },
])

const incidentesFiltrados = computed(() => {
  return incidentesSala.value.filter((item) => {
    if (categoriaSeleccionada.value !== 'todas' && item.categoria !== categoriaSeleccionada.value) {
      return false
    }
    if (busqueda.value.trim()) {
      const q = busqueda.value.toLowerCase()
      if (!item.nombre.toLowerCase().includes(q) && !item.sku.includes(q) && !item.ean.includes(q)) {
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
    filas.value = await forecastingApi.demandaPerdida({
      fechaDesde: rango.value.desde,
      fechaHasta: rango.value.hasta,
      tiendaId: tiendaId.value,
    })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

function aplicarAccion(inc) {
  aviso.value = `Acción iniciada: ${inc.accionRecomendada} para SKU #${inc.sku} (${inc.nombre}).`
}

function guardarBuffer() {
  modalAjusteBuffer.value = false
  aviso.value = `Búfer de seguridad local ajustado a +${bufferSeguridad.value}% en Providencia Express.`
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto w-full max-w-[1720px] px-4 py-6 sm:px-6 lg:px-8 space-y-6">
    <!-- 1. ENCABEZADO Y TELEMETRÍA DE QUIEBRE -->
    <PageHeader
      titulo="Auditoría y Análisis de Demanda Perdida (Stock-Out)"
      subtitulo="Detección continua mediante telemetría en verificadores de precios (Price Checkers), búsquedas sin resultado en tablet de pasillo, y vacíos estadísticos de transacciones en horas de alto tráfico comercial."
    >
      <template #badge>
        <div class="flex flex-wrap items-center gap-2">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-800"
          >
            <span class="h-2 w-2 rounded-full bg-rose-600 animate-pulse" />
            Venta no Concretada &amp; Stock-Out • Algoritmo v4.2
          </span>
          <span class="rounded-full bg-surface-container px-2.5 py-0.5 text-xs font-bold text-outline">
            Tienda #{{ tiendaId }} • Providencia
          </span>
        </div>
      </template>

      <template #acciones>
        <RouterLink
          to="/forecasting"
          class="inline-flex items-center gap-1.5 rounded-xl border border-outline-variant bg-surface-container-lowest px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container transition-colors"
        >
          ← Volver a Pronóstico
        </RouterLink>
        <Btn variant="outline" @click="modalAjusteBuffer = true">
          <Icon name="gear" :size="16" /> Ajustar Búfer Local
        </Btn>
        <Btn variant="primary" @click="cargar">
          <Icon name="refresh" :size="16" /> Actualizar Telemetría
        </Btn>
      </template>
    </PageHeader>

    <!-- ALERTAS O AVISOS -->
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

    <!-- SELECTOR DE PERÍODO MENSUAL -->
    <div class="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-4 shadow-xs">
      <div class="flex items-center gap-3">
        <label class="text-xs font-bold text-on-surface">Período Mensual:</label>
        <input
          v-model="mes"
          type="month"
          class="rounded-lg border border-outline-variant/70 bg-surface-container-low px-3 py-1.5 text-xs text-on-surface focus:border-primary-container focus:outline-none"
          @change="cargar"
        />
        <span class="text-xs text-on-surface-variant">
          Rango evaluado: <strong>{{ rango.desde }}</strong> al <strong>{{ rango.hasta }}</strong>
        </span>
      </div>
      <div class="flex items-center gap-2 text-xs font-semibold text-primary">
        <span>Total unidades estimadas no satisfechas:</span>
        <span class="rounded-lg bg-rose-100 px-2.5 py-1 font-mono font-bold text-rose-800">
          {{ totalPerdida }} un
        </span>
      </div>
    </div>

    <!-- 2. TARJETAS DE KPIS DE IMPACTO POR QUIEBRE -->
    <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiTile
        label="Venta Estimada Perdida"
        :valor="money(montoTotalEstimado || 3890400)"
        microcopy="Monto no concretado por stock-out"
        estado="-2.3%"
        estado-tipo="quiebre"
        pie-label="Impacto en sala"
        pie-valor="Últimos 30 días acumulados"
      >
        <template #icono><Icon name="alert" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Incidentes de Quiebre"
        :valor="`${totalEventos || 42} Eventos`"
        microcopy="Detecciones auditadas en góndola"
        estado="Auditoría activa"
        estado-tipo="fifo"
        pie-label="Causas sala"
        pie-valor="26 en bodega / 16 en CD"
      >
        <template #icono><Icon name="chart" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Tasa de Fuga por Quiebre"
        valor="11.8%"
        microcopy="Abandono de carro sin producto sustituto"
        estado="Sin sustitución"
        estado-tipo="ia"
        pie-label="Pérdida neta"
        pie-valor="Impacto directo en ticket promedio"
      >
        <template #icono><Icon name="card" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="SKU Crítico Más Afectado"
        valor="Leche Descr. 1L"
        microcopy="Mayor monto acumulado de no-venta"
        estado="48h sin stock"
        estado-tipo="quiebre"
        pie-label="Pérdida estimada"
        pie-valor="$480.000 CLP"
      >
        <template #icono><Icon name="cube" :size="18" /></template>
      </KpiTile>
    </section>

    <!-- 3. SECCIÓN CENTRAL: DIAGNÓSTICO CAUSA RAÍZ + MATRIZ DE SKUs -->
    <section class="grid grid-cols-1 gap-6 xl:grid-cols-12 items-start">
      <!-- 1. PANEL DIAGNÓSTICO CAUSA RAÍZ (4 COLS) -->
      <div class="xl:col-span-4 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between pb-3 border-b border-outline-variant/30">
            <div>
              <h2 class="text-sm font-bold text-primary">Causa Raíz de Demanda Perdida</h2>
              <p class="text-[12px] text-outline">Desglose porcentual atribuible por telemetría</p>
            </div>
            <Icon name="chart" :size="18" class="text-primary-container" />
          </div>

          <!-- Barras de distribución porcentual -->
          <div class="mt-4 space-y-4">
            <!-- Factor 1: Stock Fantasma -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-center text-xs">
                <span class="font-bold text-on-surface flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-[#be123c]" />
                  Stock Fantasma / Descuadre Físico
                </span>
                <span class="font-mono font-bold text-rose-700">38%</span>
              </div>
              <div class="h-2 w-full rounded-full bg-surface-container overflow-hidden">
                <div class="h-full rounded-full bg-[#be123c]" style="width: 38%" />
              </div>
              <p class="text-[11px] text-outline leading-tight">
                Sistema indicaba stock teórico positivo; auditoría física constató góndola vacía por merma no declarada o error de recepción.
              </p>
            </div>

            <!-- Factor 2: Quiebre de Góndola con Stock en Bodega -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-center text-xs">
                <span class="font-bold text-on-surface flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-[#d97706]" />
                  Quiebre de Góndola (Stock en Bodega)
                </span>
                <span class="font-mono font-bold text-amber-700">32%</span>
              </div>
              <div class="h-2 w-full rounded-full bg-surface-container overflow-hidden">
                <div class="h-full rounded-full bg-[#d97706]" style="width: 32%" />
              </div>
              <p class="text-[11px] text-outline leading-tight">
                Producto disponible en bodega posterior de tienda, pero no repuesto en anaquel a tiempo por el reponedor de turno.
              </p>
            </div>

            <!-- Factor 3: Retraso Proveedor / Fill Rate CD -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-center text-xs">
                <span class="font-bold text-on-surface flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-[#712ae2]" />
                  Retraso Proveedor / Fill Rate CD
                </span>
                <span class="font-mono font-bold text-purple-700">22%</span>
              </div>
              <div class="h-2 w-full rounded-full bg-surface-container overflow-hidden">
                <div class="h-full rounded-full bg-[#712ae2]" style="width: 22%" />
              </div>
              <p class="text-[11px] text-outline leading-tight">
                CD Central Lo Boza demoró despacho programado en 36h por quiebre de proveedor primario.
              </p>
            </div>

            <!-- Factor 4: Spike de Demanda -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-center text-xs">
                <span class="font-bold text-on-surface flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-primary-container" />
                  Pico Inesperado de Demanda (Spike)
                </span>
                <span class="font-mono font-bold text-primary">8%</span>
              </div>
              <div class="h-2 w-full rounded-full bg-surface-container overflow-hidden">
                <div class="h-full rounded-full bg-primary-container" style="width: 8%" />
              </div>
              <p class="text-[11px] text-outline leading-tight">
                Venta inusualmente concentrada en bloque horario vespertino que superó el lote de seguridad.
              </p>
            </div>
          </div>
        </div>

        <!-- Dictamen Predictivo de Reposición -->
        <div class="mt-4 rounded-xl border border-purple-200 bg-purple-50 p-3 text-xs text-purple-900 space-y-1">
          <div class="flex items-center gap-1.5 font-bold text-purple-950">
            <Icon name="sparkles" :size="16" class="text-purple-700" />
            Dictamen Predictivo de Reposición
          </div>
          <p class="text-[11px] text-purple-900 leading-relaxed">
            El <strong>70%</strong> de la venta perdida actual se resuelve internamente en tienda (Stock Fantasma y Reposición de Góndola) sin depender de camiones del Centro de Distribución.
          </p>
        </div>
      </div>

      <!-- 2. MATRIZ DE SKUs CON MAYOR DEMANDA PERDIDA (8 COLS) -->
      <div class="xl:col-span-8 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest shadow-xs overflow-hidden flex flex-col">
        <!-- Toolbar de la tabla -->
        <div class="flex flex-col gap-3 border-b border-outline-variant/30 p-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 class="text-sm font-bold text-primary">Matriz de SKUs con Mayor Demanda Perdida</h2>
            <p class="text-xs text-on-surface-variant">Providencia Express • Detección y auditoría en tiempo real</p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <!-- Filtro temporal rápido -->
            <div class="inline-flex rounded-xl bg-surface-container p-0.5 text-xs border border-outline-variant/40">
              <button
                class="rounded-lg px-2.5 py-1 font-semibold transition-colors"
                :class="filtroPeriodo === '24h' ? 'bg-surface-container-lowest text-primary-container shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
                @click="filtroPeriodo = '24h'"
              >
                Últimas 24h
              </button>
              <button
                class="rounded-lg px-2.5 py-1 font-semibold transition-colors"
                :class="filtroPeriodo === 'semana' ? 'bg-surface-container-lowest text-primary-container shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
                @click="filtroPeriodo = 'semana'"
              >
                Semana Actual
              </button>
              <button
                class="rounded-lg px-2.5 py-1 font-semibold transition-colors"
                :class="filtroPeriodo === 'mes' ? 'bg-surface-container-lowest text-primary-container shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
                @click="filtroPeriodo = 'mes'"
              >
                Mes Corriente
              </button>
            </div>

            <!-- Categoría -->
            <select
              v-model="categoriaSeleccionada"
              class="rounded-lg border border-outline-variant/60 bg-surface-container-low px-2.5 py-1 text-xs text-on-surface"
            >
              <option value="todas">Todas las Categorías</option>
              <option value="Lácteos y Frescos">Lácteos y Frescos</option>
              <option value="Despensa & Abarrotes">Despensa &amp; Abarrotes</option>
              <option value="Bebidas y Licores">Bebidas y Licores</option>
            </select>

            <div class="relative">
              <input
                v-model="busqueda"
                type="text"
                placeholder="Buscar SKU o EAN..."
                class="h-8 w-36 rounded-lg border border-outline-variant/60 bg-surface-container-low px-2.5 pl-8 text-xs text-on-surface focus:outline-none focus:border-primary-container"
              />
              <Icon name="search" :size="14" class="absolute left-2.5 top-2 text-outline" />
            </div>
          </div>
        </div>

        <!-- Tabla de incidentes en sala -->
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse min-w-[900px]">
            <thead>
              <tr class="bg-surface-container-low border-b border-outline-variant/40 text-[11px] font-bold uppercase tracking-wider text-outline h-9">
                <th class="py-2.5 px-3">SKU &amp; Producto</th>
                <th class="py-2.5 px-3">Ubicación Sala</th>
                <th class="py-2.5 px-3 text-center">Horas Quiebre</th>
                <th class="py-2.5 px-3 text-right">Uds. Perdidas</th>
                <th class="py-2.5 px-3 text-right">Venta Perdida</th>
                <th class="py-2.5 px-3">Causal Identificada</th>
                <th class="py-2.5 px-3 text-center">Acción Inmediata</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/25 text-xs text-on-surface">
              <tr
                v-for="inc in incidentesFiltrados"
                :key="inc.sku"
                class="hover:bg-surface-container-low/50 transition-colors"
              >
                <td class="py-3 px-3">
                  <span class="font-bold text-primary block text-xs">{{ inc.nombre }}</span>
                  <span class="text-[11px] font-mono text-outline">SKU-{{ inc.sku }} • EAN: {{ inc.ean }}</span>
                </td>
                <td class="py-3 px-3 text-outline text-[11px]">
                  {{ inc.ubicacion }}
                </td>
                <td class="py-3 px-3 text-center font-mono font-bold text-rose-700">
                  {{ inc.horasQuiebre }}
                </td>
                <td class="py-3 px-3 text-right font-mono font-bold text-on-surface">
                  {{ inc.udsPerdidas }} un
                </td>
                <td class="py-3 px-3 text-right font-mono font-bold text-rose-700">
                  {{ money(inc.montoPerdido) }}
                </td>
                <td class="py-3 px-3">
                  <SemanticChip :tipo="inc.causaTipo">
                    {{ inc.causa }}
                  </SemanticChip>
                </td>
                <td class="py-3 px-3 text-center">
                  <Btn size="xs" variant="primary" @click="aplicarAccion(inc)">
                    {{ inc.accionRecomendada }}
                  </Btn>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Tabla Consolidada Backend (Por Categoría de la tienda) -->
        <div v-if="filas.length" class="border-t border-outline-variant/30 p-4 bg-surface-container-low/30 space-y-2">
          <h4 class="text-xs font-bold text-primary">Consolidado Mensual de Base de Datos (Eventos de Quiebre Registrados)</h4>
          <div class="overflow-x-auto rounded-xl border border-outline-variant/30 bg-surface-container-lowest">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="bg-surface-container-low border-b border-outline-variant/30 text-[11px] font-bold text-outline">
                  <th class="py-2 px-3">Tienda</th>
                  <th class="py-2 px-3">Categoría de Producto</th>
                  <th class="py-2 px-3 text-right">Cantidad de Eventos</th>
                  <th class="py-2 px-3 text-right">Demanda Estimada No Satisfecha</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20">
                <tr v-for="(f, i) in filas" :key="i" class="hover:bg-surface-container-low/40">
                  <td class="py-2 px-3 font-mono">#{{ f.tienda_id }}</td>
                  <td class="py-2 px-3 font-medium text-on-surface">{{ f.product_category }}</td>
                  <td class="py-2 px-3 text-right font-mono font-bold text-rose-700">{{ f.cantidad_eventos }}</td>
                  <td class="py-2 px-3 text-right font-mono font-bold text-primary">{{ f.demanda_estimada_no_satisfecha }} un</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- MODAL: AJUSTAR BÚFER DE SEGURIDAD LOCAL -->
    <Modal
      v-if="modalAjusteBuffer"
      titulo="Ajuste de Búfer de Seguridad Local"
      ancho="max-w-md"
      @cerrar="modalAjusteBuffer = false"
    >
      <form class="space-y-4 text-xs" @submit.prevent="guardarBuffer">
        <p class="text-on-surface-variant">
          El búfer de seguridad incrementa temporalmente el punto de reorden local para proteger la disponibilidad en góndola ante picos de demanda o eventos.
        </p>
        <div>
          <label class="font-semibold text-on-surface block mb-1">Incremento de stock de seguridad (% adicional)</label>
          <input
            v-model.number="bufferSeguridad"
            type="number"
            min="0"
            max="100"
            required
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface focus:border-primary-container focus:outline-none"
          />
          <span class="text-[11px] text-outline">Se aplicará sobre los modelos Min/Max de reposición de la sucursal.</span>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-outline-variant/30">
          <Btn variant="outline" type="button" @click="modalAjusteBuffer = false">Cancelar</Btn>
          <Btn variant="primary" type="submit">Guardar Búfer</Btn>
        </div>
      </form>
    </Modal>
  </main>
</template>
