import { apiFetch } from '../../../lib/api'

export type SaleStatus = 'draft' | 'confirmed' | 'cancelled'
export type PaymentMethod = 'cash' | 'transfer' | 'card' | 'check' | 'other'
export type DiscountType = 'amount' | 'percent'

export interface SaleCreate {
  id: string
  customer_id?: string | null
  sale_date: string
  warehouse_id: string
  currency_code: string
  exchange_rate: number
  notes?: string | null
  header_discount_amount: number
  header_discount_type: DiscountType
  header_discount_percent?: number | null
}

export interface SaleItemCreate {
  id: string
  product_id: string
  product_unit_id: string
  quantity: number
  unit_price: number
  discount_amount: number
  discount_type: DiscountType
  tax_rate?: number
}

export interface SalePaymentCreate {
  id: string
  payment_method: PaymentMethod
  amount: number
  reference?: string | null
  notes?: string | null
}

export interface SaleItemOut {
  id: string
  sale_id: string
  product_id: string
  product_unit_id: string
  product_name: string | null
  unit_name: string | null
  quantity: string
  quantity_base: string
  unit_price: string
  discount_amount: string
  discount_type: DiscountType
  tax_rate: string
  tax_included: boolean
  subtotal: string
  tax_amount: string
  total: string
  unit_cost_base_at_sale: string
  line_number: number
}

export interface SalePaymentOut {
  id: string
  sale_id: string
  payment_method: PaymentMethod
  amount: string
  reference: string | null
  notes: string | null
  created_at: string
}

export interface SaleListItem {
  id: string
  sale_number: string | null
  customer_id: string | null
  customer_name: string | null
  sale_date: string
  warehouse_id: string
  currency_code: string
  exchange_rate: string
  items_subtotal: string
  items_discount_total: string
  header_discount_amount: string
  header_discount_type: DiscountType
  header_discount_percent: string | null
  tax_total: string
  total: string
  total_base_currency: string
  cost_total_base: string
  status: SaleStatus
  notes: string | null
  cancelled_at: string | null
  cancelled_reason: string | null
  created_at: string
  updated_at: string
  created_by_user_id: string | null
  updated_by_user_id: string | null
}

export interface SaleOut extends SaleListItem {
  items: SaleItemOut[]
  payments: SalePaymentOut[]
}

export function createSale(data: SaleCreate): Promise<SaleOut> {
  return apiFetch<SaleOut>('/sales', { method: 'POST', body: JSON.stringify(data) })
}

export function addSaleItem(saleId: string, data: SaleItemCreate): Promise<SaleItemOut> {
  return apiFetch<SaleItemOut>(`/sales/${saleId}/items`, { method: 'POST', body: JSON.stringify(data) })
}

export function addSalePayment(saleId: string, data: SalePaymentCreate): Promise<SalePaymentOut> {
  return apiFetch<SalePaymentOut>(`/sales/${saleId}/payments`, { method: 'POST', body: JSON.stringify(data) })
}

export function confirmSale(saleId: string): Promise<SaleOut> {
  return apiFetch<SaleOut>(`/sales/${saleId}/confirm`, { method: 'POST' })
}

export function cancelSale(saleId: string, reason: string): Promise<SaleOut> {
  return apiFetch<SaleOut>(`/sales/${saleId}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) })
}

export interface SaleListParams {
  page?: number
  page_size?: number
  status?: SaleStatus
  customer_id?: string
  date_from?: string
  date_to?: string
}

export interface SaleListOut {
  items: SaleListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export function fetchSales(params: SaleListParams = {}): Promise<SaleListOut> {
  const q = new URLSearchParams()
  if (params.page) q.set('page', String(params.page))
  if (params.page_size) q.set('page_size', String(params.page_size))
  if (params.status) q.set('status', params.status)
  if (params.customer_id) q.set('customer_id', params.customer_id)
  if (params.date_from) q.set('date_from', params.date_from + 'T00:00:00')
  if (params.date_to) q.set('date_to', params.date_to + 'T23:59:59')
  return apiFetch<SaleListOut>(`/sales?${q}`)
}

export function getSale(saleId: string): Promise<SaleOut> {
  return apiFetch<SaleOut>(`/sales/${saleId}`)
}
