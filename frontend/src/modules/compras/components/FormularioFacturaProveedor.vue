<script setup>
/** Registro de factura de proveedor (FR-033). Requiere una orden en estado 'recibida'. */
import { onMounted, reactive, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'
import { money } from '@/shared/currency'
import Btn from '@/shared/ui/Btn.vue'

const props = defineProps({ empleadoId: { type: Number, required: true } })
const emit = defineEmits(['registrada'])

const form = reactive({
  ordenId: null,
  numeroFactura: '',
  montoTotal: '',
  fechaEmision: '',
  fechaVencimiento: '',
})
const ordenes = ref([])
const error = ref('')
const aviso = ref('')
const enviando = ref(false)

onMounted(async () => {
  ordenes.value = await comprasApi.ordenesFacturables().catch(() => [])
})

async function enviar() {
  error.value = ''
  aviso.value = ''
  enviando.value = true
  try {
    const factura = await comprasApi.crearFactura({
      ordenId: Number(form.ordenId),
      numeroFactura: form.numeroFactura,
      montoTotal: form.montoTotal,
      fechaEmision: form.fechaEmision,
      fechaVencimiento: form.fechaVencimiento,
      empleadoRegistraId: props.empleadoId,
    })
    aviso.value = `Factura ${factura.numero_factura} registrada.`
    Object.assign(form, {
      ordenId: null,
      numeroFactura: '',
      montoTotal: '',
      fechaEmision: '',
      fechaVencimiento: '',
    })
    emit('registrada', factura)
  } catch (e) {
    error.value = e.message
  } finally {
    enviando.value = false
  }
}

const inputClass =
  'mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none'
</script>

<template>
  <form class="space-y-3 rounded-xl border border-brand-200 bg-white p-4" @submit.prevent="enviar">
    <h3 class="text-[13px] font-bold text-brand-950">Registrar factura de proveedor</h3>
    <label class="block text-[12px] font-semibold text-slate-600">
      Orden recibida
      <select v-model.number="form.ordenId" required :class="inputClass">
        <option :value="null" disabled>Elegí una orden…</option>
        <option v-for="o in ordenes" :key="o.orden_id" :value="o.orden_id">
          OC-{{ String(o.orden_id).padStart(4, '0') }} · {{ o.proveedor_nombre || `Proveedor ${o.proveedor_id}` }} · {{ money(o.total_neto) }}
        </option>
      </select>
      <span v-if="!ordenes.length" class="mt-1 block text-[11px] text-slate-400">
        No hay órdenes en estado «recibida».
      </span>
    </label>
    <label class="block text-[12px] font-semibold text-slate-600">
      Número de factura
      <input v-model="form.numeroFactura" required :class="inputClass" />
    </label>
    <label class="block text-[12px] font-semibold text-slate-600">
      Monto total
      <input v-model="form.montoTotal" type="number" step="0.01" required :class="inputClass" />
    </label>
    <div class="grid grid-cols-2 gap-3">
      <label class="block text-[12px] font-semibold text-slate-600">
        Emisión
        <input v-model="form.fechaEmision" type="date" required :class="inputClass" />
      </label>
      <label class="block text-[12px] font-semibold text-slate-600">
        Vencimiento
        <input v-model="form.fechaVencimiento" type="date" required :class="inputClass" />
      </label>
    </div>
    <p v-if="aviso" class="rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-sm text-brand-800">
      {{ aviso }}
    </p>
    <p v-if="error" class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-crimson-ruby">{{ error }}</p>
    <div class="flex justify-end">
      <Btn variant="primary" type="submit" :disabled="enviando || !form.ordenId">
        {{ enviando ? 'Registrando…' : 'Registrar factura' }}
      </Btn>
    </div>
  </form>
</template>
