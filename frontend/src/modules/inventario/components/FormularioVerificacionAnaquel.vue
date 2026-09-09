<script setup>
/**
 * Auditoría de anaquel y planograma en góndola (FR-042, Reponedor / Encargado).
 * Estructura de `docs/diseno-ui/.../sira_verificar_y_auditar_anaquel_en_g_ndola/`:
 * sesión multi-SKU de clase A → resumen de facing (3 tarjetas) + matriz de
 * comprobación por SKU (facing asignado vs real, ESL, FIFO) + observaciones.
 *
 * Al finalizar se hace un POST `verificacion-anaquel` por cada SKU de la lista;
 * el backend rechaza productos que no sean clasificación A.
 */
import { computed, reactive, ref } from 'vue'
import { inventarioApi } from '@/services/inventarioApi'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  tiendaId: { type: Number, required: true },
  empleadoId: { type: Number, required: true },
})
const emit = defineEmits(['registrada', 'cerrar'])

const skus = ref([]) // filas en revisión
const picker = ref(null)
const observaciones = ref('')
const aviso = ref('')
const error = ref('')
const enviando = ref(false)
const reponiendo = reactive({})

function onSku(row) {
  aviso.value = ''
  if (!row?.product_id) return
  if (skus.value.some((s) => s.product_id === row.product_id)) {
    aviso.value = 'Ese SKU ya está en la matriz.'
  } else if ((row.clasificacion_abc || '').toUpperCase() !== 'A') {
    aviso.value = 'Sólo se audita anaquel de productos clasificación A (alta rotación).'
  } else {
    skus.value.push({
      product_id: row.product_id,
      nombre: row.nombre || `SKU ${row.product_id}`,
      marca: row.marca,
      categoria: row.product_category,
      disponible: (row.cantidad_disponible ?? 0) > 0,
      facingAsignado: 3,
      facingReal: 3,
      eslOk: true,
      fifoOk: true,
    })
  }
  picker.value = null
}

function quitar(id) {
  skus.value = skus.value.filter((s) => s.product_id !== id)
}

const total = computed(() => skus.value.length)
const conformes = computed(
  () => skus.value.filter((s) => s.facingReal >= s.facingAsignado && s.disponible).length,
)
const planogramaPct = computed(() =>
  total.value ? Math.round((conformes.value / total.value) * 100) : 0,
)
const quiebres = computed(
  () => skus.value.filter((s) => !s.disponible || s.facingReal < s.facingAsignado).length,
)
const eslPct = computed(() =>
  total.value ? Math.round((skus.value.filter((s) => s.eslOk).length / total.value) * 100) : 0,
)

function diagnostico(s) {
  if (!s.disponible || s.facingReal < s.facingAsignado)
    return { t: 'Quiebre visual', cls: 'bg-rose-50 text-crimson-ruby border-rose-200', repo: true }
  if (!s.fifoOk)
    return { t: 'Advertencia FIFO', cls: 'bg-amber-50 text-amber-800 border-amber-300', repo: false }
  if (!s.eslOk)
    return { t: 'ESL desincronizado', cls: 'bg-amber-50 text-amber-800 border-amber-300', repo: false }
  return { t: 'Conforme', cls: 'bg-emerald-50 text-emerald-800 border-emerald-200', repo: false }
}

async function solicitarReposicion(s) {
  reponiendo[s.product_id] = 'enviando'
  try {
    await inventarioApi.solicitarReposicion({
      productId: s.product_id,
      tiendaId: props.tiendaId,
      empleadoId: props.empleadoId,
    })
    reponiendo[s.product_id] = 'ok'
  } catch {
    reponiendo[s.product_id] = 'error'
  }
}

