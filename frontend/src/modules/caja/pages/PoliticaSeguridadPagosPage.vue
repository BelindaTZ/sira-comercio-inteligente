<script setup>
/**
 * Política de seguridad de pagos (feature 007, FR-012 a FR-014). Texto de
 * referencia versionado (append-only), mismo criterio que el protocolo de
 * escalamiento de 006. El Jefe de TI publica; Jefe de Finanzas y Encargado de
 * Tienda consultan. Las versiones anteriores quedan en el historial para saber
 * cuál regía cuando se abrió un incidente en curso (FR-014).
 */
import { computed } from 'vue'
import { cajaApi } from '@/services/cajaApi'
import { useSesion } from '@/stores/sesion'
import DocumentoVersionado from '../components/DocumentoVersionado.vue'

const sesion = useSesion()
const puedePublicar = computed(() => sesion.rol === 'Jefe_TI')
</script>

<template>
  <DocumentoVersionado
    titulo="Política de Seguridad de Pagos"
    subtitulo="Lineamientos de seguridad de los medios de pago de la red. Documento de referencia versionado; la edición es del Jefe de TI (FR-012)."
    badge="Documento de referencia"
    id-key="politica_id"
    publicar-label="Publicar nueva versión"
    :puede-publicar="puedePublicar"
    :cargar-vigente="cajaApi.politicaSeguridad"
    :cargar-historial="cajaApi.politicaSeguridadHistorial"
    :publicar="cajaApi.definirPoliticaSeguridad"
  />
</template>
