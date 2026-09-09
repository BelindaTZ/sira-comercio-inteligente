<script setup>
/**
 * FR-014/FR-015/FR-016 — competidores nombrados, captura manual de precio de
 * referencia y alertas de desviación (job semanal). Arquetipo "Gestión" del kit.
 * La captura la hace el Jefe Comercial; el resto (incl. Gerencia) consulta.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { pricingApi } from '@/services/pricingApi'
import { useSesion } from '@/stores/sesion'
import { money as moneyUsd } from '@/shared/currency'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const puedeRegistrar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Comercial', 'precio_competencia'),
)

const money = (v) => moneyUsd(v, { showCode: false })
const competidores = ref([])
const alertas = ref([])
const error = ref('')
const aviso = ref('')
const cargando = ref(false)
const page = ref(1)
const size = ref(15)

const modal = ref(null) // 'competidor' | 'precio' | null
const nuevoCompetidor = reactive({ nombre: '', tipo: 'supermercado', ciudad: '' })
const captura = reactive({ productId: '', competidorId: '', precio: '', esPromocional: false })

const kpi = computed(() => {
  const peor = [...alertas.value].sort(
    (a, b) => Math.abs(b.desviacion_pct) - Math.abs(a.desviacion_pct),
  )[0]
  return {
    alertas: alertas.value.length,
    competidores: competidores.value.length,
    peorPct: peor ? peor.desviacion_pct : null,
    peorProducto: peor ? peor.product_id : null,
  }
})

const columnas = [
  { key: 'producto', label: 'Producto' },
  { key: 'propio', label: 'Precio propio', align: 'right', width: '130px' },
  { key: 'competencia', label: 'Competencia', align: 'right', width: '130px' },
  { key: 'fuente', label: 'Fuente', width: '150px' },
  { key: 'desviacion', label: 'Desviación', align: 'right', width: '120px' },
]
const pagina = computed(() =>
  alertas.value.slice((page.value - 1) * size.value, page.value * size.value),
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    competidores.value = await pricingApi.competidores()
    alertas.value = (await pricingApi.alertasCompetencia()).items
    page.value = 1
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
    Object.assign(nuevoCompetidor, { nombre: '', tipo: 'supermercado', ciudad: '' })
    modal.value = null
    aviso.value = 'Competidor agregado.'
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
    Object.assign(captura, { productId: '', competidorId: '', precio: '', esPromocional: false })
    modal.value = null
    aviso.value = 'Precio de competencia registrado.'
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Precio de competencia"
      subtitulo="Precios de referencia capturados frente a competidores nombrados y desviaciones que superan el umbral (job semanal, FR-014 a FR-016)."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.alertas > 0 ? 'quiebre' : 'ok'">
          {{ kpi.alertas > 0 ? `${kpi.alertas} desviaciones activas` : 'Sin desviaciones' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn variant="ghost" @click="$router.push('/pricing')">
          <Icon name="chevron" :size="14" class="rotate-90" /> Márgenes
        </Btn>
        <template v-if="puedeRegistrar">
          <Btn variant="ghost" @click="modal = 'competidor'">
            <Icon name="plus" :size="15" /> Competidor
          </Btn>
          <Btn variant="primary" @click="modal = 'precio'">
            <Icon name="tag" :size="15" /> Registrar precio
          </Btn>
        </template>
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

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <KpiTile
        label="Desviaciones sobre el umbral"
        :valor="kpi.alertas.toLocaleString('es-EC')"
        :variant="kpi.alertas > 0 ? 'default' : 'emerald'"
        :estado-tipo="kpi.alertas > 0 ? 'quiebre' : 'ok'"
      >
        <template #icono><Icon name="alert" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Competidores en seguimiento" :valor="kpi.competidores.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="users" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Mayor desviación"
        :valor="kpi.peorPct == null ? '—' : `${kpi.peorPct}%`"
        estado-tipo="fifo"
        :microcopy="kpi.peorProducto ? `Producto #${kpi.peorProducto}` : 'Sin alertas'"
      >
        <template #icono><Icon name="chart" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      titulo="Alertas de desviación"
      subtitulo="Productos cuyo precio propio se aleja del de la competencia más allá del umbral configurado."
      :columns="columnas"
      :rows="pagina"
      row-key="product_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="alertas.length"
      empty-text="Sin desviaciones por encima del umbral"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
    >
      <template #cell:producto="{ row }">
        <span class="font-mono text-[12px] font-semibold text-brand-800">#{{ row.product_id }}</span>
      </template>
      <template #cell:propio="{ row }">
        <span class="tabular-nums text-[13px] text-slate-700">{{ money(row.precio_base) }}</span>
      </template>
      <template #cell:competencia="{ row }">
        <span class="tabular-nums text-[13px] text-slate-700">{{ money(row.precio_competencia) }}</span>
      </template>
      <template #cell:fuente="{ row }">
        <span class="text-[12px] text-slate-500">{{ row.fuente_captura }}</span>
      </template>
      <template #cell:desviacion="{ row }">
        <SemanticChip tipo="quiebre">{{ row.desviacion_pct }}%</SemanticChip>
      </template>
    </DataTable>

    <!-- Modal: nuevo competidor -->
    <Modal v-if="modal === 'competidor'" titulo="Nuevo competidor" @cerrar="modal = null">
      <form class="space-y-3" @submit.prevent="crearCompetidor">
        <label class="block text-[12px] font-semibold text-slate-600">
          Nombre
          <input
            v-model="nuevoCompetidor.nombre"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Tipo
          <select
            v-model="nuevoCompetidor.tipo"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option value="supermercado">Supermercado</option>
            <option value="tienda_barrio">Tienda de barrio</option>
            <option value="tienda_digital">Tienda digital</option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Ciudad (opcional)
          <input
            v-model="nuevoCompetidor.ciudad"
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = null">Cancelar</Btn>
          <Btn variant="primary" type="submit">Agregar competidor</Btn>
        </div>
      </form>
    </Modal>

    <!-- Modal: registrar precio -->
    <Modal v-if="modal === 'precio'" titulo="Registrar precio de competencia" @cerrar="modal = null">
      <form class="space-y-3" @submit.prevent="registrarPrecio">
        <label class="block text-[12px] font-semibold text-slate-600">
          Producto (ID)
          <input
            v-model="captura.productId"
            type="number"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Competidor
          <select
            v-model="captura.competidorId"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          >
            <option value="" disabled>Elegí un competidor…</option>
            <option v-for="c in competidores" :key="c.competidor_id" :value="c.competidor_id">
              {{ c.nombre }}
            </option>
          </select>
        </label>
        <label class="block text-[12px] font-semibold text-slate-600">
          Precio observado (USD)
          <input
            v-model="captura.precio"
            type="number"
            min="0"
            step="0.01"
            required
            class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <label class="flex items-center gap-2 text-[12px] text-slate-600">
          <input v-model="captura.esPromocional" type="checkbox" /> Es un precio promocional
        </label>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = null">Cancelar</Btn>
          <Btn variant="primary" type="submit">Registrar captura</Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
