import { apiFetch } from '../../../lib/api'

export type AdjustmentStatus = 'draft' | 'confirmed' | 'cancelled'
export type StockDirection = 'in' | 'out'
export type AdjustmentReason = 'inventory_count' | 'damage' | 'loss' | 'expired' | 'correction' | 'other'

export interface AdjustmentListItem {
  id: string
  adjustment_number: string
  warehouse_id: string
  adjustment_date: string
  reason: AdjustmentReason
  status: AdjustmentStatus
  notes: string | null
  created_at: string
  updated_at: string
  created_by_user_id: string | null
  updated_by_user_id: string | null
}

export interface AdjustmentListOut {
  items: AdjustmentListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AdjustmentListParams {
  warehouse_id?: string
  status?: AdjustmentStatus
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface AdjustmentItemOut {
  id: string
  adjustment_id: string
  product_id: string
  product_unit_id: string
  quantity: string
  quantity_base: string
  direction: StockDirection
  unit_cost_base: string | null
  notes: string | null
}

export interface AdjustmentOut extends AdjustmentListItem {
  items: AdjustmentItemOut[]
}

export interface AdjustmentCreate {
  id: string
  warehouse_id: string
  adjustment_date: string
  reason: AdjustmentReason
  notes?: string | null
}

export interface AdjustmentUpdate {
  warehouse_id?: string
  adjustment_date?: string
  reason?: AdjustmentReason
  notes?: string | null
}

export interface AdjustmentItemCreate {
  id: string
  product_id: string
  product_unit_id: string
  quantity: number
  direction: StockDirection
  unit_cost_base?: number | null
  notes?: string | null
}

export interface AdjustmentAuditEntry {
  id: string
  action: 'create' | 'confirm' | 'cancel'
  user_id: string
  user_name: string
  created_at: string
  changes: Record<string, unknown> | null
}

export function fetchAdjustment(id: string): Promise<AdjustmentOut> {
  return apiFetch<AdjustmentOut>(`/adjustments/${id}`)
}

export function fetchAdjustments(params: AdjustmentListParams = {}): Promise<AdjustmentListOut> {
  const qs = new URLSearchParams()
  if (params.warehouse_id) qs.set('warehouse_id', params.warehouse_id)
  if (params.status) qs.set('status', params.status)
  if (params.date_from) qs.set('date_from', params.date_from)
  if (params.date_to) qs.set('date_to', params.date_to)
  if (params.page != null) qs.set('page', String(params.page))
  if (params.page_size != null) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return apiFetch<AdjustmentListOut>(`/adjustments${query ? `?${query}` : ''}`)
}

export function createAdjustment(data: AdjustmentCreate): Promise<AdjustmentOut> {
  return apiFetch<AdjustmentOut>('/adjustments', { method: 'POST', body: JSON.stringify(data) })
}

export function updateAdjustment(id: string, data: AdjustmentUpdate): Promise<AdjustmentOut> {
  return apiFetch<AdjustmentOut>(`/adjustments/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteAdjustment(id: string): Promise<void> {
  return apiFetch<void>(`/adjustments/${id}`, { method: 'DELETE' })
}

export function addAdjustmentItem(adjustmentId: string, data: AdjustmentItemCreate): Promise<AdjustmentItemOut> {
  return apiFetch<AdjustmentItemOut>(`/adjustments/${adjustmentId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function removeAdjustmentItem(adjustmentId: string, itemId: string): Promise<void> {
  return apiFetch<void>(`/adjustments/${adjustmentId}/items/${itemId}`, { method: 'DELETE' })
}

export function confirmAdjustment(id: string): Promise<AdjustmentOut> {
  return apiFetch<AdjustmentOut>(`/adjustments/${id}/confirm`, { method: 'POST' })
}

export function cancelAdjustment(id: string, reason: string): Promise<AdjustmentOut> {
  return apiFetch<AdjustmentOut>(`/adjustments/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export function fetchAdjustmentAudit(id: string): Promise<AdjustmentAuditEntry[]> {
  return apiFetch<AdjustmentAuditEntry[]>(`/adjustments/${id}/audit`)
}
