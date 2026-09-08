<script setup>
/**
 * Incidentes de seguridad de pago (feature 007, FR-008 a FR-011) — entidad
 * distinta e independiente del incidente de fraude interno de 006. El Jefe de TI
 * registra y avanza el incidente (abierto → en investigación → cerrado); el Jefe
 * de Finanzas consulta el conteo del periodo.
 */
import { onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'

const incidentes = ref([])
const filtroEstado = ref('')
const nuevo = reactive({ datafono_id: '', descripcion: '' })
const periodo = reactive({ desde: '', hasta: '' })
const conteo = ref(null)
const error = ref('')
const cargando = ref(false)

const SIGUIENTE = { abierto: 'en_investigacion', en_investigacion: 'cerrado' }

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    incidentes.value = await cajaApi.incidentesSeguridad(filtroEstado.value)
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function registrar() {
  error.value = ''
  try {
    await cajaApi.registrarIncidenteSeguridad({
      datafonoId: nuevo.datafono_id ? Number(nuevo.datafono_id) : null,
      descripcion: nuevo.descripcion,
    })
    nuevo.datafono_id = ''
    nuevo.descripcion = ''
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function avanzar(inc) {
  try {
    await cajaApi.transicionarIncidenteSeguridad(inc.incidente_seguridad_id, SIGUIENTE[inc.estado])
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function consultarConteo() {
  error.value = ''
  try {
    conteo.value = await cajaApi.conteoIncidentesSeguridad({
      desde: periodo.desde || undefined,
      hasta: periodo.hasta || undefined,
    })
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Incidentes de seguridad de pago</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="registrar"
    >
      <h2 class="w-full text-sm font-semibold text-on-surface">Registrar incidente</h2>
      <label class="text-xs text-on-surface-variant">
        Datáfono (opcional)
        <input
          v-model="nuevo.datafono_id"
          type="number"
          class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="flex-1 text-xs text-on-surface-variant">
        Descripción
        <input
          v-model="nuevo.descripcion"
          type="text"
          required
          class="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Registrar
      </button>
    </form>

    <form
      class="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      @submit.prevent="consultarConteo"
    >
      <h2 class="w-full text-sm font-semibold text-on-surface">Conteo del periodo (Jefe de Finanzas)</h2>
      <label class="text-xs text-on-surface-variant">
        Desde
        <input
          v-model="periodo.desde"
          type="date"
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Hasta
        <input
          v-model="periodo.hasta"
          type="date"
          class="mt-1 block rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Consultar
      </button>
      <p v-if="conteo" class="text-sm font-semibold text-on-surface">
        {{ conteo.total }} incidente(s)
      </p>
    </form>

    <div class="mb-3 flex items-center gap-2">
      <label class="text-xs text-on-surface-variant" for="filtro-sp">Estado</label>
      <select
        id="filtro-sp"
        v-model="filtroEstado"
        class="rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
        @change="cargar"
      >
        <option value="">Todos</option>
        <option value="abierto">Abierto</option>
        <option value="en_investigacion">En investigación</option>
        <option value="cerrado">Cerrado</option>
      </select>
    </div>

    <div class="space-y-3">
      <p v-if="cargando" class="text-sm text-on-surface-variant">Cargando…</p>
      <p v-else-if="!incidentes.length" class="text-sm text-on-surface-variant">Sin incidentes</p>
      <article
        v-for="inc in incidentes"
        :key="inc.incidente_seguridad_id"
        class="rounded-xl border border-outline-variant bg-surface-container-lowest p-4"
      >
        <div class="mb-1 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-on-surface">
            Incidente #{{ inc.incidente_seguridad_id }}
            <span v-if="inc.datafono_id" class="text-on-surface-variant">
              · datáfono #{{ inc.datafono_id }}</span
            >
          </h3>
          <span
            class="rounded-md px-2 py-0.5 text-xs font-semibold"
            :class="{
              'bg-error-container text-on-error-container': inc.estado === 'abierto',
              'bg-secondary-container text-on-secondary-container':
                inc.estado === 'en_investigacion',
              'bg-tertiary-container text-on-tertiary-container': inc.estado === 'cerrado',
            }"
          >
            {{ inc.estado }}
          </span>
        </div>
        <p class="text-sm text-on-surface-variant">{{ inc.descripcion }}</p>
        <button
          v-if="SIGUIENTE[inc.estado]"
          type="button"
          class="mt-3 rounded-lg bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
          @click="avanzar(inc)"
        >
          Avanzar a «{{ SIGUIENTE[inc.estado] }}»
        </button>
      </article>
    </div>
  </main>
</template>
