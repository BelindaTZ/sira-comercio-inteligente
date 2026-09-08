<script setup>
/**
 * Cuentas de usuario (feature 008, FR-007/FR-008/FR-012). El Jefe de TI crea la
 * cuenta de un empleado ya registrado y asigna/revoca su rol con efecto inmediato.
 */
import { reactive, ref } from 'vue'
import { sistemaApi } from '@/services/sistemaApi'

const nueva = reactive({ empleado_id: '', username: '', password_inicial: '', role_id: '' })
const creada = ref(null)
const consultaId = ref('')
const cuenta = ref(null)
const nuevoRol = ref('')
const error = ref('')

async function crear() {
  error.value = ''
  try {
    creada.value = await sistemaApi.crearUsuario({
      empleadoId: Number(nueva.empleado_id),
      username: nueva.username.trim(),
      passwordInicial: nueva.password_inicial,
      roleId: Number(nueva.role_id),
    })
    nueva.username = ''
    nueva.password_inicial = ''
  } catch (e) {
    error.value = e.message
  }
}

async function consultar() {
  error.value = ''
  try {
    cuenta.value = await sistemaApi.obtenerUsuario(Number(consultaId.value))
  } catch (e) {
    error.value = e.message
    cuenta.value = null
  }
}

async function cambiarRol() {
  error.value = ''
  try {
    cuenta.value = await sistemaApi.asignarRol(cuenta.value.usuario_id, Number(nuevoRol.value))
    nuevoRol.value = ''
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Cuentas de usuario</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <form
      class="mb-6 grid gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 sm:grid-cols-2"
      @submit.prevent="crear"
    >
      <h2 class="col-span-full text-sm font-semibold text-on-surface">Crear cuenta</h2>
      <label class="text-xs text-on-surface-variant">
        Empleado (id)
        <input v-model="nueva.empleado_id" type="number" required class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Rol (id)
        <input v-model="nueva.role_id" type="number" required class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Usuario
        <input v-model="nueva.username" required class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <label class="text-xs text-on-surface-variant">
        Contraseña inicial
        <input v-model="nueva.password_inicial" type="password" minlength="8" required class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <button type="submit" class="col-span-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container">
        Crear
      </button>
      <p v-if="creada" class="col-span-full text-xs text-tertiary">
        Cuenta #{{ creada.usuario_id }} ({{ creada.username }}) creada.
      </p>
    </form>

    <form class="mb-4 flex items-end gap-3" @submit.prevent="consultar">
      <label class="text-xs text-on-surface-variant">
        Buscar cuenta por id
        <input v-model="consultaId" type="number" class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
      </label>
      <button type="submit" class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container">
        Consultar
      </button>
    </form>

    <article v-if="cuenta" class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
      <h3 class="text-sm font-semibold text-on-surface">
        Cuenta #{{ cuenta.usuario_id }} — {{ cuenta.username }}
      </h3>
      <p class="mt-1 text-xs text-on-surface-variant">
        empleado #{{ cuenta.empleado_id }} · rol #{{ cuenta.role_id }} ·
        {{ cuenta.activo ? 'activa' : 'inhabilitada' }} ·
        último login {{ cuenta.ultimo_login || 'nunca' }}
      </p>
      <div class="mt-3 flex items-end gap-2">
        <label class="text-xs text-on-surface-variant">
          Nuevo rol (id)
          <input v-model="nuevoRol" type="number" class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface" />
        </label>
        <button
          type="button"
          class="rounded-lg bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
          @click="cambiarRol"
        >
          Asignar rol (efecto inmediato)
        </button>
      </div>
    </article>
  </main>
</template>
