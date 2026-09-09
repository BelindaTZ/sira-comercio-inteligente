<script setup>
/**
 * Raíz de la SPA. Las rutas autenticadas se montan dentro del shell de
 * navegación maestro (feature 013, Principio XII); las rutas públicas
 * (`/auth/*`, `meta.publica`) se renderizan sin shell.
 */
import { useRoute } from 'vue-router'
import AppShell from '@/shared/AppShell.vue'
import DialogHost from '@/shared/ui/DialogHost.vue'

const route = useRoute()
</script>

<template>
  <AppShell v-if="!route.meta.publica" />
  <RouterView v-else />
  <DialogHost />
</template>
