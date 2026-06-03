import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { AlertCircle, CheckCircle2, Lock } from 'lucide-react'
import { fetchProducts, type ProductOut } from '../../products/api/products'
import { fetchWarehouses, type WarehouseOut } from '../api/warehouses'
import { applyInitialInventory, fetchStockedProductIds } from '../api/stock'
import { useAuthStore } from '../../auth/store'

// TODO: si un cliente supera 500 productos con track_stock=true, replantear
// este flujo (paginación en cliente o endpoint dedicado de batch).
async function fetchAllTrackedProducts(): Promise<ProductOut[]> {
  const first = await fetchProducts({ page_size: 500, page: 1 })
  const all = first.items.filter((p) => p.track_stock && !p.deleted_at)

  if (first.total_pages > 1) {
    const pages = Array.from({ length: first.total_pages - 1 }, (_, i) => i + 2)
    const rest = await Promise.all(pages.map((page) => fetchProducts({ page_size: 500, page })))
    rest.forEach((r) => {
      all.push(...r.items.filter((p) => p.track_stock && !p.deleted_at))
    })
  }

  return all
}

function parseConflictProductId(err: unknown): string | null {
  if (!(err instanceof Error)) return null
  try {
    const parsed = JSON.parse(err.message) as {
      detail?: { code?: string; product_id?: string }
    }
    if (
      parsed?.detail?.code === 'initial_inventory_already_applied' &&
      parsed.detail.product_id
    ) {
      return parsed.detail.product_id
    }
  } catch {
    // not JSON
  }
  return null
}

function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) return 'Error desconocido'
  try {
    const parsed = JSON.parse(err.message) as { detail?: unknown }
    if (typeof parsed?.detail === 'string') return parsed.detail
  } catch {
    // not JSON
  }
  return err.message
}

interface RowState {
  quantity: string
  unit_cost: string
}

type RowErrors = Record<string, { quantity?: string; unit_cost?: string }>

