import { Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import { formatCurrency } from '../../../lib/format'
import { fetchTopProducts, type TopProductItem, type TopProductsOut } from '../api/reports'
import { csvFilename, downloadCSV } from '../lib/csv'
import type { DateRange } from './DateRangeFilter'

type SortBy = 'amount' | 'quantity'

function formatQty(value: string): string {
  const n = parseFloat(value)
  if (isNaN(n)) return '—'
  return n % 1 === 0 ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
}

export function TopProductsReport({ dateRange }: { dateRange: DateRange }) {
  const [data, setData] = useState<TopProductsOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortBy>('amount')

  useEffect(() => {
    setLoading(true)
    setData(null)
    fetchTopProducts({ date_from: dateRange.dateFrom, date_to: dateRange.dateTo, limit: 25 })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [dateRange.dateFrom, dateRange.dateTo])

  const items: TopProductItem[] = sortBy === 'amount' ? (data?.by_amount ?? []) : (data?.by_quantity ?? [])

  function handleExport() {
    if (!data) return
    downloadCSV(
      items.map((i, idx) => ({
        '#': idx + 1,
        SKU: i.sku,
        Producto: i.product_name,
        'Cantidad vendida': formatQty(i.quantity_sold),
        'Total (Gs)': formatCurrency(i.total_pyg),
      })),
      csvFilename('top_productos', dateRange.dateFrom, dateRange.dateTo)
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1">
          {(['amount', 'quantity'] as SortBy[]).map((s) => (
            <button
              key={s}
              type="button"
              className={`btn-secondary text-xs py-1.5 px-3 ${
                sortBy === s ? 'ring-1 ring-primary-500 text-primary-500' : ''
              }`}
              onClick={() => setSortBy(s)}
            >
              {s === 'amount' ? 'Por monto' : 'Por cantidad'}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="btn-secondary text-sm flex items-center gap-1.5"
          onClick={handleExport}
          disabled={!data || items.length === 0}
        >
          <Download className="w-4 h-4" />
          Exportar CSV
        </button>
      </div>

      {loading ? (
        <div className="card h-48 animate-pulse bg-bg-elevated" />
      ) : items.length === 0 ? (
        <div className="card py-12 text-center text-sm text-text-muted">
          Sin ventas en el período seleccionado
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="text-left py-2.5 pr-4 font-medium text-text-secondary w-8">#</th>
                <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">SKU</th>
                <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Producto</th>
                <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">
                  Cantidad
                </th>
                <th className="text-right py-2.5 font-medium text-text-secondary tabular-nums">
                  Total (Gs)
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr
                  key={item.product_id}
                  className="border-b border-border-subtle last:border-0 hover:bg-bg-elevated transition-colors"
                >
                  <td className="py-2.5 pr-4 text-text-muted tabular-nums">{idx + 1}</td>
                  <td className="py-2.5 pr-4 text-text-secondary font-mono text-xs">{item.sku}</td>
                  <td className="py-2.5 pr-4 text-text-primary">{item.product_name}</td>
                  <td className="py-2.5 pr-4 text-right tabular-nums text-text-primary">
                    {formatQty(item.quantity_sold)}
                  </td>
                  <td className="py-2.5 text-right tabular-nums text-text-primary">
                    Gs {formatCurrency(item.total_pyg)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
