import { apiFetch } from '../../../lib/api'

export interface SettingOut {
  key: string
  value_type: 'string' | 'int' | 'decimal' | 'bool' | 'json'
  value: unknown
  description: string | null
  updated_at: string
  updated_by_user_id: string | null
}

export function fetchAllSettings(): Promise<SettingOut[]> {
  return apiFetch<SettingOut[]>('/settings')
}

export function updateSetting(key: string, value: unknown): Promise<SettingOut> {
  return apiFetch<SettingOut>(`/settings/${key}`, {
    method: 'PUT',
    body: JSON.stringify({ value }),
  })
}
