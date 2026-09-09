<script setup>
/**
 * FR-014/FR-015/FR-016 — competidores nombrados, captura manual de precio de
 * referencia (con tienda opcional y flag promocional) y listado de alertas de
 * desviación (generadas por el job semanal). Open Prices se captura solo para
 * productos en vivo con barcode real, sin UI propia (research.md §5).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
// captura de competencia = Jefe Comercial; el resto (incl. Gerencia) consulta
const puedeRegistrar = computed(() => sesion.puedeEditarTabla('Comercial', 'precio_competencia'))

const competidores = ref([])
const alertas = ref([])
const error = ref('')
const cargando = ref(false)

const nuevoCompetidor = reactive({ nombre: '', tipo: 'supermercado', ciudad: '' })
const captura = reactive({ productId: '', competidorId: '', precio: '', esPromocional: false })

function moneda(v) {
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(
    Number(v || 0)
  )
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    competidores.value = await pricingApi.competidores()
    alertas.value = (await pricingApi.alertasCompetencia()).items
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function crearCompetidor() {
  if (!nuevoCompetidor.nombre.trim()) return
  try {
    await pricingApi.crearCompetidor({ ...nuevoCompetidor, ciudad: nuevoCompetidor.ciudad || null })
    nuevoCompetidor.nombre = ''
    nuevoCompetidor.ciudad = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function registrarPrecio() {
  if (!captura.productId || !captura.competidorId || !captura.precio) return
  try {
    await pricingApi.registrarPrecioCompetencia(Number(captura.productId), {
      competidorId: Number(captura.competidorId),
      precio: captura.precio,
      esPromocional: captura.esPromocional,
    })
    captura.precio = ''
    captura.esPromocional = false
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Precio de competencia</h1>
      <RouterLink
        to="/pricing"
        class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
      >
        ← Márgenes
      </RouterLink>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div class="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <section class="space-y-3">
        <h2 class="text-sm font-semibold text-on-surface">
          Alertas de desviación <span class="text-on-surface-variant">({{ alertas.length }})</span>
        </h2>
        <div
          class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-4 py-2 font-semibold">Producto</th>
                <th class="px-4 py-2 text-right font-semibold">Precio propio</th>
                <th class="px-4 py-2 text-right font-semibold">Competencia</th>
                <th class="px-4 py-2 font-semibold">Fuente</th>
                <th class="px-4 py-2 text-right font-semibold">Desviación</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="5" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
              </tr>
              <tr v-else-if="!alertas.length">
                <td colspan="5" class="px-4 py-6 text-center text-on-surface-variant">
                  Sin desviaciones por encima del umbral
                </td>
              </tr>
              <tr
                v-for="a in alertas"
                :key="a.product_id"
                class="border-b border-outline-variant last:border-0"
              >
                <td class="px-4 py-2 tabular-nums">#{{ a.product_id }}</td>
                <td class="px-4 py-2 text-right tabular-nums">{{ moneda(a.precio_base) }}</td>
                <td class="px-4 py-2 text-right tabular-nums">
                  {{ moneda(a.precio_competencia) }}
                </td>
                <td class="px-4 py-2 text-on-surface-variant">{{ a.fuente_captura }}</td>
                <td class="px-4 py-2 text-right font-semibold tabular-nums text-error">
                  {{ a.desviacion_pct }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <aside v-if="puedeRegistrar" class="space-y-4">
        <form
          class="space-y-2 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
          @submit.prevent="crearCompetidor"
        >
          <h3 class="text-sm font-semibold text-on-surface">Nuevo competidor</h3>
          <input
            v-model="nuevoCompetidor.nombre"
            placeholder="Nombre"
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
          <select
            v-model="nuevoCompetidor.tipo"
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          >
            <option value="supermercado">Supermercado</option>
            <option value="tienda_barrio">Tienda de barrio</option>
            <option value="tienda_digital">Tienda digital</option>
          </select>
          <input
            v-model="nuevoCompetidor.ciudad"
            placeholder="Ciudad (opcional)"
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
          <button
            type="submit"
            class="w-full rounded-lg bg-primary-container px-3 py-2 text-sm font-semibold text-on-primary-container"
          >
            Agregar competidor
          </button>
        </form>

        <form
          class="space-y-2 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
          @submit.prevent="registrarPrecio"
        >
          <h3 class="text-sm font-semibold text-on-surface">Registrar precio de competencia</h3>
          <input
            v-model="captura.productId"
            type="number"
            placeholder="ID de producto"
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
          <select
            v-model="captura.competidorId"
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          >
            <option value="">Competidor…</option>
            <option v-for="c in competidores" :key="c.competidor_id" :value="c.competidor_id">
              {{ c.nombre }}
            </option>
          </select>
          <input
            v-model="captura.precio"
            type="number"
            min="0"
            step="0.01"
            placeholder="Precio observado"
            class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
          />
          <label class="flex items-center gap-2 text-xs text-on-surface-variant">
            <input v-model="captura.esPromocional" type="checkbox" />
            Precio promocional
          </label>
          <button
            type="submit"
            class="w-full rounded-lg bg-primary-container px-3 py-2 text-sm font-semibold text-on-primary-container"
          >
            Registrar captura
          </button>
        </form>
      </aside>
    </div>
  </main>
</template>
