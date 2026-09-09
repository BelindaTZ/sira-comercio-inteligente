<script setup>
/**
 * Registro rápido de productos en el POS (001, FR-001). Estructura de
 * `docs/diseno-ui/.../sira_punto_de_venta_y_registro_r_pido…`: buscador + pills
 * de categoría + grid de productos con precio y stock. También el escáner físico
 * (keyboard-wedge) y la cámara (`BarcodeDetector`), y entrada manual por código.
 * El grid se sirve de `GET /api/ventas/catalogo` (RBAC `Ventas`).
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import { money as moneyUsd } from '@/shared/currency'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  // { product_id: cantidad } de las líneas ya en el ticket
  enTicket: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['agregar'])

// --- escáner / entrada manual ---
const entrada = ref('')
const escaneando = ref(false)
const soporteCamara = typeof window !== 'undefined' && 'BarcodeDetector' in window
let stream = null
let rafId = null

function enviarCodigo() {
  const valor = entrada.value.trim()
  if (!valor) return
  const esNumeroPuro = /^\d+$/.test(valor)
  const pareceBarcode = esNumeroPuro && valor.length >= 6
  // texto libre corto = está filtrando el grid por nombre, no escaneando
  if (!esNumeroPuro && valor.length < 4) return
  emit('agregar', {
    codigoBarras: pareceBarcode || !esNumeroPuro ? valor : null,
    productId: !pareceBarcode && esNumeroPuro ? Number(valor) : null,
    cantidad: 1,
  })
  entrada.value = ''
}

async function toggleCamara() {
  if (escaneando.value) return detenerCamara()
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    const video = document.getElementById('pos-camara')
    video.srcObject = stream
    await video.play()
    escaneando.value = true
    const detector = new window.BarcodeDetector()
    const tick = async () => {
      if (!escaneando.value) return
      try {
        const [code] = await detector.detect(video)
        if (code?.rawValue) {
          entrada.value = code.rawValue
          enviarCodigo()
          detenerCamara()
          return
        }
      } catch {
        /* frame sin código, se reintenta */
      }
      rafId = requestAnimationFrame(tick)
    }
    rafId = requestAnimationFrame(tick)
  } catch {
    escaneando.value = false
  }
}

function detenerCamara() {
  escaneando.value = false
  if (rafId) cancelAnimationFrame(rafId)
  stream?.getTracks().forEach((t) => t.stop())
  stream = null
}
onBeforeUnmount(detenerCamara)

// --- grid de productos ---
const busqueda = computed(() => entrada.value.trim())
const categoria = ref('')
const categorias = ref([])
const productos = ref([])
const total = ref(0)
const cargando = ref(false)
const money = (v) => moneyUsd(v, { showCode: false })
const esFoto = (u) => u && u.startsWith('http')
const entradaEl = ref(null)
defineExpose({ focar: () => entradaEl.value?.focus() })

async function cargarProductos() {
  cargando.value = true
  try {
    const data = await ventasApi.catalogo({
      tiendaId: props.tiendaId,
      search: busqueda.value || undefined,
      categoria: categoria.value || undefined,
      size: 30,
    })
    productos.value = data.items
    total.value = data.total
  } catch {
    productos.value = []
  } finally {
    cargando.value = false
  }
}

let deb
watch([busqueda, categoria], () => {
  clearTimeout(deb)
  deb = setTimeout(cargarProductos, 250)
})

onMounted(async () => {
  categorias.value = await ventasApi.catalogoCategorias(props.tiendaId).catch(() => [])
  await cargarProductos()
})

// bloqueo breve para que un doble-clic no cree dos líneas del mismo SKU (el
// backend acumula, pero dos requests simultáneos ven el ticket sin la línea aún)
const bloqueado = ref(false)
function elegir(p) {
  if (p.stock_disponible <= 0 || bloqueado.value) return
  bloqueado.value = true
  emit('agregar', { productId: p.product_id, codigoBarras: null, cantidad: 1 })
  setTimeout(() => (bloqueado.value = false), 400)
}
</script>

