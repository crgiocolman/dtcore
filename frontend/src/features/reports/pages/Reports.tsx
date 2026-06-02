import { useState } from 'react'
import { DateRangeFilter, thisMonthRange } from '../components/DateRangeFilter'
import type { DateRange } from '../components/DateRangeFilter'
import { KardexReport } from '../components/KardexReport'
import { ProfitReport } from '../components/ProfitReport'
import { SalesReport } from '../components/SalesReport'
import { StockValueReport } from '../components/StockValueReport'
import { TopProductsReport } from '../components/TopProductsReport'

type Tab = 'ventas' | 'top_productos' | 'utilidad' | 'kardex' | 'inventario'

const TABS: { id: Tab; label: string; hasDateFilter: boolean }[] = [
  { id: 'ventas', label: 'Ventas por período', hasDateFilter: true },
  { id: 'top_productos', label: 'Top productos', hasDateFilter: true },
  { id: 'utilidad', label: 'Utilidad por producto', hasDateFilter: true },
  { id: 'kardex', label: 'Kardex', hasDateFilter: true },
  { id: 'inventario', label: 'Valor de inventario', hasDateFilter: false },
]

export function Reports() {
  const [tab, setTab] = useState<Tab>('ventas')
  const [dateRange, setDateRange] = useState<DateRange>(thisMonthRange())

  const currentTab = TABS.find((t) => t.id === tab)!

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-text-primary">Reportes</h1>

      {/* Tab bar */}
      <div className="border-b border-border-subtle flex overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
              tab === t.id
                ? 'border-primary-500 text-primary-500'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Date range filter (only for tabs that use it) */}
      {currentTab.hasDateFilter && (
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      )}

      {/* Tab content */}
      {tab === 'ventas' && <SalesReport dateRange={dateRange} />}
      {tab === 'top_productos' && <TopProductsReport dateRange={dateRange} />}
      {tab === 'utilidad' && <ProfitReport dateRange={dateRange} />}
      {tab === 'kardex' && <KardexReport dateRange={dateRange} />}
      {tab === 'inventario' && <StockValueReport />}
    </div>
  )
}
