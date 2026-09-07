<script setup>
/**
 * Maestro de clientes (US1, feature 002). Lista con búsqueda reactiva por
 * nombre/email/cédula (Principio XII), alta con captura de consentimiento,
 * edición y baja lógica con anonimización. Toda regla vive en el backend.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import FormularioCliente from './components/FormularioCliente.vue'

const filtros = reactive({ search: '', activo: true })
const clientes = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')
const seleccionado = ref(null)
const niveles = ref([])

const nivelPorId = computed(() =>
  Object.fromEntries(niveles.value.map((n) => [n.nivel_id, n.nombre]))
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await clientesApi.listar({
      search: filtros.search || undefined,
      activo: filtros.activo,
    })
    clientes.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function darDeBaja(c) {
  if (!window.confirm(`Anonimizar y dar de baja a "${c.nombre}"? (irreversible)`)) return
  try {
    await clientesApi.darDeBaja(c.household_id)
    seleccionado.value = null
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

function onGuardado() {
  seleccionado.value = null
  cargar()
}

watch(filtros, cargar, { deep: true })
onMounted(async () => {
  await cargar()
  try {
    niveles.value = await clientesApi.niveles()
  } catch {
    niveles.value = []
  }
})
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-primary-container">Clientes</h1>
      <div class="flex gap-2">
        <RouterLink
          to="/clientes/riesgo-fuga"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
        >
          Riesgo de fuga →
        </RouterLink>
        <RouterLink
          to="/clientes/campanas"
          class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-low"
        >
          Campañas →
        </RouterLink>
      </div>
    </div>

    <p
      v-if="error"
      class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container"
    >
      {{ error }}
    </p>

    <div class="grid gap-6 lg:grid-cols-[1fr_22rem]">
      <section class="space-y-4">
        <div
          class="flex flex-wrap items-center gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-3"
        >
          <input
            v-model="filtros.search"
            placeholder="Buscar por nombre, email o cédula"
            class="flex-1 rounded-lg border border-outline-variant bg-surface px-3 py-1.5 text-sm text-on-surface"
          />
          <label class="flex items-center gap-2 text-sm text-on-surface-variant">
            <input v-model="filtros.activo" type="checkbox" />
            Sólo activos
          </label>
          <span class="text-sm text-on-surface-variant">{{ total }}</span>
        </div>

        <div
          class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-4 py-2 font-semibold">ID</th>
                <th class="px-4 py-2 font-semibold">Nombre</th>
                <th class="px-4 py-2 font-semibold">Cédula</th>
                <th class="px-4 py-2 font-semibold">Consent.</th>
                <th class="px-4 py-2 text-right font-semibold">CLV</th>
                <th class="px-4 py-2 font-semibold">Nivel</th>
                <th class="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="7" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
              </tr>
              <tr v-else-if="!clientes.length">
                <td colspan="7" class="px-4 py-6 text-center text-on-surface-variant">
                  Sin resultados
                </td>
              </tr>
              <tr
                v-for="c in clientes"
                :key="c.household_id"
                class="cursor-pointer border-b border-outline-variant last:border-0 hover:bg-surface-container-low"
                :class="{ 'opacity-50': !c.activo }"
                @click="seleccionado = c"
              >
                <td class="px-4 py-2 tabular-nums">{{ c.household_id }}</td>
                <td class="px-4 py-2">{{ c.nombre }}</td>
                <td class="px-4 py-2 text-on-surface-variant">
                  {{ c.documento_identidad || '—' }}
                </td>
                <td class="px-4 py-2">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-semibold"
                    :class="
                      c.consentimiento_datos
                        ? 'bg-tertiary-container text-on-tertiary-container'
                        : 'bg-error-container text-on-error-container'
                    "
                  >
                    {{ c.consentimiento_datos ? 'sí' : 'no' }}
                  </span>
                </td>
                <td class="px-4 py-2 text-right tabular-nums">{{ c.clv_score ?? '—' }}</td>
                <td class="px-4 py-2">
                  {{ nivelPorId[c.nivel_fidelizacion_id] || '—' }}
                  <span v-if="c.severidad_churn" class="ml-1 text-xs font-semibold text-error">
                    · {{ c.severidad_churn }}
                  </span>
                </td>
                <td class="px-4 py-2 text-right">
                  <button
                    v-if="c.activo"
                    type="button"
                    class="text-xs font-semibold text-error hover:underline"
                    @click.stop="darDeBaja(c)"
                  >
                    Dar de baja
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <aside class="space-y-3">
        <div
          v-if="seleccionado"
          class="rounded-xl border border-outline-variant bg-surface-container-high p-4 text-sm"
        >
          <p class="font-semibold text-on-surface">
            Fidelización — cliente #{{ seleccionado.household_id }}
          </p>
          <p class="mt-1 text-on-surface-variant">
            CLV:
            <strong class="text-on-surface">{{ seleccionado.clv_score ?? 'sin calcular' }}</strong>
            · Nivel:
            <strong class="text-on-surface">
              {{ nivelPorId[seleccionado.nivel_fidelizacion_id] || '—' }}
            </strong>
          </p>
          <p v-if="seleccionado.severidad_churn" class="mt-1 text-error">
            Riesgo de fuga: <strong>{{ seleccionado.severidad_churn }}</strong>
          </p>
        </div>
        <FormularioCliente :cliente="seleccionado" @guardado="onGuardado" />
        <button
          v-if="seleccionado"
          type="button"
          class="mt-2 w-full rounded-lg border border-outline-variant px-3 py-2 text-sm text-on-surface"
          @click="seleccionado = null"
        >
          Cancelar edición / nuevo cliente
        </button>
      </aside>
    </div>
  </main>
</template>
