<script setup>
/**
 * Sub-barra de contexto operativo (Principio XII, punto 2 del patrón de referencia
 * `sira_inventario_y_alertas_fifo_header_verde_abisal/code.html` → «SUB-RIBBON &
 * OPERATIONS ROLE CONTEXT»).
 *
 * Un encargado o cajero necesita saber sin ambigüedad **en qué tienda está** y
 * **qué hora es** (cuadres, aperturas y turnos dependen de ello). Antes nada en
 * la interfaz lo indicaba.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useSesion } from '@/stores/sesion'
import Icon from './Icon.vue'

const sesion = useSesion()

const ahora = ref(new Date())
let timer = null
onMounted(() => {
  timer = setInterval(() => (ahora.value = new Date()), 1000)
})
onBeforeUnmount(() => clearInterval(timer))

const hora = computed(() =>
  ahora.value.toLocaleTimeString('es-EC', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
)
const fecha = computed(() =>
  ahora.value.toLocaleDateString('es-EC', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
)

const tienda = computed(() => sesion.tiendaNombre)
const ciudad = computed(() => sesion.tiendaCiudad)
const codigo = computed(() => sesion.tiendaCodigo)
</script>

<template>
  <section
    class="w-full border-b border-brand-200 bg-brand-50/80 px-4 py-2 backdrop-blur lg:px-6"
  >
    <div
      class="mx-auto flex max-w-[1840px] flex-wrap items-center justify-between gap-x-4 gap-y-1.5"
    >
      <!-- Ubicación -->
      <div class="flex items-center gap-2 text-[12px] text-slate-600">
        <span class="inline-flex items-center gap-1.5 font-medium">
          <Icon name="pin" :size="14" class="text-brand-700" />
          Marzú Retail Group
        </span>
        <template v-if="tienda">
          <span class="text-slate-300">/</span>
          <span class="inline-flex items-center gap-1.5 font-bold text-brand-900">
            <span class="h-1.5 w-1.5 rounded-full bg-brand-700" />
            {{ tienda }}
          </span>
          <span v-if="ciudad" class="text-slate-300">/</span>
          <span v-if="ciudad" class="font-medium text-slate-500">{{ ciudad }}</span>
          <span
            v-if="codigo"
            class="rounded-md border border-brand-200 bg-white px-1.5 py-0.5 font-mono text-[10px] font-bold text-brand-700"
          >
            {{ codigo }}
          </span>
        </template>
        <template v-else>
          <span class="text-slate-300">/</span>
          <span class="font-medium text-slate-500">Vista corporativa · todas las tiendas</span>
        </template>
      </div>

      <!-- Reloj -->
      <div class="flex items-center gap-2 text-[12px]">
        <Icon name="clock" :size="14" class="text-slate-400" />
        <span class="font-medium capitalize text-slate-500">{{ fecha }}</span>
        <span
          class="rounded-md border border-brand-200 bg-white px-2 py-0.5 font-mono text-[12px] font-bold tabular-nums text-brand-900"
        >
          {{ hora }}
        </span>
      </div>
    </div>
  </section>
</template>
