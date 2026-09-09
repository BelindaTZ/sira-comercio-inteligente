<script setup>
/**
 * US1 / FR-001 (feature 010) — el Jefe de TI define el modelo de datos del
 * warehouse (fact_venta + dimensiones) y activa/desactiva cada entidad. La carga
 * diaria sólo procesa entidades activas. Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { plataformaDatosApi } from '@/services/plataformaDatosApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const puedeEditar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('TI', 'modelo_datos_warehouse'),
)

const entidades = ref([])
const error = ref('')
const aviso = ref('')
const cargando = ref(false)
const modal = ref(false)
const guardando = ref(false)
const form = reactive({ nombreEntidad: '', tipo: 'dimension', tablaOrigenPostgres: '', descripcion: '' })

const kpi = computed(() => ({
  total: entidades.value.length,
  activas: entidades.value.filter((e) => e.activa).length,
  facts: entidades.value.filter((e) => e.tipo === 'fact').length,
  dims: entidades.value.filter((e) => e.tipo === 'dimension').length,
}))

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    entidades.value = await plataformaDatosApi.modelo()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function registrar() {
  guardando.value = true
  error.value = ''
  try {
    await plataformaDatosApi.registrarEntidad({ ...form })
    Object.assign(form, { nombreEntidad: '', tipo: 'dimension', tablaOrigenPostgres: '', descripcion: '' })
    modal.value = false
    aviso.value = 'Entidad registrada en el modelo.'
    await cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

async function alternarActiva(entidad) {
  error.value = ''
  try {
    await plataformaDatosApi.actualizarEntidad(entidad.entidad_id, { activa: !entidad.activa })
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1200px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Modelo de datos del warehouse"
      subtitulo="Entidades (fact y dimensiones) que la carga diaria puebla en el warehouse (FR-001). Una entidad inactiva queda definida pero su carga no arranca hasta activarla."
    >
      <template #badge>
        <SemanticChip tipo="ok">{{ kpi.activas }} de {{ kpi.total }} activas</SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeEditar" variant="primary" @click="modal = true">
          <Icon name="plus" :size="15" /> Registrar entidad
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
      <KpiTile label="Entidades en el modelo" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile label="Activas en la carga" :valor="kpi.activas.toLocaleString('es-EC')" estado-tipo="ok">
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Tablas de hechos" :valor="kpi.facts.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="database" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Dimensiones" :valor="kpi.dims.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[720px] text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-5 py-3">Entidad</th>
              <th class="px-4 py-3">Tipo</th>
              <th class="px-4 py-3">Tabla origen (PostgreSQL)</th>
              <th class="px-4 py-3 text-center">Estado</th>
              <th v-if="puedeEditar" class="px-4 py-3 text-right" />
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="cargando"><td :colspan="puedeEditar ? 5 : 4" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
            <tr v-else-if="!entidades.length"><td :colspan="puedeEditar ? 5 : 4" class="px-5 py-8 text-center text-slate-400">Todavía no hay ninguna entidad en el modelo.</td></tr>
            <tr v-for="ent in entidades" :key="ent.entidad_id" class="hover:bg-brand-50/70">
              <td class="px-5 py-2.5 font-semibold text-slate-800">{{ ent.nombre_entidad }}</td>
              <td class="px-4 py-2.5">
                <SemanticChip :tipo="ent.tipo === 'fact' ? 'ia' : 'neutral'">{{ ent.tipo }}</SemanticChip>
              </td>
              <td class="px-4 py-2.5 font-mono text-[12px] text-slate-600">{{ ent.tabla_origen_postgres }}</td>
              <td class="px-4 py-2.5 text-center">
                <SemanticChip :tipo="ent.activa ? 'ok' : 'fifo'">{{ ent.activa ? 'activa' : 'inactiva' }}</SemanticChip>
              </td>
              <td v-if="puedeEditar" class="px-4 py-2.5 text-right">
                <Btn variant="ghost" class="!px-2.5 !py-1 !text-[12px]" @click="alternarActiva(ent)">
                  {{ ent.activa ? 'Desactivar' : 'Activar' }}
                </Btn>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Modal v-if="modal" titulo="Registrar una entidad del modelo" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="registrar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Nombre de la entidad
          <input
            v-model="form.nombreEntidad"
            required
            placeholder="dim_producto"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Tipo
          <select
            v-model="form.tipo"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option value="fact">Tabla de hechos (fact)</option>
            <option value="dimension">Dimensión</option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Tabla origen (PostgreSQL)
          <input
            v-model="form.tablaOrigenPostgres"
            required
            placeholder="productos"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Descripción (opcional)
          <input
            v-model="form.descripcion"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
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
