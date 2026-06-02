import { Download, Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { formatCurrency } from '../../../lib/format'
import { searchProducts, type ProductSearchResult } from '../../products/api/products'
import { fetchKardex, type KardexOut } from '../api/reports'
import { csvFilename, downloadCSV } from '../lib/csv'
import type { DateRange } from './DateRangeFilter'

const MOVEMENT_LABELS: Record<string, string> = {
  purchase: 'Compra',
  sale: 'Venta',
  return_in: 'Dev. entrada',
  return_out: 'Dev. salida',
  adjustment_in: 'Ajuste +',
  adjustment_out: 'Ajuste −',
  initial: 'Stock inicial',
}

const DIRECTION_CLASSES: Record<string, string> = {
  in: 'text-success-500',
  out: 'text-danger-500',
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatQty(value: string): string {
  const n = parseFloat(value)
  if (isNaN(n)) return '—'
  return n % 1 === 0 ? String(n) : n.toFixed(4).replace(/\.?0+$/, '')
}

export function KardexReport({ dateRange }: { dateRange: DateRange }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ProductSearchResult[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [selected, setSelected] = useState<ProductSearchResult | null>(null)
  const [kardex, setKardex] = useState<KardexOut | null>(null)
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Product search
  useEffect(() => {
    if (query.length < 2) {
      setResults([])
      setShowDropdown(false)
      return
    }
    const timer = setTimeout(() => {
      searchProducts(query)
        .then((r) => {
          setResults(r.slice(0, 8))
          setShowDropdown(r.length > 0)
        })
        .catch(() => setResults([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [query])

  // Reload kardex when product or date range changes
  useEffect(() => {
    if (!selected) return
    setLoading(true)
    setKardex(null)
    fetchKardex(selected.id, {
      date_from: dateRange.dateFrom,
      date_to: dateRange.dateTo,
    })
      .then(setKardex)
      .catch(() => setKardex(null))
      .finally(() => setLoading(false))
  }, [selected, dateRange.dateFrom, dateRange.dateTo])

  function selectProduct(p: ProductSearchResult) {
    setSelected(p)
    setQuery('')
    setShowDropdown(false)
    setResults([])
  }

  function clearProduct() {
    setSelected(null)
    setKardex(null)
    setQuery('')
  }

  function handleExport() {
    if (!kardex || !selected) return
    downloadCSV(
      kardex.lines.map((l) => ({
        Fecha: formatDateTime(l.created_at),
        Tipo: MOVEMENT_LABELS[l.movement_type] ?? l.movement_type,
        Dirección: l.direction === 'in' ? 'Entrada' : 'Salida',
        Cantidad: formatQty(l.quantity_base),
        'Costo unit. (Gs)': l.unit_cost_base !== null ? formatCurrency(l.unit_cost_base) : '—',
        'Saldo (Gs)': formatCurrency(l.balance_after),
        Notas: l.notes ?? '',
      })),
      csvFilename(`kardex_${selected.sku}`, dateRange.dateFrom, dateRange.dateTo)
    )
  }

  return (
    <div className="space-y-4">
      {/* Product selector */}
      <div className="relative" ref={dropdownRef}>
        {selected ? (
          <div className="flex items-center gap-3 card py-2.5">
            <span className="text-sm font-medium text-text-primary flex-1">
              {selected.name}
              <span className="ml-2 text-xs text-text-muted font-normal font-mono">
                {selected.sku}
              </span>
            </span>
            <button
              type="button"
              className="btn-ghost p-1 text-text-muted hover:text-text-primary"
              onClick={clearProduct}
              title="Cambiar producto"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
            <input
              type="text"
              className="input pl-9 text-sm"
              placeholder="Buscar producto por nombre, SKU o código de barras…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => results.length > 0 && setShowDropdown(true)}
            />
          </div>
        )}

        {showDropdown && (
          <div className="absolute z-10 w-full mt-1 bg-bg-elevated border border-border rounded-lg shadow-lg overflow-hidden">
            {results.map((p) => (
              <button
                key={p.id}
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-sm hover:bg-bg-input transition-colors text-left"
                onMouseDown={() => selectProduct(p)}
              >
                <span className="font-medium text-text-primary flex-1 truncate">{p.name}</span>
                <span className="text-xs text-text-muted font-mono flex-shrink-0">{p.sku}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      {!selected ? (
        <div className="card py-12 text-center text-sm text-text-muted">
          Seleccioná un producto para ver su kardex
        </div>
      ) : loading ? (
        <div className="card h-48 animate-pulse bg-bg-elevated" />
      ) : !kardex || kardex.lines.length === 0 ? (
        <div className="card py-12 text-center text-sm text-text-muted">
          Sin movimientos en el período seleccionado
        </div>
      ) : (
        <>
          <div className="flex justify-between items-center">
            <p className="text-xs text-text-muted">
              {kardex.lines.length} movimiento{kardex.lines.length !== 1 ? 's' : ''}
            </p>
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
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-subtle">
                  <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Fecha</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Tipo</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Dir.</th>
                  <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">
                    Cantidad
                  </th>
                  <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">
                    Costo unit.
                  </th>
                  <th className="text-right py-2.5 font-medium text-text-secondary tabular-nums">
                    Saldo
                  </th>
                </tr>
              </thead>
              <tbody>
                {kardex.lines.map((line) => (
                  <tr
                    key={line.id}
                    className="border-b border-border-subtle last:border-0 hover:bg-bg-elevated transition-colors"
                  >
                    <td className="py-2.5 pr-4 text-text-secondary text-xs tabular-nums whitespace-nowrap">
                      {formatDateTime(line.created_at)}
                    </td>
                    <td className="py-2.5 pr-4 text-text-primary">
                      {MOVEMENT_LABELS[line.movement_type] ?? line.movement_type}
                    </td>
                    <td className={`py-2.5 pr-4 text-xs font-medium ${DIRECTION_CLASSES[line.direction] ?? ''}`}>
                      {line.direction === 'in' ? 'Entrada' : 'Salida'}
                    </td>
                    <td className={`py-2.5 pr-4 text-right tabular-nums font-medium ${DIRECTION_CLASSES[line.direction] ?? ''}`}>
                      {line.direction === 'out' ? '−' : '+'}{formatQty(line.quantity_base)}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-text-secondary">
                      {line.unit_cost_base !== null
                        ? `Gs ${formatCurrency(line.unit_cost_base)}`
                        : '—'}
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-text-primary font-medium">
                      {formatQty(line.balance_after)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
