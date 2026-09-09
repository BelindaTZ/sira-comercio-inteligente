<script setup>
/**
 * Analítica de Tiempo de Cobro — feature 007 US5 (FR-015 a FR-018).
 * Estructura de `docs/diseno-ui/.../sira_anal_tica_de_tiempo_de_cobro/`: page
 * header, fila de KPI y dos paneles de revisión (semanal por caja para el
 * Encargado de Tienda, mensual por tienda a nivel de red para el Jefe Comercial).
 *
 * Alcance = spec: sólo el promedio de duración del cobro (`fecha_hora −
 * fecha_inicio_cobro`) y el conteo de ventas consideradas, calculados en el
 * backend, excluyendo anuladas (FR-018) y ventas sembradas del dataset. El
 * desglose anatómico del ciclo, la telemetría horaria y la fricción por medio de
 * pago del mockup NO están en la feature (no se fabrican datos — Principio VII).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const puedeVerRed = computed(() =>
  ['Jefe_Comercial', 'Gerente_General'].includes(sesion.rol),
)

const hoy = new Date()

function isoWeek(d) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  const day = (t.getUTCDay() + 6) % 7
  t.setUTCDate(t.getUTCDate() - day + 3)
  const firstThursday = new Date(Date.UTC(t.getUTCFullYear(), 0, 4))
  return 1 + Math.round((t - firstThursday) / 604800000)
}

const semanal = reactive({
  cajaId: Number(localStorage.getItem('sira_caja_id')) || null,
  semana: isoWeek(hoy),
  anio: hoy.getFullYear(),
})
const mensual = reactive({ mes: hoy.getMonth() + 1, anio: hoy.getFullYear() })

const cajas = ref([])
const resSemanal = ref(null)
const resMensual = ref([])
const cargandoSemanal = ref(false)
const cargandoMensual = ref(false)
const error = ref('')

const cajaSeleccionada = computed(
  () => cajas.value.find((c) => c.caja_id === semanal.cajaId) || null,
)

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]

function fmt(segundos) {
  if (segundos == null) return '—'
  if (segundos < 60) return `${segundos.toFixed(1)} s`
  const m = Math.floor(segundos / 60)
  const s = Math.round(segundos % 60)
  return `${m} min ${String(s).padStart(2, '0')} s`
}

const promedioRed = computed(() => {
  const v = resMensual.value.filter((f) => f.duracion_promedio_segundos != null)
  if (!v.length) return null
  const tot = v.reduce(
    (a, f) => a + f.duracion_promedio_segundos * f.cantidad_ventas_consideradas,
    0,
  )
  const n = v.reduce((a, f) => a + f.cantidad_ventas_consideradas, 0)
  return n ? tot / n : null
})
const tiendasMedidas = computed(
  () => resMensual.value.filter((f) => f.cantidad_ventas_consideradas > 0).length,
)

const columnas = [
  { key: 'tienda', label: 'Tienda', width: '120px' },
  { key: 'promedio', label: 'Tiempo de cobro promedio', align: 'right', width: '200px' },
  { key: 'ventas', label: 'Ventas medidas', align: 'right', width: '150px' },
  { key: 'lectura', label: 'Lectura' },
]

async function cargarCajas() {
  try {
    cajas.value = await ventasApi.cajas()
    if (!cajas.value.some((c) => c.caja_id === semanal.cajaId))
      semanal.cajaId = cajas.value[0]?.caja_id ?? null
  } catch {
    /* informativo — el selector queda vacío */
  }
}

async function consultarSemanal() {
  if (semanal.cajaId == null) return
  cargandoSemanal.value = true
  error.value = ''
  try {
    resSemanal.value = await ventasApi.tiempoCobroSemanal(semanal.cajaId, {
      semana: semanal.semana,
      anio: semanal.anio,
    })
    localStorage.setItem('sira_caja_id', String(semanal.cajaId))
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargandoSemanal.value = false
  }
}

async function consultarMensual() {
  if (!puedeVerRed.value) return
  cargandoMensual.value = true
  error.value = ''
  try {
    resMensual.value = await ventasApi.tiempoCobroMensual({
      mes: mensual.mes,
      anio: mensual.anio,
    })
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargandoMensual.value = false
  }
}

