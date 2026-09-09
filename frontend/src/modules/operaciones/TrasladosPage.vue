<script setup>
/**
 * Traslados de Stock entre Tiendas — feature 012 (OT-2.5). Arquetipo "Gestión":
 * page header + KPI de la red + consulta de disponibilidad por sucursal (US1) +
 * data-grid del ciclo solicitud → resolución → despacho → recepción (US2/US3).
 *
 * No hay pantalla de referencia para esta feature; se sigue el sistema de diseño
 * ya implementado (mismo kit que Datáfonos / Incidentes / Inventario). Toda regla
 * de negocio (descuento FIFO, herencia de vencimiento, revalidación de stock)
 * vive en el backend (Principio V).
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { trasladosApi } from '@/services/trasladosApi'
import { useSesion } from '@/stores/sesion'
import { prompt } from '@/shared/ui/dialogs'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import Btn from '@/shared/ui/Btn.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'
import ProductoPicker from '@/shared/ui/ProductoPicker.vue'

const sesion = useSesion()
const esJefeOps = computed(() => sesion.rol === 'Jefe_Operaciones')
const puedeOperar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Operaciones', 'traslados_stock'),
)

const ESTADO = {
  solicitado: { tipo: 'fifo', txt: 'Solicitado' },
  en_transito: { tipo: 'ia', txt: 'En tránsito' },
  recibido: { tipo: 'ok', txt: 'Recibido' },
  rechazado: { tipo: 'quiebre', txt: 'Rechazado' },
  cancelado: { tipo: 'neutral', txt: 'Cancelado' },
}

const traslados = ref([])
const tiendas = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')

const busqueda = ref('')
const pill = ref('')
const page = ref(1)
const size = ref(15)

function msg(e) {
  const err = e.response?.data?.error
  if (err?.details?.stock_disponible != null) {
    return `Stock insuficiente en la tienda origen: hay ${err.details.stock_disponible}, se solicitaron ${err.details.cantidad_solicitada}.`
  }
  return err?.message || e.message || 'No se pudo completar la operación.'
}

const tiendasById = computed(() => Object.fromEntries(tiendas.value.map((t) => [t.tienda_id, t])))
function nombreTienda(id, nombre) {
  return nombre || tiendasById.value[id]?.nombre || `Tienda ${id}`
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const fuentes = esJefeOps.value
      ? [trasladosApi.listar()]
      : [
          trasladosApi.listar({ direccion: 'origen' }),
          trasladosApi.listar({ direccion: 'destino' }),
        ]
    const [tnds, ...listas] = await Promise.all([trasladosApi.tiendas(), ...fuentes])
    tiendas.value = tnds
    const porId = new Map()
    for (const lista of listas) for (const t of lista) porId.set(t.traslado_id, t)
    traslados.value = [...porId.values()].sort((a, b) =>
      (b.fecha_hora || '').localeCompare(a.fecha_hora || ''),
    )
  } catch (e) {
    error.value = msg(e)
  } finally {
    cargando.value = false
  }
}

const kpi = computed(() => {
  const d = traslados.value
  const por = (e) => d.filter((x) => x.estado === e).length
  return {
    total: d.length,
    solicitados: por('solicitado'),
    enTransito: por('en_transito'),
    recibidos: por('recibido'),
    cerrados: por('rechazado') + por('cancelado'),
  }
})

const pills = computed(() => [
  { value: '', label: 'Todos', count: kpi.value.total },
  { value: 'solicitado', label: 'Solicitados', count: kpi.value.solicitados },
  { value: 'en_transito', label: 'En tránsito', count: kpi.value.enTransito },
  { value: 'recibido', label: 'Recibidos', count: kpi.value.recibidos },
  {
    value: 'cerrados',
    label: 'Rechazados / cancelados',
    count: kpi.value.cerrados,
  },
])

const columnas = [
  { key: 'ref', label: 'Traslado', width: '120px' },
  { key: 'producto', label: 'Producto' },
  { key: 'cantidad', label: 'Unidades', align: 'right', width: '90px' },
  { key: 'ruta', label: 'Origen → Destino' },
  { key: 'estado', label: 'Estado', align: 'center', width: '150px' },
  { key: 'solicitante', label: 'Solicitado por', width: '160px' },
  { key: 'acciones', label: '', align: 'right', width: '230px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return traslados.value.filter((t) => {
    if (pill.value === 'cerrados') {
      if (t.estado !== 'rechazado' && t.estado !== 'cancelado') return false
    } else if (pill.value && t.estado !== pill.value) return false
    if (!q) return true
    return (
      String(t.traslado_id).includes(q) ||
      String(t.product_id).includes(q) ||
      (t.producto_nombre || '').toLowerCase().includes(q) ||
      nombreTienda(t.tienda_origen_id, t.tienda_origen_nombre).toLowerCase().includes(q) ||
      nombreTienda(t.tienda_destino_id, t.tienda_destino_nombre).toLowerCase().includes(q) ||
      (t.solicitante_nombre || '').toLowerCase().includes(q)
    )
  })
})
const filas = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

// ---- permisos por fila -------------------------------------------------------
const miTienda = computed(() => sesion.tiendaId)
function puedeResolver(t) {
  return (
    puedeOperar.value &&
    t.estado === 'solicitado' &&
    (esJefeOps.value || t.tienda_origen_id === miTienda.value)
  )
}
function puedeCancelar(t) {
  return (
    puedeOperar.value &&
    t.estado === 'solicitado' &&
    (esJefeOps.value || t.empleado_id === sesion.empleadoId)
  )
}
function puedeRecibir(t) {
  return (
    puedeOperar.value &&
    t.estado === 'en_transito' &&
    (esJefeOps.value || t.tienda_destino_id === miTienda.value)
  )
}

// ---- acciones ---------------------------------------------------------------
const trabajando = ref(null) // traslado_id en curso

async function aprobar(t) {
  trabajando.value = t.traslado_id
  error.value = ''
  aviso.value = ''
  try {
    const r = await trasladosApi.resolver(t.traslado_id, 'aprobar')
    aviso.value = `Traslado #${r.traslado_id} despachado: se descontó el stock de ${nombreTienda(r.tienda_origen_id, r.tienda_origen_nombre)}.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    trabajando.value = null
  }
}

async function rechazar(t) {
  const motivo = await prompt({
    title: `Rechazar traslado #${t.traslado_id}`,
    message: `${t.cantidad} u de ${t.producto_nombre || 'producto ' + t.product_id} hacia ${nombreTienda(t.tienda_destino_id, t.tienda_destino_nombre)}.`,
    label: 'Motivo del rechazo',
    placeholder: 'Ej.: stock reservado para reposición local, diferencia de conteo…',
    required: true,
    tone: 'danger',
    confirmText: 'Rechazar solicitud',
  })
  if (!motivo) return
  trabajando.value = t.traslado_id
  error.value = ''
  aviso.value = ''
  try {
    await trasladosApi.resolver(t.traslado_id, 'rechazar', motivo)
    aviso.value = `Traslado #${t.traslado_id} rechazado. Sin efecto sobre el inventario.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    trabajando.value = null
  }
}

async function cancelar(t) {
  const motivo = await prompt({
    title: `Cancelar solicitud #${t.traslado_id}`,
    message: 'La solicitud se cierra sin mover inventario en ninguna tienda.',
    label: 'Motivo (opcional)',
    placeholder: 'Ej.: ya no se necesita, se resolvió con otra sucursal…',
    confirmText: 'Cancelar solicitud',
    tone: 'danger',
  })
  if (motivo === null) return
  trabajando.value = t.traslado_id
  error.value = ''
  aviso.value = ''
  try {
    await trasladosApi.cancelar(t.traslado_id)
    aviso.value = `Solicitud #${t.traslado_id} cancelada.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    trabajando.value = null
  }
}

async function recibir(t) {
  trabajando.value = t.traslado_id
  error.value = ''
  aviso.value = ''
  try {
    const r = await trasladosApi.confirmarRecepcion(t.traslado_id)
    aviso.value = `Recepción confirmada: +${r.cantidad} u en ${nombreTienda(r.tienda_destino_id, r.tienda_destino_nombre)}.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    trabajando.value = null
  }
}

// ---- consulta de disponibilidad (US1) -------------------------------------
const consulta = reactive({ productId: null, producto: null, filas: [], cargando: false })
async function consultarDisponibilidad(pid) {
  consulta.filas = []
  if (!pid) return
  consulta.cargando = true
  try {
    const data = await trasladosApi.disponibilidadSucursales(pid)
    consulta.filas = data.disponibilidad
  } catch (e) {
    error.value = msg(e)
  } finally {
    consulta.cargando = false
  }
}
watch(() => consulta.productId, consultarDisponibilidad)

// ---- modal: solicitar traslado ------------------------------------------
const modal = ref(false)
const form = reactive({
  productId: null,
  producto: null,
  origen: null,
  destino: null,
  cantidad: 1,
})
const formDisponibilidad = ref([])
const formDispCargando = ref(false)
const guardando = ref(false)

const stockOrigen = computed(() => {
  const f = formDisponibilidad.value.find((d) => d.tienda_id === form.origen)
  return f ? f.cantidad_disponible : null
})
const excedeStock = computed(
  () => stockOrigen.value != null && Number(form.cantidad) > stockOrigen.value,
)

function abrirSolicitud() {
  Object.assign(form, {
    productId: null,
    producto: null,
    origen: null,
    destino: sesion.tiendaId ?? null,
    cantidad: 1,
  })
  formDisponibilidad.value = []
  error.value = ''
  modal.value = true
}

watch(
  () => form.productId,
  async (pid) => {
    formDisponibilidad.value = []
    if (!pid) return
    formDispCargando.value = true
    try {
      const data = await trasladosApi.disponibilidadSucursales(pid)
      formDisponibilidad.value = data.disponibilidad
    } finally {
      formDispCargando.value = false
    }
  },
)

async function enviarSolicitud() {
  if (!form.productId || !form.origen || !form.destino) return
  guardando.value = true
  error.value = ''
  aviso.value = ''
  try {
    const r = await trasladosApi.solicitar({
      productId: form.productId,
      tiendaOrigenId: form.origen,
      tiendaDestinoId: form.destino,
      cantidad: Number(form.cantidad),
    })
    modal.value = false
    aviso.value = `Solicitud #${r.traslado_id} registrada. Queda pendiente de que ${nombreTienda(r.tienda_origen_id, r.tienda_origen_nombre)} la apruebe.`
    await cargar()
  } catch (e) {
    error.value = msg(e)
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1560px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Traslados de stock entre tiendas"
      subtitulo="Coordina el movimiento de mercadería entre sucursales antes de comprar al proveedor: solicitud, aprobación de la tienda origen, despacho FIFO y confirmación de recepción."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.solicitados > 0 ? 'fifo' : 'ok'">
          {{ kpi.solicitados > 0 ? `${kpi.solicitados} por resolver` : 'Sin pendientes' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <Btn
          v-if="puedeOperar"
          variant="primary"
          :disabled="!tiendas.length"
          @click="abrirSolicitud"
        >
          <Icon name="plus" :size="17" /> Solicitar traslado
        </Btn>
        <span
          v-else
          class="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600"
        >
          <Icon name="shield" :size="14" /> Solo lectura
        </span>
      </template>
    </PageHeader>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Solicitudes por resolver"
        :valor="kpi.solicitados.toLocaleString('es-EC')"
        variant="emerald"
        :microcopy="
          esJefeOps
            ? 'En toda la red — esperan aprobación de la tienda origen'
            : 'Dirigidas a tu tienda como origen'
        "
        pie-label="Traslados registrados"
        :pie-valor="`${kpi.total} en total`"
      />
      <KpiTile
        label="En tránsito"
        :valor="kpi.enTransito.toLocaleString('es-EC')"
        :estado="kpi.enTransito > 0 ? 'esperan recepción' : 'al día'"
        :estado-tipo="kpi.enTransito > 0 ? 'ia' : 'ok'"
        microcopy="Despachados: stock ya descontado del origen, aún no confirmado en destino"
      >
        <template #icono><Icon name="truck" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Recibidos"
        :valor="kpi.recibidos.toLocaleString('es-EC')"
        estado-tipo="ok"
        microcopy="Ciclo cerrado: la cantidad ya está disponible en la tienda destino"
      >
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Rechazados / cancelados"
        :valor="kpi.cerrados.toLocaleString('es-EC')"
        estado-tipo="neutral"
        microcopy="Cerrados sin mover inventario en ninguna tienda"
      >
        <template #icono><Icon name="x" :size="16" /></template>
      </KpiTile>
    </section>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby"
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-4 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      {{ aviso }}
    </p>

    <!-- US1: consulta de disponibilidad por sucursal -->
    <section class="satin-card mb-6 rounded-2xl p-5 shadow-card-subtle">
      <div class="mb-3 flex items-center gap-2">
        <Icon name="database" :size="16" class="text-brand-700" />
        <h2 class="font-display text-base font-bold text-brand-950">Stock del producto en la red</h2>
      </div>
      <p class="mb-3 text-[12px] text-slate-600">
        Antes de comprar o de pedir un traslado, revisa cuánto hay de un producto en cada sucursal
        (FR-001).
      </p>
      <div class="max-w-md">
        <ProductoPicker v-model="consulta.productId" label="Producto a consultar" />
      </div>
      <div v-if="consulta.cargando" class="mt-4 text-[12px] text-slate-400">Consultando…</div>
      <div
        v-else-if="consulta.filas.length"
        class="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      >
        <div
          v-for="d in consulta.filas"
          :key="d.tienda_id"
          class="flex items-center justify-between rounded-xl border px-3 py-2"
          :class="
            d.cantidad_disponible > 0
              ? 'border-brand-200 bg-white'
              : 'border-slate-200 bg-slate-50/60'
          "
        >
          <span class="flex items-center gap-1.5 text-[12px] font-medium text-slate-700">
            <Icon name="pin" :size="13" class="text-brand-600" />
            {{ d.nombre_tienda }}
          </span>
          <span
            class="tabular-nums text-[13px] font-bold"
            :class="d.cantidad_disponible > 0 ? 'text-brand-900' : 'text-slate-400'"
          >
            {{ d.cantidad_disponible }}
          </span>
        </div>
      </div>
    </section>

    <DataTable
      titulo="Ciclo de traslados"
      subtitulo="Solicitud → aprobación de la tienda origen (despacho FIFO) → confirmación de recepción en destino."
      :columns="columnas"
      :rows="filas"
      row-key="traslado_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Traslado, producto o tienda…"
      :pills="pills"
      :pill-activa="pill"
      empty-text="No hay traslados registrados"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
      @pill="((pill = $event), (page = 1))"
    >
      <template #cell:ref="{ row }">
        <div class="leading-tight">
          <div class="font-mono text-[12px] font-semibold text-slate-800">#{{ row.traslado_id }}</div>
          <div class="text-[10px] text-slate-400">{{ (row.fecha_hora || '').slice(0, 10) }}</div>
        </div>
      </template>

      <template #cell:producto="{ row }">
        <div class="flex items-center gap-2">
          <Icon name="cube" :size="15" class="shrink-0 text-slate-400" />
          <div class="leading-tight">
            <div class="text-[12px] font-medium text-slate-800">
              {{ row.producto_nombre || `Producto ${row.product_id}` }}
            </div>
            <div class="font-mono text-[10px] text-slate-400">ID {{ row.product_id }}</div>
          </div>
        </div>
      </template>

      <template #cell:cantidad="{ row }">
        <span class="tabular-nums text-[13px] font-bold text-slate-900">{{ row.cantidad }}</span>
      </template>

      <template #cell:ruta="{ row }">
        <div class="flex items-center gap-1.5 text-[12px] text-slate-700">
          <span class="font-medium">{{
            nombreTienda(row.tienda_origen_id, row.tienda_origen_nombre)
          }}</span>
          <Icon name="chevron" :size="13" class="-rotate-90 text-slate-400" />
          <span class="font-medium">{{
            nombreTienda(row.tienda_destino_id, row.tienda_destino_nombre)
          }}</span>
        </div>
      </template>

      <template #cell:estado="{ row }">
        <SemanticChip :tipo="ESTADO[row.estado]?.tipo || 'neutral'">
          {{ ESTADO[row.estado]?.txt || row.estado }}
        </SemanticChip>
        <div
          v-if="row.estado === 'en_transito'"
          class="mt-1 text-[10px] font-medium text-amethyst-700"
        >
          pendiente de confirmar
        </div>
      </template>

      <template #cell:solicitante="{ row }">
        <div class="leading-tight">
          <div class="text-[12px] text-slate-700">{{ row.solicitante_nombre || '—' }}</div>
          <div v-if="row.resuelto_por_nombre" class="text-[10px] text-slate-400">
            resolvió {{ row.resuelto_por_nombre }}
          </div>
        </div>
      </template>

      <template #cell:acciones="{ row }">
        <div class="flex items-center justify-end gap-1 whitespace-nowrap">
          <Btn
            v-if="puedeResolver(row)"
            variant="primary"
            class="!px-2.5 !py-1 !text-[12px]"
            :disabled="trabajando === row.traslado_id"
            @click="aprobar(row)"
          >
            <Icon name="check" :size="14" /> Aprobar
          </Btn>
          <Btn
            v-if="puedeResolver(row)"
            variant="danger"
            class="!px-2.5 !py-1 !text-[12px]"
            :disabled="trabajando === row.traslado_id"
            @click="rechazar(row)"
          >
            Rechazar
          </Btn>
          <Btn
            v-if="puedeRecibir(row)"
            variant="primary"
            class="!px-2.5 !py-1 !text-[12px]"
            :disabled="trabajando === row.traslado_id"
            @click="recibir(row)"
          >
            <Icon name="check" :size="14" /> Confirmar recepción
          </Btn>
          <button
            v-if="puedeCancelar(row) && !puedeResolver(row)"
            type="button"
            class="rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-crimson-ruby"
            title="Cancelar solicitud"
            :disabled="trabajando === row.traslado_id"
            @click="cancelar(row)"
          >
            <Icon name="x" :size="15" />
          </button>
          <span
            v-if="
              !puedeResolver(row) && !puedeRecibir(row) && !puedeCancelar(row)
            "
            class="text-[11px] text-slate-400"
            >—</span
          >
        </div>
      </template>
    </DataTable>

    <Modal v-if="modal" titulo="Solicitar traslado entre tiendas" size="lg" @cerrar="modal = false">
      <p class="mb-4 text-[13px] text-slate-600">
        La tienda origen deberá aprobar la solicitud. Al aprobarla, el sistema descuenta el stock por
        FIFO y lo marca en tránsito; la tienda destino confirma la recepción para cerrar el ciclo
        (FR-003 a FR-008).
      </p>
      <form class="space-y-4" @submit.prevent="enviarSolicitud">
        <ProductoPicker
          v-model="form.productId"
          label="Producto"
          required
          @seleccionado="form.producto = $event"
        />

        <div
          v-if="formDispCargando"
          class="text-[12px] text-slate-400"
        >
          Consultando disponibilidad…
        </div>
        <div
          v-else-if="formDisponibilidad.length"
          class="rounded-xl border border-brand-200 bg-brand-50/50 p-3"
        >
          <p class="mb-2 text-[11px] font-bold uppercase tracking-wide text-brand-800">
            Disponibilidad por sucursal — toca una para elegirla como origen
          </p>
          <div class="grid gap-1.5 sm:grid-cols-2">
            <button
              v-for="d in formDisponibilidad"
              :key="d.tienda_id"
              type="button"
              :disabled="d.tienda_id === form.destino || d.cantidad_disponible <= 0"
              class="flex items-center justify-between rounded-lg border px-3 py-1.5 text-left transition disabled:cursor-not-allowed disabled:opacity-40"
              :class="
                form.origen === d.tienda_id
                  ? 'border-brand-600 bg-white ring-1 ring-brand-500/30'
                  : 'border-brand-200 bg-white hover:border-brand-400'
              "
              @click="form.origen = d.tienda_id"
            >
              <span class="text-[12px] font-medium text-slate-700">{{ d.nombre_tienda }}</span>
              <span class="tabular-nums text-[12px] font-bold text-brand-900">{{
                d.cantidad_disponible
              }}</span>
            </button>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block text-[12px] font-semibold text-slate-600">
            Tienda origen <span class="text-crimson-ruby">*</span>
            <select
              v-model.number="form.origen"
              required
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
            >
              <option :value="null" disabled>Selecciona…</option>
              <option
                v-for="t in tiendas"
                :key="t.tienda_id"
                :value="t.tienda_id"
                :disabled="t.tienda_id === form.destino"
              >
                {{ t.nombre }}
              </option>
            </select>
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Tienda destino <span class="text-crimson-ruby">*</span>
            <select
              v-model.number="form.destino"
              required
              :disabled="!esJefeOps && sesion.tiendaId != null"
              class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:bg-slate-50 disabled:text-slate-500"
            >
              <option :value="null" disabled>Selecciona…</option>
              <option
                v-for="t in tiendas"
                :key="t.tienda_id"
                :value="t.tienda_id"
                :disabled="t.tienda_id === form.origen"
              >
                {{ t.nombre }}
              </option>
            </select>
          </label>
        </div>

        <label class="block text-[12px] font-semibold text-slate-600">
          Cantidad a trasladar <span class="text-crimson-ruby">*</span>
          <input
            v-model.number="form.cantidad"
            type="number"
            min="1"
            required
            class="mt-1 block w-40 rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
        <p v-if="excedeStock" class="text-[12px] font-medium text-amber-700">
          El origen tiene {{ stockOrigen }} u disponibles ahora. El sistema revalida el stock al
          aprobar y no dejará despachar de más (FR-005).
        </p>

        <div class="flex justify-end gap-2.5 pt-2">
          <Btn variant="ghost" @click="modal = false">Cancelar</Btn>
          <Btn
            variant="primary"
            type="submit"
            :disabled="guardando || !form.productId || !form.origen || !form.destino"
          >
            {{ guardando ? 'Registrando…' : 'Registrar solicitud' }}
          </Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
