export * from '../../dashboard/api/reports'

import { apiFetch } from '../../../lib/api'

export interface KardexLine {
  id: string
  movement_type: string
  direction: 'in' | 'out'
  created_at: string
  quantity_base: string
  unit_cost_base: string | null
  balance_after: string
  reference_type: string | null
  reference_id: string | null
  notes: string | null
}

export interface KardexOut {
  product_id: string
  warehouse_id: string
  date_from: string | null
  date_to: string | null
  lines: KardexLine[]
}

export function fetchKardex(
  productId: string,
  params: { warehouse_id?: string; date_from?: string; date_to?: string } = {}
): Promise<KardexOut> {
  const q = new URLSearchParams()
  if (params.warehouse_id) q.set('warehouse_id', params.warehouse_id)
  if (params.date_from) q.set('date_from', params.date_from)
  if (params.date_to) q.set('date_to', params.date_to)
  const qs = q.toString()
  return apiFetch<KardexOut>(`/reports/kardex/${productId}${qs ? `?${qs}` : ''}`)
}
