import {
  BarChart3,
  Boxes,
  ClipboardEdit,
  Coins,
  FolderTree,
  Home,
  Package,
  PackagePlus,
  Receipt,
  Ruler,
  Settings,
  ShoppingCart,
  Truck,
  Users,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../features/auth/store'
import { useUIStore } from '../lib/uiStore'

type NavItem = {
  label: string
  to: string
  end?: boolean
  Icon: React.ComponentType<{ className?: string }>
  adminOnly?: boolean
}

const HOME_ITEM: NavItem = { label: 'Inicio', to: '/', end: true, Icon: Home }

const SIDEBAR_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Operación',
    items: [
      { label: 'POS', to: '/pos', Icon: ShoppingCart },
      { label: 'Ventas', to: '/ventas', Icon: Receipt },
      { label: 'Compras', to: '/compras', Icon: Truck },
      { label: 'Ajustes', to: '/ajustes', Icon: ClipboardEdit },
    ],
  },
  {
    label: 'Catálogo',
    items: [
      { label: 'Productos', to: '/productos', Icon: Package },
      { label: 'Categorías', to: '/admin/categorias', Icon: FolderTree },
      { label: 'Contactos', to: '/contactos', Icon: Users },
    ],
  },
  {
    label: 'Inventario',
    items: [
      { label: 'Stock actual', to: '/inventario', Icon: Boxes },
      { label: 'Inventario inicial', to: '/admin/inventario-inicial', Icon: PackagePlus, adminOnly: true },
    ],
  },
  {
    label: 'Reportes',
    items: [{ label: 'Reportes', to: '/reportes', Icon: BarChart3 }],
  },
  {
    label: 'Configuración',
    items: [
      { label: 'Settings', to: '/admin/settings', Icon: Settings },
      { label: 'Monedas', to: '/admin/currencies', Icon: Coins },
      { label: 'Unidades', to: '/admin/units', Icon: Ruler },
    ],
  },
]

function SidebarNavItem({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const { label, to, end, Icon } = item
  return (
    <li>
      <div className="relative group/item">
        <NavLink
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex items-center rounded px-3 py-2 text-sm font-medium transition-colors ${
              collapsed ? 'justify-center' : 'gap-2.5'
            } ${
              isActive
                ? 'bg-primary-500/10 text-primary-500'
                : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary'
            }`
          }
        >
          <Icon className="w-5 h-5 shrink-0" />
          {!collapsed && label}
        </NavLink>
        {collapsed && (
          <span className="pointer-events-none absolute left-full top-1/2 ml-2 -translate-y-1/2 z-50 rounded px-2 py-1 text-xs text-text-primary bg-bg-elevated border border-border-subtle whitespace-nowrap opacity-0 group-hover/item:opacity-100 transition-opacity duration-150">
            {label}
          </span>
        )}
      </div>
    </li>
  )
}

export function Sidebar() {
  const user = useAuthStore((s) => s.user)
  const sidebarState = useUIStore((s) => s.sidebarState)

  const collapsed = sidebarState === 'collapsed'
  const hidden = sidebarState === 'hidden'

  return (
    <nav
      className={`flex flex-shrink-0 flex-col border-r border-border-subtle bg-bg-surface overflow-hidden transition-all duration-200 ${
        hidden ? 'w-0' : collapsed ? 'w-[60px]' : 'w-52'
      }`}
    >
      <ul className="flex-1 overflow-y-auto overflow-x-hidden p-2 pt-3 space-y-0.5">
        <SidebarNavItem item={HOME_ITEM} collapsed={collapsed} />

        {SIDEBAR_SECTIONS.map((section, idx) => {
          const visibleItems = section.items.filter(
            (item) => !item.adminOnly || user?.role === 'admin'
          )
          if (visibleItems.length === 0) return null

          return (
            <li key={section.label} className={idx === 0 ? 'mt-2' : 'mt-1'}>
              {collapsed ? (
                <div className="border-b border-border-subtle mx-2 mb-1 mt-2" />
              ) : (
                <div className="px-3 pt-3 pb-1">
                  <span className="text-xs uppercase tracking-wider text-text-muted">
                    {section.label}
                  </span>
                </div>
              )}
              <ul className="space-y-0.5">
                {visibleItems.map((item) => (
                  <SidebarNavItem key={item.to} item={item} collapsed={collapsed} />
                ))}
              </ul>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
