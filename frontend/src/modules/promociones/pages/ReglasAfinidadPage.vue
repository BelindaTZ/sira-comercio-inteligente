<script setup>
/**
 * Reglas de asociación de canasta (FR-001, FR-002) + tasa de redención de cupones
 * de afinidad (FR-008). El sistema calcula las reglas mensualmente; el Jefe de
 * Marketing desactiva las que no considera accionables. Arquetipo "Gestión".
 */
import { computed, onMounted, ref } from 'vue'
import { promocionesApi } from '@/services/promocionesApi'
import { useSesion } from '@/stores/sesion'
import { confirm, prompt } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'

const sesion = useSesion()
const puedeEditar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Marketing_CRM', 'regla_afinidad'),
)
const esDesarrollo = import.meta.env.DEV

const ESTADOS = [
  { value: 'vigente', label: 'Vigentes' },
  { value: 'desactivada', label: 'Desactivadas' },
  { value: 'reemplazada', label: 'Reemplazadas' },
  { value: '', label: 'Todas' },
]

const filtroEstado = ref('vigente')
const reglas = ref([])
const tasa = ref(null)
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const chipEstado = (e) =>
  ({ vigente: 'ok', desactivada: 'quiebre', reemplazada: 'neutral' })[e] || 'neutral'

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    ;[reglas.value, tasa.value] = await Promise.all([
      promocionesApi.reglasAfinidad(filtroEstado.value || undefined),
      promocionesApi.tasaRedencionAfinidad().catch(() => null),
    ])
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function recalcular() {
  const ok = await confirm({
    title: 'Recalcular reglas de afinidad',
    message: 'Vuelve a correr el análisis de canasta sobre el histórico. Sólo disponible en desarrollo.',
    confirmText: 'Recalcular',
  })
  if (!ok) return
  try {
    await promocionesApi.forzarCalculoAfinidad()
    aviso.value = 'Reglas recalculadas.'
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function desactivar(regla) {
  const motivo = await prompt({
    title: 'Desactivar la regla de afinidad',
    message: `${nombre(regla, 'ant')} → ${nombre(regla, 'con')}. No se reactiva sola.`,
    label: 'Motivo (opcional)',
    confirmText: 'Desactivar',
    tone: 'danger',
  })
  if (motivo === null) return
  try {
    await promocionesApi.desactivarRegla(regla.regla_id, motivo)
    aviso.value = 'Regla desactivada.'
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

function nombre(r, lado) {
  const id = lado === 'ant' ? r.product_id_antecedente : r.product_id_consecuente
  const nom = lado === 'ant' ? r.product_nombre_antecedente : r.product_nombre_consecuente
  return nom || `Producto #${id}`
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1200px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Reglas de afinidad"
      subtitulo="Asociaciones de canasta calculadas mensualmente (compra de A → compra de B). Desactivá las que no consideres accionables; la decisión persiste (FR-001 / FR-002)."
    >
      <template #badge>
        <SemanticChip tipo="neutral">{{ reglas.length }} reglas</SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="esDesarrollo && puedeEditar" variant="ghost" @click="recalcular">
          <Icon name="bolt" :size="15" /> Recalcular (dev)
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

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile label="Reglas en la vista" :valor="reglas.length.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile
        label="Cupones de afinidad enviados"
        :valor="tasa ? tasa.enviados.toLocaleString('es-EC') : '—'"
        estado-tipo="neutral"
      >
        <template #icono><Icon name="megaphone" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Cupones redimidos"
        :valor="tasa ? tasa.redimidos.toLocaleString('es-EC') : '—'"
        estado-tipo="ok"
      >
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Tasa de redención"
        :valor="tasa ? `${tasa.tasa_pct}%` : '—'"
        microcopy="separada de los cupones por hito"
        :estado-tipo="tasa && tasa.tasa_pct >= 5 ? 'ok' : 'neutral'"
      />
    </section>

    <div class="mb-4 flex items-center gap-2">
      <label class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600">
        <Icon name="filter" :size="14" class="text-brand-700" />
        <select v-model="filtroEstado" class="bg-transparent text-slate-800 focus:outline-none" @change="cargar">
          <option v-for="e in ESTADOS" :key="e.value" :value="e.value">{{ e.label }}</option>
        </select>
      </label>
    </div>

    <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <table class="w-full text-left text-[13px]">
        <thead>
          <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
            <th class="px-5 py-3">Antecedente → Consecuente</th>
            <th class="px-4 py-3 text-right">Soporte</th>
            <th class="px-4 py-3 text-right">Confianza</th>
            <th class="px-4 py-3 text-right">Lift</th>
            <th class="px-4 py-3 text-center">Estado</th>
            <th v-if="puedeEditar" class="px-4 py-3 text-right" />
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100/90 bg-white/80">
          <tr v-if="cargando"><td :colspan="puedeEditar ? 6 : 5" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
          <tr v-else-if="!reglas.length"><td :colspan="puedeEditar ? 6 : 5" class="px-5 py-8 text-center text-slate-400">Sin reglas para este filtro.</td></tr>
          <tr v-for="r in reglas" :key="r.regla_id" class="hover:bg-brand-50/70">
            <td class="px-5 py-3">
              <div class="font-semibold text-slate-800">
                {{ nombre(r, 'ant') }} <span class="text-brand-500">→</span> {{ nombre(r, 'con') }}
              </div>
              <div class="font-mono text-[11px] text-slate-400">
                #{{ r.product_id_antecedente }} → #{{ r.product_id_consecuente }}
              </div>
            </td>
            <td class="px-4 py-3 text-right tabular-nums text-slate-600">{{ Number(r.soporte).toFixed(3) }}</td>
            <td class="px-4 py-3 text-right font-semibold tabular-nums text-slate-800">{{ Number(r.confianza).toFixed(3) }}</td>
            <td class="px-4 py-3 text-right tabular-nums text-slate-600">
              {{ r.lift == null ? '—' : Number(r.lift).toFixed(2) }}
            </td>
            <td class="px-4 py-3 text-center">
              <SemanticChip :tipo="chipEstado(r.estado)">{{ r.estado }}</SemanticChip>
            </td>
            <td v-if="puedeEditar" class="px-4 py-3 text-right">
              <Btn v-if="r.estado === 'vigente'" variant="danger" class="!px-2.5 !py-1 !text-[12px]" @click="desactivar(r)">
                Desactivar
              </Btn>
              <span v-else class="text-[11px] text-slate-400">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
