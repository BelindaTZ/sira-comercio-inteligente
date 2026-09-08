<script setup>
/**
 * Home de `/` — el portal del rol de la sesión (feature 013). No es un menú
 * suelto: cada rol aterriza en su propio panel. Si el home del rol es
 * directamente otra pantalla (Cajero → POS), redirige.
 */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { portalDe } from './portales'
import { categoriasVisibles } from './navegacion'
import PageHeader from './ui/PageHeader.vue'

const sesion = useSesion()
const router = useRouter()

const portal = computed(() => portalDe(sesion.rol))
const categorias = computed(() => categoriasVisibles(sesion))

onMounted(() => {
  if (portal.value.redirect) router.replace(portal.value.redirect)
})
</script>

<template>
  <div v-if="!portal.redirect" class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader :titulo="portal.titulo" :subtitulo="portal.bienvenida" />

    <section
      v-if="portal.destacados?.length"
      class="mb-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <RouterLink
        v-for="d in portal.destacados"
        :key="d.to"
        :to="d.to"
        class="group rounded-lg border-t-2 border-primary-container bg-surface-container-lowest p-5 shadow-tier-1 transition hover:shadow-tier-2"
      >
        <h2
          class="font-display text-base font-semibold text-on-surface group-hover:text-primary-container"
        >
          {{ d.label }}
        </h2>
        <p class="mt-1 text-sm text-on-surface-variant">{{ d.desc }}</p>
      </RouterLink>
    </section>

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
