<script setup>
/**
 * Protocolo de escalamiento ante fraude confirmado (feature 006, FR-012/FR-013).
 * Texto de referencia versionado (append-only) — NO un motor de flujo multi-paso
 * (spec 006, Assumptions). El Jefe de Finanzas publica una nueva versión; cualquier
 * Encargado de Tienda lo consulta. Enlaza a los incidentes de fraude abiertos que
 * esperan que se les aplique el protocolo.
 */
import { computed, onMounted, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { useSesion } from '@/stores/sesion'
import Icon from '@/shared/ui/Icon.vue'
import DocumentoVersionado from '../components/DocumentoVersionado.vue'

const sesion = useSesion()
const puedePublicar = computed(() => sesion.rol === 'Jefe_Finanzas')

const abiertos = ref(0)
onMounted(async () => {
  try {
    const inc = await cajaApi.incidentes('abierto')
    abiertos.value = inc.length
  } catch {
    /* informativo */
  }
})
</script>

<template>
  <DocumentoVersionado
    titulo="Protocolo de Escalamiento"
    subtitulo="Pasos a seguir ante un incidente de fraude confirmado. Documento de referencia versionado, consultable por cualquier Encargado de Tienda (FR-013)."
    badge="Documento de referencia"
    id-key="protocolo_id"
    publicar-label="Publicar nueva versión"
    :puede-publicar="puedePublicar"
    :cargar-vigente="cajaApi.protocolo"
    :cargar-historial="cajaApi.protocoloHistorial"
    :publicar="cajaApi.definirProtocolo"
  >
    <template #antes>
      <RouterLink
        v-if="abiertos > 0"
        to="/caja/incidentes"
        class="mb-6 flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-[13px] font-semibold text-amber-800 hover:bg-amber-100"
      >
        <span class="flex items-center gap-2">
          <Icon name="alert" :size="16" />
          {{ abiertos }} incidente(s) de fraude abierto(s) esperan que se aplique el protocolo
        </span>
        <span class="flex items-center gap-1 text-[12px]">Ir a incidentes <Icon name="chevron" :size="14" /></span>
      </RouterLink>
    </template>
  </DocumentoVersionado>
</template>
