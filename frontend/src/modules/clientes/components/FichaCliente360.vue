<script setup>
/**
 * Ficha 360° del cliente — panel derecho de la referencia
 * "Gestión de Clientes & Programa de Lealtad Club Marzú".
 * Cabecera con gradiente verde abisal, saldo de puntos, cupones del Club,
 * distribución de consumo por categoría y últimas 3 compras.
 */
import { computed, ref, watch } from 'vue'
import { clientesApi } from '@/services/clientesApi'
import Icon from '@/shared/ui/Icon.vue'

const props = defineProps({
  cliente: { type: Object, default: null }, // fila del directorio
  niveles: { type: Array, default: () => [] },
})
const emit = defineEmits(['editar', 'asignar-cupon'])

const ficha = ref(null)
const cargando = ref(false)

const money = (v) => `$${Math.round(Number(v || 0)).toLocaleString('es-CL')}`
const iniciales = (n) =>
  (n || '?')
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()

const TIER = {
  Bronce: 'bg-amber-800/10 text-amber-800 ring-amber-700/20',
  Plata: 'bg-slate-100 text-slate-700 ring-slate-400/30',
  Oro: 'bg-amber-50 text-amber-800 ring-amber-400/40',
  Platino: 'bg-amethyst-100 text-amethyst-800 ring-amethyst-400/30',
}

const consumoTotal = computed(() =>
  (ficha.value?.consumo || []).reduce((a, c) => a + Number(c.monto), 0),
)
const SEGCOL = ['bg-brand-700', 'bg-emerald-500', 'bg-amber-500', 'bg-amethyst-500']

watch(
  () => props.cliente?.household_id,
  async (id) => {
    ficha.value = null
    if (!id) return
    cargando.value = true
    try {
      ficha.value = await clientesApi.ficha360(id)
    } finally {
      cargando.value = false
    }
  },
  { immediate: true },
)

const fmtFecha = (d) =>
  d
    ? new Date(d).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' })
    : '—'
</script>

