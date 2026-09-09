<script setup>
/**
 * Reporte mensual de auditoría de accesos (feature 008, FR-016). Agrupado por
 * usuario: logins exitosos, intentos fallidos y acciones registradas en
 * `auditoria_log` — el backend consolida, aquí sólo se presenta. Arquetipo
 * "Gestión" del kit.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { sistemaApi } from '@/services/sistemaApi'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Icon from '@/shared/ui/Icon.vue'
import DataTable from '@/shared/DataTable.vue'

const hoy = new Date()
const filtro = reactive({ mes: hoy.getMonth() + 1, anio: hoy.getFullYear() })
const filas = ref([])
const error = ref('')
const cargando = ref(false)
const busqueda = ref('')
const page = ref(1)
const size = ref(15)

const columnas = [
  { key: 'usuario', label: 'Usuario' },
  { key: 'exitosos', label: 'Logins exitosos', align: 'right', width: '150px' },
  { key: 'fallidos', label: 'Intentos fallidos', align: 'right', width: '150px' },
  { key: 'acciones', label: 'Acciones registradas', align: 'right', width: '170px' },
  { key: 'ultimo', label: 'Último acceso', align: 'right', width: '170px' },
]

const kpi = computed(() => ({
  usuarios: filas.value.length,
  exitosos: filas.value.reduce((a, f) => a + (f.logins_exitosos || 0), 0),
  fallidos: filas.value.reduce((a, f) => a + (f.intentos_fallidos || 0), 0),
  conFallos: filas.value.filter((f) => f.intentos_fallidos > 0).length,
}))

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return q ? filas.value.filter((f) => (f.username || '').toLowerCase().includes(q)) : filas.value
})
const pagina = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    filas.value = await sistemaApi.reporteAuditoria({ mes: filtro.mes, anio: filtro.anio })
    page.value = 1
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

const fechaCorta = (s) => (s ? String(s).slice(0, 16).replace('T', ' ') : '—')

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Auditoría de accesos"
      subtitulo="Actividad de inicio de sesión y acciones auditadas del periodo, consolidada por usuario (FR-016). Sólo lectura."
    >
      <template #badge>
        <SemanticChip :tipo="kpi.fallidos > 0 ? 'quiebre' : 'ok'">
          {{ kpi.fallidos > 0 ? `${kpi.fallidos} intentos fallidos` : 'Sin intentos fallidos' }}
        </SemanticChip>
      </template>
      <template #acciones>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="clock" :size="14" class="text-brand-700" />
          <input
            v-model.number="filtro.mes"
            type="number"
            min="1"
            max="12"
            class="w-10 bg-transparent text-center text-slate-800 focus:outline-none"
          />
          <span class="text-slate-300">/</span>
          <input
            v-model.number="filtro.anio"
            type="number"
            class="w-16 bg-transparent text-center text-slate-800 focus:outline-none"
          />
        </label>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl bg-brand-800 px-3.5 py-2 text-[13px] font-bold text-white hover:bg-brand-700"
          @click="cargar"
        >
          <Icon name="search" :size="15" /> Consultar
        </button>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile
        label="Usuarios con actividad"
        :valor="kpi.usuarios.toLocaleString('es-EC')"
        variant="emerald"
        :microcopy="`Mes ${filtro.mes}/${filtro.anio}`"
      />
      <KpiTile label="Logins exitosos" :valor="kpi.exitosos.toLocaleString('es-EC')" estado-tipo="ok">
        <template #icono><Icon name="check" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Intentos fallidos"
        :valor="kpi.fallidos.toLocaleString('es-EC')"
        :estado-tipo="kpi.fallidos > 0 ? 'quiebre' : 'ok'"
        :microcopy="`${kpi.conFallos} usuario(s) con al menos un fallo`"
      >
        <template #icono><Icon name="shield" :size="16" /></template>
      </KpiTile>
      <KpiTile
        label="Acciones auditadas"
        :valor="filas.reduce((a, f) => a + (f.acciones_registradas || 0), 0).toLocaleString('es-EC')"
        estado-tipo="neutral"
      >
        <template #icono><Icon name="pencil" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      titulo="Detalle por usuario"
      :columns="columnas"
      :rows="pagina"
      row-key="usuario_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Buscar usuario…"
      empty-text="Sin actividad de acceso en el periodo seleccionado"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
    >
      <template #cell:usuario="{ row }">
        <span class="font-semibold text-slate-800">{{ row.username || '(intentos anónimos)' }}</span>
      </template>
      <template #cell:exitosos="{ row }">
        <span class="tabular-nums text-[13px] text-slate-700">{{ row.logins_exitosos }}</span>
      </template>
      <template #cell:fallidos="{ row }">
        <span
          class="tabular-nums text-[13px] font-bold"
          :class="row.intentos_fallidos > 0 ? 'text-crimson-ruby' : 'text-slate-400'"
        >
          {{ row.intentos_fallidos }}
        </span>
      </template>
      <template #cell:acciones="{ row }">
        <span class="tabular-nums text-[13px] text-slate-700">{{ row.acciones_registradas }}</span>
      </template>
      <template #cell:ultimo="{ row }">
        <span class="tabular-nums text-[12px] text-slate-500">{{ fechaCorta(row.ultimo_login) }}</span>
      </template>
    </DataTable>
  </div>
</template>
