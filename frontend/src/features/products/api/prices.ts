import { apiFetch } from '../../../lib/api'

export interface PriceOut {
  id: string
  product_unit_id: string
  currency_code: string
  price: string
  effective_from: string
  notes: string | null
  created_at: string
  created_by_user_id: string | null
}

export interface PriceCreate {
  id: string
  currency_code: string
  price: string
  effective_from: string
  notes: string | null
}

export function fetchPriceHistory(
  productId: string,
  unitId: string,
  currencyCode: string,
): Promise<PriceOut[]> {
  return apiFetch<PriceOut[]>(
    `/products/${productId}/units/${unitId}/prices?currency_code=${encodeURIComponent(currencyCode)}`,
  )
}

export function createPrice(
  productId: string,
  unitId: string,
  data: PriceCreate,
): Promise<PriceOut> {
  return apiFetch<PriceOut>(`/products/${productId}/units/${unitId}/prices`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
