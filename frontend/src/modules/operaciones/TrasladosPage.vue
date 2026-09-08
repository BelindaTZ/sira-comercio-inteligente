<script setup>
/**
 * Traslados de Stock entre Tiendas (feature 012, OT-2.5). Reúne las tres historias
 * de usuario: visibilidad de stock por sucursal (US1), solicitud + resolución
 * (US2), recepción + listado semanal (US3). Toda regla vive en el backend.
 */
import DisponibilidadSucursales from './components/DisponibilidadSucursales.vue'
import SolicitarTraslado from './components/SolicitarTraslado.vue'
import AprobarTraslados from './components/AprobarTraslados.vue'
import ConfirmarRecepcion from './components/ConfirmarRecepcion.vue'
</script>

<template>
  <main class="mx-auto max-w-4xl space-y-8 px-6 py-8">
    <h1 class="text-2xl font-bold text-primary-container">Traslados de stock entre tiendas</h1>
    <DisponibilidadSucursales />
    <SolicitarTraslado />
    <AprobarTraslados />
    <ConfirmarRecepcion />
  </main>
</template>
