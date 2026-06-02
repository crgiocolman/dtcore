import { Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import { formatCurrency } from '../../../lib/format'
import { fetchStockValue, type StockValueOut } from '../api/reports'
import { downloadCSV } from '../lib/csv'

export function StockValueReport() {
  const [data, setData] = useState<StockValueOut | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchStockValue()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  function handleExport() {
    if (!data) return
    downloadCSV(
      data.by_category.map((c) => ({
        Categoría: c.category_name ?? 'Sin categoría',
        'Valor (Gs)': formatCurrency(c.total_value),
      })),
      `valor_inventario_${new Date().toISOString().split('T')[0]}.csv`
    )
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="card h-24 animate-pulse bg-bg-elevated" />
        <div className="card h-48 animate-pulse bg-bg-elevated" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="card py-12 text-center text-sm text-text-muted">
        No se pudo cargar el valor de inventario
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Total value card */}
      <div className="card flex flex-col gap-2">
        <span className="text-sm text-text-secondary">Valor total del inventario</span>
        <div className="text-3xl font-bold tabular-nums text-text-primary">
          Gs {formatCurrency(data.total_value)}
        </div>
        <p className="text-xs text-text-muted">
          Costo promedio × stock actual — todos los productos con track_stock activo
        </p>
      </div>

      {/* By category */}
      {data.by_category.length > 0 && (
        <>
          <div className="flex justify-end">
            <button
              type="button"
              className="btn-secondary text-sm flex items-center gap-1.5"
              onClick={handleExport}
            >
              <Download className="w-4 h-4" />
              Exportar CSV
            </button>
          </div>

          <div className="card overflow-x-auto">
            <h3 className="text-base font-medium text-text-primary mb-4">Por categoría</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-subtle">
                  <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">
                    Categoría
                  </th>
                  <th className="text-right py-2.5 font-medium text-text-secondary tabular-nums">
                    Valor (Gs)
                  </th>
                  <th className="text-right py-2.5 pl-4 font-medium text-text-secondary tabular-nums">
                    %
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.by_category.map((cat, i) => {
                  const pct =
                    parseFloat(data.total_value) > 0
                      ? (parseFloat(cat.total_value) / parseFloat(data.total_value)) * 100
                      : 0
                  return (
                    <tr
                      key={cat.category_id ?? `uncategorized-${i}`}
                      className="border-b border-border-subtle last:border-0 hover:bg-bg-elevated transition-colors"
                    >
                      <td className="py-2.5 pr-4 text-text-primary">
                        {cat.category_name ?? (
                          <span className="text-text-muted italic">Sin categoría</span>
                        )}
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-text-primary">
                        Gs {formatCurrency(cat.total_value)}
                      </td>
                      <td className="py-2.5 pl-4 text-right tabular-nums text-text-secondary text-xs">
                        {pct.toFixed(1)}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-border">
                  <td className="py-2.5 pr-4 font-semibold text-text-primary">Total</td>
                  <td className="py-2.5 text-right tabular-nums font-semibold text-text-primary">
                    Gs {formatCurrency(data.total_value)}
                  </td>
                  <td className="py-2.5 pl-4 text-right tabular-nums text-text-muted text-xs">
                    100%
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
