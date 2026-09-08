<script setup>
/**
 * Recuperación de contraseña (feature 008, FR-009/FR-010). Dos pasos: solicitar
 * el enlace por correo y confirmar con el token de un solo uso. La respuesta a la
 * solicitud es siempre genérica (anti-enumeración).
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/services/authApi'

const router = useRouter()
const email = ref('')
const token = ref('')
const passwordNueva = ref('')
const solicitado = ref(false)
const listo = ref(false)
const error = ref('')

async function solicitar() {
  error.value = ''
  try {
    await authApi.solicitarRecuperacion(email.value.trim())
    solicitado.value = true
  } catch (e) {
    error.value = e.message
  }
}

async function confirmar() {
  error.value = ''
  try {
    await authApi.confirmarRecuperacion(token.value.trim(), passwordNueva.value)
    listo.value = true
    setTimeout(() => router.replace('/auth/login'), 1500)
  } catch (e) {
    error.value = e.status === 410 ? 'El enlace ya fue usado o venció' : e.message
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-surface-container px-4">
    <div class="w-full max-w-sm rounded-2xl border border-outline-variant bg-surface-container-lowest p-8">
      <h1 class="mb-6 text-lg font-bold text-primary-container">Recuperar contraseña</h1>

      <p
        v-if="error"
        class="mb-4 rounded-lg bg-error-container px-3 py-2 text-sm text-on-error-container"
      >
        {{ error }}
      </p>

      <p v-if="listo" class="rounded-lg bg-tertiary-container px-3 py-2 text-sm text-on-tertiary-container">
        Contraseña actualizada. Redirigiendo al inicio de sesión…
      </p>

      <form v-else-if="!solicitado" @submit.prevent="solicitar">
        <label class="mb-4 block text-xs font-medium text-on-surface-variant">
          Correo de la cuenta
          <input
            v-model="email"
            type="email"
            required
            class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <button
          type="submit"
          class="w-full rounded-lg bg-primary-container px-4 py-2.5 text-sm font-bold text-on-primary-container"
        >
          Enviar enlace
        </button>
      </form>

      <form v-else @submit.prevent="confirmar">
        <p class="mb-4 text-sm text-on-surface-variant">
          Si el correo corresponde a una cuenta, te enviamos un enlace de un solo uso. Pega el
          token y define tu nueva contraseña.
        </p>
        <label class="mb-3 block text-xs font-medium text-on-surface-variant">
          Token
          <input
            v-model="token"
            type="text"
            required
            class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <label class="mb-4 block text-xs font-medium text-on-surface-variant">
          Nueva contraseña
          <input
            v-model="passwordNueva"
            type="password"
            minlength="8"
            required
            class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
        </label>
        <button
          type="submit"
          class="w-full rounded-lg bg-primary-container px-4 py-2.5 text-sm font-bold text-on-primary-container"
        >
          Cambiar contraseña
        </button>
      </form>

      <RouterLink
        to="/auth/login"
        class="mt-4 block text-center text-xs text-on-surface-variant hover:underline"
      >
        Volver al inicio de sesión
      </RouterLink>
    </div>
  </main>
</template>