onMounted(async () => {
  await cargarCajas()
  consultarSemanal()
  consultarMensual()
})
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Analítica de Tiempo de Cobro"
      subtitulo="Duración del cobro por caja y por tienda para localizar dónde el flujo en sala es más lento (OT-4.2: reducir el tiempo de cobro)."
    >
      <template #badge>
        <SemanticChip tipo="neutral">Sólo ventas en vivo</SemanticChip>
      </template>
    </PageHeader>

    <div
      class="mb-6 flex items-start gap-2.5 rounded-xl border border-brand-200 bg-brand-50/60 px-4 py-3 text-[12px] text-slate-600"
    >
      <Icon name="alert" :size="15" class="mt-0.5 shrink-0 text-brand-600" />
      <p>
        La medición aplica sólo a las ventas registradas en vivo desde que esta función está
        disponible. Las ventas históricas del dataset no tienen un momento de inicio de cobro y no
        se les fabrica una duración (FR-015). Las ventas anuladas quedan excluidas (FR-018).
      </p>
    </div>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
      {{ error }}
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Ciclo de cobro — caja seleccionada"
        :valor="resSemanal ? fmt(resSemanal.duracion_promedio_segundos) : '—'"
        variant="emerald"
        :microcopy="`${cajaSeleccionada ? cajaSeleccionada.nombre : 'Sin caja'} · semana ISO ${semanal.semana}/${semanal.anio}`"
        pie-label="Ventas consideradas"
        :pie-valor="`${resSemanal ? resSemanal.cantidad_ventas_consideradas : 0} en la semana`"
      />
      <KpiTile
        label="Muestra semanal de la caja"
        :valor="resSemanal ? resSemanal.cantidad_ventas_consideradas.toLocaleString('es-CL') : '0'"
        :estado="resSemanal && resSemanal.cantidad_ventas_consideradas ? 'con datos' : 'sin datos aún'"
        :estado-tipo="resSemanal && resSemanal.cantidad_ventas_consideradas ? 'ok' : 'neutral'"
        microcopy="Ventas confirmadas en vivo con inicio de cobro registrado"
      >
        <template #icono><Icon name="cart" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Promedio de la red — mes"
        :valor="puedeVerRed ? fmt(promedioRed) : 'Restringido'"
        :microcopy="
          puedeVerRed
            ? `${MESES[mensual.mes - 1]} ${mensual.anio}, ponderado por ventas`
            : 'Vista del Jefe Comercial'
        "
      >
        <template #icono><Icon name="clock" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Tiendas con medición este mes"
        :valor="puedeVerRed ? tiendasMedidas.toLocaleString('es-CL') : '—'"
        :estado="puedeVerRed && tiendasMedidas ? 'operando en vivo' : 'arranque en frío'"
        :estado-tipo="puedeVerRed && tiendasMedidas ? 'ok' : 'neutral'"
        microcopy="Red completa (FR-017)"
      >
        <template #icono><Icon name="truck" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="grid items-start gap-6" :class="puedeVerRed ? 'lg:grid-cols-[380px_minmax(0,1fr)]' : ''">
      <!-- Revisión semanal por caja (Encargado de Tienda) -->
      <section class="satin-card rounded-2xl p-5 shadow-card-subtle">
        <div class="mb-1 flex items-center gap-2">
          <Icon name="clock" :size="18" class="text-brand-700" />
          <h2 class="font-display text-base font-bold text-brand-950">Revisión semanal por caja</h2>
        </div>
        <p class="mb-4 text-[12px] text-slate-600">
          El Encargado de Tienda revisa el promedio de cada caja de su tienda (FR-016).
        </p>

        <form class="space-y-3" @submit.prevent="consultarSemanal">
          <label class="block text-[12px] font-semibold text-slate-600">
            Caja
            <select
              v-model.number="semanal.cajaId"
              :disabled="!cajas.length"
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:bg-slate-50"
            >
              <option v-if="!cajas.length" :value="null">Sin cajas registradas</option>
              <option v-for="c in cajas" :key="c.caja_id" :value="c.caja_id">
                {{ c.nombre }}<template v-if="!c.activa"> (inactiva)</template>
              </option>
            </select>
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block text-[12px] font-semibold text-slate-600">
              Semana ISO
              <input
                v-model.number="semanal.semana"
                type="number"
                min="1"
                max="53"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
              />
            </label>
            <label class="block text-[12px] font-semibold text-slate-600">
              Año
              <input
                v-model.number="semanal.anio"
                type="number"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
              />
            </label>
          </div>
          <Btn type="submit" variant="primary" class="w-full justify-center" :disabled="cargandoSemanal">
            <Icon name="search" :size="15" /> {{ cargandoSemanal ? 'Consultando…' : 'Consultar' }}
          </Btn>
        </form>

        <div
          v-if="resSemanal"
          class="mt-4 rounded-xl border border-brand-200 bg-brand-50/50 p-4 text-center"
        >
          <div class="font-display text-2xl font-extrabold tabular-nums text-brand-900">
            {{ fmt(resSemanal.duracion_promedio_segundos) }}
          </div>
          <p class="mt-0.5 text-[11px] text-slate-600">
            promedio de {{ cajaSeleccionada ? cajaSeleccionada.nombre : `caja ${resSemanal.caja_id}` }}
            · semana {{ resSemanal.semana }}
          </p>
          <p class="mt-1 text-[11px] font-semibold text-slate-500">
            {{ resSemanal.cantidad_ventas_consideradas }} venta(s) consideradas
          </p>
          <p
            v-if="!resSemanal.cantidad_ventas_consideradas"
            class="mt-2 text-[11px] text-amber-700"
          >
            Sin ventas en vivo registradas para esta caja y semana todavía.
          </p>
        </div>
      </section>

      <!-- Revisión mensual por tienda a nivel de red (Jefe Comercial) -->
      <section v-if="puedeVerRed">
        <DataTable
          titulo="Revisión mensual por tienda — red completa"
          subtitulo="El Jefe Comercial compara las tiendas del mes para decidir dónde actuar (FR-017)."
          :columns="columnas"
          :rows="resMensual"
          row-key="tienda_id"
          :loading="cargandoMensual"
          densa
          :page="1"
          :size="100"
          :total="resMensual.length"
          empty-text="Sin ventas en vivo medidas en el mes seleccionado"
        >
          <template #acciones-cabecera>
            <select
              v-model.number="mensual.mes"
              class="h-9 rounded-lg border border-brand-300 bg-white px-2 text-[12px] text-slate-700"
              @change="consultarMensual"
            >
              <option v-for="(m, i) in MESES" :key="m" :value="i + 1">{{ m }}</option>
            </select>
            <input
              v-model.number="mensual.anio"
              type="number"
              class="h-9 w-20 rounded-lg border border-brand-300 bg-white px-2 text-[12px] text-slate-700"
              @change="consultarMensual"
            />
          </template>

          <template #cell:tienda="{ row }">
            <span class="font-mono text-[12px] font-bold text-brand-800">#{{ row.tienda_id }}</span>
          </template>

          <template #cell:promedio="{ row }">
            <span class="font-bold tabular-nums text-slate-900">
              {{ fmt(row.duracion_promedio_segundos) }}
            </span>
          </template>

          <template #cell:ventas="{ row }">
            <span class="tabular-nums text-slate-600">
              {{ row.cantidad_ventas_consideradas.toLocaleString('es-CL') }}
            </span>
          </template>

          <template #cell:lectura="{ row }">
            <SemanticChip
              v-if="row.duracion_promedio_segundos == null"
              tipo="neutral"
            >
              Sin datos
            </SemanticChip>
            <SemanticChip
              v-else-if="promedioRed != null && row.duracion_promedio_segundos > promedioRed * 1.15"
              tipo="fifo"
            >
              Sobre el promedio de la red
            </SemanticChip>
            <SemanticChip v-else tipo="ok">En rango</SemanticChip>
          </template>
        </DataTable>
      </section>
    </div>
  </div>
</template>
