<script setup>
/**
 * Incidentes de seguridad de pago (feature 007, FR-008 a FR-011) — entidad
 * distinta e independiente del incidente de fraude interno de 006. El Jefe de TI
 * registra y avanza el incidente (abierto → en investigación → cerrado); el Jefe
 * de Finanzas consulta el conteo del periodo. Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const puedeGestionar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Finanzas', 'incidente_seguridad_pago'),
)

const SIGUIENTE = { abierto: 'en_investigacion', en_investigacion: 'cerrado' }
const ESTADO = {
  abierto: { chip: 'quiebre', txt: 'Abierto' },
  en_investigacion: { chip: 'fifo', txt: 'En investigación' },
  cerrado: { chip: 'ok', txt: 'Cerrado' },
}
const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'abierto', label: 'Abiertos' },
  { value: 'en_investigacion', label: 'En investigación' },
  { value: 'cerrado', label: 'Cerrados' },
]

const incidentes = ref([])
const datafonos = ref([])
const filtroEstado = ref('')
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const modal = ref(false)
const guardando = ref(false)
const nuevo = reactive({ datafonoId: '', descripcion: '' })

const periodo = reactive({ desde: '', hasta: '' })
const conteo = ref(null)

const kpi = computed(() => {
  const por = (e) => incidentes.value.filter((i) => i.estado === e).length
  return {
    total: incidentes.value.length,
    abierto: por('abierto'),
    en_investigacion: por('en_investigacion'),
    cerrado: por('cerrado'),
  }
})

const datafonoLabel = (id) => {
  if (id == null) return null
  const d = datafonos.value.find((x) => x.datafono_id === id)
  return d ? `Datáfono #${id}${d.modelo ? ` · ${d.modelo}` : ''} · caja ${d.caja_id}` : `Datáfono #${id}`
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    incidentes.value = await cajaApi.incidentesSeguridad(filtroEstado.value || undefined)
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function registrar() {
  if (!nuevo.descripcion.trim()) return
  guardando.value = true
  error.value = ''
  try {
    await cajaApi.registrarIncidenteSeguridad({
      datafonoId: nuevo.datafonoId ? Number(nuevo.datafonoId) : null,
      descripcion: nuevo.descripcion.trim(),
    })
    modal.value = false
    nuevo.datafonoId = ''
    nuevo.descripcion = ''
    aviso.value = 'Incidente registrado.'
    await cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

async function avanzar(inc) {
  error.value = ''
  try {
    await cajaApi.transicionarIncidenteSeguridad(inc.incidente_seguridad_id, SIGUIENTE[inc.estado])
    aviso.value = `Incidente #${inc.incidente_seguridad_id} → ${ESTADO[SIGUIENTE[inc.estado]].txt}.`
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function consultarConteo() {
  error.value = ''
  try {
    conteo.value = await cajaApi.conteoIncidentesSeguridad({
      desde: periodo.desde || undefined,
      hasta: periodo.hasta || undefined,
    })
  } catch (e) {
    error.value = e.message
  }
}

onMounted(async () => {
  if (puedeGestionar.value) datafonos.value = await cajaApi.datafonos().catch(() => [])
  await cargar()
})
</script>

<template>
  <div class="mx-auto max-w-[1200px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Incidentes de seguridad de pago"
      subtitulo="Sospechas de manipulación de datáfonos o clonación de tarjetas. El Jefe de TI registra y hace avanzar el caso (abierto → en investigación → cerrado); Finanzas consulta el conteo del periodo (FR-008 a FR-011)."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.abierto > 0 ? 'quiebre' : 'ok'">
          {{ kpi.abierto > 0 ? `${kpi.abierto} abiertos` : 'Sin abiertos' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeGestionar" variant="primary" @click="modal = true">
          <Icon name="plus" :size="15" /> Registrar incidente
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
      <KpiTile label="Incidentes en la vista" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile label="Abiertos" :valor="kpi.abierto.toLocaleString('es-EC')" :estado-tipo="kpi.abierto > 0 ? 'quiebre' : 'ok'">
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile label="En investigación" :valor="kpi.en_investigacion.toLocaleString('es-EC')" estado-tipo="fifo">
        <template #icono><Icon name="search" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Cerrados" :valor="kpi.cerrado.toLocaleString('es-EC')" estado-tipo="ok">
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
    </section>

    <!-- Conteo del periodo -->
    <section class="satin-card mb-6 rounded-2xl p-5 shadow-card-subtle">
      <h2 class="mb-3 font-display text-[14px] font-bold text-brand-950">Conteo del periodo</h2>
      <form class="flex flex-wrap items-end gap-3" @submit.prevent="consultarConteo">
        <label class="text-[12px] font-semibold text-slate-600">
          Desde
          <input v-model="periodo.desde" type="date" class="mt-1 block rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
        </label>
        <label class="text-[12px] font-semibold text-slate-600">
          Hasta
          <input v-model="periodo.hasta" type="date" class="mt-1 block rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
        </label>
        <Btn variant="ghost" type="submit">Consultar</Btn>
        <p v-if="conteo" class="text-[13px] font-semibold text-brand-900">
          {{ conteo.total }} incidente(s) en el periodo
        </p>
      </form>
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
            <th class="px-5 py-3">Incidente</th>
            <th class="px-4 py-3">Datáfono</th>
            <th class="px-4 py-3">Descripción</th>
            <th class="px-4 py-3">Registrado</th>
            <th class="px-4 py-3 text-center">Estado</th>
            <th v-if="puedeGestionar" class="px-4 py-3 text-right" />
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100/90 bg-white/80">
          <tr v-if="cargando"><td :colspan="puedeGestionar ? 6 : 5" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
          <tr v-else-if="!incidentes.length"><td :colspan="puedeGestionar ? 6 : 5" class="px-5 py-8 text-center text-slate-400">Sin incidentes para este filtro.</td></tr>
          <tr v-for="inc in incidentes" :key="inc.incidente_seguridad_id" class="hover:bg-brand-50/70">
            <td class="px-5 py-3 font-mono text-[12px] font-semibold text-slate-800">
              #{{ inc.incidente_seguridad_id }}
            </td>
            <td class="px-4 py-3 text-slate-600">{{ datafonoLabel(inc.datafono_id) || '—' }}</td>
            <td class="px-4 py-3 text-slate-700">{{ inc.descripcion }}</td>
            <td class="px-4 py-3 tabular-nums text-[12px] text-slate-500">
              {{ String(inc.fecha_hora).slice(0, 16).replace('T', ' ') }}
            </td>
            <td class="px-4 py-3 text-center">
              <SemanticChip :tipo="ESTADO[inc.estado]?.chip || 'neutral'">
                {{ ESTADO[inc.estado]?.txt || inc.estado }}
              </SemanticChip>
            </td>
            <td v-if="puedeGestionar" class="px-4 py-3 text-right">
              <Btn
                v-if="SIGUIENTE[inc.estado]"
                variant="ghost"
                class="!px-2.5 !py-1 !text-[12px]"
                @click="avanzar(inc)"
              >
                Avanzar a «{{ ESTADO[SIGUIENTE[inc.estado]].txt }}»
              </Btn>
              <span v-else class="text-[11px] text-slate-400">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-if="modal" titulo="Registrar incidente de seguridad" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="registrar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Datáfono involucrado (opcional)
          <select
            v-model="nuevo.datafonoId"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option value="">Sin datáfono específico</option>
            <option v-for="d in datafonos" :key="d.datafono_id" :value="d.datafono_id">
              Datáfono #{{ d.datafono_id }}<template v-if="d.modelo"> · {{ d.modelo }}</template> · caja {{ d.caja_id }}
            </option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Descripción
          <textarea
            v-model="nuevo.descripcion"
            rows="3"
            required
            maxlength="500"
            placeholder="Qué se observó, cuándo y en qué caja."
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando || !nuevo.descripcion.trim()">
            {{ guardando ? 'Registrando…' : 'Registrar' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
