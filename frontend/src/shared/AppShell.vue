<script setup>
/**
 * Shell de navegación maestro (feature 013, Principio XII).
 *
 * Barra horizontal superior fija en Abyssal Emerald (`#0a3632`) — no sidebar.
 * Categorías de primer nivel de `navegacion.js`, filtradas a los módulos que el
 * rol de la sesión puede ver. Una categoría con ≥4 sub-opciones abre un mega-menú
 * (panel blanco redondeado, columnas temáticas con ícono + título); con <4, una
 * lista simple.
 */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { categoriasVisibles } from './navegacion'
import AppFooter from './ui/AppFooter.vue'
import UserMenu from './UserMenu.vue'
import Icon from './ui/Icon.vue'
import logoUrl from '@/assets/branding/logo.svg'

const sesion = useSesion()
const route = useRoute()

const categorias = computed(() => categoriasVisibles(sesion))
const abierta = ref(null) // label de la categoría con el panel abierto
const catAbierta = computed(() => categorias.value.find((c) => c.label === abierta.value) ?? null)
// Columnas del mega-menú: los `grupos`, o un único grupo sintético si es lista plana.
const columnas = computed(() => {
  const c = catAbierta.value
  if (!c) return []
  return c.grupos ?? [{ titulo: c.label, icon: c.icon, items: c.items, plano: true }]
})

function toggle(label) {
  abierta.value = abierta.value === label ? null : label
}
function cerrar() {
  abierta.value = null
}
function activa(cat) {
  return cat.items.some((it) => esActivo(it.to))
}
function esActivo(to) {
  return route.path === to || route.path.startsWith(to + '/')
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
            class="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-[13px] font-medium transition"
            :class="
              activa(cat) || abierta === cat.label
                ? 'bg-[#145952] text-primary-fixed ring-1 ring-primary-fixed/30'
                : 'text-white/80 hover:bg-white/15 hover:text-white'
            "
            @click="toggle(cat.label)"
          >
            <Icon :name="cat.icon" :size="16" class="opacity-90" />
            {{ cat.label }}
            <Icon
              v-if="cat.items.length > 1"
              name="chevron"
              :size="12"
              class="opacity-50 transition"
              :class="abierta === cat.label ? '-rotate-180' : ''"
            />
          </button>
        </nav>

        <!-- Menú de usuario -->
        <div class="shrink-0">
          <UserMenu />
        </div>
      </div>

      <!-- Mega-menú: panel blanco redondeado, columnas temáticas -->
      <div
        v-if="catAbierta"
        class="absolute left-0 right-0 top-full z-50 hidden px-6 pt-1.5 md:block lg:px-8"
        @mouseleave="cerrar"
      >
        <div class="mx-auto w-full max-w-[1720px]">
          <div
            class="rounded-2xl border border-black/5 bg-white p-5 text-on-surface shadow-tier-2"
            :class="columnas.length === 1 ? 'inline-block min-w-[15rem]' : 'w-full'"
          >
            <div
              class="grid gap-x-10 gap-y-6"
              :class="{
                'sm:grid-cols-2': columnas.length === 2,
                'sm:grid-cols-2 lg:grid-cols-3': columnas.length >= 3,
              }"
            >
              <div v-for="col in columnas" :key="col.titulo">
                <p
                  v-if="!col.plano"
                  class="mb-3 flex items-center gap-2 text-[13px] font-bold text-on-surface"
                >
                  <Icon :name="col.icon" :size="16" class="text-primary-container" />
                  {{ col.titulo }}
                </p>
                <ul class="space-y-0.5">
                  <li v-for="it in col.items" :key="it.to">
                    <RouterLink
                      :to="it.to"
                      class="block rounded-lg px-3 py-2 text-[13px] font-medium transition"
                      :class="
                        esActivo(it.to)
                          ? 'bg-[#ede9fe] font-semibold text-[#6d28d9]'
                          : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                      "
                      @click="cerrar"
                    >
                      {{ it.label }}
                    </RouterLink>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Nav compacta (móvil) -->
      <nav class="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden">
        <RouterLink
          v-for="cat in categorias"
          :key="cat.label"
          :to="cat.items[0].to"
          class="flex items-center gap-1 whitespace-nowrap rounded-lg px-3 py-1 text-[12px] font-medium text-white/80"
          :class="activa(cat) ? 'bg-[#145952] text-primary-fixed' : ''"
        >
          <Icon :name="cat.icon" :size="13" />
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
