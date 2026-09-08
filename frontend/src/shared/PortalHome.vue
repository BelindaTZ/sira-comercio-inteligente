<script setup>
/**
 * Fallback de `/` — sólo se ve si el rol no tiene un home definido en
 * `portales.js` (el guard del router ya redirige a los que sí lo tienen).
 * Muestra los accesos que el rol puede abrir, para no dejarlo sin salida.
 */
import { computed } from 'vue'
import { useSesion } from '@/stores/sesion'
import { categoriasVisibles } from './navegacion'
import PageHeader from './ui/PageHeader.vue'

const sesion = useSesion()
const categorias = computed(() => categoriasVisibles(sesion))
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      :titulo="`Hola, ${sesion.nombre || 'usuario'}`"
      :subtitulo="`${sesion.rol || ''} — elegí una sección para empezar`"
    />
    <section v-for="cat in categorias" :key="cat.label" class="mb-7">
      <h3
        class="mb-2 text-[11px] font-semibold uppercase tracking-[0.04em] text-on-surface-variant"
      >
        {{ cat.label }}
      </h3>
      <ul class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <li v-for="it in cat.items" :key="it.to">
          <RouterLink
            :to="it.to"
            class="block rounded-md border border-outline-variant bg-surface-container-lowest px-3.5 py-2.5 text-[13px] font-medium text-on-surface-variant transition hover:border-primary-container hover:text-on-surface"
          >
            {{ it.label }}
          </RouterLink>
        </li>
      </ul>
    </section>
  </div>
</template>
