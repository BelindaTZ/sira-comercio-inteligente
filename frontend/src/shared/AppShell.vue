<script setup>
/**
 * Shell de navegación maestro (feature 013, Principio XII).
 *
 * Barra horizontal superior fija en Abyssal Emerald (`#0a3632`) — no sidebar.
 * Categorías de primer nivel de `navegacion.js`, filtradas a los módulos que el
 * rol de la sesión puede ver. Una categoría con ≥4 ítems visibles abre un
 * mega-menú (panel blanco, columnas); con <4, una lista simple.
 *
 * Réplica del header de
 * `docs/diseno-ui/.../sira_inventario_y_alertas_fifo_header_verde_abisal/code.html`.
 */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { categoriasVisibles } from './navegacion'
import AppFooter from './ui/AppFooter.vue'
import UserMenu from './UserMenu.vue'
import logoUrl from '@/assets/branding/logo.svg'

const sesion = useSesion()
const route = useRoute()

const categorias = computed(() => categoriasVisibles(sesion))
const abierta = ref(null) // label de la categoría con el panel abierto
const catAbierta = computed(() => categorias.value.find((c) => c.label === abierta.value) ?? null)

function toggle(label) {
  abierta.value = abierta.value === label ? null : label
}
function cerrar() {
  abierta.value = null
}
function activa(cat) {
  return cat.items.some((it) => route.path === it.to || route.path.startsWith(it.to + '/'))
}
</script>

<template>
  <div class="flex min-h-screen flex-col overflow-x-hidden bg-background">
    <header
      class="relative sticky top-0 z-40 w-full border-b border-[#072623] bg-primary-container shadow-md"
      @mouseleave="cerrar"
    >
      <div
        class="mx-auto flex min-h-16 w-full max-w-[1720px] items-center justify-between gap-4 px-6 py-1.5 text-white lg:px-8"
      >
        <!-- Marca -->
        <RouterLink to="/" class="flex shrink-0 items-center gap-2.5" @click="cerrar">
          <img :src="logoUrl" alt="" class="h-9 w-9 rounded-xl bg-[#145952] p-1.5" />
          <span class="flex flex-col leading-none">
            <span class="font-display text-[18px] font-extrabold tracking-tight">SIRA</span>
            <span class="mt-0.5 text-[10px] font-bold tracking-[0.2em] text-primary-fixed-dim">
              RETAIL OS
            </span>
          </span>
        </RouterLink>

        <!-- Navegación de categorías -->
        <nav class="hidden min-w-0 flex-1 flex-wrap items-center gap-0.5 md:flex">
          <button
            v-for="cat in categorias"
            :key="cat.label"
            type="button"
            class="flex shrink-0 items-center gap-1 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-[13px] font-medium transition"
            :class="
              activa(cat) || abierta === cat.label
                ? 'bg-[#145952] text-primary-fixed ring-1 ring-primary-fixed/30'
                : 'text-white/80 hover:bg-white/15 hover:text-white'
            "
            @click="toggle(cat.label)"
          >
            {{ cat.label }}
            <svg
              v-if="cat.items.length > 1"
              class="h-3 w-3 opacity-60"
              viewBox="0 0 12 12"
              fill="none"
            >
              <path
                d="M2 4l4 4 4-4"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
              />
            </svg>
          </button>
        </nav>

        <!-- Menú de usuario -->
        <div class="shrink-0">
          <UserMenu />
        </div>
      </div>

      <!-- Panel desplegable (mega-menú >=4 en columnas; <4 lista simple) -->
      <div
        v-if="catAbierta"
        class="absolute inset-x-0 top-full hidden border-b border-black/10 bg-white text-on-surface shadow-tier-2 md:block"
        @mouseleave="cerrar"
      >
        <div class="mx-auto w-full max-w-[1720px] px-6 py-4 lg:px-8">
          <p
            class="mb-2 text-[11px] font-semibold uppercase tracking-[0.04em] text-on-surface-variant"
          >
            {{ catAbierta.label }}
          </p>
          <ul
            class="grid gap-1"
            :class="
              catAbierta.items.length >= 4 ? 'sm:grid-cols-2 lg:grid-cols-3' : 'sm:grid-cols-2'
            "
          >
            <li v-for="it in catAbierta.items" :key="it.to">
              <RouterLink
                :to="it.to"
                class="block rounded-lg px-3 py-2 text-[13px] font-medium text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                active-class="bg-surface-container text-primary-container"
                @click="cerrar"
              >
                {{ it.label }}
              </RouterLink>
            </li>
          </ul>
        </div>
      </div>

      <!-- Nav compacta (móvil) -->
      <nav class="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden">
        <RouterLink
          v-for="cat in categorias"
          :key="cat.label"
          :to="cat.items[0].to"
          class="whitespace-nowrap rounded-lg px-3 py-1 text-[12px] font-medium text-white/80"
          :class="activa(cat) ? 'bg-[#145952] text-primary-fixed' : ''"
        >
          {{ cat.label }}
        </RouterLink>
      </nav>
    </header>

    <!-- Cierra el panel al hacer clic fuera -->
    <div v-if="catAbierta" class="fixed inset-0 z-30" @click="cerrar" />

    <main class="flex-1">
      <RouterView />
    </main>

    <AppFooter />
  </div>
</template>
