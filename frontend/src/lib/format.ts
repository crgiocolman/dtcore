import type { UnitType } from '../features/admin/api/unit_catalog'

export function formatCurrency(value: string | number, decimals = 0): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '—'
  return new Intl.NumberFormat('es-PY', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

export function formatQuantity(value: string | number, unitType: UnitType): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '—'
  if (unitType === 'count' || unitType === 'package') {
    return new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(n)
  }
  // weight / length / volume: hasta 3 decimales, sin trailing zeros
  return new Intl.NumberFormat('es-PY', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(n)
}

export function formatExchangeRate(value: string | number): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '—'
  const hasDecimals = n % 1 !== 0
  return new Intl.NumberFormat('es-PY', {
    minimumFractionDigits: 0,
    maximumFractionDigits: hasDecimals ? 2 : 0,
  }).format(n)
}
