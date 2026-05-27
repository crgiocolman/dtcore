import { BarChart3, Boxes, Coins, FolderTree, Home, Package, Receipt, Settings, ShoppingCart, Truck, Users } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Inicio', to: '/', end: true, Icon: Home },
  { label: 'POS', to: '/pos', end: false, Icon: ShoppingCart },
  { label: 'Ventas', to: '/ventas', end: false, Icon: Receipt },
  { label: 'Compras', to: '/compras', end: false, Icon: Truck },
  { label: 'Productos', to: '/productos', end: false, Icon: Package },
  { label: 'Contactos', to: '/contactos', end: false, Icon: Users },
  { label: 'Inventario', to: '/inventario', end: false, Icon: Boxes },
  { label: 'Reportes', to: '/reportes', end: false, Icon: BarChart3 },
  { label: 'Configuración', to: '/admin/settings', end: false, Icon: Settings },
  { label: 'Monedas', to: '/admin/currencies', end: false, Icon: Coins },
  { label: 'Categorías', to: '/admin/categorias', end: false, Icon: FolderTree },
]

export function Sidebar() {
  return (
    <nav className="flex w-52 flex-shrink-0 flex-col border-r border-border-subtle bg-bg-surface">
      <ul className="flex-1 space-y-0.5 p-2 pt-3">
        {NAV_ITEMS.map(({ label, to, end, Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-500/10 text-primary-500'
                    : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary'
                }`
              }
            >
              <Icon className="w-5 h-5 shrink-0" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
