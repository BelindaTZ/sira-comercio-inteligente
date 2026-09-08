<script setup>
/**
 * Inicio de sesión (feature 008, FR-001). Fuera del layout de navegación estándar.
 * El backend responde el mismo 401 genérico ante cualquier fallo de credenciales
 * (FR-002/FR-003) — la UI no intenta distinguir la causa.
 */
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi } from '@/services/authApi'

const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const error = ref('')
const cargando = ref(false)

async function entrar() {
  error.value = ''
  cargando.value = true
  try {
    await authApi.login(username.value.trim(), password.value)
    router.replace(route.query.redirect || '/')
  } catch (e) {
    error.value = e.status === 401 ? 'Credenciales inválidas o cuenta inactiva' : e.message
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-surface-container px-4">
    <form
      class="w-full max-w-sm rounded-2xl border border-outline-variant bg-surface-container-lowest p-8"
      @submit.prevent="entrar"
    >
      <h1 class="mb-1 text-xl font-bold text-primary-container">SIRA</h1>
      <p class="mb-6 text-sm text-on-surface-variant">Sistema Inteligente de Retail Adaptativo</p>

      <label class="mb-3 block text-xs font-medium text-on-surface-variant">
        Usuario
        <input
          v-model="username"
          type="text"
          autocomplete="username"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="mb-4 block text-xs font-medium text-on-surface-variant">
        Contraseña
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>

      <p
        v-if="error"
        class="mb-4 rounded-lg bg-error-container px-3 py-2 text-sm text-on-error-container"
      >
        {{ error }}
      </p>

      <button
        type="submit"
        :disabled="cargando"
        class="w-full rounded-lg bg-primary-container px-4 py-2.5 text-sm font-bold text-on-primary-container disabled:opacity-40"
      >
        {{ cargando ? 'Ingresando…' : 'Iniciar sesión' }}
      </button>

      <RouterLink
        to="/auth/recuperar"
        class="mt-4 block text-center text-xs text-on-surface-variant hover:underline"
      >
        Olvidé mi contraseña
      </RouterLink>
    </form>
  </main>
</template>
