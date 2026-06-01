import { apiFetch } from '../../../lib/api'

export interface WarehouseOut {
  id: string
  name: string
  is_default: boolean
  is_active: boolean
}

export function fetchWarehouses(): Promise<WarehouseOut[]> {
  return apiFetch<WarehouseOut[]>('/warehouses')
}
