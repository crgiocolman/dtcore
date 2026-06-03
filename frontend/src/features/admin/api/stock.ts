import { apiFetch } from '../../../lib/api'

export interface InitialInventoryItem {
  product_id: string
  quantity_base: string
  unit_cost_base: string
}

export interface InitialInventoryRequest {
  warehouse_id: string
  items: InitialInventoryItem[]
}

export function applyInitialInventory(data: InitialInventoryRequest): Promise<unknown> {
  return apiFetch('/stock/initial', { method: 'POST', body: JSON.stringify(data) })
}

export interface StockCurrentOut {
  product_id: string
  warehouse_id: string
  quantity_base: string
  avg_cost_base: string
  last_movement_at: string | null
  updated_at: string
}

interface StockSummaryPage {
  items: { product_id: string; avg_cost_base: string }[]
  total_pages: number
}

export async function fetchStockedProductIds(warehouseId: string): Promise<Set<string>> {
  const first = await apiFetch<StockSummaryPage>(
    `/stock?warehouse_id=${warehouseId}&page_size=500&page=1`,
  )
  const ids = new Set(first.items.map((i) => i.product_id))
  if (first.total_pages > 1) {
    const pages = Array.from({ length: first.total_pages - 1 }, (_, i) => i + 2)
    const rest = await Promise.all(
      pages.map((page) =>
        apiFetch<StockSummaryPage>(
          `/stock?warehouse_id=${warehouseId}&page_size=500&page=${page}`,
        ),
      ),
    )
    rest.forEach((r) => r.items.forEach((i) => ids.add(i.product_id)))
  }
  return ids
}

export function fetchProductStock(productId: string): Promise<StockCurrentOut[]> {
  return apiFetch<StockCurrentOut[]>(`/stock/products/${productId}`)
}
