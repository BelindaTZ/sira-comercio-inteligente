<script setup>
/**
 * Campañas (feature 002).
 *  - US4: tasa de redención de los cupones automáticos por hito (FR-014).
 *  - US5: campañas de reactivación con grupo de control obligatorio y uplift
 *    real al cierre (FR-016..FR-019). Toda regla vive en el backend.
 * Kit visual compartido con Inventario / Catálogo / CRM.
 */
import { computed, onMounted, ref } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import FormularioCampana from './components/FormularioCampana.vue'

const ETIQUETA_HITO = {
  cumpleanos: 'Cumpleaños',
  aniversario_registro: 'Aniversario de registro',
}

const sesion = useSesion()
const puedeVer = computed(() => sesion.puedeLeerTabla('Marketing_CRM', 'campanas'))
const puedeCrear = computed(() => sesion.puedeEditarTabla('Marketing_CRM', 'campanas'))

const hito = ref([])
const campanas = ref([])
const resumen = ref({ redimidos: 0, tasa_redencion_pct: null })
const detalle = ref(null)
const cargando = ref(false)
const error = ref('')
const modal = ref(null) // 'nueva'

const pct = (v) => (v == null ? '—' : `${(v * 100).toFixed(1)} %`)
const fmt = (d) =>
  d ? new Date(d).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

const kpi = computed(() => {
  const enviados = hito.value.reduce((a, f) => a + f.enviados, 0)
  const redHito = hito.value.reduce((a, f) => a + f.redimidos, 0)
  // Si no hay cupones por hito todavía, se muestra la redención global del
  // programa (cupones de campaña del histórico), que sí tiene datos.
  return {
    tasa: enviados ? redHito / enviados : (resumen.value.tasa_redencion_pct ?? null) / 100,
    origen_tasa: enviados ? 'hito' : 'programa',
    redimidos: enviados ? redHito : resumen.value.redimidos,
    reactivaciones: campanas.value.length,
  }
})

