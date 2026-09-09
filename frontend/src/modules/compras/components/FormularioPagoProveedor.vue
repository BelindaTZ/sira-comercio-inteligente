<script setup>
/**
 * Autorización de pago a proveedor (FR-034, T073). Control de doble persona
 * entre pasos separados: quien usa este formulario es el AUTORIZADOR (su sesión
 * firma la operación); indica además el empleado que registró el pago en el paso
 * previo, que debe ser distinto de él. El backend rechaza (403) si el autorizador
 * no coincide con el usuario autenticado o si registra == autoriza.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { comprasApi } from '@/services/comprasApi'
import { cajaApi } from '@/services/cajaApi'
import { money } from '@/shared/currency'
import Btn from '@/shared/ui/Btn.vue'

const props = defineProps({
  // Empleado en sesión = autorizador del pago.
  empleadoAutorizaId: { type: Number, required: true },
})
const emit = defineEmits(['pagado'])

const MEDIOS = [
  { id: 1, t: 'Efectivo' },
  { id: 3, t: 'Transferencia' },
  { id: 2, t: 'Tarjeta' },
  { id: 4, t: 'Billetera digital' },
]

const form = reactive({
  facturaId: null,
  monto: '',
  medioPagoId: 3,
  referencia: '',
  empleadoRegistraId: null,
})
const facturas = ref([])
const empleados = ref([])
const error = ref('')
const aviso = ref('')
const enviando = ref(false)

onMounted(async () => {
  const [pag, emp] = await Promise.all([
    comprasApi.facturas().then((p) => p.items ?? p).catch(() => []),
    cajaApi.empleados().catch(() => []),
  ])
  facturas.value = (pag || []).filter((f) => Number(f.saldo) > 0)
  empleados.value = (emp || []).filter((e) => e.empleado_id !== props.empleadoAutorizaId)
})

const facturaSel = computed(() =>
  facturas.value.find((f) => f.factura_id === Number(form.facturaId)),
)

async function enviar() {
  error.value = ''
  aviso.value = ''
  enviando.value = true
  try {
    const pago = await comprasApi.registrarPago(Number(form.facturaId), {
      monto: form.monto,
      medioPagoId: Number(form.medioPagoId),
      referencia: form.referencia,
      empleadoRegistraId: Number(form.empleadoRegistraId),
      empleadoAutorizaId: props.empleadoAutorizaId,
    })
    aviso.value = 'Pago autorizado y registrado.'
    Object.assign(form, {
      facturaId: null,
      monto: '',
      referencia: '',
      empleadoRegistraId: null,
    })
    emit('pagado', pago)
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
    <h3 class="text-[13px] font-bold text-brand-950">Autorizar pago a proveedor</h3>
    <p class="text-[11px] text-slate-500">
      Autorizás con tu propia sesión. Quien registró el pago (paso previo) debe ser otra persona.
    </p>

    <label class="block text-[12px] font-semibold text-slate-600">
      Factura con saldo
      <select v-model.number="form.facturaId" required :class="inputClass">
        <option :value="null" disabled>Elegí una factura…</option>
        <option v-for="f in facturas" :key="f.factura_id" :value="f.factura_id">
          {{ f.numero_factura }} · OC-{{ String(f.orden_id).padStart(4, '0') }} · saldo {{ money(f.saldo) }}
        </option>
      </select>
      <span v-if="!facturas.length" class="mt-1 block text-[11px] text-slate-400">
        No hay facturas con saldo pendiente.
      </span>
    </label>

    <div class="grid grid-cols-2 gap-3">
      <label class="block text-[12px] font-semibold text-slate-600">
        Monto
        <input
          v-model="form.monto"
          type="number"
          step="0.01"
          :max="facturaSel ? Number(facturaSel.saldo) : undefined"
          required
          :class="inputClass"
        />
      </label>
      <label class="block text-[12px] font-semibold text-slate-600">
        Medio de pago
        <select v-model.number="form.medioPagoId" :class="inputClass">
          <option v-for="m in MEDIOS" :key="m.id" :value="m.id">{{ m.t }}</option>
        </select>
      </label>
    </div>

    <label class="block text-[12px] font-semibold text-slate-600">
      Referencia (opcional)
      <input v-model="form.referencia" :class="inputClass" />
    </label>

    <label class="block text-[12px] font-semibold text-slate-600">
      Empleado que registró el pago (paso previo, distinto de vos)
      <select v-model.number="form.empleadoRegistraId" required :class="inputClass">
        <option :value="null" disabled>Elegí un empleado…</option>
        <option v-for="e in empleados" :key="e.empleado_id" :value="e.empleado_id">
          {{ e.nombre }}
        </option>
      </select>
    </label>

    <p v-if="aviso" class="rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-sm text-brand-800">
      {{ aviso }}
    </p>
    <p v-if="error" class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-crimson-ruby">{{ error }}</p>
    <div class="flex justify-end">
      <Btn
        variant="primary"
        type="submit"
        :disabled="enviando || !form.facturaId || !form.empleadoRegistraId"
      >
        {{ enviando ? 'Registrando…' : 'Autorizar y registrar pago' }}
      </Btn>
    </div>
  </form>
</template>
