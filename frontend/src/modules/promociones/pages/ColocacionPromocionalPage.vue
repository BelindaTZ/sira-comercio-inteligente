<script setup>
/**
 * Registro de colocación en anaquel destacado / mailer promocional (FR-015) y
 * consulta de su efecto en ventas frente a un periodo de referencia (FR-016), sin
 * atribución causal automática — la lectura la hace el usuario. Arquetipo "Gestión".
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { promocionesApi } from '@/services/promocionesApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'

const sesion = useSesion()
const puedeRegistrar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Marketing_CRM', 'promociones'),
)

function semanaIso(d = new Date()) {
  const fecha = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  const dia = fecha.getUTCDay() || 7
  fecha.setUTCDate(fecha.getUTCDate() + 4 - dia)
  const inicioAnio = new Date(Date.UTC(fecha.getUTCFullYear(), 0, 1))
  return Math.ceil(((fecha - inicioAnio) / 86400000 + 1) / 7)
}

const hoy = new Date()
const colocaciones = ref([])
const tiendas = ref([])
const tiendaFiltro = ref('')
const efectoPorId = reactive({})
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const modal = ref(false)
const guardando = ref(false)
const form = reactive({
  productId: '',
  productLabel: '',
  tiendaId: '',
  displayLocation: '',
  mailerLocation: '',
  semana: semanaIso(hoy),
  anio: hoy.getFullYear(),
})
const buscando = ref(false)
const opciones = ref([])

const kpi = computed(() => {
  const efectos = Object.values(efectoPorId)
  const conMejora = efectos.filter(
    (e) => e.ventas_semana_colocacion > e.ventas_semana_referencia,
  ).length
  return {
    total: colocaciones.value.length,
    anaquel: colocaciones.value.filter((c) => c.display_location).length,
    mailer: colocaciones.value.filter((c) => c.mailer_location).length,
    conMejora,
    medidas: efectos.length,
  }
})

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    colocaciones.value = await promocionesApi.colocaciones({
      tiendaId: tiendaFiltro.value || undefined,
    })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function buscarProducto(q) {
  form.productLabel = q
  form.productId = ''
  if (!q || q.trim().length < 2) {
    opciones.value = []
    return
  }
  buscando.value = true
  try {
    opciones.value = await promocionesApi.buscarProductosColocacion(q.trim())
  } catch {
    opciones.value = []
  } finally {
    buscando.value = false
  }
}

function elegirProducto(p) {
  form.productId = p.product_id
  form.productLabel = `${p.nombre} · #${p.product_id}`
  opciones.value = []
}

function abrirModal() {
  Object.assign(form, {
    productId: '',
    productLabel: '',
    tiendaId: tiendaFiltro.value || (tiendas.value[0]?.tienda_id ?? ''),
    displayLocation: '',
    mailerLocation: '',
    semana: semanaIso(new Date()),
    anio: new Date().getFullYear(),
  })
  opciones.value = []
  modal.value = true
}

async function registrar() {
  if (!form.productId || !form.tiendaId) return
  if (!form.displayLocation && !form.mailerLocation) {
    error.value = 'Indica al menos una ubicación (anaquel o mailer).'
    return
  }
  guardando.value = true
  error.value = ''
  try {
    await promocionesApi.registrarColocacion({
      productId: Number(form.productId),
      tiendaId: Number(form.tiendaId),
      displayLocation: form.displayLocation || null,
      mailerLocation: form.mailerLocation || null,
      semana: Number(form.semana),
      anio: Number(form.anio),
    })
    modal.value = false
    aviso.value = 'Colocación registrada.'
    tiendaFiltro.value = String(form.tiendaId)
    await cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

async function verEfecto(c) {
  try {
    efectoPorId[c.promocion_id] = await promocionesApi.efectoColocacion(c.promocion_id)
  } catch (e) {
    error.value = e.message
  }
}

onMounted(async () => {
  tiendas.value = await promocionesApi.tiendasColocacion().catch(() => [])
  await cargar()
})
</script>

<template>
  <div class="mx-auto max-w-[1200px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Colocación promocional"
      subtitulo="Registro de producto en anaquel destacado o mailer, y su efecto en unidades vendidas frente a la semana anterior — sin atribución causal automática (FR-015 / FR-016)."
    >
      <template #badge>
        <SemanticChip tipo="neutral">{{ kpi.total }} colocaciones</SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeRegistrar" variant="primary" @click="abrirModal">
          <Icon name="plus" :size="15" /> Registrar colocación
        </Btn>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-4 flex items-center justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      <span>{{ aviso }}</span>
      <button class="text-brand-600 hover:text-brand-900" @click="aviso = ''"><Icon name="x" :size="14" /></button>
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile label="Colocaciones registradas" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" />
      <KpiTile label="En anaquel destacado" :valor="kpi.anaquel.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="cube" :size="16" /></template>
      </KpiTile>
      <KpiTile label="En mailer" :valor="kpi.mailer.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="megaphone" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Con más ventas que la semana previa"
        :valor="kpi.medidas ? `${kpi.conMejora} / ${kpi.medidas}` : '—'"
        microcopy="de las colocaciones ya medidas"
        :estado-tipo="kpi.conMejora > 0 ? 'ok' : 'neutral'"
      />
    </section>

    <div class="mb-4 flex items-center gap-2">
      <label class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600">
        <Icon name="pin" :size="14" class="text-brand-700" />
        <select v-model="tiendaFiltro" class="bg-transparent text-slate-800 focus:outline-none" @change="cargar">
          <option value="">Todas las tiendas</option>
          <option v-for="t in tiendas" :key="t.tienda_id" :value="t.tienda_id">{{ t.nombre }}</option>
        </select>
      </label>
    </div>

    <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
      <table class="w-full text-left text-[13px]">
        <thead>
          <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
            <th class="px-5 py-3">Producto</th>
            <th class="px-4 py-3">Anaquel / Mailer</th>
            <th class="px-4 py-3">Semana</th>
            <th class="px-4 py-3">Efecto (colocación vs. semana previa)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-brand-100/90 bg-white/80">
          <tr v-if="cargando"><td colspan="4" class="px-5 py-8 text-center text-slate-400">Cargando…</td></tr>
          <tr v-else-if="!colocaciones.length"><td colspan="4" class="px-5 py-8 text-center text-slate-400">Sin colocaciones registradas.</td></tr>
          <tr v-for="c in colocaciones" :key="c.promocion_id" class="hover:bg-brand-50/70">
            <td class="px-5 py-3">
              <div class="font-semibold text-slate-800">{{ c.product_nombre || `Producto #${c.product_id}` }}</div>
              <div class="font-mono text-[11px] text-slate-400">
                #{{ c.product_id }}<template v-if="c.product_category"> · {{ c.product_category }}</template>
              </div>
            </td>
            <td class="px-4 py-3 text-slate-600">
              {{ c.display_location || '—' }} / {{ c.mailer_location || '—' }}
            </td>
            <td class="px-4 py-3 tabular-nums text-slate-600">{{ c.anio }}-S{{ c.semana }}</td>
            <td class="px-4 py-3">
              <template v-if="efectoPorId[c.promocion_id]">
                <span class="font-semibold tabular-nums text-slate-800">
                  {{ efectoPorId[c.promocion_id].ventas_semana_colocacion }} uds
                </span>
                <span class="text-slate-500">
                  vs. {{ efectoPorId[c.promocion_id].ventas_semana_referencia }} uds la semana previa
                </span>
              </template>
              <Btn v-else variant="ghost" class="!px-2.5 !py-1 !text-[12px]" @click="verEfecto(c)">
                Ver efecto
              </Btn>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-if="modal" titulo="Registrar colocación promocional" @cerrar="modal = false">
      <form class="space-y-3" @submit.prevent="registrar">
        <label class="block text-[12px] font-semibold text-slate-600">
          Producto
          <input
            :value="form.productLabel"
            placeholder="Buscá por nombre o id…"
            autocomplete="off"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            @input="buscarProducto($event.target.value)"
          />
        </label>
        <ul v-if="opciones.length" class="max-h-44 divide-y divide-brand-100 overflow-y-auto rounded-lg border border-brand-200">
          <li
            v-for="p in opciones"
            :key="p.product_id"
            class="cursor-pointer px-3 py-1.5 text-[12px] hover:bg-brand-50"
            @click="elegirProducto(p)"
          >
            <span class="font-semibold text-slate-800">{{ p.nombre }}</span>
            <span class="font-mono text-slate-400"> · #{{ p.product_id }}</span>
          </li>
        </ul>
        <p v-else-if="buscando" class="text-[11px] text-slate-400">Buscando…</p>

        <label class="block text-[12px] font-semibold text-slate-600">
          Tienda
          <select v-model="form.tiendaId" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
            <option value="" disabled>Elegí una tienda…</option>
            <option v-for="t in tiendas" :key="t.tienda_id" :value="t.tienda_id">{{ t.nombre }}</option>
          </select>
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="block text-[12px] font-semibold text-slate-600">
            Ubicación anaquel (código)
            <input v-model="form.displayLocation" maxlength="2" placeholder="p. ej. A1" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Ubicación mailer (código)
            <input v-model="form.mailerLocation" maxlength="2" placeholder="p. ej. M2" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Semana
            <input v-model.number="form.semana" type="number" min="1" max="53" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Año
            <input v-model.number="form.anio" type="number" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
        </div>
        <p class="text-[11px] text-slate-500">Indicá al menos una ubicación (anaquel o mailer).</p>

        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = false">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando || !form.productId">
            {{ guardando ? 'Registrando…' : 'Registrar' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
