<script setup>
/**
 * Clima laboral semestral y su cruce con rotación (feature 011, US3 / FR-006,
 * FR-007, FR-010). El Jefe de RRHH registra el resultado promedio por tienda y
 * periodo (`AAAA-Sn`) y ve, junto a él, la tasa de rotación del mismo periodo
 * (calculada desde `empleados.fecha_baja`). Arquetipo "Dashboard/BI" del kit.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const puedeEditar = computed(() => !sesion.esGerente && sesion.rol === 'Jefe_RRHH')

const tiendas = ref([])
const consulta = reactive({ tiendaId: '', periodo: periodoActual() })
const cruce = ref(null)
const sinDatos = ref(false)
const error = ref('')
const aviso = ref('')
const modal = ref(false)
const guardando = ref(false)
const nuevo = reactive({ tiendaId: '', periodo: periodoActual(), resultado: '' })

function periodoActual() {
  const d = new Date()
  return `${d.getFullYear()}-S${d.getMonth() < 6 ? 1 : 2}`
}

const climaChip = computed(() => {
  const v = Number(cruce.value?.resultado_promedio)
  if (!cruce.value || cruce.value.resultado_promedio == null) return 'neutral'
  return v >= 7.5 ? 'ok' : v >= 6 ? 'fifo' : 'quiebre'
})

async function cargar() {
  tiendas.value = await rrhhApi.tiendas().catch(() => [])
}

async function verCruce() {
  error.value = ''
  cruce.value = null
  sinDatos.value = false
  if (!consulta.tiendaId || !consulta.periodo) return
  try {
    cruce.value = await rrhhApi.climaRotacion(Number(consulta.tiendaId), consulta.periodo.trim())
  } catch (e) {
    if (e.status === 404) sinDatos.value = true
    else error.value = e.message
  }
}

async function registrar() {
  if (!nuevo.tiendaId || !nuevo.periodo || nuevo.resultado === '') return
  guardando.value = true
  error.value = ''
  try {
    await rrhhApi.registrarClima({
      tiendaId: Number(nuevo.tiendaId),
      periodo: nuevo.periodo.trim(),
      resultadoPromedio: Number(nuevo.resultado),
    })
    modal.value = false
    nuevo.resultado = ''
    aviso.value = 'Resultado de clima registrado.'
    if (Number(consulta.tiendaId) === Number(nuevo.tiendaId) && consulta.periodo === nuevo.periodo) {
      await verCruce()
    }
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1000px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Clima laboral y rotación"
      subtitulo="Resultado de la encuesta de clima por tienda y semestre, junto a la tasa de rotación del mismo periodo (FR-006/FR-007/FR-010). Un periodo sin encuesta se informa como sin datos."
    >
      <template #acciones>
        <Btn v-if="puedeEditar" variant="primary" @click="modal = true">
          <Icon name="pencil" :size="15" /> Registrar resultado
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

    <section class="satin-card rounded-2xl p-5 shadow-card-subtle">
      <form class="flex flex-wrap items-end gap-3" @submit.prevent="verCruce">
        <label class="text-[12px] font-semibold text-slate-600">
          Tienda
          <select v-model="consulta.tiendaId" required class="mt-1 block rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
            <option value="" disabled>Elegí una tienda…</option>
            <option v-for="t in tiendas" :key="t.tienda_id" :value="t.tienda_id">{{ t.nombre }}</option>
          </select>
        </label>
        <label class="text-[12px] font-semibold text-slate-600">
          Periodo
          <input v-model="consulta.periodo" placeholder="2026-S2" pattern="\d{4}-S[12]" required class="mt-1 block w-28 rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
        </label>
        <Btn variant="ghost" type="submit"><Icon name="search" :size="15" /> Consultar</Btn>
      </form>

      <div v-if="cruce" class="mt-5 grid gap-4 sm:grid-cols-2">
        <KpiTile
          label="Clima laboral (0–10)"
          :valor="cruce.resultado_promedio != null ? Number(cruce.resultado_promedio).toFixed(2) : '—'"
          variant="emerald"
          :estado="cruce.resultado_promedio != null ? (Number(cruce.resultado_promedio) >= 7.5 ? 'sano' : 'a vigilar') : ''"
          :estado-tipo="climaChip"
        />
        <KpiTile
          label="Tasa de rotación del periodo"
          :valor="cruce.tasa_rotacion_pct == null ? 'sin datos' : `${cruce.tasa_rotacion_pct}%`"
          :estado-tipo="cruce.tasa_rotacion_pct == null ? 'neutral' : Number(cruce.tasa_rotacion_pct) > 10 ? 'quiebre' : 'ok'"
          microcopy="Bajas sobre la dotación media del semestre"
        >
          <template #icono><Icon name="users" :size="16" /></template>
        </KpiTile>
      </div>
      <p
        v-else-if="sinDatos"
        class="mt-4 flex items-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-[13px] text-brand-800"
      >
        <Icon name="alert" :size="16" class="text-brand-600" />
        No hay encuesta de clima registrada para esa tienda y periodo.
      </p>
    </section>

    <Modal v-if="modal" titulo="Registrar resultado de clima laboral" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="registrar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Tienda
          <select v-model="nuevo.tiendaId" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
            <option value="" disabled>Elegí una tienda…</option>
            <option v-for="t in tiendas" :key="t.tienda_id" :value="t.tienda_id">{{ t.nombre }}</option>
          </select>
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-[12px] font-semibold text-slate-600">
            Periodo (AAAA-Sn)
            <input v-model="nuevo.periodo" required placeholder="2026-S2" pattern="\d{4}-S[12]" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Resultado promedio (0–10)
            <input v-model="nuevo.resultado" type="number" step="0.01" min="0" max="10" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
        </div>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Registrando…' : 'Registrar' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
