<script setup>
/**
 * Reporte mensual de patrones de diferencias de cuadre (FR-009 a FR-011). El Jefe
 * de Finanzas ve las diferencias agrupadas por cajero y turno, más los ajustes de
 * inventario de 001 con faltante inusual, y puede escalar un patrón abriendo un
 * incidente de fraude directamente desde aquí.
 */
import { onMounted, reactive, ref } from 'vue'
import { cajaApi } from '@/services/cajaApi'

const hoy = new Date()
const filtro = reactive({ mes: hoy.getMonth() + 1, anio: hoy.getFullYear() })
const reporte = ref({ cuadres: [], ajustes_senalados: [] })
const error = ref('')
const cargando = ref(false)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    reporte.value = await cajaApi.reporteDiferencias({ mes: filtro.mes, anio: filtro.anio })
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function escalarCuadre(turno) {
  const descripcion = window.prompt(
    `Evidencia para el incidente sobre el cajero #${turno.cajero_id}`,
    `Patrón de diferencias en el turno ${turno.apertura_id}: ${turno.suma_diferencias}`,
  )
  if (!descripcion) return
  try {
    await cajaApi.abrirIncidente({ empleadoId: turno.cajero_id, descripcion })
    window.alert('Incidente abierto')
  } catch (e) {
    error.value = e.message
  }
}

async function escalarAjuste(ajuste) {
  const descripcion = window.prompt(
    `Evidencia para el incidente sobre el empleado #${ajuste.empleado_id}`,
    `Ajuste de inventario ${ajuste.ajuste_id} con faltante de ${ajuste.diferencia}`,
  )
  if (!descripcion) return
  try {
    await cajaApi.abrirIncidente({
      empleadoId: ajuste.empleado_id,
      ajusteId: ajuste.ajuste_id,
      descripcion,
    })
    window.alert('Incidente abierto')
  } catch (e) {
    error.value = e.message
  }
}

onMounted(cargar)
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Patrones de diferencias de cuadre</h1>

    <form class="mb-6 flex flex-wrap items-end gap-3" @submit.prevent="cargar">
      <label class="text-xs text-on-surface-variant">
        Mes
        <input
          v-model.number="filtro.mes"
          type="number"
          min="1"
          max="12"
          class="mt-1 block w-20 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <label class="text-xs text-on-surface-variant">
        Año
        <input
          v-model.number="filtro.anio"
          type="number"
          class="mt-1 block w-28 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
        />
      </label>
      <button
        type="submit"
        class="rounded-lg bg-primary-container px-4 py-2 text-sm font-semibold text-on-primary-container"
      >
        Consultar
      </button>
    </form>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <div class="grid gap-6 lg:grid-cols-2">
      <section>
        <h2 class="mb-2 text-sm font-semibold text-on-surface">Diferencias por cajero y turno</h2>
        <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-3 py-2 font-semibold">Cajero</th>
                <th class="px-3 py-2 font-semibold">Turno</th>
                <th class="px-3 py-2 text-right font-semibold">Σ diferencias</th>
                <th class="px-3 py-2 text-right font-semibold"># cuadres</th>
                <th class="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">Cargando…</td>
              </tr>
              <tr v-else-if="!reporte.cuadres.length">
                <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">Sin datos</td>
              </tr>
              <tr
                v-for="t in reporte.cuadres"
                :key="`${t.cajero_id}-${t.apertura_id}`"
                class="border-b border-outline-variant last:border-0"
              >
                <td class="px-3 py-2 tabular-nums">#{{ t.cajero_id }}</td>
                <td class="px-3 py-2 tabular-nums">{{ t.fecha_turno || `#${t.apertura_id}` }}</td>
                <td
                  class="px-3 py-2 text-right font-semibold tabular-nums"
                  :class="Number(t.suma_diferencias) < 0 ? 'text-error' : 'text-on-surface'"
                >
                  {{ t.suma_diferencias }}
                </td>
                <td class="px-3 py-2 text-right tabular-nums">
                  {{ t.cantidad_cuadres_con_diferencia }}
                </td>
                <td class="px-3 py-2 text-right">
                  <button
                    type="button"
                    class="rounded-lg bg-error-container px-2 py-1 text-xs font-semibold text-on-error-container"
                    @click="escalarCuadre(t)"
                  >
                    Escalar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 class="mb-2 text-sm font-semibold text-on-surface">Ajustes de inventario señalados</h2>
        <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-3 py-2 font-semibold">Ajuste</th>
                <th class="px-3 py-2 font-semibold">Producto</th>
                <th class="px-3 py-2 text-right font-semibold">Diferencia</th>
                <th class="px-3 py-2 font-semibold">Empleado</th>
                <th class="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-if="!reporte.ajustes_senalados.length">
                <td colspan="5" class="px-3 py-6 text-center text-on-surface-variant">
                  Sin ajustes anómalos
                </td>
              </tr>
              <tr
                v-for="a in reporte.ajustes_senalados"
                :key="a.ajuste_id"
                class="border-b border-outline-variant last:border-0"
              >
                <td class="px-3 py-2 tabular-nums">#{{ a.ajuste_id }}</td>
                <td class="px-3 py-2 tabular-nums">#{{ a.product_id }}</td>
                <td class="px-3 py-2 text-right font-semibold tabular-nums text-error">
                  {{ a.diferencia }}
                </td>
                <td class="px-3 py-2 tabular-nums">#{{ a.empleado_id }}</td>
                <td class="px-3 py-2 text-right">
                  <button
                    type="button"
                    class="rounded-lg bg-error-container px-2 py-1 text-xs font-semibold text-on-error-container"
                    @click="escalarAjuste(a)"
                  >
                    Escalar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
</template>
