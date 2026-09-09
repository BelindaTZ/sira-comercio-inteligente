<script setup>
/**
 * Cuadre de caja horario (feature 006, US1 — FR-001 a FR-005). El Cajero registra
 * la apertura con el fondo inicial y el cuadre con el total físico contado; el
 * sistema calcula la diferencia server-side (Principio V) y marca para revisión
 * cualquier cuadre con diferencia ≠ 0. El Encargado de Tienda ve el estado de
 * todas las cajas de su tienda en una sola consulta (FR-005).
 *
 * Alcance = spec: la entidad `cierre_caja` sólo tiene total_esperado /
 * total_registrado / diferencia. El arqueo ciego por denominación, los "sobres de
 * alivio", el bloqueo de emisión y el Cierre Z del mockup NO están en la feature;
 * el contador de billetes de abajo es sólo una ayuda visual para llegar al total.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const tiendaId = computed(() => sesion.tiendaId ?? (Number(localStorage.getItem("sira_tienda_id")) || 1))

const cajas = ref([])
const cierres = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const apertura = reactive({ cajaId: null, fondoInicial: '' })
const cuadre = reactive({ cajaId: null, totalRegistrado: '' })
const ultimoCierre = ref(null)

// contador de efectivo (ayuda para llegar al total físico — no se envía al backend)
const DENOMS = [20000, 10000, 5000, 2000, 1000, 500, 100, 50, 10]
const conteo = reactive(Object.fromEntries(DENOMS.map((d) => [d, ''])))
const mostrarContador = ref(false)
const totalContado = computed(() =>
  DENOMS.reduce((s, d) => s + d * (Number(conteo[d]) || 0), 0),
)

const money = (v) => `$${Math.round(Number(v || 0)).toLocaleString('es-CL')}`
const cajaNombre = (id) => cajas.value.find((c) => c.caja_id === id)?.nombre || `Caja ${id}`

const kpi = computed(() => {
  const hoy = cierres.value
  const descuadres = hoy.filter((c) => Number(c.diferencia) !== 0)
  const neta = hoy.reduce((s, c) => s + Number(c.diferencia), 0)
  const cajasCuadradas = new Set(hoy.map((c) => c.caja_id)).size
  return {
    total: cajas.value.length,
    cuadradas: cajasCuadradas,
    cuadres: hoy.length,
    descuadres: descuadres.length,
    neta,
  }
})

const columnas = [
  { key: 'caja', label: 'Caja', width: '160px' },
  { key: 'cajero', label: 'Cajero', width: '110px' },
  { key: 'esperado', label: 'Total esperado', align: 'right', width: '150px' },
  { key: 'contado', label: 'Total contado', align: 'right', width: '150px' },
  { key: 'diferencia', label: 'Diferencia', align: 'right', width: '150px' },
  { key: 'revision', label: 'Estado', align: 'center', width: '150px' },
]

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    cajas.value = await cajaApi.cajas(tiendaId.value).catch(() => [])
    cierres.value = await cajaApi.cierres({ tiendaId: tiendaId.value })
    if (apertura.cajaId == null) apertura.cajaId = cajas.value[0]?.caja_id ?? null
    if (cuadre.cajaId == null) cuadre.cajaId = cajas.value[0]?.caja_id ?? null
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

async function registrarApertura() {
  error.value = ''
  aviso.value = ''
  try {
    const r = await cajaApi.registrarApertura({
      cajaId: Number(apertura.cajaId),
      fondoInicial: apertura.fondoInicial,
    })
    aviso.value = `${cajaNombre(r.caja_id)} abierta con fondo ${money(r.fondo_inicial)}`
    apertura.fondoInicial = ''
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

async function registrarCuadre() {
  error.value = ''
  aviso.value = ''
  try {
    ultimoCierre.value = await cajaApi.registrarCierre({
      cajaId: Number(cuadre.cajaId),
      totalRegistrado: cuadre.totalRegistrado,
    })
    cuadre.totalRegistrado = ''
    DENOMS.forEach((d) => (conteo[d] = ''))
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

function usarContado() {
  cuadre.totalRegistrado = String(totalContado.value)
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Cuadre de Caja"
      subtitulo="Apertura con fondo inicial y cuadre horario con el total físico contado. El sistema calcula la diferencia y marca para revisión cualquier descuadre (FR-003/FR-004)."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.descuadres > 0 ? 'quiebre' : 'ok'">
          {{ kpi.descuadres > 0 ? `${kpi.descuadres} descuadres hoy` : 'Sin descuadres hoy' }}
        </SemanticChip>
      </template>
    </PageHeader>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Cajas de la tienda"
        :valor="kpi.total.toLocaleString('es-CL')"
        variant="emerald"
        :microcopy="`${kpi.cuadradas} con cuadre registrado hoy`"
        pie-label="Cuadres del día"
        :pie-valor="`${kpi.cuadres} registrados`"
      />
      <KpiTile
        label="Descuadres del día"
        :valor="kpi.descuadres.toLocaleString('es-CL')"
        :estado="kpi.descuadres > 0 ? 'marcados para revisión' : 'todo cuadra'"
        :estado-tipo="kpi.descuadres > 0 ? 'quiebre' : 'ok'"
        microcopy="Cuadres con diferencia distinta de cero (FR-004)"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Diferencia neta del día"
        :valor="(kpi.neta >= 0 ? '+' : '') + money(kpi.neta)"
        :estado="kpi.neta < 0 ? 'faltante' : kpi.neta > 0 ? 'sobrante' : 'exacto'"
        :estado-tipo="kpi.neta < 0 ? 'quiebre' : kpi.neta > 0 ? 'fifo' : 'ok'"
        microcopy="Suma de todas las diferencias de cuadre de hoy"
      >
        <template #icono><Icon name="bank" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Total contado (contador)"
        :valor="money(totalContado)"
        variant="ia"
        estado="ayuda"
        estado-tipo="ia"
        microcopy="Desglose de billetes/monedas de abajo"
      >
        <template #icono><Icon name="filter" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">{{ error }}</p>
    <p v-if="aviso" class="mb-4 rounded-lg bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800">
      {{ aviso }}
    </p>

    <div class="grid items-start gap-6 2xl:grid-cols-[400px_minmax(0,1fr)]">
      <div class="space-y-4">
        <!-- Apertura -->
        <section class="satin-card rounded-2xl p-5 shadow-card-subtle">
          <div class="mb-3 flex items-center gap-2">
            <Icon name="bank" :size="18" class="text-brand-700" />
            <h2 class="font-display text-base font-bold text-brand-950">Apertura de caja</h2>
          </div>
          <form class="space-y-3" @submit.prevent="registrarApertura">
            <label class="block text-[12px] font-semibold text-slate-600">
              Caja
              <select
                v-model.number="apertura.cajaId"
                :disabled="!cajas.length"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:bg-slate-50"
              >
                <option v-if="!cajas.length" :value="null">Sin cajas</option>
                <option v-for="c in cajas" :key="c.caja_id" :value="c.caja_id">{{ c.nombre }}</option>
              </select>
            </label>
            <label class="block text-[12px] font-semibold text-slate-600">
              Fondo inicial (CLP)
              <input
                v-model="apertura.fondoInicial"
                type="number"
                min="0"
                required
                placeholder="50000"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
              />
            </label>
            <Btn type="submit" variant="primary" class="w-full justify-center" :disabled="apertura.cajaId == null">
              <Icon name="check" :size="15" /> Registrar apertura
            </Btn>
          </form>
        </section>

        <!-- Cuadre -->
        <section class="satin-card rounded-2xl p-5 shadow-card-subtle">
          <div class="mb-3 flex items-center gap-2">
            <Icon name="chart" :size="18" class="text-brand-700" />
            <h2 class="font-display text-base font-bold text-brand-950">Cuadre horario</h2>
          </div>
          <form class="space-y-3" @submit.prevent="registrarCuadre">
            <label class="block text-[12px] font-semibold text-slate-600">
              Caja
              <select
                v-model.number="cuadre.cajaId"
                :disabled="!cajas.length"
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:bg-slate-50"
              >
                <option v-if="!cajas.length" :value="null">Sin cajas</option>
                <option v-for="c in cajas" :key="c.caja_id" :value="c.caja_id">{{ c.nombre }}</option>
              </select>
            </label>
            <label class="block text-[12px] font-semibold text-slate-600">
              Total físico contado (CLP)
              <input
                v-model="cuadre.totalRegistrado"
                type="number"
                min="0"
                required
                class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
              />
            </label>

            <button
              type="button"
              class="flex w-full items-center justify-between rounded-lg border border-brand-200 bg-brand-50/50 px-3 py-2 text-[12px] font-semibold text-slate-700 hover:bg-brand-50"
              @click="mostrarContador = !mostrarContador"
            >
              <span>Contador de efectivo por denominación</span>
              <Icon name="chevron" :size="14" :class="mostrarContador ? 'rotate-180' : ''" />
            </button>
            <div v-if="mostrarContador" class="space-y-1.5 rounded-lg border border-brand-200 p-2.5">
              <div v-for="d in DENOMS" :key="d" class="flex items-center gap-2 text-[12px]">
                <span class="w-16 shrink-0 tabular-nums text-slate-600">{{ money(d) }}</span>
                <span class="text-slate-400">×</span>
                <input
                  v-model="conteo[d]"
                  type="number"
                  min="0"
                  placeholder="0"
                  class="w-16 rounded border border-brand-300 bg-white px-2 py-1 text-right tabular-nums"
                />
                <span class="ml-auto tabular-nums font-semibold text-slate-700">
                  {{ money(d * (Number(conteo[d]) || 0)) }}
                </span>
              </div>
              <div class="flex items-center justify-between border-t border-brand-200 pt-1.5 text-[12px] font-bold">
                <span class="text-slate-700">Total contado</span>
                <span class="tabular-nums text-brand-900">{{ money(totalContado) }}</span>
              </div>
              <button
                type="button"
                class="w-full rounded-lg bg-brand-100 px-2 py-1 text-[11px] font-semibold text-brand-800 hover:bg-brand-200"
                @click="usarContado"
              >
                Usar este total
              </button>
            </div>

            <Btn type="submit" variant="primary" class="w-full justify-center" :disabled="cuadre.cajaId == null">
              <Icon name="check" :size="15" /> Registrar cuadre
            </Btn>
          </form>

          <div
            v-if="ultimoCierre"
            class="mt-3 rounded-xl border border-brand-200 bg-brand-50/50 p-3 text-center text-[12px]"
          >
            <p class="text-slate-600">
              Esperado {{ money(ultimoCierre.total_esperado) }} · Contado
              {{ money(ultimoCierre.total_registrado) }}
            </p>
            <div class="mt-1 flex items-center justify-center gap-2">
              <SemanticChip
                :tipo="Number(ultimoCierre.diferencia) === 0 ? 'ok' : Number(ultimoCierre.diferencia) < 0 ? 'quiebre' : 'fifo'"
              >
                {{ Number(ultimoCierre.diferencia) > 0 ? '+' : '' }}{{ money(ultimoCierre.diferencia) }}
              </SemanticChip>
              <span v-if="ultimoCierre.marcado_para_revision" class="text-[11px] font-semibold text-crimson-ruby">
                marcado para revisión
              </span>
            </div>
          </div>
        </section>
      </div>

      <DataTable
        titulo="Cajas de la tienda"
        :subtitulo="`Estado de cuadre de todas las cajas de la tienda #${tiendaId} en el día (FR-005).`"
        :columns="columnas"
        :rows="cierres"
        row-key="cierre_id"
        :loading="cargando"
        densa
        :page="1"
        :size="100"
        :total="cierres.length"
        empty-text="Sin cuadres registrados hoy"
      >
        <template #cell:caja="{ row }">
          <span class="text-[12px] font-semibold text-slate-800">{{ cajaNombre(row.caja_id) }}</span>
        </template>
        <template #cell:cajero="{ row }">
          <span class="font-mono text-[11px] text-slate-500">#{{ row.cajero_id }}</span>
        </template>
        <template #cell:esperado="{ row }">
          <span class="tabular-nums text-slate-600">{{ money(row.total_esperado) }}</span>
        </template>
        <template #cell:contado="{ row }">
          <span class="tabular-nums font-semibold text-slate-800">{{ money(row.total_registrado) }}</span>
        </template>
        <template #cell:diferencia="{ row }">
          <span
            class="tabular-nums font-bold"
            :class="Number(row.diferencia) === 0 ? 'text-emerald-700' : Number(row.diferencia) < 0 ? 'text-crimson-ruby' : 'text-amber-700'"
          >
            {{ Number(row.diferencia) > 0 ? '+' : '' }}{{ money(row.diferencia) }}
          </span>
        </template>
        <template #cell:revision="{ row }">
          <SemanticChip :tipo="row.marcado_para_revision ? 'quiebre' : 'ok'">
            {{ row.marcado_para_revision ? 'En revisión' : 'Cuadrada' }}
          </SemanticChip>
        </template>
      </DataTable>
    </div>
  </div>
</template>
