<script setup>
/**
 * Alta de campaña de reactivación (US5, FR-016). Los candidatos salen de
 * `riesgo-fuga`; cada uno se asigna a `tratado` o `control`. El backend rechaza
 * el envío si no queda ningún `control` (FR-017) — aquí sólo se arma la lista.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { clientesApi } from '@/services/clientesApi'

const emit = defineEmits(['creada'])

const hoy = new Date().toISOString().slice(0, 10)
const form = reactive({ startDate: hoy, endDate: hoy })
const candidatos = ref([])
const grupo = reactive({}) // household_id -> 'tratado' | 'control' | undefined
const guardando = ref(false)
const error = ref('')

const seleccion = computed(() =>
  candidatos.value
    .filter((c) => grupo[c.household_id])
    .map((c) => ({ household_id: c.household_id, grupo: grupo[c.household_id] }))
)
const hayControl = computed(() => seleccion.value.some((m) => m.grupo === 'control'))
const hayTratado = computed(() => seleccion.value.some((m) => m.grupo === 'tratado'))

onMounted(async () => {
  try {
    candidatos.value = (await clientesApi.riesgoFuga({ size: 100 })).items
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  }
})

function ciclar(id) {
  grupo[id] = grupo[id] === 'tratado' ? 'control' : grupo[id] === 'control' ? undefined : 'tratado'
}

async function guardar() {
  error.value = ''
  guardando.value = true
  try {
    const campana = await clientesApi.crearCampana({
      startDate: form.startDate,
      endDate: form.endDate,
      miembros: seleccion.value,
    })
    emit('creada', campana)
    for (const k of Object.keys(grupo)) delete grupo[k]
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.response?.data?.detail || e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <form
    class="space-y-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    @submit.prevent="guardar"
  >
    <p class="font-semibold text-on-surface">Nueva campaña de reactivación</p>

    <p v-if="error" class="rounded-lg bg-error-container px-3 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <div class="flex flex-wrap gap-3 text-sm">
      <label class="flex flex-col gap-1">
        <span class="text-on-surface-variant">Inicio</span>
        <input
          v-model="form.startDate"
          type="date"
          class="rounded-lg border border-outline-variant bg-surface px-2 py-1 text-on-surface"
        />
      </label>
      <label class="flex flex-col gap-1">
        <span class="text-on-surface-variant">Fin</span>
        <input
          v-model="form.endDate"
          type="date"
          class="rounded-lg border border-outline-variant bg-surface px-2 py-1 text-on-surface"
        />
      </label>
    </div>

    <div class="max-h-72 overflow-auto rounded-lg border border-outline-variant">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-3 py-2">Cliente</th>
            <th class="px-3 py-2">Severidad</th>
            <th class="px-3 py-2 text-right">Grupo</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!candidatos.length">
            <td colspan="3" class="px-3 py-4 text-center text-on-surface-variant">
              Sin clientes en riesgo de fuga
            </td>
          </tr>
          <tr
            v-for="c in candidatos"
            :key="c.household_id"
            class="cursor-pointer border-b border-outline-variant last:border-0 hover:bg-surface-container-low"
            @click="ciclar(c.household_id)"
          >
            <td class="px-3 py-2">
              {{ c.nombre }} <span class="text-on-surface-variant">#{{ c.household_id }}</span>
            </td>
            <td class="px-3 py-2 text-on-surface-variant">{{ c.severidad }}</td>
            <td class="px-3 py-2 text-right">
              <span
                class="rounded-full px-2 py-0.5 text-xs font-semibold"
                :class="{
                  'bg-primary-container text-on-primary-container':
                    grupo[c.household_id] === 'tratado',
                  'bg-tertiary-container text-on-tertiary-container':
                    grupo[c.household_id] === 'control',
                  'text-on-surface-variant': !grupo[c.household_id],
                }"
              >
                {{ grupo[c.household_id] || '—' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="text-xs text-on-surface-variant">
      Clic en una fila para alternar tratado → control → sin asignar.
    </p>

    <button
      type="submit"
      class="w-full rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-on-primary disabled:opacity-40"
      :disabled="guardando || !hayControl || !hayTratado"
    >
      Crear campaña ({{ seleccion.length }} miembros)
    </button>
    <p v-if="seleccion.length && !hayControl" class="text-xs text-error">
      Define al menos un cliente de control antes de poder enviarla (FR-017).
    </p>
  </form>
</template>
