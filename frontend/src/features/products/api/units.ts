import { apiFetch } from '../../../lib/api'

export interface ProductUnitOut {
  id: string
  product_id: string
  unit_name: string
  factor_to_base: string
  is_default_sale_unit: boolean
  is_default_purchase_unit: boolean
  barcode: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductUnitCreate {
  id: string
  unit_name: string
  factor_to_base: string
  is_default_sale_unit: boolean
  is_default_purchase_unit: boolean
  barcode: string | null
  is_active: boolean
}

export interface ProductUnitUpdate {
  unit_name?: string
  factor_to_base?: string
  is_default_sale_unit?: boolean
  is_default_purchase_unit?: boolean
  barcode?: string | null
  is_active?: boolean
}

export function fetchUnits(productId: string): Promise<ProductUnitOut[]> {
  return apiFetch<ProductUnitOut[]>(`/products/${productId}/units`)
}

export function createUnit(productId: string, data: ProductUnitCreate): Promise<ProductUnitOut> {
  return apiFetch<ProductUnitOut>(`/products/${productId}/units`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateUnit(
  productId: string,
  unitId: string,
  data: ProductUnitUpdate,
): Promise<ProductUnitOut> {
  return apiFetch<ProductUnitOut>(`/products/${productId}/units/${unitId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteUnit(productId: string, unitId: string): Promise<void> {
  return apiFetch<void>(`/products/${productId}/units/${unitId}`, { method: 'DELETE' })
}
