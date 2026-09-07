<script setup>
/**
 * Búsqueda de producto para agregar a la venta (FR-001).
 * Tres vías (research.md #8):
 *  - Lector físico USB/Bluetooth (keyboard-wedge): escribe los dígitos + Enter.
 *  - Cámara: BarcodeDetector nativo del navegador donde exista.
 *  - Manual: se escribe el código o el product_id y se pulsa Enter.
 */
import { onBeforeUnmount, ref } from 'vue'

const emit = defineEmits(['agregar'])

const entrada = ref('')
const cantidad = ref(1)
const escaneando = ref(false)
const soporteCamara = typeof window !== 'undefined' && 'BarcodeDetector' in window
let stream = null
let rafId = null

function enviar() {
  const valor = entrada.value.trim()
  if (!valor) return
  const esNumeroPuro = /^\d+$/.test(valor)
  // Un EAN suele tener 8/12/13 dígitos; menos que eso lo tratamos como product_id.
  const pareceBarcode = esNumeroPuro && valor.length >= 6
  emit('agregar', {
    codigoBarras: pareceBarcode || !esNumeroPuro ? valor : null,
    productId: !pareceBarcode && esNumeroPuro ? Number(valor) : null,
    cantidad: Math.max(1, Number(cantidad.value) || 1),
  })
  entrada.value = ''
  cantidad.value = 1
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
          enviar()
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
</script>

<template>
  <div class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
    <form class="flex flex-wrap items-end gap-3" @submit.prevent="enviar">
      <label class="flex-1">
        <span class="mb-1 block text-xs font-medium text-on-surface-variant">
          Código de barras o ID de producto
        </span>
        <input
          v-model="entrada"
          autofocus
          inputmode="text"
          placeholder="Escanea o escribe y pulsa Enter"
          class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface outline-none focus:border-primary-container"
        />
      </label>
      <label class="w-24">
        <span class="mb-1 block text-xs font-medium text-on-surface-variant">Cant.</span>
        <input
          v-model.number="cantidad"
          type="number"
          min="1"
          class="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-on-surface outline-none focus:border-primary-container"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Agregar
      </button>
      <button
        v-if="soporteCamara"
        type="button"
        class="rounded-lg border border-outline-variant px-3 py-2 text-sm font-medium text-on-surface"
        @click="toggleCamara"
      >
        {{ escaneando ? 'Detener cámara' : 'Escanear con cámara' }}
      </button>
    </form>
    <video v-show="escaneando" id="pos-camara" class="mt-3 w-full max-w-sm rounded-lg" muted />
  </div>
</template>
