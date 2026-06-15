import { ApiError, apiFetch } from '../../../lib/api'

export interface PriceOut {
  id: string
  product_unit_id: string
  currency_code: string
  price: string
  effective_from: string
  notes: string | null
  created_at: string
  created_by_user_id: string | null
  can_edit: boolean
  sales_count: number
  is_current: boolean
}

export interface PriceCreate {
  id: string
  currency_code: string
  price: string
  effective_from: string
  notes: string | null
}

export interface PriceUpdate {
  price?: string
  effective_from?: string
  notes?: string | null
}

export interface PriceCanEditOut {
  can_edit: boolean
  sales_count: number
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

export function updatePrice(priceId: string, data: PriceUpdate): Promise<PriceOut> {
  return apiFetch<PriceOut>(`/prices/${priceId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deletePrice(priceId: string): Promise<void> {
  return apiFetch<void>(`/prices/${priceId}`, { method: 'DELETE' })
}

export function checkCanEditPrice(priceId: string): Promise<PriceCanEditOut> {
  return apiFetch<PriceCanEditOut>(`/prices/${priceId}/can-edit`)
}

export async function fetchCurrentPrice(
  productId: string,
  unitId: string,
  currencyCode: string,
  asOfDate?: string,
): Promise<PriceOut | null> {
  const params = new URLSearchParams({ currency_code: currencyCode })
  if (asOfDate) params.set('as_of_date', asOfDate)
  try {
    return await apiFetch<PriceOut>(
      `/products/${productId}/units/${unitId}/current-price?${params}`,
    )
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
