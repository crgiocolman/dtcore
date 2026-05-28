import { apiFetch } from '../../../lib/api'
import type { UnitCatalogOut } from '../../admin/api/unit_catalog'

export type { UnitCatalogOut } from '../../admin/api/unit_catalog'

export interface ProductOut {
  id: string
  sku: string
  barcode: string | null
  name: string
  description: string | null
  category_id: string | null
  base_unit_id: string
  base_unit_catalog: UnitCatalogOut | null
  track_stock: boolean
  tax_rate: string
  tax_included_in_price: boolean
  low_stock_threshold: string | null
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
  include_deleted?: boolean
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
  base_unit_id: string
  track_stock: boolean
  tax_rate: string
  tax_included_in_price: boolean
  low_stock_threshold: string | null
}

export interface ProductUpdate {
  sku?: string
  barcode?: string | null
  name?: string
  description?: string | null
  category_id?: string | null
  base_unit_id?: string
  track_stock?: boolean
  tax_rate?: string
  tax_included_in_price?: boolean
  low_stock_threshold?: string | null
}

export interface ProductSearchResult {
  id: string
  sku: string
  barcode: string | null
  name: string
  base_unit_id: string
  base_unit_catalog: UnitCatalogOut | null
  tax_rate: string
  tax_included_in_price: boolean
  category_id: string | null
  similarity: number
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
  if (params.include_deleted) qs.set('include_deleted', 'true')
  if (params.page != null) qs.set('page', String(params.page))
  if (params.page_size != null) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return apiFetch<ProductListOut>(`/products${query ? `?${query}` : ''}`)
}

export function restoreProduct(id: string): Promise<ProductOut> {
  return apiFetch<ProductOut>(`/products/${id}/restore`, { method: 'POST' })
}

export function searchProducts(q: string): Promise<ProductSearchResult[]> {
  return apiFetch<ProductSearchResult[]>(`/products/search?q=${encodeURIComponent(q)}`)
}
