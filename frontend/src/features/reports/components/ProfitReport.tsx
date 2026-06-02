import { Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import { formatCurrency } from '../../../lib/format'
import { fetchProfitByProduct, type ProfitByProductOut } from '../api/reports'
import { csvFilename, downloadCSV } from '../lib/csv'
import type { DateRange } from './DateRangeFilter'

export function ProfitReport({ dateRange }: { dateRange: DateRange }) {
  const [data, setData] = useState<ProfitByProductOut | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setData(null)
    fetchProfitByProduct({ date_from: dateRange.dateFrom, date_to: dateRange.dateTo })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [dateRange.dateFrom, dateRange.dateTo])

  function handleExport() {
    if (!data) return
    downloadCSV(
      data.items.map((i) => ({
        SKU: i.sku,
        Producto: i.product_name,
        'Ingresos (Gs)': formatCurrency(i.revenue_pyg),
        'Costo (Gs)': formatCurrency(i.cost_pyg),
        'Utilidad (Gs)': formatCurrency(i.profit_pyg),
        'Margen (%)':
          i.margin_pct !== null ? parseFloat(i.margin_pct).toFixed(1) + '%' : '—',
      })),
      csvFilename('utilidad_por_producto', dateRange.dateFrom, dateRange.dateTo)
    )
  }

  const totalProfit = data ? parseFloat(data.total_profit_pyg) : null

  return (
    <div className="space-y-4">
      {loading ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card h-20 animate-pulse bg-bg-elevated" />
            ))}
          </div>
          <div className="card h-48 animate-pulse bg-bg-elevated" />
        </>
      ) : !data ? (
        <div className="card py-12 text-center text-sm text-text-muted">
          Sin datos en el período seleccionado
        </div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="card flex flex-col gap-1">
              <span className="text-xs text-text-secondary">Ingresos</span>
              <span className="text-xl font-bold tabular-nums text-text-primary">
                Gs {formatCurrency(data.total_revenue_pyg)}
              </span>
            </div>
            <div className="card flex flex-col gap-1">
              <span className="text-xs text-text-secondary">Costo</span>
              <span className="text-xl font-bold tabular-nums text-text-primary">
                Gs {formatCurrency(data.total_cost_pyg)}
              </span>
            </div>
            <div className="card flex flex-col gap-1">
              <span className="text-xs text-text-secondary">Utilidad</span>
              <span
                className={`text-xl font-bold tabular-nums ${
                  totalProfit !== null && totalProfit >= 0 ? 'text-success-500' : 'text-danger-500'
                }`}
              >
                Gs {formatCurrency(data.total_profit_pyg)}
              </span>
            </div>
            <div className="card flex flex-col gap-1">
              <span className="text-xs text-text-secondary">Margen promedio</span>
              <span className="text-xl font-bold tabular-nums text-text-primary">
                {data.items.length > 0
                  ? (() => {
                      const withMargin = data.items.filter((i) => i.margin_pct !== null)
                      if (withMargin.length === 0) return '—'
                      const avg =
                        withMargin.reduce((s, i) => s + parseFloat(i.margin_pct!), 0) /
                        withMargin.length
                      return `${avg.toFixed(1)}%`
                    })()
                  : '—'}
              </span>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              className="btn-secondary text-sm flex items-center gap-1.5"
              onClick={handleExport}
              disabled={data.items.length === 0}
            >
              <Download className="w-4 h-4" />
              Exportar CSV
            </button>
          </div>

          {data.items.length === 0 ? (
            <div className="card py-12 text-center text-sm text-text-muted">
              Sin ventas en el período seleccionado
            </div>
          ) : (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">SKU</th>
                    <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">
                      Producto
                    </th>
                    <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">
                      Ingresos (Gs)
                    </th>
                    <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">
                      Costo (Gs)
                    </th>
                    <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">
                      Utilidad (Gs)
                    </th>
                    <th className="text-right py-2.5 font-medium text-text-secondary tabular-nums">
                      Margen
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => {
                    const profit = parseFloat(item.profit_pyg)
                    return (
                      <tr
                        key={item.product_id}
                        className="border-b border-border-subtle last:border-0 hover:bg-bg-elevated transition-colors"
                      >
                        <td className="py-2.5 pr-4 text-text-secondary font-mono text-xs">
                          {item.sku}
                        </td>
                        <td className="py-2.5 pr-4 text-text-primary">{item.product_name}</td>
                        <td className="py-2.5 pr-4 text-right tabular-nums text-text-primary">
                          Gs {formatCurrency(item.revenue_pyg)}
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums text-text-primary">
                          Gs {formatCurrency(item.cost_pyg)}
                        </td>
                        <td
                          className={`py-2.5 pr-4 text-right tabular-nums font-medium ${
                            profit >= 0 ? 'text-success-500' : 'text-danger-500'
                          }`}
                        >
                          Gs {formatCurrency(item.profit_pyg)}
                        </td>
                        <td className="py-2.5 text-right tabular-nums text-text-secondary">
                          {item.margin_pct !== null
                            ? `${parseFloat(item.margin_pct).toFixed(1)}%`
                            : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t border-border">
                    <td colSpan={2} className="py-2.5 pr-4 font-semibold text-text-primary">
                      Total
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums font-semibold text-text-primary">
                      Gs {formatCurrency(data.total_revenue_pyg)}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums font-semibold text-text-primary">
                      Gs {formatCurrency(data.total_cost_pyg)}
                    </td>
                    <td
                      className={`py-2.5 pr-4 text-right tabular-nums font-semibold ${
                        totalProfit !== null && totalProfit >= 0
                          ? 'text-success-500'
                          : 'text-danger-500'
                      }`}
                    >
                      Gs {formatCurrency(data.total_profit_pyg)}
                    </td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
