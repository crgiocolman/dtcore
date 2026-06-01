import { apiFetch } from '../../../lib/api'

export type PurchaseStatus = 'draft' | 'confirmed' | 'cancelled'

export interface PurchaseListItem {
  id: string
  purchase_number: string | null
  supplier_id: string
  supplier_name: string | null
  supplier_document_number: string | null
  purchase_date: string
  warehouse_id: string
  currency_code: string
  exchange_rate: string
  subtotal: string
  tax_total: string
  total: string
  total_base_currency: string
  status: PurchaseStatus
  notes: string | null
  confirmed_at: string | null
  cancelled_at: string | null
  cancelled_reason: string | null
  created_at: string
  updated_at: string
  created_by_user_id: string | null
  updated_by_user_id: string | null
}

export interface PurchaseListOut {
  items: PurchaseListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PurchaseListParams {
  supplier_id?: string
  status?: PurchaseStatus
  date_from?: string
  date_to?: string
  warehouse_id?: string
  page?: number
  page_size?: number
}

export interface PurchaseItemOut {
  id: string
  purchase_id: string
  product_id: string
  product_unit_id: string
  quantity: string
  quantity_base: string
  unit_cost: string
  unit_cost_base_currency: string
  tax_rate: string
  tax_included: boolean
  subtotal: string
  tax_amount: string
  total: string
  line_number: number
}

export interface PurchaseOut extends PurchaseListItem {
  items: PurchaseItemOut[]
}

export interface PurchaseCreate {
  id: string
  supplier_id: string
  supplier_document_number?: string | null
  purchase_date: string
  warehouse_id: string
  currency_code: string
  exchange_rate: number
  notes?: string | null
}

export interface PurchaseUpdate {
  supplier_id?: string
  supplier_document_number?: string | null
  purchase_date?: string
  warehouse_id?: string
  currency_code?: string
  exchange_rate?: number
  notes?: string | null
}

export interface PurchaseItemCreate {
  id: string
  product_id: string
  product_unit_id: string
  quantity: number
  unit_cost: number
  tax_rate?: number
}

export interface PurchaseItemUpdate {
  quantity?: number
  unit_cost?: number
}

export function fetchPurchase(id: string): Promise<PurchaseOut> {
  return apiFetch<PurchaseOut>(`/purchases/${id}`)
}

export function createPurchase(data: PurchaseCreate): Promise<PurchaseOut> {
  return apiFetch<PurchaseOut>('/purchases', { method: 'POST', body: JSON.stringify(data) })
}

export function updatePurchase(id: string, data: PurchaseUpdate): Promise<PurchaseOut> {
  return apiFetch<PurchaseOut>(`/purchases/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deletePurchase(id: string): Promise<void> {
  return apiFetch<void>(`/purchases/${id}`, { method: 'DELETE' })
}

export function addPurchaseItem(purchaseId: string, data: PurchaseItemCreate): Promise<PurchaseItemOut> {
  return apiFetch<PurchaseItemOut>(`/purchases/${purchaseId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updatePurchaseItem(
  purchaseId: string,
  itemId: string,
  data: PurchaseItemUpdate,
): Promise<PurchaseItemOut> {
  return apiFetch<PurchaseItemOut>(`/purchases/${purchaseId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function removePurchaseItem(purchaseId: string, itemId: string): Promise<void> {
  return apiFetch<void>(`/purchases/${purchaseId}/items/${itemId}`, { method: 'DELETE' })
}

export function confirmPurchase(id: string): Promise<PurchaseOut> {
  return apiFetch<PurchaseOut>(`/purchases/${id}/confirm`, { method: 'POST' })
}

export function cancelPurchase(id: string, reason: string): Promise<PurchaseOut> {
  return apiFetch<PurchaseOut>(`/purchases/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export interface PurchaseAuditEntry {
  id: string
  action: 'create' | 'confirm' | 'cancel'
  user_id: string
  user_name: string
  created_at: string
  changes: Record<string, unknown> | null
}

export function fetchPurchaseAudit(id: string): Promise<PurchaseAuditEntry[]> {
  return apiFetch<PurchaseAuditEntry[]>(`/purchases/${id}/audit`)
}

export function fetchPurchases(params: PurchaseListParams = {}): Promise<PurchaseListOut> {
  const qs = new URLSearchParams()
  if (params.supplier_id) qs.set('supplier_id', params.supplier_id)
  if (params.status) qs.set('status', params.status)
  if (params.date_from) qs.set('date_from', params.date_from)
  if (params.date_to) qs.set('date_to', params.date_to)
  if (params.warehouse_id) qs.set('warehouse_id', params.warehouse_id)
  if (params.page != null) qs.set('page', String(params.page))
  if (params.page_size != null) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return apiFetch<PurchaseListOut>(`/purchases${query ? `?${query}` : ''}`)
}
