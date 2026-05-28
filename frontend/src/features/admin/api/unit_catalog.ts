import { apiFetch } from '../../../lib/api'

export type UnitType = 'weight' | 'length' | 'volume' | 'count' | 'package'

export interface UnitCatalogOut {
  id: string
  code: string
  name: string
  symbol: string
  unit_type: UnitType
  is_active: boolean
}

export interface UnitCatalogCreate {
  id: string
  code: string
  name: string
  symbol: string
  unit_type: UnitType
}

export interface UnitCatalogUpdate {
  name?: string
  symbol?: string
  unit_type?: UnitType
  is_active?: boolean
}

export const UNIT_TYPE_LABELS: Record<UnitType, string> = {
  weight: 'Peso',
  length: 'Longitud',
  volume: 'Volumen',
  count: 'Cantidad',
  package: 'Empaque',
}

export function fetchUnitCatalog(onlyActive?: boolean): Promise<UnitCatalogOut[]> {
  const qs = onlyActive ? '?active_only=true' : ''
  return apiFetch<UnitCatalogOut[]>(`/units${qs}`)
}

export function createUnitCatalog(data: UnitCatalogCreate): Promise<UnitCatalogOut> {
  return apiFetch<UnitCatalogOut>('/units', { method: 'POST', body: JSON.stringify(data) })
}

export function updateUnitCatalog(id: string, data: UnitCatalogUpdate): Promise<UnitCatalogOut> {
  return apiFetch<UnitCatalogOut>(`/units/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteUnitCatalog(id: string): Promise<void> {
  return apiFetch<void>(`/units/${id}`, { method: 'DELETE' })
}
