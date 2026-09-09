<script setup>
/**
 * Plan de sucesión (feature 011, US4 / FR-008, FR-009). El Jefe de RRHH registra
 * candidatos internos para puestos críticos; el sistema señala los puestos
 * críticos sin ningún candidato con un badge de alerta. Arquetipo "Gestión".
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { rrhhApi } from '@/services/rrhhApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const puedeEditar = computed(() => !sesion.esGerente && sesion.rol === 'Jefe_RRHH')

const cobertura = ref([])
const empleados = ref([])
const error = ref('')
const aviso = ref('')
const cargando = ref(false)
const modal = ref(false)
const guardando = ref(false)
const nuevo = reactive({ puestoId: '', empleadoCandidatoId: '' })

const kpi = computed(() => ({
  criticos: cobertura.value.length,
  sinCobertura: cobertura.value.filter((p) => p.sin_cobertura).length,
  candidatos: cobertura.value.reduce((a, p) => a + p.candidatos.length, 0),
}))

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    ;[cobertura.value, empleados.value] = await Promise.all([
      rrhhApi.coberturaSucesion(),
      empleados.value.length
        ? Promise.resolve(empleados.value)
        : rrhhApi.listarEmpleados({ activo: true }),
    ])
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function registrar() {
  if (!nuevo.puestoId || !nuevo.empleadoCandidatoId) return
  guardando.value = true
  error.value = ''
  try {
    await rrhhApi.registrarCandidatoSucesion({
      puestoId: Number(nuevo.puestoId),
      empleadoCandidatoId: Number(nuevo.empleadoCandidatoId),
    })
    modal.value = false
    nuevo.puestoId = ''
    nuevo.empleadoCandidatoId = ''
    aviso.value = 'Candidato de sucesión registrado.'
    await cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1100px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Plan de sucesión"
      subtitulo="Candidatos internos para cada puesto crítico. Un puesto crítico sin candidato queda señalado como riesgo de continuidad (FR-008/FR-009)."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.sinCobertura > 0 ? 'quiebre' : 'ok'">
          {{ kpi.sinCobertura > 0 ? `${kpi.sinCobertura} puestos sin cobertura` : 'Todos los críticos con candidato' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeEditar && cobertura.length" variant="primary" @click="modal = true">
          <Icon name="plus" :size="15" /> Registrar candidato
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

    <section class="mb-6 grid gap-4 sm:grid-cols-3">
      <KpiTile label="Puestos críticos" :valor="kpi.criticos.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile
        label="Sin candidato"
        :valor="kpi.sinCobertura.toLocaleString('es-EC')"
        :estado-tipo="kpi.sinCobertura > 0 ? 'quiebre' : 'ok'"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Candidatos registrados" :valor="kpi.candidatos.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="users" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="!cargando && !cobertura.length" class="satin-card rounded-2xl p-8 text-center text-[13px] text-slate-500 shadow-card-subtle">
      No hay puestos marcados como críticos. Marcá alguno en «Puestos críticos» para armar su plan de sucesión.
    </p>

    <div v-else class="grid gap-3 sm:grid-cols-2">
      <div
        v-for="p in cobertura"
        :key="p.puesto_id"
        class="satin-card rounded-2xl p-4 shadow-card-subtle"
        :class="p.sin_cobertura ? 'border border-rose-200' : ''"
      >
        <div class="flex items-center justify-between">
          <h3 class="font-display text-[14px] font-bold text-brand-950">{{ p.nombre }}</h3>
          <SemanticChip :tipo="p.sin_cobertura ? 'quiebre' : 'ok'">
            {{ p.sin_cobertura ? 'sin cobertura' : `${p.candidatos.length} candidato${p.candidatos.length === 1 ? '' : 's'}` }}
          </SemanticChip>
        </div>
        <ul v-if="p.candidatos.length" class="mt-2 space-y-1">
          <li
            v-for="c in p.candidatos"
            :key="c.empleado_candidato_id"
            class="flex items-center justify-between text-[12px] text-slate-600"
          >
            <span class="font-semibold text-slate-800">{{ c.nombre }}</span>
            <span class="font-mono text-[11px] text-slate-400">{{ c.fecha }}</span>
          </li>
        </ul>
        <p v-else class="mt-2 text-[12px] text-rose-700">
          Ningún candidato interno identificado para este puesto.
        </p>
      </div>
    </div>

    <Modal v-if="modal" titulo="Registrar candidato de sucesión" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="registrar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Puesto crítico
          <select v-model="nuevo.puestoId" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
            <option value="" disabled>Elegí un puesto…</option>
            <option v-for="p in cobertura" :key="p.puesto_id" :value="p.puesto_id">{{ p.nombre }}</option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Empleado candidato
          <select v-model="nuevo.empleadoCandidatoId" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
            <option value="" disabled>Elegí un empleado…</option>
            <option v-for="e in empleados" :key="e.empleado_id" :value="e.empleado_id">
              {{ e.nombre }} — {{ e.puesto_nombre }}
            </option>
          </select>
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Registrando…' : 'Registrar candidato' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