async function finalizar() {
  error.value = ''
  enviando.value = true
  try {
    for (const s of skus.value) {
      await inventarioApi.verificacionAnaquel({
        productId: s.product_id,
        tiendaId: props.tiendaId,
        disponible: s.disponible,
        empleadoId: props.empleadoId,
        facingAsignado: Number(s.facingAsignado),
        facingReal: Number(s.facingReal),
        eslOk: s.eslOk,
        fifoOk: s.fifoOk,
        observaciones: observaciones.value || null,
      })
    }
    emit('registrada', { auditados: skus.value.length })
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- Resumen: 3 tarjetas -->
    <div class="grid gap-3 md:grid-cols-3">
      <div class="rounded-xl border border-brand-200 bg-white p-3">
        <div class="flex items-center justify-between text-[11px] font-bold uppercase text-slate-500">
          Planograma conforme <Icon name="check" :size="16" class="text-emerald-700" />
        </div>
        <div class="mt-1 flex items-baseline gap-2">
          <span class="font-display text-[26px] font-extrabold tabular-nums text-brand-900">
            {{ planogramaPct }}%
          </span>
          <span
            class="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700"
          >
            {{ conformes }} de {{ total || 0 }} facings
          </span>
        </div>
        <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div class="h-full rounded-full bg-brand-700" :style="{ width: planogramaPct + '%' }" />
        </div>
      </div>

      <div class="rounded-xl border border-rose-200 bg-white p-3">
        <div class="flex items-center justify-between text-[11px] font-bold uppercase text-slate-500">
          Quiebres visuales (gaps) <Icon name="alert" :size="16" class="text-crimson-ruby" />
        </div>
        <div class="mt-1 flex items-baseline gap-2">
          <span class="font-display text-[26px] font-extrabold tabular-nums text-crimson-ruby">
            {{ quiebres }}
          </span>
          <span
            v-if="quiebres"
            class="rounded border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold text-crimson-ruby"
          >
            Acción requerida
          </span>
        </div>
        <p class="mt-1 text-[11px] text-slate-500">Espacios sin producto en primera línea.</p>
      </div>

      <div class="rounded-xl border border-brand-200 bg-white p-3">
        <div class="flex items-center justify-between text-[11px] font-bold uppercase text-slate-500">
          Sincronización ESL <Icon name="wifi" :size="16" class="text-emerald-700" />
        </div>
        <div class="mt-1 flex items-baseline gap-2">
          <span class="font-display text-[26px] font-extrabold tabular-nums text-brand-900">
            {{ eslPct }}%
          </span>
          <span
            class="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700"
          >
            Etiquetas digitales OK
          </span>
        </div>
        <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div class="h-full rounded-full bg-emerald-600" :style="{ width: eslPct + '%' }" />
        </div>
      </div>
    </div>

    <!-- Alta de SKU -->
    <div class="rounded-xl border border-brand-200 bg-brand-50/40 p-3">
      <p class="mb-1.5 text-[12px] font-semibold text-slate-700">
        Agregar SKU clase A a la matriz de comprobación
      </p>
      <ProductoPicker
        v-model="picker"
        :tienda-id="tiendaId"
        placeholder="Buscá por nombre o código…"
        @seleccionado="onSku"
      />
      <p v-if="aviso" class="mt-1 text-[11px] text-amber-700">{{ aviso }}</p>
    </div>

    <!-- Matriz por SKU -->
    <div class="overflow-x-auto rounded-xl border border-brand-200">
      <table class="w-full text-left text-[12px]">
        <thead>
          <tr class="bg-brand-50 text-[10px] font-bold uppercase tracking-wide text-slate-500">
            <th class="px-3 py-2">SKU &amp; producto</th>
            <th class="px-3 py-2 text-center">Planograma / facing</th>
            <th class="px-3 py-2 text-center">Precio ESL</th>
            <th class="px-3 py-2 text-center">Rotación / lote FIFO</th>
            <th class="px-3 py-2 text-right">Diagnóstico &amp; acciones</th>
            <th class="w-8 px-1 py-2"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100">
          <tr v-if="!skus.length">
            <td colspan="6" class="px-3 py-6 text-center text-[12px] text-slate-400">
              Todavía no agregaste SKUs. Buscá arriba los productos de alta rotación de la góndola.
            </td>
          </tr>
          <tr v-for="s in skus" :key="s.product_id" class="align-top">
            <td class="px-3 py-3">
              <div class="font-semibold text-slate-800">{{ s.nombre }}</div>
              <div class="mt-0.5 text-[10px] text-slate-400">
                #{{ s.product_id }}<span v-if="s.marca"> · {{ s.marca }}</span>
                <span v-if="s.categoria"> · {{ s.categoria }}</span>
              </div>
              <label class="mt-1 inline-flex items-center gap-1.5 text-[11px] text-slate-600">
                <input v-model="s.disponible" type="checkbox" class="accent-brand-700" />
                Disponible en primera línea
              </label>
            </td>
            <td class="px-3 py-3">
              <div class="flex items-center justify-center gap-2">
                <label class="text-[10px] text-slate-500">
                  Asig
                  <input
                    v-model.number="s.facingAsignado"
                    type="number"
                    min="0"
                    class="ml-1 w-12 rounded border border-brand-200 py-0.5 text-center tabular-nums"
                  />
                </label>
                <label class="text-[10px] text-slate-500">
                  Real
                  <input
                    v-model.number="s.facingReal"
                    type="number"
                    min="0"
                    class="ml-1 w-12 rounded border border-brand-200 py-0.5 text-center tabular-nums"
                    :class="s.facingReal < s.facingAsignado ? 'text-crimson-ruby' : ''"
                  />
                </label>
              </div>
              <div class="mt-1.5 flex items-center justify-center gap-0.5">
                <span
                  v-for="i in Math.max(s.facingAsignado, s.facingReal, 1)"
                  :key="i"
                  class="inline-block h-3 w-2.5 rounded-[2px]"
                  :class="
                    i <= s.facingReal
                      ? s.facingReal >= s.facingAsignado
                        ? 'bg-emerald-600'
                        : 'bg-amber-500'
                      : 'border border-dashed border-rose-400 bg-rose-100'
                  "
                />
              </div>
            </td>
            <td class="px-3 py-3 text-center">
              <label class="inline-flex items-center gap-1.5 text-[11px]">
                <input v-model="s.eslOk" type="checkbox" class="accent-brand-700" />
                <span :class="s.eslOk ? 'text-emerald-700' : 'text-amber-700'">
                  {{ s.eslOk ? 'Sincronizado POS' : 'Revisar etiqueta' }}
                </span>
              </label>
            </td>
            <td class="px-3 py-3 text-center">
              <label class="inline-flex items-center gap-1.5 text-[11px]">
                <input v-model="s.fifoOk" type="checkbox" class="accent-brand-700" />
                <span :class="s.fifoOk ? 'text-emerald-700' : 'text-amber-700'">
                  {{ s.fifoOk ? 'FIFO correcto (frente)' : 'Lote antiguo al fondo' }}
                </span>
              </label>
            </td>
            <td class="px-3 py-3 text-right">
              <span
                class="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-semibold"
                :class="diagnostico(s).cls"
              >
                {{ diagnostico(s).t }}
              </span>
              <div v-if="diagnostico(s).repo" class="mt-1.5">
                <button
                  type="button"
                  :disabled="reponiendo[s.product_id] === 'enviando'"
                  class="inline-flex items-center gap-1 rounded-lg bg-amethyst-600 px-2.5 py-1 text-[10px] font-bold text-white hover:bg-amethyst-500 disabled:opacity-50"
                  @click="solicitarReposicion(s)"
                >
                  <Icon name="bolt" :size="13" />
                  {{
                    reponiendo[s.product_id] === 'ok'
                      ? 'Reposición solicitada'
                      : reponiendo[s.product_id] === 'error'
                        ? 'Reintentar solicitud'
                        : 'Solicitar reposición inmediata'
                  }}
                </button>
              </div>
            </td>
            <td class="px-1 py-3 text-center">
              <button
                type="button"
                class="text-slate-300 hover:text-crimson-ruby"
                title="Quitar de la matriz"
                @click="quitar(s.product_id)"
              >
                <Icon name="x" :size="15" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Observaciones -->
    <div>
      <label class="mb-1 block text-[12px] font-semibold text-slate-700">
        Observaciones del operador de sala
      </label>
      <textarea
        v-model="observaciones"
        rows="2"
        maxlength="300"
        placeholder="Incidencias detectadas en la góndola (producto intruso, daño, planograma desactualizado…)"
        class="w-full resize-none rounded-lg border border-brand-200 p-2.5 text-[13px] outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/15"
      />
      <p class="mt-0.5 text-right text-[10px] text-slate-400">
        {{ observaciones.length }} / 300 caracteres
      </p>
    </div>

    <p v-if="error" class="text-[12px] text-crimson-ruby">{{ error }}</p>

    <div class="flex items-center justify-end gap-2.5">
      <button
        type="button"
        class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
        @click="emit('cerrar')"
      >
        Cancelar
      </button>
      <button
        type="button"
        :disabled="!skus.length || enviando"
        class="inline-flex items-center gap-1.5 rounded-xl border border-brand-600 bg-brand-800 px-4 py-2 text-[13px] font-bold text-white hover:bg-brand-700 disabled:opacity-40"
        @click="finalizar"
      >
        <Icon name="check" :size="16" />
        {{ enviando ? 'Validando…' : 'Finalizar y validar auditoría' }}
      </button>
    </div>
  </div>
</template>
