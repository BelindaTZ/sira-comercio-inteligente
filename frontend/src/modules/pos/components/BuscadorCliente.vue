<script setup>
/**
 * Búsqueda de cliente afiliado en el punto de venta (feature 002, Ronda 5).
 * Localiza por nombre/email/cédula vía `GET /api/clientes?search=` y vincula el
 * `household_id` a la venta en curso. FR-008 de 001 dejó `household_id?` opcional
 * en `POST /api/ventas` desde el inicio; aquí se le da UI (no reabre 001).
 */
import { ref } from 'vue'
import { clientesApi } from '@/services/clientesApi'

// `seleccionadoId`: household_id ya vinculado a la venta, si hay alguno.
defineProps({ seleccionadoId: { type: Number, default: null } })
const emit = defineEmits(['seleccionar', 'quitar'])

const termino = ref('')
const resultados = ref([])
const buscando = ref(false)
const error = ref('')
let timer = null

function buscar() {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    const q = termino.value.trim()
    if (q.length < 2) {
      resultados.value = []
      return
    }
    buscando.value = true
    error.value = ''
    try {
      const data = await clientesApi.listar({ search: q, activo: true })
      resultados.value = data.items.slice(0, 8)
    } catch (e) {
      error.value = e.message
    } finally {
      buscando.value = false
    }
  }, 300)
}

function elegir(c) {
  emit('seleccionar', c)
  termino.value = ''
  resultados.value = []
}
</script>

<template>
  <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
    <h3 class="mb-2 text-sm font-semibold text-on-surface">Cliente (opcional)</h3>

    <div
      v-if="seleccionadoId"
      class="flex items-center justify-between rounded-lg bg-surface-container-high px-3 py-2 text-sm"
    >
      <span>Cliente #{{ seleccionadoId }} vinculado a la venta</span>
      <button
        type="button"
        class="text-xs font-semibold text-error hover:underline"
        @click="emit('quitar')"
      >
        Quitar
      </button>
    </div>

    <template v-else>
      <input
        v-model="termino"
        placeholder="Buscar por cédula, nombre o email"
        class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        @input="buscar"
      />
      <p v-if="error" class="mt-1 text-xs text-error">{{ error }}</p>
      <ul v-if="resultados.length" class="mt-2 divide-y divide-outline-variant">
        <li
          v-for="c in resultados"
          :key="c.household_id"
          class="cursor-pointer px-2 py-1.5 text-sm hover:bg-surface-container-low"
          @click="elegir(c)"
        >
          #{{ c.household_id }} · {{ c.nombre }}
          <span class="text-on-surface-variant">
            {{ c.documento_identidad || c.email }}
          </span>
        </li>
      </ul>
      <p v-else-if="termino.length >= 2 && !buscando" class="mt-2 text-xs text-on-surface-variant">
        Sin coincidencias — la venta puede confirmarse como anónima.
      </p>
    </template>
  </div>
</template>
