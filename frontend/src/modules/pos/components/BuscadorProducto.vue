<script setup>
/**
 * Registro rápido de productos en el POS (001, FR-001). Estructura de
 * `docs/diseno-ui/.../sira_punto_de_venta_y_registro_r_pido…`: buscador + pills
 * de categoría + grid de productos con precio y stock. También el escáner físico
 * (keyboard-wedge) y la cámara (`BarcodeDetector`), y entrada manual por código.
 * El grid se sirve de `GET /api/ventas/catalogo` (RBAC `Ventas`).
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ventasApi } from '@/services/ventasApi'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({ tiendaId: { type: Number, required: true } })
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
const busqueda = ref('')
const categoria = ref('')
const categorias = ref([])
const productos = ref([])
const total = ref(0)
const cargando = ref(false)
const money = (v) => `$${Math.round(Number(v || 0)).toLocaleString('es-CL')}`
const esFoto = (u) => u && u.startsWith('http')

async function cargarProductos() {
  cargando.value = true
  try {
    const data = await ventasApi.catalogo({
      tiendaId: props.tiendaId,
      search: busqueda.value.trim() || undefined,
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
    <div class="mb-2 flex items-center justify-between">
      <h2 class="font-display text-[13px] font-bold text-brand-950">Registro rápido</h2>
      <span class="text-[10px] font-semibold text-slate-400">{{ total.toLocaleString('es-CL') }} SKUs en stock</span>
    </div>

    <!-- escáner / código manual -->
    <form class="mb-3 flex items-center gap-2" @submit.prevent="enviarCodigo">
      <div class="relative flex-1">
        <Icon name="search" :size="15" class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-brand-600" />
        <input
          v-model="entrada"
          autofocus
          inputmode="text"
          placeholder="Escaneá o escribí un código y pulsá Enter"
          class="w-full rounded-lg border border-brand-300 bg-white py-2 pl-8 pr-3 text-[13px] text-slate-800 outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-500/20"
        />
      </div>
      <button
        v-if="soporteCamara"
        type="button"
        class="shrink-0 rounded-lg border border-brand-200 bg-white p-2 text-slate-600 hover:bg-brand-50"
        :title="escaneando ? 'Detener cámara' : 'Escanear con cámara'"
        @click="toggleCamara"
      >
        <Icon name="image" :size="16" />
      </button>
    </form>
    <video v-show="escaneando" id="pos-camara" class="mb-3 w-full max-w-sm rounded-lg" muted />

    <!-- filtro del grid -->
    <div class="mb-2 flex items-center gap-2">
      <div class="relative flex-1">
        <input
          v-model="busqueda"
          placeholder="Filtrar el catálogo por nombre o marca…"
          class="w-full rounded-lg border border-brand-200 bg-brand-50/40 px-3 py-1.5 text-[12px] text-slate-800 outline-none focus:border-brand-500"
        />
      </div>
    </div>
    <div class="mb-3 flex gap-1.5 overflow-x-auto pb-1">
      <button
        type="button"
        class="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold transition"
        :class="categoria === '' ? 'bg-brand-800 text-white' : 'border border-brand-200 bg-white text-slate-600 hover:border-brand-400'"
        @click="categoria = ''"
      >
        Todos
      </button>
      <button
        v-for="c in categorias"
        :key="c"
        type="button"
        class="shrink-0 whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize transition"
        :class="categoria === c ? 'bg-brand-800 text-white' : 'border border-brand-200 bg-white text-slate-600 hover:border-brand-400'"
        @click="categoria = c"
      >
        {{ c.toLowerCase() }}
      </button>
    </div>

    <!-- grid -->
    <div class="grid max-h-[440px] grid-cols-2 gap-2 overflow-y-auto pr-1 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
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
        class="group flex gap-2 rounded-xl border border-brand-200 bg-white p-1.5 text-left transition hover:border-brand-500 hover:shadow-card-subtle disabled:opacity-50 sm:flex-col sm:gap-1"
        @click="elegir(p)"
      >
        <div class="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-brand-50 sm:h-16 sm:w-full">
          <img v-if="esFoto(p.imagen_url)" :src="p.imagen_url" alt="" class="h-full w-full object-cover" />
          <span v-else class="grid h-full w-full place-items-center text-brand-300">
            <Icon name="cube" :size="18" />
          </span>
          <span class="absolute right-1 top-1 rounded bg-white/90 px-1 text-[9px] font-bold text-slate-600">
            {{ p.stock_disponible }}
          </span>
        </div>
        <div class="flex min-w-0 flex-1 flex-col">
          <p class="line-clamp-2 text-[11px] font-semibold leading-tight text-slate-800">
            {{ p.nombre || '(sin nombre)' }}
          </p>
          <div class="mt-auto flex items-center justify-between pt-1">
            <span class="font-display text-[12px] font-extrabold tabular-nums text-brand-900">
              {{ money(p.precio_base) }}
            </span>
            <span class="grid h-5 w-5 shrink-0 place-items-center rounded bg-brand-100 text-brand-800 group-hover:bg-brand-800 group-hover:text-white">
              <Icon name="plus" :size="12" />
            </span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
