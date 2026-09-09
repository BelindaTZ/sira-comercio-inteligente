import { money } from '@/shared/currency'

/**
 * Los KPIs de los dashboards multinivel (feature 009) llegan como
 * `{ nombre_kpi, valor, disponible }` sin unidad. El nombre del KPI es un
 * contrato estable del backend (`src/shared/dashboards.py`), así que aquí se
 * deriva cómo presentarlo: moneda USD, conteo o índice 0-10.
 */
const MONEDA = new Set([
  'Ventas netas de la red',
  'Ticket promedio',
  'Merma valorizada',
  'CLV promedio de la cartera',
  'Diferencia de caja acumulada',
])
const INDICE = new Set(['Índice de clima laboral'])

export function formatoKpi(nombreKpi) {
  if (MONEDA.has(nombreKpi)) return 'moneda'
  if (INDICE.has(nombreKpi)) return 'indice'
  return 'numero'
}

export function valorKpi(kpi) {
  if (!kpi?.disponible || kpi.valor == null) return null
  const n = Number(kpi.valor)
  switch (formatoKpi(kpi.nombre_kpi)) {
    case 'moneda':
      return money(n, { decimals: n >= 1000 ? 0 : 2, showCode: false })
    case 'indice':
      return `${n.toFixed(1)} / 10`
    default:
      return Math.round(n).toLocaleString('es-EC')
  }
}
