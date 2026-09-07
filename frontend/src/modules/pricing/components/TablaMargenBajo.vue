<script setup>
/**
 * FR-011/FR-012 — líneas de venta con descuento manual autorizado cuyo margen
 * real quedó bajo el margen objetivo efectivo. Listado diario de una tienda
 * (con `tiendaId`) o consolidado semanal de Jefe_Comercial (sin `tiendaId`),
 * con formulario para registrar la acción correctiva y cerrar el ciclo.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import { pricingApi } from '@/services/pricingApi'

const props = defineProps({
  tiendaId: { type: Number, default: null },
})

const filtros = reactive({ revisado: false })
const items = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const borrador = reactive({}) // venta_detalle_id -> texto de acción correctiva

function moneda(v) {
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(
    Number(v || 0)
  )
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await pricingApi.margenBajo({
      tiendaId: props.tiendaId ?? undefined,
      revisado: filtros.revisado,
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function registrar(item) {
  const texto = (borrador[item.venta_detalle_id] || '').trim()
  if (!texto) return
  try {
    await pricingApi.registrarRevision(item.venta_detalle_id, texto)
    delete borrador[item.venta_detalle_id]
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

watch(() => props.tiendaId, cargar)
watch(filtros, cargar, { deep: true })
onMounted(cargar)
</script>

<template>
  <section class="space-y-3">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-on-surface">
        Descuentos bajo margen mínimo
        <span class="text-on-surface-variant">({{ total }})</span>
      </h2>
      <label class="flex items-center gap-2 text-xs text-on-surface-variant">
        <input v-model="filtros.revisado" type="checkbox" />
        Ver ya revisados
      </label>
    </div>

    <p v-if="error" class="rounded-lg bg-error-container px-3 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <div
      class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
    >
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-variant text-left text-on-surface-variant">
            <th class="px-3 py-2 font-semibold">Venta / Línea</th>
            <th class="px-3 py-2 font-semibold">Producto</th>
            <th class="px-3 py-2 text-right font-semibold">P. aplicado</th>
            <th class="px-3 py-2 text-right font-semibold">Margen real</th>
            <th class="px-3 py-2 font-semibold">Motivo</th>
            <th class="px-3 py-2 font-semibold">Acción correctiva</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="cargando">
            <td colspan="6" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="6" class="px-3 py-6 text-center text-on-surface-variant">
              Sin resultados
            </td>
          </tr>
          <tr
            v-for="it in items"
            :key="it.venta_detalle_id"
            class="border-b border-outline-variant last:border-0 align-top"
          >
            <td class="px-3 py-2 tabular-nums">#{{ it.venta_id }} / {{ it.venta_detalle_id }}</td>
            <td class="px-3 py-2">#{{ it.product_id }} ×{{ it.cantidad }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ moneda(it.precio_aplicado) }}</td>
            <td class="px-3 py-2 text-right tabular-nums text-error">
              {{ it.margen_real == null ? '—' : `${it.margen_real}%` }}
            </td>
            <td class="px-3 py-2 text-on-surface-variant">{{ it.motivo_descuento || '—' }}</td>
            <td class="px-3 py-2">
              <template v-if="it.revisado">
                <span class="text-tertiary">{{ it.accion_correctiva }}</span>
              </template>
              <div v-else class="flex gap-2">
                <input
                  v-model="borrador[it.venta_detalle_id]"
                  placeholder="Acción tomada…"
                  class="flex-1 rounded-lg border border-outline-variant bg-surface px-2 py-1 text-xs text-on-surface"
                />
                <button
                  type="button"
                  class="rounded-lg bg-primary-container px-2 py-1 text-xs font-semibold text-on-primary-container"
                  @click="registrar(it)"
                >
                  Registrar
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
