<script setup>
/**
 * Crear campaña de reactivación (US5, FR-016). Estructura de
 * `docs/diseno-ui/.../sira_crear_nueva_campa_a_de_cupones_omnicanal/`:
 * nombre + vigencia + segmento objetivo + proyección de alcance.
 *
 * Alcance real: la campaña de reactivación envía el cupón VIP de recuperación
 * (producto ancla, `seleccionar_producto_ancla` en el backend) — el tipo de
 * beneficio no es configurable (fuera de spec). El backend resuelve el segmento
 * a household_id y hace el split 80/20 tratado/control (FR-017).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  segmentoInicial: { type: String, default: '' },
})
const emit = defineEmits(['creada'])

const hoy = new Date().toISOString().slice(0, 10)
const en30 = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10)

const form = reactive({
  nombre: 'Reactivación gourmet — cupón VIP de recuperación',
  startDate: hoy,
  endDate: en30,
  segmento: props.segmentoInicial || '',
})
const segmentos = ref([])
const guardando = ref(false)
const error = ref('')
const ok = ref('')

const segSel = computed(() => segmentos.value.find((s) => s.clave === form.segmento) || null)
const control = computed(() => (segSel.value ? Math.max(1, Math.round(segSel.value.miembros * 0.2)) : 0))
const tratado = computed(() => (segSel.value ? segSel.value.miembros - control.value : 0))

onMounted(async () => {
  try {
    segmentos.value = await clientesApi.segmentosRiesgo()
    if (!form.segmento && segmentos.value.length) form.segmento = segmentos.value[0].clave
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message
  }
})

async function guardar() {
  error.value = ''
  ok.value = ''
  guardando.value = true
  try {
    const campana = await clientesApi.crearCampana({
      nombre: form.nombre,
      startDate: form.startDate,
      endDate: form.endDate,
      segmento: form.segmento,
    })
    ok.value = `Campaña #${campana.campaign_id} creada con ${campana.miembros.length} miembros.`
    emit('creada', campana)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.response?.data?.detail || e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="guardar">
    <!-- Paso 1: parámetros generales -->
    <section class="space-y-3">
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-brand-700" />
        <h3 class="font-display text-[14px] font-bold text-brand-950">1 · Parámetros de la campaña</h3>
      </div>
      <label class="block text-[12px] font-semibold text-slate-600">
        Nombre de la campaña
        <input
          v-model="form.nombre"
          type="text"
          maxlength="120"
          required
          class="mt-1 h-10 w-full rounded-xl border border-brand-300 bg-white px-3 text-[13px] text-slate-800 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="block text-[12px] font-semibold text-slate-600">
          Inicio
          <input v-model="form.startDate" type="date" class="mt-1 h-10 w-full rounded-xl border border-brand-300 bg-white px-3 text-[13px]" />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Fin
          <input v-model="form.endDate" type="date" class="mt-1 h-10 w-full rounded-xl border border-brand-300 bg-white px-3 text-[13px]" />
        </label>
      </div>
      <div class="flex items-start gap-2.5 rounded-xl border border-amethyst-200 bg-amethyst-50/60 p-3">
        <Icon name="tag" :size="16" class="mt-0.5 text-amethyst-700" />
        <p class="text-[11px] leading-relaxed text-slate-600">
          <strong class="text-amethyst-900">Beneficio:</strong> cupón VIP de recuperación sobre el
          producto ancla de cada cliente, redimible en caja al digitar el RUT. El tipo de descuento
          es fijo (política del Club).
        </p>
      </div>
    </section>

    <!-- Paso 2: segmento -->
    <section class="space-y-3 border-t border-brand-100 pt-4">
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-amethyst-500" />
        <h3 class="font-display text-[14px] font-bold text-brand-950">2 · Segmento objetivo</h3>
      </div>
      <label
        v-for="s in segmentos"
        :key="s.clave"
        class="flex cursor-pointer items-start gap-3 rounded-xl border-2 p-3 transition"
        :class="form.segmento === s.clave ? 'border-brand-600 bg-brand-50' : 'border-brand-200 hover:bg-brand-50/60'"
      >
        <input v-model="form.segmento" :value="s.clave" type="radio" name="segmento" class="mt-1" />
        <div class="flex-1">
          <div class="flex items-center justify-between">
            <span class="text-[13px] font-bold text-slate-900">{{ s.nombre }}</span>
            <span class="rounded-full bg-brand-800 px-2 py-0.5 text-[10px] font-bold text-white tabular-nums">
              {{ s.miembros.toLocaleString('es-CL') }} miembros
            </span>
          </div>
          <p class="text-[11px] leading-tight text-slate-500">{{ s.descripcion }}</p>
        </div>
      </label>

      <div
        v-if="segSel"
        class="rounded-xl border border-emerald-600/20 bg-emerald-500/[0.06] p-3"
      >
        <p class="flex items-center gap-1.5 text-[11px] font-bold text-emerald-900">
          <Icon name="chart" :size="13" /> Proyección de alcance
        </p>
        <p class="mt-1 text-[11px] text-emerald-950">
          <strong>{{ tratado.toLocaleString('es-CL') }}</strong> clientes reciben el cupón ·
          <strong>{{ control.toLocaleString('es-CL') }}</strong> en grupo de control (para medir el
          uplift real al cierre, FR-018).
        </p>
      </div>
    </section>

    <p v-if="error" class="rounded-lg bg-rose-50 px-3 py-2 text-[12px] text-crimson-ruby">{{ error }}</p>
    <p v-if="ok" class="rounded-lg bg-emerald-50 px-3 py-2 text-[12px] text-emerald-800">{{ ok }}</p>

    <button
      type="submit"
      :disabled="guardando || !form.segmento || !segSel || segSel.miembros < 2"
      class="inline-flex w-full items-center justify-center gap-1.5 rounded-xl border border-brand-600 bg-brand-800 px-4 py-2.5 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-40"
    >
      <Icon name="bolt" :size="16" />
      {{ guardando ? 'Creando…' : `Crear campaña de reactivación` }}
    </button>
  </form>
</template>
