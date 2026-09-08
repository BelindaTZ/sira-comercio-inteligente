<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <main class="mx-auto max-w-lg px-6 py-24 text-center">
    <p class="font-display text-5xl font-bold text-primary-container">404</p>
    <p class="mt-3 text-on-surface-variant">Esta pantalla no existe.</p>
    <RouterLink
      to="/"
      class="mt-6 inline-block rounded-md bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary"
    >
      Volver al inicio
    </RouterLink>
  </main>
</template>