const columnas = [
  { key: 'nombre', label: 'Campaña' },
  { key: 'periodo', label: 'Vigencia', width: '210px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '130px' },
  { key: 'ir', label: '', align: 'center', width: '40px' },
]

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    hito.value = await clientesApi.tasaRedencion()
    campanas.value = (await clientesApi.listarCampanas('reactivacion')).items
    resumen.value = await clientesApi.resumenCrm()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

async function abrir(id) {
  try {
    detalle.value = await clientesApi.detalleCampana(id)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

async function accion(fn, id) {
  error.value = ''
  try {
    await fn(id)
    await cargar()
    await abrir(id)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
}

function onCreada(c) {
  modal.value = null
  cargar()
  abrir(c.campaign_id)
}

onMounted(() => {
  if (puedeVer.value) cargar()
})
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Campañas de Cupones & Fidelización"
      subtitulo="Cupones automáticos por hito y campañas de reactivación con grupo de control y uplift medido al cierre."
    >
      <template #badge><SemanticChip tipo="ia">Club Marzú</SemanticChip></template>
      <template #acciones>
        <RouterLink
          to="/clientes/riesgo-fuga"
          class="inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50/70"
        >
          <Icon name="alert" :size="16" /> Riesgo de fuga
        </RouterLink>
        <Btn v-if="puedeCrear" variant="primary" @click="modal = 'nueva'">
          <Icon name="plus" :size="17" /> Nueva campaña de reactivación
        </Btn>
      </template>
    </PageHeader>

    <div
      v-if="!puedeVer"
      class="satin-card grid place-items-center rounded-2xl p-12 text-center shadow-card-subtle"
    >
      <div class="max-w-sm">
        <Icon name="shield" :size="28" class="mx-auto mb-3 text-brand-300" />
        <p class="text-[14px] font-bold text-slate-800">Sección exclusiva del Jefe de Marketing</p>
        <p class="mt-1 text-[12px] text-slate-500">
          Las campañas de reactivación y la medición de uplift las gestiona el equipo de
          Marketing / CRM (feature 002, US4–US5).
        </p>
        <RouterLink
          to="/clientes"
          class="mt-4 inline-flex items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
        >
          <Icon name="users" :size="15" /> Volver al directorio
        </RouterLink>
      </div>
    </div>

    <template v-else>
    <section class="mb-6 grid gap-4 sm:grid-cols-3">
      <KpiTile
        label="Tasa de redención de cupones"
        :valor="kpi.tasa != null && !Number.isNaN(kpi.tasa) ? (kpi.tasa * 100).toFixed(1) + '%' : null"
        variant="emerald"
        :microcopy="kpi.origen_tasa === 'hito' ? 'Cupones de cumpleaños y aniversario redimidos en caja' : 'Redención del programa de cupones (histórico)'"
        pie-label="Cupones redimidos"
        :pie-valor="kpi.redimidos.toLocaleString('es-CL')"
      />
      <KpiTile
        label="Campañas de reactivación"
        :valor="kpi.reactivaciones.toLocaleString('es-CL')"
        estado-tipo="ia"
        estado="A/B con control"
        microcopy="Cada una mide el uplift real (retorno tratado − control)"
      >
        <template #icono><Icon name="megaphone" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Cupones redimidos"
        :valor="kpi.redimidos.toLocaleString('es-CL')"
        microcopy="Clientes que canjearon al menos un cupón asignado"
      >
        <template #icono><Icon name="tag" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
      {{ error }}
    </p>

    <div class="grid items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]">
      <div class="space-y-6">
        <section class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
          <div class="border-b border-brand-200 bg-gradient-to-r from-brand-100/80 via-sage-100 to-brand-50 px-5 py-3">
            <h2 class="font-display text-[14px] font-bold text-brand-950">Cupones automáticos por hito</h2>
            <p class="text-[11px] text-slate-600">Se generan solos (job diario) — cumpleaños y aniversario de registro.</p>
          </div>
          <table class="w-full text-left text-[13px]">
            <thead>
              <tr class="bg-brand-50/70 text-[10px] font-bold uppercase tracking-wide text-slate-500">
                <th class="px-5 py-2">Tipo de hito</th>
                <th class="px-3 py-2 text-right">Enviados</th>
                <th class="px-3 py-2 text-right">Redimidos</th>
                <th class="px-5 py-2 text-right">Tasa</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-brand-100">
              <tr v-if="!hito.length">
                <td colspan="4" class="px-5 py-6 text-center text-[12px] text-slate-400">
                  Aún no se han enviado cupones por hito
                </td>
              </tr>
              <tr v-for="f in hito" :key="f.tipo_evento">
                <td class="px-5 py-2.5 font-medium text-slate-800">
                  {{ ETIQUETA_HITO[f.tipo_evento] || f.tipo_evento }}
                </td>
                <td class="px-3 py-2.5 text-right tabular-nums">{{ f.enviados }}</td>
                <td class="px-3 py-2.5 text-right tabular-nums">{{ f.redimidos }}</td>
                <td class="px-5 py-2.5 text-right font-bold tabular-nums text-brand-900">{{ pct(f.tasa) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <DataTable
          titulo="Campañas de reactivación"
          subtitulo="Clic en una campaña para ver miembros, enviarla, cerrarla y medir el uplift."
          :columns="columnas"
          :rows="campanas"
          row-key="campaign_id"
          :loading="cargando"
          densa
          :page="1"
          :size="campanas.length || 1"
          :total="campanas.length"
          empty-text="Sin campañas de reactivación — creá una desde el segmento de riesgo"
          @row-click="abrir($event.campaign_id)"
        >
          <template #cell:nombre="{ row }">
            <span class="font-semibold text-slate-800">{{ row.nombre || `Campaña #${row.campaign_id}` }}</span>
            <span class="ml-1 font-mono text-[10px] text-slate-400">#{{ row.campaign_id }}</span>
          </template>
          <template #cell:periodo="{ row }">
            <span class="text-[12px] text-slate-600">{{ fmt(row.start_date) }} → {{ fmt(row.end_date) }}</span>
          </template>
          <template #cell:estado="{ row }">
            <SemanticChip :tipo="detalle && detalle.campaign_id === row.campaign_id ? 'ia' : 'neutral'">
              reactivación
            </SemanticChip>
          </template>
          <template #cell:ir="{ row }">
            <Icon
              name="chevron"
              :size="15"
              class="-rotate-90"
              :class="detalle?.campaign_id === row.campaign_id ? 'text-amethyst-600' : 'text-slate-300'"
            />
          </template>
        </DataTable>
      </div>

      <!-- Panel de detalle -->
      <div
        v-if="detalle"
        class="satin-card rounded-2xl p-4 shadow-card-subtle"
      >
        <p class="font-display text-[14px] font-bold text-brand-950">
          {{ detalle.nombre || `Campaña #${detalle.campaign_id}` }}
        </p>
        <p class="mt-0.5 text-[11px] text-slate-500">
          {{ fmt(detalle.start_date) }} → {{ fmt(detalle.end_date) }} ·
          <span :class="detalle.enviada ? 'text-emerald-700 font-semibold' : 'text-slate-500'">
            {{ detalle.enviada ? 'enviada' : 'sin enviar' }}
          </span>
        </p>

        <div class="mt-3 grid grid-cols-2 gap-2">
          <div class="rounded-lg bg-brand-50/70 p-2 text-center">
            <p class="font-display text-lg font-extrabold text-brand-900">
              {{ detalle.miembros.filter((m) => m.grupo === 'tratado').length }}
            </p>
            <p class="text-[10px] font-semibold uppercase text-slate-500">Tratados</p>
          </div>
          <div class="rounded-lg bg-brand-50/70 p-2 text-center">
            <p class="font-display text-lg font-extrabold text-brand-900">
              {{ detalle.miembros.filter((m) => m.grupo === 'control').length }}
            </p>
            <p class="text-[10px] font-semibold uppercase text-slate-500">Control</p>
          </div>
        </div>

        <div v-if="detalle.resultado" class="mt-3 space-y-1 rounded-lg border border-emerald-600/20 bg-emerald-500/[0.06] p-3 text-[12px]">
          <p class="text-emerald-950">
            Retorno tratado <strong>{{ pct(detalle.resultado.tasa_retorno_tratado) }}</strong> ·
            control <strong>{{ pct(detalle.resultado.tasa_retorno_control) }}</strong>
          </p>
          <p class="font-display text-base font-extrabold text-emerald-800">
            Uplift {{ pct(detalle.resultado.uplift) }}
          </p>
          <p v-if="detalle.resultado.decision" class="text-slate-600">
            Decisión: <strong>{{ detalle.resultado.decision }}</strong>
          </p>
        </div>

        <div class="mt-3 flex flex-wrap gap-2">
          <button
            v-if="!detalle.enviada"
            type="button"
            class="rounded-lg bg-brand-800 px-3 py-1.5 text-[12px] font-bold text-white hover:bg-brand-700"
            @click="accion(clientesApi.enviarCampana, detalle.campaign_id)"
          >
            Enviar campaña
          </button>
          <button
            v-if="detalle.enviada && !detalle.resultado"
            type="button"
            class="rounded-lg bg-brand-800 px-3 py-1.5 text-[12px] font-bold text-white hover:bg-brand-700"
            @click="accion(clientesApi.cerrarCampana, detalle.campaign_id)"
          >
            Cerrar y medir uplift
          </button>
          <template v-if="detalle.resultado && !detalle.resultado.decision">
            <button
              type="button"
              class="rounded-lg border border-brand-300 px-3 py-1.5 text-[12px] font-semibold text-slate-700 hover:bg-brand-50"
              @click="accion((id) => clientesApi.decidirCampana(id, 'aprobada_escalar'), detalle.campaign_id)"
            >
              Aprobar y escalar
            </button>
            <button
              type="button"
              class="rounded-lg border border-rose-300 px-3 py-1.5 text-[12px] font-semibold text-crimson-ruby hover:bg-rose-50"
              @click="accion((id) => clientesApi.decidirCampana(id, 'descartada'), detalle.campaign_id)"
            >
              Descartar
            </button>
          </template>
        </div>
      </div>
      <div
        v-else
        class="satin-card grid place-items-center rounded-2xl p-10 text-center text-[13px] text-slate-500 shadow-card-subtle"
      >
        <div>
          <Icon name="megaphone" :size="24" class="mx-auto mb-2 text-brand-300" />
          Elegí una campaña para ver su detalle y accionarla.
        </div>
      </div>
    </div>

      <Modal
        v-if="modal === 'nueva'"
        size="lg"
        titulo="Nueva campaña de reactivación"
        @cerrar="modal = null"
      >
        <FormularioCampana @creada="onCreada" />
      </Modal>
    </template>
  </div>
</template>
