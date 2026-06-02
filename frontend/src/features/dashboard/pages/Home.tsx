import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '../../../lib/format'
import { MetricCard } from '../components/MetricCard'
import { useDashboard } from '../hooks/useDashboard'

// Design system hex values for Recharts (tokens can't be used directly in SVG props)
const PRIMARY_500 = '#3B82F6'
const SUCCESS_500 = '#10B981'
const WARNING_500 = '#F59E0B'
const DANGER_500 = '#EF4444'
const INFO_500 = '#6366F1'

const PIE_COLORS = [
  PRIMARY_500, SUCCESS_500, WARNING_500, INFO_500,
  '#A78BFA', '#F472B6', '#34D399', '#60A5FA', '#FB923C', DANGER_500,
]

const CHART_GRID = '#1F2C4A'
const CHART_TEXT = '#94A3B8'
const TOOLTIP_STYLE = {
  backgroundColor: '#111A2E',
  border: '1px solid #1F2C4A',
  borderRadius: 6,
  color: '#E8EEF7',
}

function formatPeriodLabel(period: string): string {
  const parts = period.split('-')
  return `${parts[2]}/${parts[1]}`
}

function formatYAxis(value: number): string {
  if (value === 0) return '0'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`
  return String(value)
}

function formatQty(value: string): string {
  const n = parseFloat(value)
  if (isNaN(n)) return '—'
  return n % 1 === 0 ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
}

export function Home() {
  const { salesByPeriod, topProducts, profit, lowStock, stockValue, loading } = useDashboard()

  const totalSales = salesByPeriod?.items.reduce((s, i) => s + parseFloat(i.total_pyg), 0) ?? null
  const saleCount = salesByPeriod?.items.reduce((s, i) => s + i.sale_count, 0) ?? null
  const avgTicket = saleCount && saleCount > 0 && totalSales !== null ? totalSales / saleCount : null
  const totalProfit = profit !== null ? parseFloat(profit.total_profit_pyg) : null
  const inventoryValue = stockValue !== null ? parseFloat(stockValue.total_value) : null

  const barData = salesByPeriod?.items.map((item) => ({
    date: formatPeriodLabel(item.period),
    total: parseFloat(item.total_pyg),
  })) ?? []

  const pieData = topProducts?.by_amount
    .filter((item) => parseFloat(item.total_pyg) > 0)
    .map((item) => ({ name: item.product_name, value: parseFloat(item.total_pyg) })) ?? []

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-text-primary">Inicio</h1>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-24 animate-pulse bg-bg-elevated" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="card lg:col-span-2 h-72 animate-pulse bg-bg-elevated" />
          <div className="card h-72 animate-pulse bg-bg-elevated" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="card lg:col-span-2 h-48 animate-pulse bg-bg-elevated" />
          <div className="card h-48 animate-pulse bg-bg-elevated" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-text-primary">Inicio</h1>

      {/* 4 métricas del mes */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Ventas del mes"
          value={totalSales !== null ? `Gs ${formatCurrency(totalSales)}` : '—'}
          subtitle="ventas confirmadas en PYG"
        />
        <MetricCard
          label="Operaciones"
          value={saleCount !== null ? saleCount : '—'}
          subtitle="ventas del mes"
        />
        <MetricCard
          label="Ticket promedio"
          value={avgTicket !== null ? `Gs ${formatCurrency(avgTicket)}` : '—'}
          subtitle="por operación"
        />
        <MetricCard
          label="Utilidad"
          value={totalProfit !== null ? `Gs ${formatCurrency(totalProfit)}` : '—'}
          subtitle="ingresos − costos"
          valueClassName={
            totalProfit !== null
              ? totalProfit >= 0
                ? 'text-success-500'
                : 'text-danger-500'
              : ''
          }
        />
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* BarChart: ventas por día */}
        <div className="card lg:col-span-2">
          <h2 className="text-base font-semibold text-text-primary mb-4">
            Ventas por día — mes actual
          </h2>
          {barData.length === 0 ? (
            <p className="text-sm text-text-muted py-12 text-center">Sin ventas este mes</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={barData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={CHART_GRID} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickFormatter={formatYAxis}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                />
                <Tooltip
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(value: any) => [`Gs ${formatCurrency(Number(value))}`, 'Ventas']}
                  contentStyle={TOOLTIP_STYLE}
                  labelStyle={{ color: CHART_TEXT }}
                  itemStyle={{ color: '#E8EEF7' }}
                  cursor={{ fill: 'rgba(59,130,246,0.08)' }}
                />
                <Bar dataKey="total" fill={PRIMARY_500} radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* PieChart: top 10 productos */}
        <div className="card">
          <h2 className="text-base font-semibold text-text-primary mb-4">
            Top productos — mes
          </h2>
          {pieData.length === 0 ? (
            <p className="text-sm text-text-muted py-12 text-center">Sin ventas este mes</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    innerRadius={35}
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={(value: any, name: any) => [
                      `Gs ${formatCurrency(Number(value))}`,
                      name,
                    ]}
                    contentStyle={TOOLTIP_STYLE}
                    labelStyle={{ color: CHART_TEXT }}
                    itemStyle={{ color: '#E8EEF7' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <ul className="mt-3 space-y-1.5">
                {pieData.slice(0, 5).map((item, i) => (
                  <li key={item.name} className="flex items-center gap-2 text-xs">
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: PIE_COLORS[i] }}
                    />
                    <span className="flex-1 truncate text-text-secondary">{item.name}</span>
                    <span className="tabular-nums text-text-primary">
                      Gs {formatCurrency(item.value)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Stock bajo + Valor inventario */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Lista de stock bajo */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-text-primary">
              Productos con stock bajo
            </h2>
            {lowStock && lowStock.items.length > 0 && (
              <span className="text-xs font-medium text-warning-500 bg-warning-500/10 px-2 py-1 rounded">
                {lowStock.items.length}{' '}
                {lowStock.items.length === 1 ? 'producto' : 'productos'}
              </span>
            )}
          </div>
          {!lowStock || lowStock.items.length === 0 ? (
            <p className="text-sm text-text-muted py-4 text-center">
              {lowStock
                ? 'Todos los productos tienen stock suficiente'
                : 'Sin datos de stock'}
            </p>
          ) : (
            <ul className="space-y-0">
              {lowStock.items.map((item) => (
                <li
                  key={item.product_id}
                  className="flex items-center justify-between py-2.5 border-b border-border-subtle last:border-0"
                >
                  <Link
                    to={`/productos/${item.product_id}`}
                    className="flex-1 min-w-0 hover:text-primary-500 transition-colors"
                  >
                    <span className="text-sm font-medium text-text-primary block truncate">
                      {item.product_name}
                    </span>
                    <span className="text-xs text-text-muted">{item.sku}</span>
                  </Link>
                  <div className="text-right ml-4 flex-shrink-0">
                    <span className="text-sm font-semibold tabular-nums text-warning-500">
                      {formatQty(item.quantity_base)}
                    </span>
                    <span className="text-xs text-text-muted ml-1">
                      / {formatQty(item.threshold)} mín
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Valor del inventario */}
        <div className="card flex flex-col gap-3">
          <h2 className="text-base font-semibold text-text-primary">Valor del inventario</h2>
          <div className="text-3xl font-bold tabular-nums text-text-primary">
            {inventoryValue !== null ? `Gs ${formatCurrency(inventoryValue)}` : '—'}
          </div>
          <p className="text-xs text-text-muted">
            Costo promedio × stock actual (depósito por defecto)
          </p>
          {stockValue && stockValue.by_category.length > 0 && (
            <ul className="mt-1 space-y-1.5 border-t border-border-subtle pt-3">
              {stockValue.by_category.slice(0, 5).map((cat, i) => (
                <li
                  key={cat.category_id ?? `uncategorized-${i}`}
                  className="flex justify-between text-xs"
                >
                  <span className="text-text-secondary truncate">
                    {cat.category_name ?? 'Sin categoría'}
                  </span>
                  <span className="tabular-nums text-text-primary ml-2 flex-shrink-0">
                    Gs {formatCurrency(parseFloat(cat.total_value))}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