export function InitialInventory() {
  const user = useAuthStore((s) => s.user)
  const [products, setProducts] = useState<ProductOut[]>([])
  const [warehouse, setWarehouse] = useState<WarehouseOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [rows, setRows] = useState<Record<string, RowState>>({})
  const [rowErrors, setRowErrors] = useState<RowErrors>({})
  const [lockedIds, setLockedIds] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [conflictProductId, setConflictProductId] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    Promise.all([fetchAllTrackedProducts(), fetchWarehouses()])
      .then(async ([tracked, warehouses]) => {
        setProducts(tracked)
        const def =
          warehouses.find((w) => w.is_default && w.is_active) ??
          warehouses.find((w) => w.is_active) ??
          null
        setWarehouse(def)
        const initial: Record<string, RowState> = {}
        tracked.forEach((p) => {
          initial[p.id] = { quantity: '', unit_cost: '' }
        })
        setRows(initial)
        if (def) {
          const ids = await fetchStockedProductIds(def.id)
          setLockedIds(ids)
        }
      })
      .catch(() => setLoadError('No se pudieron cargar los datos. Intentá recargar la página.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (conflictProductId) {
      document
        .getElementById(`inv-row-${conflictProductId}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [conflictProductId])

  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />
  }

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-text-muted">Cargando…</p>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-danger-500">{loadError}</p>
      </div>
    )
  }

  const updateRow = (productId: string, field: keyof RowState, value: string) => {
    setRows((prev) => ({ ...prev, [productId]: { ...prev[productId], [field]: value } }))
    setRowErrors((prev) => ({
      ...prev,
      [productId]: { ...prev[productId], [field]: undefined },
    }))
    if (conflictProductId === productId) setConflictProductId(null)
    setApiError(null)
    setSuccess(false)
  }

  const validate = (): boolean => {
    const errors: RowErrors = {}
    let hasAny = false

    products.forEach((p) => {
      const row = rows[p.id]
      if (!row?.quantity.trim()) return

      const qty = parseFloat(row.quantity)
      if (isNaN(qty) || qty <= 0) {
        errors[p.id] = { ...errors[p.id], quantity: 'Debe ser mayor a 0' }
        return
      }

      hasAny = true

      if (!row.unit_cost.trim()) {
        errors[p.id] = { ...errors[p.id], unit_cost: 'Requerido' }
      } else {
        const cost = parseFloat(row.unit_cost)
        if (isNaN(cost) || cost < 0) {
          errors[p.id] = { ...errors[p.id], unit_cost: 'Debe ser 0 o mayor' }
        }
      }
    })

    setRowErrors(errors)

    if (!hasAny) {
      setApiError('Ingresá cantidad para al menos un producto')
      return false
    }

    return Object.keys(errors).length === 0
  }

  const handleSubmit = async () => {
    if (!warehouse || !validate()) return

    setSaving(true)
    setApiError(null)
    setConflictProductId(null)
    setSuccess(false)

    const items = products
      .filter((p) => {
        if (lockedIds.has(p.id)) return false
        const qty = parseFloat(rows[p.id]?.quantity ?? '')
        return !isNaN(qty) && qty > 0
      })
      .map((p) => ({
        product_id: p.id,
        quantity_base: rows[p.id].quantity.trim(),
        unit_cost_base: rows[p.id].unit_cost.trim() || '0',
      }))

    try {
      await applyInitialInventory({ warehouse_id: warehouse.id, items })
      setSuccess(true)
      const cleared: Record<string, RowState> = {}
      products.forEach((p) => {
        cleared[p.id] = { quantity: '', unit_cost: '' }
      })
      setRows(cleared)
      setRowErrors({})
      const ids = await fetchStockedProductIds(warehouse.id)
      setLockedIds(ids)
    } catch (err) {
      const conflictId = parseConflictProductId(err)
      if (conflictId) {
        setConflictProductId(conflictId)
        const name = products.find((p) => p.id === conflictId)?.name ?? conflictId
        setApiError(
          `"${name}" ya tiene movimientos de stock registrados. Quitá la cantidad para ese producto.`
        )
      } else {
        setApiError(parseApiError(err))
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Inventario inicial</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Cargá el stock inicial de productos. Solo puede aplicarse una vez por producto por
          depósito.
        </p>
      </div>

      {warehouse ? (
        <div className="rounded border border-border-subtle bg-bg-surface px-4 py-3 text-sm text-text-secondary">
          Depósito:{' '}
          <span className="font-medium text-text-primary">{warehouse.name}</span>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
          <AlertCircle className="h-4 w-4 shrink-0" />
          No se encontró un depósito activo. Verificá la configuración de depósitos.
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 rounded border border-success-500/30 bg-success-500/10 px-4 py-3 text-sm text-success-500">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Inventario inicial cargado correctamente.
        </div>
      )}

      {apiError && (
        <div className="flex items-center gap-2 rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {apiError}
        </div>
      )}

      {products.length === 0 ? (
        <div className="card flex h-40 items-center justify-center">
          <p className="text-sm text-text-muted">
            No hay productos con seguimiento de stock configurado.
          </p>
        </div>
      ) : (
        <div className="card overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="pb-2 text-left text-xs font-medium text-text-secondary">SKU</th>
                <th className="pb-2 text-left text-xs font-medium text-text-secondary">Producto</th>
                <th className="pb-2 text-left text-xs font-medium text-text-secondary">Unidad</th>
                <th className="pb-2 pr-2 text-right text-xs font-medium text-text-secondary">
                  Cantidad inicial
                </th>
                <th className="pb-2 text-right text-xs font-medium text-text-secondary">
                  Costo unitario
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {products.map((p) => {
                const isLocked = lockedIds.has(p.id)
                const row = rows[p.id] ?? { quantity: '', unit_cost: '' }
                const err = rowErrors[p.id]
                const isConflict = p.id === conflictProductId
                return (
                  <tr
                    key={p.id}
                    id={`inv-row-${p.id}`}
                    className={
                      isLocked
                        ? 'bg-bg-elevated opacity-60'
                        : isConflict
                          ? 'bg-warning-500/10'
                          : undefined
                    }
                  >
                    <td className="py-2 pr-4 font-mono text-xs text-text-secondary">{p.sku}</td>
                    <td className="py-2 pr-4 text-text-primary">
                      <span className="flex items-center gap-1.5">
                        {p.name}
                        {isLocked && (
                          <span className="inline-flex items-center gap-1 rounded bg-bg-muted px-1.5 py-0.5 text-xs text-text-muted">
                            <Lock className="h-3 w-3" />
                            Con stock
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-text-secondary">
                      {p.base_unit_catalog?.symbol ?? '—'}
                    </td>
                    <td className="py-2 pr-2 text-right">
                      {isLocked ? (
                        <span className="text-xs text-text-muted tabular-nums">—</span>
                      ) : (
                        <div className="flex flex-col items-end">
                          <input
                            className={`input w-28 text-right tabular-nums${
                              isConflict ? ' border-warning-500' : ''
                            }${err?.quantity ? ' border-danger-500 focus:ring-danger-500' : ''}`}
                            type="number"
                            min="0"
                            step="0.0001"
                            placeholder="0"
                            value={row.quantity}
                            disabled={saving}
                            onChange={(e) => updateRow(p.id, 'quantity', e.target.value)}
                          />
                          {err?.quantity && (
                            <p className="mt-0.5 text-xs text-danger-500">{err.quantity}</p>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="py-2 text-right">
                      {isLocked ? (
                        <span className="text-xs text-text-muted tabular-nums">—</span>
                      ) : (
                        <div className="flex flex-col items-end">
                          <input
                            className={`input w-32 text-right tabular-nums${
                              err?.unit_cost ? ' border-danger-500 focus:ring-danger-500' : ''
                            }`}
                            type="number"
                            min="0"
                            step="0.0001"
                            placeholder="0"
                            value={row.unit_cost}
                            disabled={saving}
                            onChange={(e) => updateRow(p.id, 'unit_cost', e.target.value)}
                          />
                          {err?.unit_cost && (
                            <p className="mt-0.5 text-xs text-danger-500">{err.unit_cost}</p>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          className="btn-primary"
          disabled={saving || !warehouse || products.length === 0}
          onClick={handleSubmit}
        >
          {saving ? 'Cargando…' : 'Cargar inventario inicial'}
        </button>
      </div>
    </div>
  )
}
