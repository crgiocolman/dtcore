import { apiFetch } from '../../../lib/api'

export interface SalesByPeriodItem {
  period: string
  total_pyg: string
  sale_count: number
}

export interface SalesByPeriodOut {
  items: SalesByPeriodItem[]
  date_from: string
  date_to: string
  group_by: string
}

export interface TopProductItem {
  product_id: string
  product_name: string
  sku: string
  quantity_sold: string
  total_pyg: string
}

export interface TopProductsOut {
  by_quantity: TopProductItem[]
  by_amount: TopProductItem[]
  date_from: string
  date_to: string
}

export interface ProfitByProductItem {
  product_id: string
  product_name: string
  sku: string
  revenue_pyg: string
  cost_pyg: string
  profit_pyg: string
  margin_pct: string | null
}

export interface ProfitByProductOut {
  items: ProfitByProductItem[]
  date_from: string
  date_to: string
  total_revenue_pyg: string
  total_cost_pyg: string
  total_profit_pyg: string
}

export interface LowStockProduct {
  product_id: string
  sku: string
  product_name: string
  warehouse_id: string
  quantity_base: string
  threshold: string
}

export interface LowStockOut {
  items: LowStockProduct[]
  warehouse_id: string | null
}

export interface StockValueCategoryItem {
  category_id: string | null
  category_name: string | null
  total_value: string
}

export interface StockValueOut {
  total_value: string
  warehouse_id: string | null
  by_category: StockValueCategoryItem[]
}

export function fetchSalesByPeriod(params: {
  date_from: string
  date_to: string
  group_by?: 'day' | 'week' | 'month'
  warehouse_id?: string
}): Promise<SalesByPeriodOut> {
  const q = new URLSearchParams({
    date_from: params.date_from,
    date_to: params.date_to,
    group_by: params.group_by ?? 'day',
  })
  if (params.warehouse_id) q.set('warehouse_id', params.warehouse_id)
  return apiFetch(`/reports/sales-by-period?${q}`)
}

export function fetchTopProducts(params: {
  date_from: string
  date_to: string
  limit?: number
  warehouse_id?: string
}): Promise<TopProductsOut> {
  const q = new URLSearchParams({
    date_from: params.date_from,
    date_to: params.date_to,
    limit: String(params.limit ?? 10),
  })
  if (params.warehouse_id) q.set('warehouse_id', params.warehouse_id)
  return apiFetch(`/reports/top-products?${q}`)
}

export function fetchProfitByProduct(params: {
  date_from: string
  date_to: string
  warehouse_id?: string
}): Promise<ProfitByProductOut> {
  const q = new URLSearchParams({
    date_from: params.date_from,
    date_to: params.date_to,
  })
  if (params.warehouse_id) q.set('warehouse_id', params.warehouse_id)
  return apiFetch(`/reports/profit-by-product?${q}`)
}

export function fetchLowStock(warehouseId?: string): Promise<LowStockOut> {
  const q = new URLSearchParams()
  if (warehouseId) q.set('warehouse_id', warehouseId)
  const qs = q.toString()
  return apiFetch(`/reports/low-stock${qs ? `?${qs}` : ''}`)
}

export function fetchStockValue(warehouseId?: string): Promise<StockValueOut> {
  const q = new URLSearchParams()
  if (warehouseId) q.set('warehouse_id', warehouseId)
  const qs = q.toString()
  return apiFetch(`/reports/stock-value${qs ? `?${qs}` : ''}`)
}
