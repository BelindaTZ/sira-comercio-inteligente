<script setup>
/**
 * Reporte mensual de patrones de diferencias de cuadre (FR-009 a FR-011). El Jefe
 * de Finanzas ve las diferencias por cajero y turno y los ajustes de inventario
 * con faltante inusual, y puede escalar un patrón abriendo un incidente de fraude
 * desde aquí. La Gerencia lo consulta en lectura. Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { useSesion } from '@/stores/sesion'
import { prompt } from '@/shared/ui/dialogs'
import { money as moneyUsd } from '@/shared/currency'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'

const sesion = useSesion()
const puedeEscalar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Finanzas', 'incidentes_fraude'),
)
const money = (v) => moneyUsd(v, { showCode: false })

const hoy = new Date()
const filtro = reactive({ mes: hoy.getMonth() + 1, anio: hoy.getFullYear() })
const reporte = ref({ cuadres: [], ajustes_senalados: [] })
const error = ref('')
const aviso = ref('')
const cargando = ref(false)

const kpi = computed(() => {
  const sumaCuadres = reporte.value.cuadres.reduce((a, t) => a + Number(t.suma_diferencias || 0), 0)
  return {
    turnos: reporte.value.cuadres.length,
    sumaCuadres,
    ajustes: reporte.value.ajustes_senalados.length,
    faltanteAjustes: reporte.value.ajustes_senalados.reduce(
      (a, x) => a + Number(x.diferencia || 0),
      0,
    ),
  }
})

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    reporte.value = await cajaApi.reporteDiferencias({ mes: filtro.mes, anio: filtro.anio })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function escalarCuadre(turno) {
  const descripcion = await prompt({
    title: `Abrir incidente — cajero #${turno.cajero_id}`,
    label: 'Evidencia del patrón',
    required: true,
    initial: `Patrón de diferencias en el turno ${turno.apertura_id}: ${money(turno.suma_diferencias)}`,
    confirmText: 'Abrir incidente',
    tone: 'danger',
  })
  if (!descripcion) return
  try {
    await cajaApi.abrirIncidente({ empleadoId: turno.cajero_id, descripcion })
    aviso.value = `Incidente abierto sobre el cajero #${turno.cajero_id}.`
  } catch (e) {
    error.value = e.message
  }
}

async function escalarAjuste(ajuste) {
  const descripcion = await prompt({
    title: `Abrir incidente — empleado #${ajuste.empleado_id}`,
    label: 'Evidencia del patrón',
    required: true,
    initial: `Ajuste de inventario ${ajuste.ajuste_id} con faltante de ${money(ajuste.diferencia)}`,
    confirmText: 'Abrir incidente',
    tone: 'danger',
  })
  if (!descripcion) return
  try {
    await cajaApi.abrirIncidente({
      empleadoId: ajuste.empleado_id,
      ajusteId: ajuste.ajuste_id,
      descripcion,
    })
    aviso.value = `Incidente abierto sobre el empleado #${ajuste.empleado_id}.`
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Patrones de diferencias de cuadre"
      subtitulo="Diferencias de caja agrupadas por cajero y turno y ajustes de inventario con faltante inusual del mes (FR-009 a FR-011). Escalá un patrón para abrir un incidente de fraude."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.ajustes > 0 || kpi.sumaCuadres < 0 ? 'quiebre' : 'ok'">
          {{ kpi.turnos }} turnos con diferencia · {{ kpi.ajustes }} ajustes señalados
        </SemanticChip>
      </template>
      <template #acciones>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="clock" :size="14" class="text-brand-700" />
          <input v-model.number="filtro.mes" type="number" min="1" max="12" class="w-10 bg-transparent text-center focus:outline-none" />
          <span class="text-slate-300">/</span>
          <input v-model.number="filtro.anio" type="number" class="w-16 bg-transparent text-center focus:outline-none" />
        </label>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl bg-brand-800 px-3.5 py-2 text-[13px] font-bold text-white hover:bg-brand-700"
          @click="cargar"
        >
          <Icon name="search" :size="15" /> Consultar
        </button>
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
        label="Turnos con diferencia"
        :valor="kpi.turnos.toLocaleString('es-EC')"
        variant="emerald"
        :microcopy="`Mes ${filtro.mes}/${filtro.anio}`"
      />
      <KpiTile
        label="Diferencia acumulada"
        :valor="money(kpi.sumaCuadres)"
        :estado-tipo="kpi.sumaCuadres < 0 ? 'quiebre' : 'ok'"
        microcopy="Suma de los descuadres de todos los turnos"
      >
        <template #icono><Icon name="bank" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Ajustes señalados"
        :valor="kpi.ajustes.toLocaleString('es-EC')"
        :estado-tipo="kpi.ajustes > 0 ? 'quiebre' : 'ok'"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Faltante en ajustes" :valor="money(kpi.faltanteAjustes)" estado-tipo="fifo">
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="grid gap-6 xl:grid-cols-2">
      <section class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
        <div class="border-b border-brand-200 px-5 py-3">
          <h2 class="font-display text-[14px] font-bold text-brand-950">Diferencias por cajero y turno</h2>
        </div>
        <table class="w-full text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-4 py-2.5">Cajero</th>
              <th class="px-3 py-2.5">Turno</th>
              <th class="px-3 py-2.5 text-right">Σ diferencias</th>
              <th class="px-3 py-2.5 text-right">Cuadres</th>
              <th v-if="puedeEscalar" class="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="cargando"><td :colspan="puedeEscalar ? 5 : 4" class="px-4 py-8 text-center text-slate-400">Cargando…</td></tr>
            <tr v-else-if="!reporte.cuadres.length"><td :colspan="puedeEscalar ? 5 : 4" class="px-4 py-8 text-center text-slate-400">Sin turnos con diferencia en el mes</td></tr>
            <tr v-for="t in reporte.cuadres" :key="`${t.cajero_id}-${t.apertura_id}`" class="hover:bg-brand-50/70">
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-brand-800">#{{ t.cajero_id }}</td>
              <td class="px-3 py-2.5 tabular-nums text-slate-600">{{ t.fecha_turno || `#${t.apertura_id}` }}</td>
              <td class="px-3 py-2.5 text-right font-bold tabular-nums" :class="Number(t.suma_diferencias) < 0 ? 'text-crimson-ruby' : 'text-slate-800'">
                {{ money(t.suma_diferencias) }}
              </td>
              <td class="px-3 py-2.5 text-right tabular-nums text-slate-600">{{ t.cantidad_cuadres_con_diferencia }}</td>
              <td v-if="puedeEscalar" class="px-3 py-2.5 text-right">
                <Btn variant="danger" class="!px-2.5 !py-1 !text-[12px]" @click="escalarCuadre(t)">Escalar</Btn>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
        <div class="border-b border-brand-200 px-5 py-3">
          <h2 class="font-display text-[14px] font-bold text-brand-950">Ajustes de inventario señalados</h2>
        </div>
        <table class="w-full text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-4 py-2.5">Ajuste</th>
              <th class="px-3 py-2.5">Producto</th>
              <th class="px-3 py-2.5 text-right">Faltante</th>
              <th class="px-3 py-2.5">Empleado</th>
              <th v-if="puedeEscalar" class="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="!reporte.ajustes_senalados.length"><td :colspan="puedeEscalar ? 5 : 4" class="px-4 py-8 text-center text-slate-400">Sin ajustes anómalos en el mes</td></tr>
            <tr v-for="a in reporte.ajustes_senalados" :key="a.ajuste_id" class="hover:bg-brand-50/70">
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-brand-800">#{{ a.ajuste_id }}</td>
              <td class="px-3 py-2.5 font-mono text-[12px] text-slate-600">#{{ a.product_id }}</td>
              <td class="px-3 py-2.5 text-right font-bold tabular-nums text-crimson-ruby">{{ money(a.diferencia) }}</td>
              <td class="px-3 py-2.5 font-mono text-[12px] text-slate-600">#{{ a.empleado_id }}</td>
              <td v-if="puedeEscalar" class="px-3 py-2.5 text-right">
                <Btn variant="danger" class="!px-2.5 !py-1 !text-[12px]" @click="escalarAjuste(a)">Escalar</Btn>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>
