/**
 * Utilidades estándar de formateo de moneda en Dólares Estadounidenses (USD).
 */

export function money(v, { decimals = 2, showCode = true } = {}) {
  if (v == null || isNaN(v)) return '—'
  const num = Number(v)
  const formatted = `$${num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`
  return showCode ? `${formatted} USD` : formatted
}

export function moneyShort(v) {
  if (v == null || isNaN(v)) return '—'
  const num = Number(v)
  if (Math.abs(num) >= 1_000_000) {
    return `$${(num / 1_000_000).toFixed(1)}M USD`
  }
  if (Math.abs(num) >= 1_000) {
    return `$${(num / 1_000).toFixed(1)}k USD`
  }
  return `$${num.toFixed(2)} USD`
}