<template>
  <div
    v-if="!cliente"
    class="satin-card grid place-items-center rounded-2xl p-10 text-center text-[13px] text-slate-500 shadow-card-subtle"
  >
    <div>
      <Icon name="users" :size="26" class="mx-auto mb-2 text-brand-300" />
      Elegí un cliente del directorio para ver su ficha 360°.
    </div>
  </div>

  <div v-else class="space-y-4">
    <div class="satin-card overflow-hidden rounded-2xl shadow-card-subtle" :class="cargando ? 'opacity-60' : ''">
      <!-- Cabecera -->
      <div class="bg-gradient-to-br from-brand-900 via-brand-800 to-brand-750 p-4 text-white">
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-3">
            <span
              class="grid h-12 w-12 place-items-center rounded-xl bg-amethyst-200 font-display text-lg font-extrabold text-amethyst-950 ring-4 ring-white/15"
            >
              {{ iniciales(cliente.nombre) }}
            </span>
            <div>
              <h3 class="font-display text-[15px] font-bold leading-tight">
                {{ cliente.nombre || `Cliente ${cliente.household_id}` }}
              </h3>
              <p class="mt-0.5 font-mono text-[11px] text-brand-200">
                RUT {{ cliente.documento_identidad || '—' }}
              </p>
              <span
                class="mt-1 inline-flex items-center gap-1 rounded-full bg-amethyst-500 px-2 py-0.5 text-[10px] font-bold text-white"
              >
                <Icon name="tag" :size="11" /> Club Marzú · {{ cliente.nivel_nombre || 'Sin nivel' }}
              </span>
            </div>
          </div>
          <span
            v-if="cliente.severidad_churn"
            class="rounded-full border border-white/20 bg-white/10 px-2 py-0.5 text-[10px] font-semibold"
          >
            {{ cliente.severidad_churn }}
          </span>
        </div>
        <div class="mt-3 grid grid-cols-2 gap-2 border-t border-white/15 pt-2 text-[11px] text-white/80">
          <span class="flex items-center gap-1.5 truncate">
            <Icon name="id" :size="13" /> {{ cliente.telefono || '—' }}
          </span>
          <span class="flex items-center gap-1.5 truncate">
            <Icon name="megaphone" :size="13" /> {{ cliente.email || '—' }}
          </span>
        </div>
      </div>

      <!-- Saldo de puntos -->
      <div class="flex items-center justify-between border-b border-amethyst-100 bg-amethyst-50/70 p-3.5">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-wider text-amethyst-900">
            Saldo puntos Club Marzú
          </p>
          <div class="mt-0.5 flex items-baseline gap-2">
            <span class="font-display text-xl font-extrabold tabular-nums text-amethyst-700">
              {{ (ficha?.puntos ?? 0).toLocaleString('es-CL') }} pts
            </span>
            <span class="text-[11px] font-semibold text-amethyst-700">
              = {{ money(ficha?.valor_canje_clp) }} para canje
            </span>
          </div>
        </div>
        <RouterLink
          to="/pos"
          class="inline-flex items-center gap-1 rounded-lg bg-amethyst-600 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-amethyst-500"
        >
          <Icon name="cart" :size="13" /> Canjear en POS
        </RouterLink>
      </div>

      <!-- Cupones del Club -->
      <div class="border-b border-brand-100 p-3.5">
        <div class="mb-2 flex items-center justify-between">
          <span class="flex items-center gap-1.5 text-[12px] font-bold text-slate-800">
            <Icon name="tag" :size="14" class="text-amethyst-600" />
            Cupones del Club ({{ ficha?.cupones?.length ?? 0 }})
          </span>
          <button
            type="button"
            class="text-[11px] font-semibold text-amethyst-700 hover:underline"
            @click="emit('asignar-cupon', cliente)"
          >
            + Asignar
          </button>
        </div>
        <div v-if="ficha?.cupones?.length" class="space-y-1.5">
          <div
            v-for="cu in ficha.cupones"
            :key="cu.coupon_upc"
            class="flex items-center justify-between rounded-lg border border-brand-200 bg-white px-2.5 py-1.5"
          >
            <div class="min-w-0">
              <p class="truncate text-[11px] font-bold text-slate-800">
                {{ cu.producto || 'Producto' }}
              </p>
              <p class="text-[10px] text-slate-500">
                {{ cu.categoria || '—' }} · vence {{ fmtFecha(cu.end_date) }}
              </p>
            </div>
            <span class="ml-2 shrink-0 font-mono text-[10px] text-slate-400">{{ cu.coupon_upc }}</span>
          </div>
        </div>
        <p v-else class="text-[11px] text-slate-400">Sin cupones asignados pendientes.</p>
      </div>

      <!-- Distribución de consumo -->
      <div v-if="ficha?.consumo?.length" class="border-b border-brand-100 p-3.5">
        <p class="mb-2 flex items-center gap-1.5 text-[12px] font-bold text-slate-800">
          <Icon name="chart" :size="14" class="text-brand-700" /> Distribución de consumo
        </p>
        <div class="flex h-3 overflow-hidden rounded-full bg-slate-100">
          <div
            v-for="(c, i) in ficha.consumo"
            :key="c.categoria"
            class="h-full"
            :class="SEGCOL[i]"
            :style="{ width: (Number(c.monto) / consumoTotal) * 100 + '%' }"
          />
        </div>
        <div class="mt-1.5 grid grid-cols-2 gap-x-2 gap-y-1 text-[10px]">
          <span v-for="(c, i) in ficha.consumo" :key="c.categoria" class="flex items-center gap-1.5">
            <span class="h-2.5 w-2.5 rounded-sm" :class="SEGCOL[i]" />
            <span class="truncate text-slate-600">
              {{ c.categoria }} ({{ Math.round((Number(c.monto) / consumoTotal) * 100) }}%)
            </span>
          </span>
        </div>
      </div>

      <!-- Últimas compras -->
      <div class="p-3.5">
        <p class="mb-2 flex items-center gap-1.5 text-[12px] font-bold text-slate-800">
          <Icon name="clock" :size="14" class="text-slate-500" />
          Últimas compras · {{ ficha?.tickets ?? 0 }} tickets · LTV {{ money(ficha?.ltv) }}
        </p>
        <div v-if="ficha?.compras?.length" class="space-y-1.5">
          <div
            v-for="co in ficha.compras"
            :key="co.venta_id"
            class="flex items-center justify-between rounded-lg bg-brand-50/60 px-2.5 py-1.5"
          >
            <div>
              <p class="text-[11px] font-bold text-slate-800">
                {{ fmtFecha(co.fecha_hora) }} · Ticket #{{ co.venta_id }}
              </p>
              <p class="text-[10px] text-slate-500">{{ co.tienda }} · {{ co.items }} ítems</p>
            </div>
            <div class="text-right">
              <p class="font-bold tabular-nums text-slate-900">{{ money(co.total) }}</p>
              <p class="text-[9px] font-semibold text-emerald-700">+{{ co.puntos }} pts</p>
            </div>
          </div>
        </div>
        <p v-else class="text-[11px] text-slate-400">Sin compras registradas.</p>

        <div class="mt-3 grid grid-cols-2 gap-2 border-t border-brand-100 pt-3">
          <button
            type="button"
            class="rounded-lg border border-brand-200 py-2 text-[12px] font-semibold text-slate-700 hover:bg-brand-50"
            @click="emit('editar', cliente)"
          >
            <Icon name="pencil" :size="13" class="mr-1 inline" /> Editar contacto
          </button>
          <button
            type="button"
            class="rounded-lg bg-brand-800 py-2 text-[12px] font-bold text-white hover:bg-brand-700"
            @click="emit('asignar-cupon', cliente)"
          >
            <Icon name="tag" :size="13" class="mr-1 inline" /> Asignar cupón
          </button>
        </div>
      </div>
    </div>

    <div class="satin-card rounded-2xl p-4 shadow-card-subtle">
      <p class="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-brand-900">
        <Icon name="shield" :size="13" class="text-amber-600" /> Reglas de segmentación Club Marzú
      </p>
      <ul class="space-y-1.5 text-[11px]">
        <li
          v-for="n in niveles"
          :key="n.nivel_id"
          class="flex items-center justify-between rounded px-2 py-1"
          :class="TIER[n.nombre] || 'bg-slate-50 text-slate-700'"
        >
          <span class="font-semibold">Nivel {{ n.nombre }}</span>
          <span class="font-mono font-bold tabular-nums">CLV ≥ {{ Number(n.umbral_clv_min).toFixed(2) }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>
