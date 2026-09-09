<script setup>
/**
 * Documento de referencia versionado (append-only) — patrón compartido por el
 * Protocolo de Escalamiento (006, FR-012/013) y la Política de Seguridad de
 * Pagos (007, FR-012/014). Ambos son "texto de referencia versionado, no un
 * motor de flujo" (spec 006 Assumptions): versión vigente + historial + publicar
 * una nueva.
 */
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const props = defineProps({
  titulo: { type: String, required: true },
  subtitulo: { type: String, default: '' },
  badge: { type: String, default: '' },
  publicarLabel: { type: String, default: 'Publicar nueva versión' },
  puedePublicar: { type: Boolean, default: false },
  // fn() -> Promise<{ ..._id, texto, definido_por, fecha_creacion }>
  cargarVigente: { type: Function, required: true },
  // fn() -> Promise<Array<...>>
  cargarHistorial: { type: Function, required: true },
  // fn(texto) -> Promise
  publicar: { type: Function, required: true },
  idKey: { type: String, default: 'protocolo_id' },
})

const vigente = ref(null)
const historial = ref([])
const cargando = ref(false)
const error = ref('')
const modal = ref(false)
const borrador = ref('')
const guardando = ref(false)

const idDe = (v) => (v ? (v[props.idKey] ?? v.politica_id ?? v.protocolo_id) : null)

const fmtFecha = (s) => {
  if (!s) return '—'
  const d = new Date(s)
  return d.toLocaleString('es-CL', { dateStyle: 'medium', timeStyle: 'short' })
}
const hace = computed(() => {
  if (!vigente.value?.fecha_creacion) return null
  const min = Math.round((Date.now() - new Date(vigente.value.fecha_creacion)) / 60000)
  if (min < 60) return `hace ${Math.max(1, min)} min`
  const h = Math.round(min / 60)
  return h < 24 ? `hace ${h} h` : `hace ${Math.round(h / 24)} d`
})

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    vigente.value = await props.cargarVigente().catch((e) => {
      if (e.response?.status === 404 || e.status === 404) return null
      throw e
    })
    historial.value = await props.cargarHistorial().catch(() => [])
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    cargando.value = false
  }
}

function abrirEditor() {
  borrador.value = vigente.value?.texto || ''
  modal.value = true
}

async function guardar() {
  guardando.value = true
  error.value = ''
  try {
    await props.publicar(borrador.value.trim())
    modal.value = false
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1100px] px-6 py-8 lg:px-8">
    <PageHeader :titulo="titulo" :subtitulo="subtitulo">
      <template v-if="badge" #badge>
        <SemanticChip tipo="neutral">{{ badge }}</SemanticChip>
      </template>
      <template #acciones>
        <slot name="acciones" />
        <Btn v-if="puedePublicar" variant="primary" @click="abrirEditor">
          <Icon name="pencil" :size="16" /> {{ publicarLabel }}
        </Btn>
        <span
          v-else
          class="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600"
        >
          <Icon name="shield" :size="14" /> Solo lectura
        </span>
      </template>
    </PageHeader>

    <section class="mb-6 grid gap-4 sm:grid-cols-3">
      <KpiTile
        label="Versión vigente"
        :valor="vigente ? `v${idDe(vigente)}` : 'Sin definir'"
        variant="emerald"
        :microcopy="vigente ? `Publicada ${hace}` : 'Aún no se ha publicado ninguna versión'"
        pie-label="Última actualización"
        :pie-valor="vigente ? fmtFecha(vigente.fecha_creacion) : '—'"
      />
      <KpiTile
        label="Versiones publicadas"
        :valor="historial.length.toLocaleString('es-CL')"
        microcopy="Registro append-only — nada se sobrescribe"
      >
        <template #icono><Icon name="database" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Definida por"
        :valor="vigente ? `Empleado #${vigente.definido_por}` : '—'"
        microcopy="Responsable de la versión vigente"
      >
        <template #icono><Icon name="id" :size="16" /></template>
      </KpiTile>
    </section>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby">
      {{ error }}
    </p>

    <slot name="antes" />

    <div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
      <!-- Documento vigente -->
      <section class="satin-card rounded-2xl p-6 shadow-card-subtle">
        <div class="mb-3 flex items-center gap-2">
          <Icon name="academic" :size="18" class="text-brand-700" />
          <h2 class="font-display text-base font-bold text-brand-950">Texto vigente</h2>
        </div>
        <p v-if="cargando" class="text-[13px] text-slate-500">Cargando…</p>
        <p
          v-else-if="vigente"
          class="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700"
        >
          {{ vigente.texto }}
        </p>
        <div v-else class="rounded-xl border border-dashed border-brand-300 bg-brand-50/40 p-6 text-center">
          <Icon name="academic" :size="24" class="mx-auto mb-2 text-brand-300" />
          <p class="text-[13px] font-semibold text-slate-700">Todavía no hay un documento publicado</p>
          <p v-if="puedePublicar" class="mt-1 text-[11px] text-slate-500">
            Publicá la primera versión para que el equipo pueda consultarla.
          </p>
        </div>
      </section>

      <!-- Historial -->
      <section class="satin-card rounded-2xl p-5 shadow-card-subtle">
        <h3 class="mb-3 font-display text-[13px] font-bold text-brand-950">Historial de versiones</h3>
        <ol v-if="historial.length" class="space-y-3">
          <li
            v-for="(v, i) in historial"
            :key="idDe(v)"
            class="relative border-l-2 pl-3.5"
            :class="i === 0 ? 'border-brand-600' : 'border-brand-200'"
          >
            <span
              class="absolute -left-[5px] top-1 h-2 w-2 rounded-full"
              :class="i === 0 ? 'bg-brand-600' : 'bg-brand-300'"
            />
            <div class="flex items-center gap-1.5">
              <span class="text-[12px] font-bold text-slate-800">v{{ idDe(v) }}</span>
              <SemanticChip v-if="i === 0" tipo="ok">Vigente</SemanticChip>
            </div>
            <div class="text-[10px] text-slate-500">{{ fmtFecha(v.fecha_creacion) }}</div>
            <div class="text-[10px] text-slate-400">Empleado #{{ v.definido_por }}</div>
            <p class="mt-0.5 line-clamp-2 text-[11px] text-slate-500">{{ v.texto }}</p>
          </li>
        </ol>
        <p v-else class="text-[11px] text-slate-400">Sin versiones registradas.</p>
      </section>
    </div>

    <Modal v-if="modal" size="lg" :titulo="publicarLabel" @cerrar="modal = null">
      <p class="mb-3 text-[13px] text-slate-600">
        Se guarda como una versión nueva; la anterior queda en el historial (append-only).
      </p>
      <form class="space-y-3" @submit.prevent="guardar">
        <textarea
          v-model="borrador"
          rows="14"
          required
          class="block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-[13px] leading-relaxed text-slate-800 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          placeholder="Texto del documento…"
        />
        <div class="flex items-center justify-end gap-2.5">
          <button
            type="button"
            class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
            @click="modal = null"
          >
            Cancelar
          </button>
          <button
            type="submit"
            :disabled="guardando || !borrador.trim()"
            class="rounded-xl bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-40"
          >
            {{ guardando ? 'Publicando…' : 'Publicar versión' }}
          </button>
        </div>
      </form>
    </Modal>
  </div>
</template>
