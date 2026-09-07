<script setup>
/**
 * FR-004 — regla de ajuste por categoría: el factor de sensibilidad ("elasticidad")
 * con el que el motor calcula las propuestas semanales. `null` = sin regla activa
 * (el job la omite). Toda la fórmula vive en el backend (Principio V).
 */
import { reactive, watch } from 'vue'
import { pricingApi } from '@/services/pricingApi'

const props = defineProps({
  margen: { type: Object, default: null }, // fila de /api/pricing/margenes
})
const emit = defineEmits(['guardado'])

const form = reactive({ margenObjetivoPct: '', factorSensibilidad: '' })
const estado = reactive({ error: '', guardando: false })

watch(
  () => props.margen,
  (m) => {
    form.margenObjetivoPct = m?.margen_objetivo_pct ?? ''
    form.factorSensibilidad = m?.factor_sensibilidad ?? ''
  },
  { immediate: true }
)

async function guardar() {
  if (!props.margen) return
  estado.error = ''
  estado.guardando = true
  try {
    await pricingApi.actualizarMargen(props.margen.product_category, {
      margenObjetivoPct: form.margenObjetivoPct === '' ? undefined : form.margenObjetivoPct,
      factorSensibilidad: form.factorSensibilidad === '' ? undefined : form.factorSensibilidad,
    })
    emit('guardado')
  } catch (e) {
    estado.error = e.message
  } finally {
    estado.guardando = false
  }
}
</script>

<template>
  <form
    v-if="margen"
    class="space-y-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
    @submit.prevent="guardar"
  >
    <h3 class="text-sm font-semibold text-on-surface">
      Regla de ajuste — {{ margen.product_category }}
    </h3>
    <label class="block text-xs text-on-surface-variant">
      Margen objetivo (%)
      <input
        v-model="form.margenObjetivoPct"
        type="number"
        min="0"
        max="100"
        step="0.01"
        class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
    </label>
    <label class="block text-xs text-on-surface-variant">
      Factor de sensibilidad (0–1; vacío = sin regla activa)
      <input
        v-model="form.factorSensibilidad"
        type="number"
        min="0"
        max="1"
        step="0.05"
        class="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
    </label>
    <button
      type="submit"
      :disabled="estado.guardando"
      class="w-full rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-40"
    >
      Guardar regla
    </button>
    <p v-if="estado.error" class="text-sm text-error">{{ estado.error }}</p>
  </form>
</template>
