<script setup>
/**
 * Simulador de datáfono (FR-003, FR-030). Componente separado del formulario de
 * venta: el cajero elige un escenario y ve la animación, nunca captura datos de
 * tarjeta. El backend usa una tarjeta de prueba de Stripe según el escenario.
 *
 * Los 3 resultados de FR-030 son distintos entre sí:
 *  - aprobado      → banco autoriza
 *  - rechazado     → banco rechaza
 *  - error_tecnico → no se pudo contactar la pasarela
 */
import { computed, ref } from 'vue'
import exitosoUrl from '@/assets/animations/pago-exitoso.mp4'
import rechazadoUrl from '@/assets/animations/pago-rechazado.mp4'
import errorUrl from '@/assets/animations/pago-error.mp4'

const props = defineProps({
  monto: { type: [Number, String], required: true },
  procesando: { type: Boolean, default: false },
})
const emit = defineEmits(['cobrar'])

const ANIMACIONES = {
  aprobado: exitosoUrl,
  rechazado: rechazadoUrl,
  error_tecnico: errorUrl,
}

const ultimoResultado = ref(null)

const animacionActual = computed(() =>
  ultimoResultado.value ? ANIMACIONES[ultimoResultado.value] : null
)

const ESCENARIOS = [
  {
    key: 'aprobado',
    label: 'Simular pago aprobado',
    clase: 'bg-emerald-100 text-emerald-800',
  },
  {
    key: 'rechazado',
    label: 'Simular rechazo del banco',
    clase: 'bg-rose-100 text-crimson-ruby',
  },
  {
    key: 'error_tecnico',
    label: 'Simular error técnico',
    clase: 'border border-brand-200 text-slate-800',
  },
]

async function cobrar(escenario) {
  ultimoResultado.value = null
  emit('cobrar', {
    escenario,
    // callback para que el padre nos informe el resultado real del backend
    onResultado: (resultado) => {
      ultimoResultado.value = resultado
    },
  })
}
</script>

<template>
  <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
    <p class="text-sm text-slate-500">
      Cobro con tarjeta — monto
      <strong class="text-slate-800">{{ props.monto }}</strong>
    </p>

    <div class="mt-3 flex flex-wrap gap-2">
      <button
        v-for="e in ESCENARIOS"
        :key="e.key"
        type="button"
        :disabled="procesando"
        class="rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
        :class="e.clase"
        @click="cobrar(e.key)"
      >
        {{ e.label }}
      </button>
    </div>

    <video
      v-if="animacionActual"
      :key="animacionActual"
      :src="animacionActual"
      class="mt-4 w-full max-w-xs rounded-lg"
      autoplay
      muted
      playsinline
    />
    <p
      v-if="ultimoResultado"
      class="mt-2 text-sm font-semibold"
      :class="
        ultimoResultado === 'aprobado' ? 'text-on-tertiary-container' : 'text-on-error-container'
      "
    >
      Resultado: {{ ultimoResultado.replace('_', ' ') }}
    </p>
  </div>
</template>
