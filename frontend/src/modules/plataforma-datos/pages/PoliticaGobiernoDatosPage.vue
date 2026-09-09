<script setup>
/**
 * US4 / FR-009, FR-010 (feature 010) — el Jefe de TI mantiene el texto vigente de
 * la política de gobierno de datos. Append-only: cada versión nueva no reemplaza
 * a la anterior, que queda en el historial (mismo criterio que 006/007).
 */
import { computed, onMounted, ref } from 'vue'
import { plataformaDatosApi } from '@/services/plataformaDatosApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const puedeEditar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('TI', 'politica_gobierno_datos'),
)

const vigente = ref(null)
const historial = ref([])
const nuevoTexto = ref('')
const error = ref('')
const aviso = ref('')
const sinPolitica = ref(false)
const modal = ref(false)
const guardando = ref(false)

const fecha = (s) => (s ? new Date(s).toLocaleString('es-EC') : '—')
const anteriores = computed(() => historial.value.slice(1))

async function cargar() {
  error.value = ''
  sinPolitica.value = false
  try {
    vigente.value = await plataformaDatosApi.politicaVigente()
  } catch (e) {
    if (e.status === 404) sinPolitica.value = true
    else error.value = e.message
  }
  try {
    historial.value = await plataformaDatosApi.politicaHistorial()
  } catch (e) {
    error.value = e.message
  }
}

async function registrar() {
  if (!nuevoTexto.value.trim()) return
  guardando.value = true
  error.value = ''
  try {
    await plataformaDatosApi.registrarPolitica(nuevoTexto.value.trim())
    nuevoTexto.value = ''
    modal.value = false
    aviso.value = 'Nueva versión de la política registrada.'
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
  <div class="mx-auto max-w-[1000px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Política de gobierno de datos"
      subtitulo="Calidad, trazabilidad y acceso a los datos del sistema (FR-009/FR-010). Cada versión se conserva; la vigente es siempre la más reciente."
    >
      <template #badge>
        <SemanticChip :tipo="sinPolitica ? 'fifo' : 'ok'">
          {{ sinPolitica ? 'Sin política registrada' : `Vigente desde ${fecha(vigente?.fecha_creacion)}` }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeEditar" variant="primary" @click="modal = true">
          <Icon name="pencil" :size="15" /> Registrar nueva versión
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
      <h2 class="mb-2 font-display text-[14px] font-bold text-brand-950">Versión vigente</h2>
      <p v-if="sinPolitica" class="text-[13px] text-slate-500">
        Todavía no se registró ninguna política de gobierno de datos.
      </p>
      <template v-else-if="vigente">
        <p class="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700">{{ vigente.texto }}</p>
        <p class="mt-4 border-t border-brand-100 pt-2 text-[11px] text-slate-400">
          Registrada el {{ fecha(vigente.fecha_creacion) }}
        </p>
      </template>
    </section>

    <section v-if="anteriores.length" class="mt-6">
      <h2 class="mb-2 font-display text-[14px] font-bold text-brand-950">Versiones anteriores</h2>
      <ol class="space-y-2">
        <li
          v-for="p in anteriores"
          :key="p.politica_id"
          class="satin-card rounded-xl p-3 shadow-card-subtle"
        >
          <p class="text-[11px] font-semibold text-slate-500">{{ fecha(p.fecha_creacion) }}</p>
          <p class="mt-1 line-clamp-3 whitespace-pre-wrap text-[12px] text-slate-600">{{ p.texto }}</p>
        </li>
      </ol>
    </section>

    <Modal v-if="modal" titulo="Registrar nueva versión de la política" size="lg" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="registrar">
        <p class="text-[12px] text-slate-600">
          El texto completo reemplaza a la versión vigente; la anterior queda archivada.
        </p>
        <textarea
          v-model="nuevoTexto"
          required
          rows="12"
          placeholder="Texto completo de la política de gobierno de datos…"
          class="block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
        />
        <div class="flex justify-end gap-2.5">
          <Btn variant="ghost" type="button" @click="modal = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Guardando…' : 'Guardar versión' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
