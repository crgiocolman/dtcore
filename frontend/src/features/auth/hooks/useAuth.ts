import { useEffect } from 'react'
import { useAuthStore } from '../store'

export function useAuth() {
  const store = useAuthStore()

  useEffect(() => {
    if (!store.isAuthenticated) {
      store.initFromStorage()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return store
}
