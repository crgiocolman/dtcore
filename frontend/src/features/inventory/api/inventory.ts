import { apiFetch } from '../../../lib/api'

export interface InventoryItem {
  product_id: string
  product_name: string
  product_sku: string
  warehouse_id: string
  warehouse_name: string
  quantity_base: string
  avg_cost_base: string
  base_unit_symbol: string | null
  last_movement_at: string | null
  is_low_stock: boolean
  category_id: string | null
  category_name: string | null
}

export interface InventoryPage {
  items: InventoryItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type SortKey =
  | 'product_name'
  | 'product_sku'
  | 'quantity_base'
  | 'avg_cost_base'
  | 'total_value'
  | 'last_movement_at'
  | 'category_name'

export function fetchInventory(params: {
  search?: string
  category_id?: string
  with_stock_only?: boolean
  low_stock_only?: boolean
  sort_by?: SortKey
  sort_dir?: 'asc' | 'desc'
  page?: number
  page_size?: number
}): Promise<InventoryPage> {
  const q = new URLSearchParams()
  if (params.search) q.set('search', params.search)
  if (params.category_id) q.set('category_id', params.category_id)
  if (params.with_stock_only) q.set('with_stock_only', 'true')
  if (params.low_stock_only) q.set('low_stock_only', 'true')
  if (params.sort_by) q.set('sort_by', params.sort_by)
  if (params.sort_dir) q.set('sort_dir', params.sort_dir)
  if (params.page != null) q.set('page', String(params.page))
  if (params.page_size != null) q.set('page_size', String(params.page_size))
  return apiFetch<InventoryPage>(`/stock?${q.toString()}`)
}
