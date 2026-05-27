import { apiFetch } from '../../../lib/api'

export interface ProductOut {
  id: string
  sku: string
  barcode: string | null
  name: string
  description: string | null
  category_id: string | null
  base_unit: string
  track_stock: boolean
  tax_rate: string
  tax_included_in_price: boolean
  low_stock_threshold: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
  created_by_user_id: string | null
  updated_by_user_id: string | null
}

export interface ProductListOut {
  items: ProductOut[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ProductListParams {
  search?: string
  category_id?: string
  is_active?: boolean
  page?: number
  page_size?: number
}

export interface ProductCreate {
  id: string
  sku: string
  barcode: string | null
  name: string
  description: string | null
  category_id: string | null
  base_unit: string
  track_stock: boolean
  tax_rate: string
  tax_included_in_price: boolean
  low_stock_threshold: string | null
  is_active: boolean
}

export interface ProductUpdate {
  sku?: string
  barcode?: string | null
  name?: string
  description?: string | null
  category_id?: string | null
  base_unit?: string
  track_stock?: boolean
  tax_rate?: string
  tax_included_in_price?: boolean
  low_stock_threshold?: string | null
  is_active?: boolean
}

export function fetchProduct(id: string): Promise<ProductOut> {
  return apiFetch<ProductOut>(`/products/${id}`)
}

export function createProduct(data: ProductCreate): Promise<ProductOut> {
  return apiFetch<ProductOut>('/products', { method: 'POST', body: JSON.stringify(data) })
}

export function updateProduct(id: string, data: ProductUpdate): Promise<ProductOut> {
  return apiFetch<ProductOut>(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteProduct(id: string): Promise<void> {
  return apiFetch<void>(`/products/${id}`, { method: 'DELETE' })
}

export function fetchProducts(params: ProductListParams = {}): Promise<ProductListOut> {
  const qs = new URLSearchParams()
  if (params.search) qs.set('search', params.search)
  if (params.category_id) qs.set('category_id', params.category_id)
  if (params.is_active != null) qs.set('is_active', String(params.is_active))
  if (params.page != null) qs.set('page', String(params.page))
  if (params.page_size != null) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return apiFetch<ProductListOut>(`/products${query ? `?${query}` : ''}`)
}
