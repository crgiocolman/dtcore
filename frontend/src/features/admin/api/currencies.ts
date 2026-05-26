import { apiFetch } from '../../../lib/api'

export interface CurrencyOut {
  code: string
  name: string
  symbol: string
  decimal_places: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ExchangeRateOut {
  id: string
  currency_code: string
  rate_to_base: string // Decimal serialized as string by Pydantic v2
  effective_date: string
  notes: string | null
  created_at: string
  created_by_user_id: string | null
  can_edit: boolean
}

export interface ExchangeRateCreate {
  id: string
  rate_to_base: number
  effective_date: string
  notes?: string
}

export interface ExchangeRatePatch {
  rate_to_base: number
  notes?: string | null
}

export function fetchCurrencies(): Promise<CurrencyOut[]> {
  return apiFetch<CurrencyOut[]>('/currencies')
}

export function toggleCurrency(code: string, is_active: boolean): Promise<CurrencyOut> {
  return apiFetch<CurrencyOut>(`/currencies/${code}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active }),
  })
}

export function fetchExchangeRates(code: string): Promise<ExchangeRateOut[]> {
  return apiFetch<ExchangeRateOut[]>(`/currencies/${code}/rates`)
}

export function createExchangeRate(code: string, data: ExchangeRateCreate): Promise<ExchangeRateOut> {
  return apiFetch<ExchangeRateOut>(`/currencies/${code}/rates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateExchangeRate(id: string, data: ExchangeRatePatch): Promise<ExchangeRateOut> {
  return apiFetch<ExchangeRateOut>(`/exchange-rates/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteExchangeRate(id: string): Promise<void> {
  return apiFetch<void>(`/exchange-rates/${id}`, { method: 'DELETE' })
}
