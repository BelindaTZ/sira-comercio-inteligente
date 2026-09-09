<script setup>
/**
 * Shell de navegación maestro (feature 013, Principio XII).
 *
 * Réplica fiel del header de
 * `docs/diseno-ui/.../sira_punto_de_venta_y_registro_r_pido_header_verde_abisal/code.html`:
 * barra superior fija `#072623`, nav dentro de un pill oscuro embebido, tab activo
 * en gradiente amatista (`secondary → secondary-subtle`).
 *
 * Categorías de `navegacion.js` filtradas a los módulos que el rol puede ver. Una
 * categoría con ≥4 sub-opciones abre un mega-menú (panel blanco redondeado,
 * columnas temáticas con ícono + título); con <4, lista simple (Principio XII).
 */
import { computed, nextTick, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { categoriasVisibles } from './navegacion'
import AppFooter from './ui/AppFooter.vue'
import ContextoOperativo from './ui/ContextoOperativo.vue'
import UserMenu from './UserMenu.vue'
import Icon from './ui/Icon.vue'
import logoUrl from '@/assets/branding/logo.svg'

const sesion = useSesion()
const route = useRoute()

const categorias = computed(() => categoriasVisibles(sesion))
const abierta = ref(null)
const catAbierta = computed(() => categorias.value.find((c) => c.label === abierta.value) ?? null)
const columnas = computed(() => {
  const c = catAbierta.value
  if (!c) return []
  return c.grupos ?? [{ titulo: c.label, icon: c.icon, items: c.items, plano: true }]
})

const navWrap = ref(null)
const panel = ref(null)
const panelLeft = ref(0)

function toggle(label, ev) {
  if (abierta.value === label) {
    abierta.value = null
    return
  }
  abierta.value = label
  const btn = ev?.currentTarget
  nextTick(() => {
    if (!btn || !navWrap.value) return
    const wrapBox = navWrap.value.getBoundingClientRect()
    const btnBox = btn.getBoundingClientRect()
    const panelW = panel.value?.offsetWidth ?? 420
    // alineado a la izquierda del botón, sin desbordar la ventana
    const left = btnBox.left - wrapBox.left
    const maxLeft = window.innerWidth - 24 - panelW - wrapBox.left
    panelLeft.value = Math.max(0, Math.min(left, Math.max(0, maxLeft)))
  })
}
function cerrar() {
  abierta.value = null
}
function esActivo(to) {
  return route.path === to || route.path.startsWith(to + '/')
}
function activa(cat) {
  return cat.items.some((it) => esActivo(it.to))
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <header
      class="relative sticky top-0 z-40 w-full border-b border-shell-line bg-shell-bar text-white shadow-lg shadow-black/20"
      @mouseleave="cerrar"
    >
      <div
        class="mx-auto flex min-h-16 w-full max-w-[1840px] items-center justify-between gap-3 px-4 py-1.5 lg:px-6"
      >
        <!-- Marca -->
        <RouterLink to="/" class="flex shrink-0 items-center gap-2.5" @click="cerrar">
          <span
            class="grid h-9 w-9 place-items-center rounded-2xl border border-emerald-400/30 bg-gradient-to-br from-[#10534c] to-[#041a18] shadow-sm"
          >
            <img :src="logoUrl" alt="" class="h-5 w-5" />
          </span>
          <span class="flex flex-col leading-none">
            <span class="flex items-center gap-1.5">
              <span class="font-display text-xl font-extrabold tracking-tight text-white"
                >SIRA</span
              >
              <span
                class="rounded-md border border-secondary/40 bg-secondary/30 px-2 py-0.5 font-mono text-[10px] font-bold text-secondary-fixed"
              >
                RETAIL OS
              </span>
            </span>
            <span class="mt-0.5 text-[10px] font-medium text-emerald-200/70">
              Retail Omnichannel Engine
            </span>
          </span>
        </RouterLink>

        <!-- Navegación + mega-menú -->
        <div ref="navWrap" class="relative hidden min-w-0 md:block">
          <nav
            class="flex flex-wrap items-center gap-1 rounded-2xl border border-shell-line bg-shell-inset p-1 shadow-inner"
          >
            <button
              v-for="cat in categorias"
              :key="cat.label"
              type="button"
              class="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xl px-3 py-1.5 text-[13px] font-medium transition-all"
              :class="
                activa(cat) || abierta === cat.label
                  ? 'bg-gradient-to-r from-secondary to-secondary-subtle font-semibold text-white shadow-md shadow-secondary/30'
                  : 'text-emerald-200/80 hover:bg-white/10 hover:text-white'
              "
              @click="toggle(cat.label, $event)"
            >
              <Icon :name="cat.icon" :size="16" />
              {{ cat.label }}
              <Icon
                v-if="cat.items.length > 1"
                name="chevron"
                :size="12"
                class="opacity-60 transition-transform"
                :class="abierta === cat.label ? '-rotate-180' : ''"
              />
            </button>
          </nav>

          <!-- Panel: anclado a la categoría abierta, del ancho de su contenido -->
          <div
            v-if="catAbierta"
            ref="panel"
            class="absolute top-full z-50 mt-2 w-max max-w-[calc(100vw-3rem)] rounded-2xl border border-brand-200 bg-white p-5 shadow-card-hover"
            :style="{ left: panelLeft + 'px' }"
          >
            <div
              class="grid gap-x-12 gap-y-6"
              :class="{
                'grid-cols-2': columnas.length === 2,
                'grid-cols-2 lg:grid-cols-3': columnas.length >= 3,
              }"
            >
              <div v-for="col in columnas" :key="col.titulo" class="min-w-[11rem]">
                <p
                  v-if="!col.plano"
                  class="mb-3 flex items-center gap-2 text-[13px] font-bold text-brand-950"
                >
                  <Icon :name="col.icon" :size="16" class="text-brand-700" />
                  {{ col.titulo }}
                </p>
                <ul class="space-y-0.5">
                  <li v-for="it in col.items" :key="it.to">
                    <RouterLink
                      :to="it.to"
                      class="block whitespace-nowrap rounded-lg px-3 py-2 text-[13px] font-medium transition"
                      :class="
                        esActivo(it.to)
                          ? 'bg-amethyst-100 font-semibold text-amethyst-800'
                          : 'text-slate-600 hover:bg-brand-50 hover:text-slate-900'
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

        <!-- Menú de usuario -->
        <div class="shrink-0">
          <UserMenu />
        </div>
      </div>

      <!-- Nav compacta (móvil) -->
      <nav class="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden">
        <RouterLink
          v-for="cat in categorias"
          :key="cat.label"
          :to="cat.items[0].to"
          class="flex items-center gap-1 whitespace-nowrap rounded-xl px-3 py-1 text-[12px] font-medium text-emerald-200/80"
          :class="
            activa(cat) ? 'bg-gradient-to-r from-secondary to-secondary-subtle text-white' : ''
          "
        >
          <Icon :name="cat.icon" :size="13" />
          {{ cat.label }}
        </RouterLink>
      </nav>
    </header>

    <ContextoOperativo />

    <!-- Cierra el panel al hacer clic fuera -->
    <div v-if="catAbierta" class="fixed inset-0 z-30" @click="cerrar" />

    <main class="ambient-canvas-bg flex-1">
      <RouterView />
    </main>

    <AppFooter />
  </div>
</template>
