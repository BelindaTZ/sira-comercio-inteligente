<script setup>
/**
 * Menú de usuario del shell (feature 013): avatar con iniciales + nombre + rol
 * pequeño; al hacer clic despliega Datos de mi cuenta / Cambiar contraseña /
 * Cerrar sesión. Réplica del bloque de contexto derecho de `docs/diseno-ui/`.
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { authApi } from '@/services/authApi'
import Modal from './ui/Modal.vue'
import Icon from './ui/Icon.vue'

const sesion = useSesion()
const router = useRouter()

const abierto = ref(false)
const modal = ref(null) // 'cuenta' | 'password' | 'pin' | null

// --- PIN de autorización (feature 018) ---
const pin = ref(null)
const pinRevelado = ref(false)
const pinCargando = ref(false)
async function abrirPin() {
  modal.value = 'pin'
  abierto.value = false
  pinRevelado.value = false
  if (pin.value === null) {
    pinCargando.value = true
    try {
      const r = await authApi.miPin()
      pin.value = r
    } finally {
      pinCargando.value = false
    }
  }
}

const iniciales = computed(() => {
  const n = (sesion.nombre || sesion.username || 'U').trim()
  const partes = n.split(/\s+/)
  return ((partes[0]?.[0] ?? '') + (partes[1]?.[0] ?? '')).toUpperCase() || 'U'
})

function salir() {
  sesion.logout()
  router.push({ name: 'auth-login' })
}

// --- cambiar contraseña ---
const pw = ref({ actual: '', nueva: '', repetir: '' })
const pwError = ref('')
const pwOk = ref(false)
const pwEnviando = ref(false)

async function cambiarPassword() {
  pwError.value = ''
  pwOk.value = false
  if (pw.value.nueva.length < 8) {
    pwError.value = 'La nueva contraseña debe tener al menos 8 caracteres'
    return
  }
  if (pw.value.nueva !== pw.value.repetir) {
    pwError.value = 'Las contraseñas nuevas no coinciden'
    return
  }
  pwEnviando.value = true
  try {
    await authApi.cambiarMiPassword(pw.value.actual, pw.value.nueva)
    pwOk.value = true
    pw.value = { actual: '', nueva: '', repetir: '' }
  } catch (e) {
    pwError.value = e.message
  } finally {
    pwEnviando.value = false
  }
}

function cerrarModal() {
  modal.value = null
  pwError.value = ''
  pwOk.value = false
  pw.value = { actual: '', nueva: '', repetir: '' }
  pinRevelado.value = false
}
</script>

<template>
  <div class="relative">
    <button
      type="button"
      class="flex items-center gap-2.5 border-l border-[#164c45] py-1 pl-3 pr-1 transition"
      @click="abierto = !abierto"
    >
      <span
        class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-[#10534c] to-[#041a18] text-[12px] font-bold text-emerald-50 ring-2 ring-emerald-400/40"
      >
        {{ iniciales }}
      </span>
      <span class="hidden text-left leading-tight lg:block">
        <span class="flex items-center gap-1.5">
          <span class="text-xs font-bold text-emerald-50">{{
            sesion.nombre || sesion.username
          }}</span>
        </span>
        <span
          class="mt-0.5 inline-block rounded border border-emerald-400/20 bg-emerald-500/20 px-1.5 font-mono text-[9px] font-bold text-emerald-300"
        >
          {{ sesion.rol }}
        </span>
      </span>
      <Icon name="chevron" :size="14" class="text-emerald-300/60" />
    </button>

    <div v-if="abierto" class="fixed inset-0 z-40" @click="abierto = false" />
    <div
      v-if="abierto"
      class="absolute right-0 z-50 mt-2 w-60 overflow-hidden rounded-xl border border-black/10 bg-white text-on-surface shadow-tier-2"
    >
      <div class="border-b border-outline-variant px-4 py-3">
        <p class="text-sm font-semibold">{{ sesion.nombre || sesion.username }}</p>
        <p class="text-xs text-on-surface-variant">{{ sesion.rol }}</p>
      </div>
      <button
        type="button"
        class="block w-full px-4 py-2.5 text-left text-[13px] text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
        @click="((modal = 'cuenta'), (abierto = false))"
      >
        Datos de mi cuenta
      </button>
      <button
        type="button"
        class="block w-full px-4 py-2.5 text-left text-[13px] text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
        @click="((modal = 'password'), (abierto = false))"
      >
        Cambiar contraseña
      </button>
      <button
        type="button"
        class="block w-full px-4 py-2.5 text-left text-[13px] text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
        @click="abrirPin"
      >
        Mi PIN de autorización
      </button>
      <button
        type="button"
        class="block w-full border-t border-outline-variant px-4 py-2.5 text-left text-[13px] font-medium text-crimson-ruby hover:bg-[#ffe4e6]"
        @click="salir"
      >
        Cerrar sesión
      </button>
    </div>

    <!-- Datos de mi cuenta -->
    <Modal v-if="modal === 'cuenta'" titulo="Datos de mi cuenta" @cerrar="cerrarModal">
      <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
        <dt class="text-on-surface-variant">Nombre</dt>
        <dd class="text-on-surface">{{ sesion.nombre || '—' }}</dd>
        <dt class="text-on-surface-variant">Usuario</dt>
        <dd class="text-on-surface">{{ sesion.username || '—' }}</dd>
        <dt class="text-on-surface-variant">Rol</dt>
        <dd class="text-on-surface">{{ sesion.rol }}</dd>
        <dt class="text-on-surface-variant">Tienda</dt>
        <dd class="text-on-surface">{{ sesion.tiendaId ?? 'Toda la red' }}</dd>
        <dt class="text-on-surface-variant">Empleado #</dt>
        <dd class="text-on-surface">{{ sesion.empleadoId }}</dd>
      </dl>
    </Modal>

    <!-- Mi PIN de autorización -->
    <Modal v-if="modal === 'pin'" titulo="Mi PIN de autorización" @cerrar="cerrarModal">
      <p v-if="pinCargando" class="text-sm text-on-surface-variant">Cargando…</p>
      <template v-else-if="pin?.puede_autorizar">
        <p class="mb-4 text-[13px] text-on-surface-variant">
          Úsalo para autorizar en caja procesos que exigen un supervisor distinto del cajero
          (remover una línea, aplicar un descuento manual). No lo compartas.
        </p>
        <div
          class="flex items-center justify-between rounded-xl border border-outline-variant bg-surface-container-lowest px-4 py-3"
        >
          <span class="font-mono text-2xl font-extrabold tracking-[0.35em] text-on-surface">
            {{ pinRevelado ? pin.pin : '••••' }}
          </span>
          <button
            type="button"
            class="rounded-lg border border-outline-variant px-3 py-1.5 text-[12px] font-semibold text-on-surface-variant hover:bg-surface-container"
            @click="pinRevelado = !pinRevelado"
          >
            {{ pinRevelado ? 'Ocultar' : 'Mostrar' }}
          </button>
        </div>
      </template>
      <p v-else class="text-[13px] text-on-surface-variant">
        Tu rol no autoriza procesos de caja, así que no tienes un PIN de autorización.
      </p>
    </Modal>

    <!-- Cambiar contraseña -->
    <Modal v-if="modal === 'password'" titulo="Cambiar contraseña" @cerrar="cerrarModal">
      <form class="space-y-3" @submit.prevent="cambiarPassword">
        <label class="block text-xs text-on-surface-variant">
          Contraseña actual
          <input
            v-model="pw.actual"
            type="password"
            required
            autocomplete="current-password"
            class="mt-1 block w-full rounded-md border border-outline-variant bg-white px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="block text-xs text-on-surface-variant">
          Nueva contraseña (mín. 8)
          <input
            v-model="pw.nueva"
            type="password"
            required
            autocomplete="new-password"
            class="mt-1 block w-full rounded-md border border-outline-variant bg-white px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="block text-xs text-on-surface-variant">
          Repetir nueva contraseña
          <input
            v-model="pw.repetir"
            type="password"
            required
            autocomplete="new-password"
            class="mt-1 block w-full rounded-md border border-outline-variant bg-white px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <p v-if="pwError" class="rounded-md bg-[#ffe4e6] px-3 py-2 text-xs text-[#be123c]">
          {{ pwError }}
        </p>
        <p v-if="pwOk" class="rounded-md bg-[#d1fae5] px-3 py-2 text-xs text-[#047857]">
          Contraseña actualizada.
        </p>
        <button
          type="submit"
          :disabled="pwEnviando"
          class="w-full rounded-md bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary disabled:opacity-50"
        >
          Guardar
        </button>
      </form>
    </Modal>
  </div>
</template>
