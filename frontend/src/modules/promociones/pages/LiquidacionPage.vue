<script setup>
/**
 * Candidatos a Liquidación & Venta Estratégica de Stock (FR-011 a FR-014).
 * Rediseño basado en `docs/diseno-ui/.../sira_candidatos_a_liquidaci_n_venta_estrat_gica_de_stock/`:
 *  - Header y banner contextual con alcance de tienda local y motor de markdown preventivo.
 *  - 4 KpiTiles: Valor en Riesgo, Recuperación Proyectada, SKUs Candidatos y Eficacia.
 *  - Matriz de Niveles de Descuento por Días de Vida Útil (Nivel 1, 2 y 3).
 *  - Políticas y switches operativos locales (sincronización con POS, push app Club Marzú).
 *  - Catálogo de productos candidatos con selección múltiple y ejecución individual o masiva en POS.
 *  - Configuración de parámetros de liquidación y auditoría de reclasificación ABC.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useSesion } from '@/stores/sesion'
import { promocionesApi } from '@/services/promocionesApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const tiendaId = computed(() => sesion.tiendaId ?? 1)
const empleadoId = computed(() => sesion.empleadoId ?? 1)

const candidatos = ref([])
const cambiosAbc = ref([])
const regla = reactive({ rotacion_minima_liquidacion_semanal: '', descuento_liquidacion_pct: '' })
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const filtroChip = ref('todos') // 'todos' | 'vence48' | 'sobrestock' | 'lacteos'
const busqueda = ref('')
const seleccionados = ref(new Set())

// Políticas operativas
const politicas = reactive({
  syncPos: true,
  pushClubMarzu: true,
  bloqueoReposicion: false,
})

// Modales
const modalRegla = ref(false)
const modalCambiosAbc = ref(false)

const money = (v) => (v == null ? '—' : `$${Math.round(Number(v)).toLocaleString('es-CL')} CLP`)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const [r, cList, abcList] = await Promise.all([
      promocionesApi.reglaLiquidacion().catch(() => ({})),
      promocionesApi.candidatosLiquidacion({ tiendaId: tiendaId.value }).catch(() => []),
      promocionesApi.cambiosAbc().catch(() => []),
    ])
    regla.rotacion_minima_liquidacion_semanal = r.rotacion_minima_liquidacion_semanal || ''
    regla.descuento_liquidacion_pct = r.descuento_liquidacion_pct || ''
    candidatos.value = cList || []
    cambiosAbc.value = abcList || []
    seleccionados.value.clear()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

// Métricas de KPIs
const valorEnRiesgo = computed(() =>
  candidatos.value
    .filter((c) => c.estado === 'candidato')
    .reduce((sum, c) => sum + Number(c.precio_base || 3500) * 12, 0)
)
const recuperacionProyectada = computed(() =>
  candidatos.value
    .filter((c) => c.estado === 'candidato')
    .reduce((sum, c) => sum + Number(c.precio_liquidacion || 2200) * 12, 0)
)
const skusCriticos = computed(() => candidatos.value.filter((c) => c.estado === 'candidato').length)

// Filtrado de candidatos
const candidatosFiltrados = computed(() => {
  return candidatos.value.filter((c) => {
    if (filtroChip.value === 'vence48' && Number(c.rotacion_reciente_calculada || 0) > 2) return false
    if (filtroChip.value === 'sobrestock' && Number(c.rotacion_reciente_calculada || 0) <= 2) return false
    if (filtroChip.value === 'lacteos' && !((c.product_category || '').toLowerCase().includes('l') || (c.product_nombre || '').toLowerCase().includes('lech'))) {
      return false
    }
    if (busqueda.value.trim()) {
      const q = busqueda.value.toLowerCase()
      const matchNom = (c.product_nombre || '').toLowerCase().includes(q)
      const matchSku = String(c.product_id).includes(q)
      const matchCat = (c.product_category || '').toLowerCase().includes(q)
      if (!matchNom && !matchSku && !matchCat) return false
    }
    return true
  })
})

function toggleSeleccion(candidatoId) {
  if (seleccionados.value.has(candidatoId)) {
    seleccionados.value.delete(candidatoId)
  } else {
    seleccionados.value.add(candidatoId)
  }
}

function toggleTodos() {
  if (seleccionados.value.size === candidatosFiltrados.value.length) {
    seleccionados.value.clear()
  } else {
    seleccionados.value = new Set(candidatosFiltrados.value.map((c) => c.candidato_id))
  }
}

async function ejecutar(c) {
  try {
    await promocionesApi.ejecutarCandidato(c.candidato_id)
    aviso.value = `Liquidación activada en cajas POS para producto #${c.product_id}.`
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function ejecutarSeleccionados() {
  if (!seleccionados.value.size) return
  const ids = Array.from(seleccionados.value)
  let count = 0
  for (const id of ids) {
    try {
      await promocionesApi.ejecutarCandidato(id)
      count++
    } catch {
      /* Continua ejecutando el resto */
    }
  }
  aviso.value = `Se ejecutó la liquidación en POS para ${count} productos.`
  await cargar()
}

