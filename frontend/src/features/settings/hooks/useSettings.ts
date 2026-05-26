import { useEffect, useState } from 'react'
import { apiFetch } from '../../../lib/api'

interface SettingOut {
  key: string
  value: unknown
}

export function useSettings() {
  const [businessName, setBusinessName] = useState<string>('DTCore')

  useEffect(() => {
    apiFetch<SettingOut>('/settings/business_name')
      .then((s) => {
        if (typeof s.value === 'string' && s.value) setBusinessName(s.value)
      })
      .catch(() => {
        // keep default on error
      })
  }, [])

  return { businessName }
}