<template>
  <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
    <!-- buscador unificado: escanea un código o busca por nombre -->
    <form class="mb-3 flex items-center gap-2" @submit.prevent="enviarCodigo">
      <div class="relative flex-1">
        <Icon
          name="search"
          :size="18"
          class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-brand-600"
        />
        <input
          ref="entradaEl"
          v-model="entrada"
          autofocus
          inputmode="text"
          placeholder="Escanea un código de barras o busca por nombre…"
          class="h-11 w-full rounded-xl border border-brand-300 bg-white pl-10 pr-16 text-[14px] text-slate-800 outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-500/20"
        />
        <span
          class="absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-brand-200 bg-brand-50 px-1.5 py-0.5 font-mono text-[10px] font-bold text-brand-700"
        >
          F2
        </span>
      </div>
      <button
        v-if="soporteCamara"
        type="button"
        class="h-11 shrink-0 rounded-xl border border-brand-200 bg-white px-2.5 text-slate-600 hover:bg-brand-50"
        :title="escaneando ? 'Detener cámara' : 'Escanear con cámara'"
        @click="toggleCamara"
      >
        <Icon name="image" :size="18" />
      </button>
    </form>
    <video v-show="escaneando" id="pos-camara" class="mb-3 w-full max-w-sm rounded-lg" muted />

    <!-- pills de categoría -->
    <div class="mb-3 flex gap-1.5 overflow-x-auto pb-1">
      <button
        type="button"
        class="shrink-0 rounded-full px-3 py-1 text-[11px] font-semibold transition"
        :class="categoria === '' ? 'bg-brand-800 text-white' : 'border border-brand-200 bg-white text-slate-600 hover:border-brand-400'"
        @click="categoria = ''"
      >
        Favoritos / Alta rotación
      </button>
      <button
        v-for="c in categorias"
        :key="c"
        type="button"
        class="shrink-0 whitespace-nowrap rounded-full px-3 py-1 text-[11px] font-semibold capitalize transition"
        :class="categoria === c ? 'bg-brand-800 text-white' : 'border border-brand-200 bg-white text-slate-600 hover:border-brand-400'"
        @click="categoria = c"
      >
        {{ c.toLowerCase() }}
      </button>
    </div>

    <!-- grid -->
    <div class="grid max-h-[560px] grid-cols-2 gap-2.5 overflow-y-auto pr-1 sm:grid-cols-3 2xl:grid-cols-4">
      <p v-if="cargando && !productos.length" class="col-span-full py-8 text-center text-[12px] text-slate-400">
        Cargando catálogo…
      </p>
      <p v-else-if="!productos.length" class="col-span-full py-8 text-center text-[12px] text-slate-400">
        Sin productos con stock para este filtro.
      </p>
      <button
        v-for="p in productos"
        :key="p.product_id"
        type="button"
        :disabled="p.stock_disponible <= 0"
        class="group flex flex-col gap-1.5 rounded-xl border bg-white p-2 text-left transition hover:shadow-card-subtle disabled:opacity-50"
        :class="enTicket[p.product_id] ? 'border-amethyst-400 ring-1 ring-amethyst-300/40' : 'border-brand-200 hover:border-brand-500'"
        @click="elegir(p)"
      >
        <div class="relative aspect-square w-full overflow-hidden rounded-lg bg-brand-50">
          <img v-if="esFoto(p.imagen_url)" :src="p.imagen_url" alt="" class="h-full w-full object-cover" />
          <span v-else class="grid h-full w-full place-items-center text-brand-300">
            <Icon name="cube" :size="22" />
          </span>
          <span
            v-if="p.product_category"
            class="absolute left-1 top-1 max-w-[70%] truncate rounded bg-white/90 px-1.5 py-0.5 text-[9px] font-bold text-slate-600"
          >
            {{ p.product_category }}
          </span>
          <span
            class="absolute right-1 top-1 rounded px-1.5 py-0.5 text-[9px] font-bold"
            :class="enTicket[p.product_id] ? 'bg-amethyst-600 text-white' : 'bg-white/90 text-slate-600'"
          >
            {{ enTicket[p.product_id] ? `En ticket ×${enTicket[p.product_id]}` : `${p.stock_disponible} u` }}
          </span>
        </div>
        <div class="flex min-w-0 flex-1 flex-col">
          <p class="line-clamp-2 text-[11px] font-semibold leading-tight text-slate-800">
            {{ p.nombre || '(sin nombre)' }}
          </p>
          <div class="mt-auto flex items-center justify-between pt-1">
            <span class="font-display text-[13px] font-extrabold tabular-nums text-brand-900">
              {{ money(p.precio_base) }}
            </span>
            <span class="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-brand-100 text-brand-800 group-hover:bg-brand-800 group-hover:text-white">
              <Icon name="plus" :size="13" />
            </span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
