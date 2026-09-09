<script setup>
/**
 * Catálogo de medios de pago (feature 007, FR-005 a FR-007). El Jefe de TI da de
 * alta un medio de pago (con constancia de aprobación) y da de baja uno existente
 * sin afectar ninguna venta ya registrada. Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, ref } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import { confirm } from '@/shared/ui/dialogs'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const puedeEditar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Ventas', 'medios_pago'),
)

const medios = ref([])
const nuevoNombre = ref('')
const error = ref('')
const aviso = ref('')
const cargando = ref(false)
const modal = ref(false)
const guardando = ref(false)

const kpi = computed(() => ({
  total: medios.value.length,
  activos: medios.value.filter((m) => m.aprobado).length,
  baja: medios.value.filter((m) => !m.aprobado).length,
}))

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    medios.value = await ventasApi.mediosPago()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function alta() {
  if (!nuevoNombre.value.trim()) return
  guardando.value = true
  error.value = ''
  try {
    await ventasApi.altaMedioPago(nuevoNombre.value.trim())
    modal.value = false
    nuevoNombre.value = ''
    aviso.value = 'Medio de pago dado de alta (queda aprobado y disponible en caja).'
    await cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

async function baja(m) {
  const ok = await confirm({
    title: `Dar de baja «${m.nombre}»`,
    message: 'Dejará de ofrecerse en caja. No afecta a ninguna venta ya registrada.',
    confirmText: 'Dar de baja',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await ventasApi.bajaMedioPago(m.medio_pago_id)
    aviso.value = `«${m.nombre}» dado de baja.`
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1000px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Medios de pago"
      subtitulo="Formas de pago ofrecidas en caja. El alta deja constancia de la aprobación; la baja retira el medio sin tocar ventas previas (FR-005 a FR-007)."
    >
      <template #badge>
        <SemanticChip tipo="ok">{{ kpi.activos }} activos</SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeEditar" variant="primary" @click="modal = true">
          <Icon name="plus" :size="15" /> Alta de medio de pago
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
      <KpiTile label="Medios en el catálogo" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile label="Activos en caja" :valor="kpi.activos.toLocaleString('es-EC')" estado-tipo="ok">
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Dados de baja" :valor="kpi.baja.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="x" :size="16" /></template>
      </KpiTile>
    </section>

    <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <table class="w-full text-left text-[13px]">
        <thead>
          <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
            <th class="px-5 py-3">Medio</th>
            <th class="px-4 py-3 text-center">Estado</th>
            <th class="px-4 py-3">Aprobado por</th>
            <th class="px-4 py-3">Fecha de baja</th>
            <th v-if="puedeEditar" class="px-4 py-3 text-right" />
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100/90 bg-white/80">
          <tr v-if="cargando"><td :colspan="puedeEditar ? 5 : 4" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
          <tr v-else-if="!medios.length"><td :colspan="puedeEditar ? 5 : 4" class="px-5 py-8 text-center text-slate-400">Sin medios de pago en el catálogo.</td></tr>
          <tr v-for="m in medios" :key="m.medio_pago_id" class="hover:bg-brand-50/70">
            <td class="px-5 py-3 font-semibold text-slate-800">{{ m.nombre }}</td>
            <td class="px-4 py-3 text-center">
              <SemanticChip :tipo="m.aprobado ? 'ok' : 'quiebre'">
                {{ m.aprobado ? 'Aprobado' : 'Dado de baja' }}
              </SemanticChip>
            </td>
            <td class="px-4 py-3 font-mono text-[12px] text-slate-500">
              {{ m.aprobado_por ? `#${m.aprobado_por}` : '—' }}
            </td>
            <td class="px-4 py-3 tabular-nums text-[12px] text-slate-500">
              {{ m.fecha_baja ? String(m.fecha_baja).slice(0, 10) : '—' }}
            </td>
            <td v-if="puedeEditar" class="px-4 py-3 text-right">
              <Btn v-if="m.aprobado" variant="danger" class="!px-2.5 !py-1 !text-[12px]" @click="baja(m)">
                Dar de baja
              </Btn>
              <span v-else class="text-[11px] text-slate-400">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-if="modal" titulo="Alta de medio de pago" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="alta">
        <p class="text-[12px] text-slate-600">
          El medio queda aprobado y disponible en caja de inmediato, con constancia de quién lo dio
          de alta.
        </p>
        <label class="block text-[12px] font-semibold text-slate-600">
          Nombre del medio de pago
          <input
            v-model="nuevoNombre"
            maxlength="30"
            required
            placeholder="p. ej. Transferencia, Vale de despensa…"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Dando de alta…' : 'Dar de alta' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
