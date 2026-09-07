<script setup>
/**
 * Alta / edición de cliente (FR-001/FR-002). El consentimiento de tratamiento de
 * datos se captura de forma explícita en el alta y puede revocarse/otorgarse
 * después desde este mismo formulario (sin anonimizar nada). Cédula opcional (Ronda 5).
 */
import { reactive, ref, watch } from 'vue'
import { clientesApi } from '@/services/clientesApi'

const props = defineProps({
  // Si viene un cliente, el formulario está en modo edición.
  cliente: { type: Object, default: null },
})
const emit = defineEmits(['guardado'])

const form = reactive({
  nombre: '',
  email: '',
  telefono: '',
  documentoIdentidad: '',
  fechaNacimiento: '',
  consentimientoDatos: false,
})
const error = ref('')
const guardando = ref(false)

watch(
  () => props.cliente,
  (c) => {
    if (!c) return
    form.nombre = c.nombre ?? ''
    form.email = c.email ?? ''
    form.telefono = c.telefono ?? ''
    form.documentoIdentidad = c.documento_identidad ?? ''
    form.fechaNacimiento = c.fecha_nacimiento ?? ''
    form.consentimientoDatos = c.consentimiento_datos
  },
  { immediate: true }
)

async function guardar() {
  error.value = ''
  guardando.value = true
  try {
    let resultado
    if (props.cliente) {
      resultado = await clientesApi.actualizar(props.cliente.household_id, {
        nombre: form.nombre,
        email: form.email,
        telefono: form.telefono || null,
        documento_identidad: form.documentoIdentidad || null,
        fecha_nacimiento: form.fechaNacimiento || null,
        consentimiento_datos: form.consentimientoDatos,
      })
    } else {
      resultado = await clientesApi.crear({
        nombre: form.nombre,
        email: form.email,
        telefono: form.telefono,
        documentoIdentidad: form.documentoIdentidad,
        fechaNacimiento: form.fechaNacimiento,
        consentimientoDatos: form.consentimientoDatos,
      })
    }
    emit('guardado', resultado)
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <form
    class="space-y-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    @submit.prevent="guardar"
  >
    <h3 class="text-sm font-semibold text-on-surface">
      {{ cliente ? `Editar cliente #${cliente.household_id}` : 'Nuevo cliente' }}
    </h3>
    <input
      v-model="form.nombre"
      placeholder="Nombre"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <input
      v-model="form.email"
      type="email"
      placeholder="Email"
      required
      class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
    />
    <div class="flex gap-3">
      <input
        v-model="form.telefono"
        placeholder="Teléfono"
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
      <input
        v-model="form.documentoIdentidad"
        placeholder="Cédula / RUC (opcional)"
        maxlength="13"
        class="w-1/2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface"
      />
    </div>
    <label class="block text-xs text-on-surface-variant">
      Fecha de nacimiento
      <input
        v-model="form.fechaNacimiento"
        type="date"
        class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
    </label>
    <label
      class="flex items-start gap-2 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface-variant"
    >
      <input v-model="form.consentimientoDatos" type="checkbox" class="mt-0.5" />
      <span>
        El cliente autoriza el tratamiento de sus datos para fidelización (CLV, campañas). Se puede
        revocar aquí mismo más tarde — revocarlo no borra sus datos.
      </span>
    </label>
    <button
      type="submit"
      :disabled="guardando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      {{ cliente ? 'Guardar cambios' : 'Registrar cliente' }}
    </button>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </form>
</template>
