import { LogOut, PanelLeft } from 'lucide-react'
import { Outlet } from 'react-router-dom'
import { useAuthStore } from '../features/auth/store'
import { useSettings } from '../features/settings/hooks/useSettings'
import { useUIStore } from '../lib/uiStore'
import { Sidebar } from './Sidebar'

export function AppLayout() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const { businessName } = useSettings()
  const cycleSidebar = useUIStore((s) => s.cycleSidebar)

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-border-subtle bg-bg-surface px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={cycleSidebar}
            className="btn-ghost p-1"
            aria-label="Toggle sidebar"
          >
            <PanelLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-text-primary">DTCore</span>
            {businessName && businessName !== 'DTCore' && (
              <span className="text-sm text-text-muted">— {businessName}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-text-secondary">{user?.full_name}</span>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Salir
          </button>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto bg-bg-base p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