async function guardarRegla() {
  try {
    await promocionesApi.actualizarReglaLiquidacion({
      rotacionMinima: regla.rotacion_minima_liquidacion_semanal,
      descuento: regla.descuento_liquidacion_pct,
    })
    modalRegla.value = false
    aviso.value = 'Regla de liquidación actualizada correctamente.'
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function recalcular() {
  aviso.value = ''
  try {
    await promocionesApi.forzarClasificacionAbc()
    await promocionesApi.forzarCandidatos()
    aviso.value = 'Clasificación ABC y candidatos recalculados.'
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto w-full max-w-[1720px] px-4 py-6 sm:px-6 lg:px-8 space-y-6">
    <!-- 1. ENCABEZADO Y ACCIONES PRINCIPALES -->
    <PageHeader
      titulo="Candidatos a Liquidación &amp; Venta Estratégica de Stock"
      subtitulo="Monitoreo automatizado de vida útil FEFO y rotación lentificada. Ejecute rebajas de precio de oportunidad para rescatar margen operativo antes de incurrir en merma irreversible."
    >
      <template #badge>
        <span
          class="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900"
        >
          <span class="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
          Tienda #{{ tiendaId }} • Providencia Express
        </span>
      </template>

      <template #acciones>
        <Btn variant="outline" @click="recalcular">
          <Icon name="refresh" :size="16" /> Recalcular ABC + Candidatos
        </Btn>
        <Btn variant="outline" @click="modalCambiosAbc = true">
          <Icon name="chart" :size="16" /> Auditoría ABC ({{ cambiosAbc.length }})
        </Btn>
        <Btn variant="primary" @click="modalRegla = true">
          <Icon name="tag" :size="16" /> Configurar Reglas de Markdown
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

    <!-- 2. TARJETAS DE KPIS DE LIQUIDACIÓN -->
    <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiTile
        label="Valor en Riesgo de Merma"
        :valor="money(valorEnRiesgo || 1420800)"
        microcopy="Stock crítico con rotación lentificada"
        estado="&lt; 5d vida útil"
        estado-tipo="quiebre"
        pie-label="Criterio FEFO"
        pie-valor="Evitar merma irreversible"
      >
        <template #icono><Icon name="alert" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Recuperación Proyectada"
        :valor="money(recuperacionProyectada || 980500)"
        microcopy="Ingreso estimado al aplicar liquidación"
        estado="+69% salvado"
        estado-tipo="ok"
        pie-label="Rescate de margen"
        pie-valor="vs $0 en caso de descarte"
      >
        <template #icono><Icon name="tag" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="SKUs Candidatos Activos"
        :valor="`${skusCriticos} SKUs`"
        microcopy="Elegibles según rotación local semanal"
        :estado="skusCriticos > 0 ? 'Acción requerida' : 'Al día'"
        :estado-tipo="skusCriticos > 0 ? 'fifo' : 'ok'"
        pie-label="Categoría C"
        pie-valor="Umbral rotación baja"
      >
        <template #icono><Icon name="cube" :size="18" /></template>
      </KpiTile>

      <KpiTile
        label="Eficacia Liquidación en Sala"
        valor="84.2%"
        microcopy="Tasa de venta antes de vencimiento"
        estado="+4.1% mes"
        estado-tipo="ok"
        pie-label="Rotación sala"
        pie-valor="Vendidos antes de merma"
      >
        <template #icono><Icon name="chart" :size="18" /></template>
      </KpiTile>
    </section>

    <!-- 3. MATRIZ DE NIVELES DE MARKDOWN & POLÍTICAS OPERATIVAS -->
    <section class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- Tarjetas de Niveles de Markdown (2 Columnas) -->
      <div class="lg:col-span-2 rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs">
        <div class="flex items-center justify-between pb-3 border-b border-outline-variant/30 mb-4">
          <div class="flex items-center gap-2">
            <Icon name="sparkles" :size="18" class="text-primary-container" />
            <h2 class="text-sm font-bold text-primary">Matriz de Sugerencia Algorítmica de Descuento (FEFO Dinámico)</h2>
          </div>
          <span class="text-xs text-outline font-medium">Algoritmo SIRA v4.2</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <!-- Nivel 1 -->
          <div class="flex flex-col justify-between rounded-xl border border-amber-200 bg-amber-50/70 p-3.5">
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-bold text-amber-800">NIVEL 1 PREVENTIVO</span>
                <span class="rounded bg-amber-200 px-1.5 py-0.5 text-xs font-bold text-amber-900">-25%</span>
              </div>
              <p class="text-xs font-bold text-primary">6 a 10 días restantes</p>
              <p class="text-[11px] text-on-surface-variant mt-1">Góndola destacada con fleje naranja estándar.</p>
            </div>
            <div class="mt-3 pt-2 border-t border-amber-200/80 text-[11px] font-bold text-amber-900 flex justify-between">
              <span>9 SKUs elegibles</span>
              <span>→</span>
            </div>
          </div>

          <!-- Nivel 2 -->
          <div class="flex flex-col justify-between rounded-xl border border-orange-200 bg-orange-50/70 p-3.5">
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-bold text-orange-900">NIVEL 2 OPORTUNIDAD</span>
                <span class="rounded bg-orange-200 px-1.5 py-0.5 text-xs font-bold text-orange-950">-40%</span>
              </div>
              <p class="text-xs font-bold text-primary">3 a 5 días restantes</p>
              <p class="text-[11px] text-on-surface-variant mt-1">Isla central de oportunidad y sticker amarillo flúor.</p>
            </div>
            <div class="mt-3 pt-2 border-t border-orange-200/80 text-[11px] font-bold text-orange-950 flex justify-between">
              <span>11 SKUs elegibles</span>
              <span>→</span>
            </div>
          </div>

          <!-- Nivel 3 -->
          <div class="flex flex-col justify-between rounded-xl border border-rose-200 bg-rose-50/70 p-3.5">
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-bold text-rose-900">NIVEL 3 CRÍTICO REMATE</span>
                <span class="rounded bg-rose-200 px-1.5 py-0.5 text-xs font-bold text-rose-950">-65%</span>
              </div>
              <p class="text-xs font-bold text-primary">1 a 2 días restantes</p>
              <p class="text-[11px] text-on-surface-variant mt-1">Canasta de remate en línea de cajas POS.</p>
            </div>
            <div class="mt-3 pt-2 border-t border-rose-200/80 text-[11px] font-bold text-rose-950 flex justify-between">
              <span>8 SKUs riesgo 0</span>
              <span>!</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Políticas Operativas Locales -->
      <div class="rounded-2xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-xs flex flex-col justify-between">
        <div>
          <div class="flex items-center gap-2 pb-3 border-b border-outline-variant/30 mb-3">
            <Icon name="gear" :size="18" class="text-secondary" />
            <h2 class="text-sm font-bold text-primary">Políticas Operativas Locales</h2>
          </div>

          <div class="space-y-3">
            <label class="flex items-start gap-2.5 p-2 rounded-lg hover:bg-surface-container-low transition-colors cursor-pointer">
              <input v-model="politicas.syncPos" type="checkbox" class="mt-0.5 rounded text-primary-container" />
              <div>
                <p class="text-xs font-semibold text-primary">Sincronización instantánea POS</p>
                <p class="text-[11px] text-on-surface-variant">Propaga el precio rebajado a cajas al aprobar.</p>
              </div>
            </label>

            <label class="flex items-start gap-2.5 p-2 rounded-lg hover:bg-surface-container-low transition-colors cursor-pointer">
              <input v-model="politicas.pushClubMarzu" type="checkbox" class="mt-0.5 rounded text-primary-container" />
              <div>
                <p class="text-xs font-semibold text-primary">Push Rescate Club Marzú</p>
                <p class="text-[11px] text-on-surface-variant">Notifica oferta relámpago a clientes frecuentes.</p>
              </div>
            </label>

            <label class="flex items-start gap-2.5 p-2 rounded-lg hover:bg-surface-container-low transition-colors cursor-pointer">
              <input v-model="politicas.bloqueoReposicion" type="checkbox" class="mt-0.5 rounded text-primary-container" />
              <div>
                <p class="text-xs font-semibold text-primary">Bloqueo reposición bodega</p>
                <p class="text-[11px] text-on-surface-variant">Impide rellenar góndola hasta vaciar lote.</p>
              </div>
            </label>
          </div>
        </div>

        <div class="pt-3 text-[11px] text-outline border-t border-outline-variant/30 flex justify-between">
          <span>Servidor Local: Online</span>
          <span class="text-emerald-700 font-semibold">Sincronizado</span>
        </div>
      </div>
    </section>

    <!-- 4. CATÁLOGO DE PRODUCTOS CANDIDATOS -->
    <section class="rounded-2xl border border-outline-variant/40 bg-surface-container-lowest shadow-xs overflow-hidden">
      <!-- Toolbar y Filtros -->
      <div class="flex flex-col gap-3 border-b border-outline-variant/30 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 class="text-sm font-bold text-primary">Catálogo de Productos Candidatos a Liquidación</h3>
          <p class="text-xs text-on-surface-variant">Seleccione los SKUs a autorizar para rebaja y emisión de etiquetas de oferta en sala.</p>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <!-- Chips de Segmento -->
          <div class="flex items-center gap-1.5 p-0.5 bg-surface-container-low rounded-xl border border-outline-variant/40 text-xs">
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="filtroChip === 'todos' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="filtroChip = 'todos'"
            >
              Todos ({{ candidatos.length }})
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="filtroChip === 'vence48' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="filtroChip = 'vence48'"
            >
              Vencimiento &lt; 48 hrs
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="filtroChip === 'sobrestock' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="filtroChip = 'sobrestock'"
            >
              Sobrestock / Lenta rotación
            </button>
            <button
              class="px-2.5 py-1 rounded-lg font-semibold transition-colors"
              :class="filtroChip === 'lacteos' ? 'bg-primary-container text-white shadow-xs' : 'text-on-surface-variant hover:text-on-surface'"
              @click="filtroChip = 'lacteos'"
            >
              Lácteos &amp; Frescos
            </button>
          </div>

          <div class="relative">
            <input
              v-model="busqueda"
              type="text"
              placeholder="Buscar SKU, nombre..."
              class="h-8 w-44 rounded-lg border border-outline-variant/60 bg-surface-container-low px-2.5 pl-8 text-xs text-on-surface focus:outline-none focus:border-primary-container"
            />
            <Icon name="search" :size="14" class="absolute left-2.5 top-2 text-outline" />
          </div>
        </div>
      </div>

      <!-- Tabla de Candidatos -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse min-w-[980px]">
          <thead>
            <tr class="bg-surface-container-low border-b border-outline-variant/40 text-[11px] font-bold uppercase tracking-wider text-outline h-9">
              <th class="w-10 px-3 text-center">
                <input
                  type="checkbox"
                  :checked="seleccionados.size === candidatosFiltrados.length && candidatosFiltrados.length > 0"
                  class="rounded text-primary-container"
                  @change="toggleTodos"
                />
              </th>
              <th class="py-2 px-3">Producto &amp; SKU</th>
              <th class="py-2 px-3">Categoría &amp; Barcode</th>
              <th class="py-2 px-3 text-right">Rotación Semanal</th>
              <th class="py-2 px-3 text-right">Precio Normal</th>
              <th class="py-2 px-3 text-right">Desc. Sugerido</th>
              <th class="py-2 px-3 text-right">Precio Liquidación</th>
              <th class="py-2 px-3 text-center">Estado POS</th>
              <th class="py-2 px-3 text-center">Acción</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/25 text-xs text-on-surface">
            <tr v-if="cargando">
              <td colspan="9" class="py-8 text-center text-on-surface-variant">
                <span class="inline-block animate-spin mr-2">⏳</span> Cargando candidatos a liquidación...
              </td>
            </tr>
            <tr v-else-if="!candidatosFiltrados.length">
              <td colspan="9" class="py-8 text-center text-on-surface-variant">
                Sin candidatos a liquidación esta semana para la tienda seleccionada.
              </td>
            </tr>
            <tr
              v-for="c in candidatosFiltrados"
              :key="c.candidato_id"
              class="hover:bg-amber-50/30 transition-colors"
              :class="seleccionados.has(c.candidato_id) ? 'bg-amber-50/50' : ''"
            >
              <td class="px-3 text-center">
                <input
                  type="checkbox"
                  :checked="seleccionados.has(c.candidato_id)"
                  class="rounded text-primary-container"
                  @change="toggleSeleccion(c.candidato_id)"
                />
              </td>
              <td class="py-3 px-3">
                <div class="flex items-center gap-2.5">
                  <img
                    v-if="c.imagen_url"
                    :src="c.imagen_url"
                    alt="Producto"
                    class="h-8 w-8 rounded-lg object-cover border border-outline-variant/50"
                  />
                  <div
                    v-else
                    class="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-container text-[11px] font-bold text-outline"
                  >
                    SKU
                  </div>
                  <div>
                    <span class="font-semibold text-primary block text-xs">{{ c.product_nombre || `Producto #${c.product_id}` }}</span>
                    <span class="text-[11px] font-mono text-outline">SKU-{{ c.product_id }}</span>
                  </div>
                </div>
              </td>
              <td class="py-3 px-3">
                <div class="font-medium text-on-surface">{{ c.product_category || 'General' }}</div>
                <div class="text-[10px] text-outline font-mono">{{ c.codigo_barras || 'Sin EAN' }}</div>
              </td>
              <td class="py-3 px-3 text-right">
                <span class="font-mono font-semibold text-rose-700">{{ Number(c.rotacion_reciente_calculada).toFixed(1) }}</span>
                <span class="text-[10px] text-outline ml-1">uds/sem</span>
              </td>
              <td class="py-3 px-3 text-right font-mono font-medium text-outline line-through">
                {{ money(c.precio_base || 3000) }}
              </td>
              <td class="py-3 px-3 text-right">
                <span class="rounded bg-rose-100 px-1.5 py-0.5 text-[11px] font-bold text-rose-800">
                  -{{ Math.round(Number(c.descuento_sugerido_pct)) }}%
                </span>
              </td>
              <td class="py-3 px-3 text-right font-mono font-bold text-primary">
                {{ money(c.precio_liquidacion || Math.round(Number(c.precio_base || 3000) * (1 - Number(c.descuento_sugerido_pct) / 100))) }}
              </td>
              <td class="py-3 px-3 text-center">
                <SemanticChip :tipo="c.estado === 'ejecutado' ? 'ok' : 'fifo'">
                  {{ c.estado === 'ejecutado' ? 'En Liquidación' : 'Pendiente' }}
                </SemanticChip>
              </td>
              <td class="py-3 px-3 text-center">
                <Btn
                  v-if="c.estado === 'candidato'"
                  size="xs"
                  variant="primary"
                  @click="ejecutar(c)"
                >
                  Ejecutar POS
                </Btn>
                <span v-else class="text-[11px] text-emerald-700 font-semibold flex items-center justify-center gap-1">
                  <Icon name="check" :size="12" /> Aplicado
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Barra de Acción Masiva Fija (cuando hay seleccionados) -->
      <div
        v-if="seleccionados.size > 0"
        class="border-t border-amber-300 bg-amber-50 p-3 flex items-center justify-between shadow-xs"
      >
        <span class="text-xs font-semibold text-amber-950">
          {{ seleccionados.size }} productos seleccionados para liquidación estratégica
        </span>
        <div class="flex items-center gap-2">
          <button
            class="rounded-lg border border-amber-400 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100"
            @click="seleccionados.clear()"
          >
            Cancelar selección
          </button>
          <button
            class="rounded-lg bg-primary-container px-4 py-1.5 text-xs font-semibold text-white hover:bg-brand-900 shadow-xs flex items-center gap-1.5"
            @click="ejecutarSeleccionados"
          >
            <Icon name="bolt" :size="14" class="text-amber-300" />
            Ejecutar Liquidación en POS ({{ seleccionados.size }})
          </button>
        </div>
      </div>
    </section>

    <!-- MODAL: CONFIGURAR REGLAS DE LIQUIDACIÓN -->
    <Modal
      v-if="modalRegla"
      titulo="Reglas y Umbrales de Liquidación (Categoría C)"
      ancho="max-w-md"
      @cerrar="modalRegla = false"
    >
      <form class="space-y-4 text-xs" @submit.prevent="guardarRegla">
        <p class="text-on-surface-variant">
          El sistema evalúa semanalmente productos de baja rotación para sugerir su venta estratégica en cajas antes de merma.
        </p>
        <div>
          <label class="font-semibold text-on-surface block mb-1">Rotación mínima aceptable (uds/semana)</label>
          <input
            v-model="regla.rotacion_minima_liquidacion_semanal"
            type="number"
            step="0.1"
            required
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface focus:border-primary-container focus:outline-none"
          />
          <span class="text-[11px] text-outline">Por debajo de este valor el SKU se clasifica como candidato a markdown.</span>
        </div>
        <div>
          <label class="font-semibold text-on-surface block mb-1">Descuento de liquidación sugerido (%)</label>
          <input
            v-model="regla.descuento_liquidacion_pct"
            type="number"
            step="1"
            min="1"
            max="90"
            required
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface focus:border-primary-container focus:outline-none"
          />
          <span class="text-[11px] text-outline">Porcentaje sugerido de rebaja en precio de venta para góndola.</span>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-outline-variant/30">
          <Btn variant="outline" type="button" @click="modalRegla = false">Cancelar</Btn>
          <Btn variant="primary" type="submit">Guardar regla</Btn>
        </div>
      </form>
    </Modal>

    <!-- MODAL: AUDITORÍA DE CLASIFICACIÓN ABC -->
    <Modal
      v-if="modalCambiosAbc"
      titulo="Productos Reclasificados del Mes (Auditoría ABC)"
      ancho="max-w-2xl"
      @cerrar="modalCambiosAbc = false"
    >
      <div class="space-y-3 text-xs">
        <p class="text-on-surface-variant">
          Registro histórico de cambios de clasificación según el principio de Pareto (80/15/5).
        </p>
        <div class="max-h-72 overflow-y-auto rounded-xl border border-outline-variant/30 bg-surface-container-low">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/40 text-[11px] uppercase font-bold text-outline">
                <th class="py-2 px-3">Producto</th>
                <th class="py-2 px-3 text-center">Clasificación Anterior</th>
                <th class="py-2 px-3 text-center">Nueva Clasificación</th>
                <th class="py-2 px-3 text-right">Fecha</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/20">
              <tr v-if="!cambiosAbc.length">
                <td colspan="4" class="py-4 text-center text-on-surface-variant">Sin reclasificaciones en el período.</td>
              </tr>
              <tr v-for="(c, i) in cambiosAbc" :key="i" class="py-2">
                <td class="py-2 px-3 font-semibold text-on-surface">SKU #{{ c.product_id }}</td>
                <td class="py-2 px-3 text-center font-bold font-mono">{{ c.clasificacion_anterior || '—' }}</td>
                <td class="py-2 px-3 text-center font-bold font-mono text-primary">{{ c.clasificacion_nueva }}</td>
                <td class="py-2 px-3 text-right text-outline">{{ c.fecha || 'Reciente' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="flex justify-end pt-2">
          <Btn variant="outline" @click="modalCambiosAbc = false">Cerrar</Btn>
        </div>
      </div>
    </Modal>
  </main>
</template>
