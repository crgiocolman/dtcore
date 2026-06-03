import { ArrowLeft, ExternalLink } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { formatCurrency } from '../../../lib/format'
import { fetchProductStock } from '../../admin/api/stock'
import { fetchProduct, type ProductOut } from '../../products/api/products'
import { fetchKardex, type KardexLine } from '../../reports/api/reports'

const MOVEMENT_LABELS: Record<string, string> = {
  purchase: 'Compra',
  sale: 'Venta',
  return_in: 'Dev. entrada',
  return_out: 'Dev. salida',
  adjustment_in: 'Ajuste +',
  adjustment_out: 'Ajuste −',
  initial: 'Stock inicial',
}

const MOVEMENT_TYPE_OPTIONS = [
  { value: '', label: 'Todos los tipos' },
  { value: 'purchase', label: 'Compra' },
  { value: 'sale', label: 'Venta' },
  { value: 'return_in', label: 'Dev. entrada' },
  { value: 'return_out', label: 'Dev. salida' },
  { value: 'adjustment_in', label: 'Ajuste +' },
  { value: 'adjustment_out', label: 'Ajuste −' },
  { value: 'initial', label: 'Stock inicial' },
]

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

function getReferenceLink(referenceType: string | null, referenceId: string | null): string | null {
  if (!referenceType || !referenceId) return null
  if (referenceType === 'purchase') return `/compras/${referenceId}`
  if (referenceType === 'adjustment') return `/ajustes/${referenceId}`
  return null
}

export function ProductKardex() {
  const { product_id } = useParams<{ product_id: string }>()
  const navigate = useNavigate()

  const [product, setProduct] = useState<ProductOut | null>(null)
  const [stockQty, setStockQty] = useState<string | null>(null)
  const [stockCost, setStockCost] = useState<string | null>(null)
  const [lines, setLines] = useState<KardexLine[]>([])
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [movementType, setMovementType] = useState('')

  // Load product header data
  useEffect(() => {
    if (!product_id) return
    Promise.all([
      fetchProduct(product_id).catch(() => null),
      fetchProductStock(product_id).catch(() => []),
    ]).then(([prod, stockList]) => {
      setProduct(prod)
      if (stockList && stockList.length > 0) {
        const s = stockList[0]
        setStockQty(s.quantity_base)
        setStockCost(s.avg_cost_base)
      }
    })
  }, [product_id])

  // Load kardex
  useEffect(() => {
    if (!product_id) return
    setLoading(true)
    fetchKardex(product_id, {
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then((r) => setLines(r.lines))
      .catch(() => setLines([]))
      .finally(() => setLoading(false))
  }, [product_id, dateFrom, dateTo])

  const filteredLines = movementType
    ? lines.filter((l) => l.movement_type === movementType)
    : lines

  const stockQtyNum = stockQty ? parseFloat(stockQty) : null

  return (
    <div className="space-y-4">
      {/* Back + title */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="btn-ghost p-1.5 text-text-muted hover:text-text-primary"
          onClick={() => navigate('/inventario')}
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-2xl font-semibold text-text-primary">
          {product ? product.name : 'Kardex de producto'}
        </h1>
      </div>

      {/* Product header card */}
      {product && (
        <div className="card flex flex-wrap gap-6">
          <div>
            <p className="text-xs text-text-muted mb-0.5">SKU</p>
            <p className="text-sm font-mono font-medium text-text-primary">{product.sku}</p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-0.5">Unidad base</p>
            <p className="text-sm text-text-primary">
              {product.base_unit_catalog?.symbol ?? product.base_unit_catalog?.name ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-0.5">Stock actual</p>
            <p className={`text-sm font-medium tabular-nums ${
              stockQtyNum === 0 ? 'text-danger-500' :
              stockQtyNum !== null && stockQtyNum > 0 ? 'text-success-500' :
              'text-text-primary'
            }`}>
              {stockQty !== null ? formatQty(stockQty) : '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-0.5">Costo CPP</p>
            <p className="text-sm tabular-nums text-text-primary">
              {stockCost !== null ? `Gs ${formatCurrency(stockCost)}` : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="label">Desde</label>
          <input
            type="date"
            className="input text-sm"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div>
          <label className="label">Hasta</label>
          <input
            type="date"
            className="input text-sm"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
        <div>
          <label className="label">Tipo</label>
          <select
            className="input text-sm w-44"
            value={movementType}
            onChange={(e) => setMovementType(e.target.value)}
          >
            {MOVEMENT_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Movements table */}
      {loading ? (
        <div className="card h-48 animate-pulse bg-bg-elevated" />
      ) : filteredLines.length === 0 ? (
        <div className="card py-12 text-center text-sm text-text-muted">
          Sin movimientos en el período seleccionado
        </div>
      ) : (
        <>
          <p className="text-xs text-text-muted">
            {filteredLines.length} movimiento{filteredLines.length !== 1 ? 's' : ''}
          </p>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-subtle">
                  <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Fecha</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Tipo</th>
                  <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Documento</th>
                  <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">Cantidad</th>
                  <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">Costo unit. (Gs)</th>
                  <th className="text-right py-2.5 font-medium text-text-secondary tabular-nums">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {filteredLines.map((line) => {
                  const link = getReferenceLink(line.reference_type, line.reference_id)
                  const isIn = line.direction === 'in'
                  return (
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
                      <td className="py-2.5 pr-4">
                        {link ? (
                          <Link
                            to={link}
                            className="inline-flex items-center gap-1 text-primary-500 hover:text-primary-600 text-xs"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink className="w-3 h-3" />
                            Ver
                          </Link>
                        ) : (
                          <span className="text-text-muted">—</span>
                        )}
                      </td>
                      <td className={`py-2.5 pr-4 text-right tabular-nums font-medium ${isIn ? 'text-success-500' : 'text-danger-500'}`}>
                        {isIn ? '+' : '−'}{formatQty(line.quantity_base)}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums text-text-secondary">
                        {line.unit_cost_base !== null
                          ? formatCurrency(line.unit_cost_base)
                          : '—'}
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-text-primary font-medium">
                        {formatQty(line.balance_after)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
