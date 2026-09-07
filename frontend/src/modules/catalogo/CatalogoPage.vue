<script setup>
/**
 * Catálogo de productos (US4). Lista con filtros reactivos (Principio XII),
 * alta con autocompletado, edición de precio y baja lógica. Toda regla en el backend.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import { catalogoApi } from '@/services/catalogoApi'
import FormularioProducto from './components/FormularioProducto.vue'

const filtros = reactive({ search: '', categoria: '', activo: true })
const productos = ref([])
const total = ref(0)
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const data = await catalogoApi.listar({
      search: filtros.search || undefined,
      categoria: filtros.categoria || undefined,
      activo: filtros.activo,
    })
    productos.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function cambiarPrecio(p) {
  const nuevo = window.prompt(
    `Nuevo precio base para "${p.nombre || p.product_id}":`,
    p.precio_base
  )
  if (nuevo == null) return
  try {
    await catalogoApi.actualizar(p.product_id, { precio_base: nuevo })
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

async function darDeBaja(p) {
  if (!window.confirm(`¿Descontinuar "${p.nombre || p.product_id}"? (baja lógica)`)) return
  try {
    await catalogoApi.darDeBaja(p.product_id)
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

watch(filtros, cargar, { deep: true })
onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Catálogo</h1>

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
            placeholder="Buscar por nombre / categoría"
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
                <th class="px-4 py-2 font-semibold">Categoría</th>
                <th class="px-4 py-2 text-right font-semibold">Precio</th>
                <th class="px-4 py-2 font-semibold">Clase</th>
                <th class="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Cargando…</td>
              </tr>
              <tr v-else-if="!productos.length">
                <td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">
                  Sin resultados
                </td>
              </tr>
              <tr
                v-for="p in productos"
                :key="p.product_id"
                class="border-b border-outline-variant last:border-0"
                :class="{ 'opacity-50': !p.activo }"
              >
                <td class="px-4 py-2 tabular-nums">{{ p.product_id }}</td>
                <td class="px-4 py-2">{{ p.nombre || p.product_type || '—' }}</td>
                <td class="px-4 py-2 text-on-surface-variant">{{ p.product_category || '—' }}</td>
                <td class="px-4 py-2 text-right tabular-nums">{{ p.precio_base }}</td>
                <td class="px-4 py-2">{{ p.es_ancla ? 'Ancla' : 'Nicho' }}</td>
                <td class="px-4 py-2 text-right">
                  <button
                    type="button"
                    class="mr-3 text-xs font-semibold text-primary-container hover:underline"
                    @click="cambiarPrecio(p)"
                  >
                    Precio
                  </button>
                  <button
                    v-if="p.activo"
                    type="button"
                    class="text-xs font-semibold text-error hover:underline"
                    @click="darDeBaja(p)"
                  >
                    Descontinuar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <aside>
        <FormularioProducto @creado="cargar" />
      </aside>
    </div>
  </main>
</template>
