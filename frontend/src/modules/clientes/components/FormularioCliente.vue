<script setup>
/**
 * Alta / edición de cliente (FR-001/FR-002). El consentimiento de tratamiento de
 * datos se captura de forma explícita en el alta y puede revocarse/otorgarse
 * después desde este mismo formulario (sin anonimizar nada). Cédula opcional (Ronda 5).
 */
import { reactive, ref, watch } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import Btn from '@/shared/ui/Btn.vue'

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
  { immediate: true },
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

const inputClass =
  'mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none'
</script>

<template>
  <form class="space-y-3" @submit.prevent="guardar">
    <label class="block text-[12px] font-semibold text-slate-600">
      Nombre
      <input v-model="form.nombre" required :class="inputClass" />
    </label>
    <label class="block text-[12px] font-semibold text-slate-600">
      Email
      <input v-model="form.email" type="email" required :class="inputClass" />
    </label>
    <div class="grid grid-cols-2 gap-3">
      <label class="block text-[12px] font-semibold text-slate-600">
        Teléfono
        <input v-model="form.telefono" :class="inputClass" />
      </label>
      <label class="block text-[12px] font-semibold text-slate-600">
        Cédula / RUC (opcional)
        <input v-model="form.documentoIdentidad" maxlength="13" :class="inputClass" />
      </label>
      <label class="col-span-2 block text-[12px] font-semibold text-slate-600">
        Fecha de nacimiento
        <input v-model="form.fechaNacimiento" type="date" :class="inputClass" />
      </label>
    </div>
    <label class="flex items-start gap-2 rounded-lg border border-brand-200 bg-brand-50/50 px-3 py-2 text-[12px] text-slate-600">
      <input v-model="form.consentimientoDatos" type="checkbox" class="mt-0.5" />
      <span>
        El cliente autoriza el tratamiento de sus datos para fidelización (CLV, campañas). Se puede
        revocar aquí mismo más tarde — revocarlo no borra sus datos.
      </span>
    </label>
    <p v-if="error" class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-crimson-ruby">{{ error }}</p>
    <div class="flex justify-end pt-1">
      <Btn variant="primary" type="submit" :disabled="guardando">
        {{ guardando ? 'Guardando…' : cliente ? 'Guardar cambios' : 'Registrar cliente' }}
      </Btn>
    </div>
  </form>
</template>
