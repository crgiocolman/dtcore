import { ChevronLeft, ChevronRight, Plus, Truck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchContacts, type ContactOut } from '../../contacts/api/contacts'
import type { PurchaseStatus } from '../api/purchases'
import { usePurchases } from '../hooks/usePurchases'

const STATUS_LABELS: Record<PurchaseStatus | '', string> = {
  '': 'Todos los estados',
  draft: 'Borrador',
  confirmed: 'Confirmada',
  cancelled: 'Cancelada',
}

const STATUS_BADGE: Record<PurchaseStatus, string> = {
  draft: 'text-text-secondary',
  confirmed: 'text-success-500',
  cancelled: 'text-danger-500',
}

function formatAmount(value: string, currencyCode: string): string {
  const num = parseFloat(value)
  if (currencyCode === 'PYG') {
    return '₲ ' + new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(num)
  }
  return currencyCode + ' ' + new Intl.NumberFormat('es-PY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num)
}

export function PurchasesList() {
  const navigate = useNavigate()
  const {
    data, loading, error,
    page, status, supplierId, dateFrom, dateTo,
    setPage, setStatus, setSupplierId, setDateFrom, setDateTo,
  } = usePurchases()

  const items = data?.items ?? []
  const totalPages = data?.total_pages ?? 1
  const total = data?.total ?? 0

  const [suppliers, setSuppliers] = useState<ContactOut[]>([])
  useEffect(() => {
    fetchContacts({ contact_type: 'supplier', page_size: 100 })
      .then((r) => setSuppliers(r.items))
      .catch(() => { /* non-critical */ })
  }, [])

  const hasFilters = status || supplierId || dateFrom || dateTo

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Compras</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Registro de compras a proveedores
          </p>
        </div>
        <button
          className="btn-primary flex flex-shrink-0 items-center gap-1.5"
          onClick={() => navigate('/compras/nueva')}
        >
          <Plus className="h-4 w-4" />
          Nueva compra
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          className="input w-auto min-w-[180px]"
          value={status}
          onChange={(e) => setStatus(e.target.value as PurchaseStatus | '')}
        >
          {(Object.keys(STATUS_LABELS) as Array<PurchaseStatus | ''>).map((key) => (
            <option key={key} value={key}>{STATUS_LABELS[key]}</option>
          ))}
        </select>

        <select
          className="input w-auto min-w-[200px]"
          value={supplierId}
          onChange={(e) => setSupplierId(e.target.value)}
        >
          <option value="">Todos los proveedores</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>{s.business_name}</option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <input
            className="input w-auto"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            aria-label="Fecha desde"
          />
          <span className="text-sm text-text-muted">—</span>
          <input
            className="input w-auto"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            aria-label="Fecha hasta"
          />
        </div>
      </div>

      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden p-0">
        {error ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-danger-500">{error}</p>
          </div>
        ) : loading && items.length === 0 ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-text-muted">Cargando…</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
            <Truck className="h-12 w-12 text-text-muted" />
            <p className="text-sm text-text-muted">
              {hasFilters
                ? 'Sin resultados para los filtros aplicados'
                : 'No hay compras registradas'}
            </p>
            {!hasFilters && (
              <button
                className="btn-secondary flex items-center gap-1.5 text-sm"
                onClick={() => navigate('/compras/nueva')}
              >
                <Plus className="h-4 w-4" />
                Registrar primera compra
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-bg-surface">
                  <tr className="border-b border-border-subtle">
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary"># Compra</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Proveedor</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Fecha</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary">Total</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary">Total (₲)</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {items.map((p) => (
                    <tr
                      key={p.id}
                      className="cursor-pointer transition-colors hover:bg-bg-elevated/50"
                      onClick={() => navigate(`/compras/${p.id}`)}
                    >
                      <td className="px-4 py-3 tabular-nums text-text-primary">
                        {p.purchase_number ?? (
                          <span className="italic text-text-muted">Sin número</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-text-primary">
                        {p.supplier_name ?? <span className="text-text-muted">—</span>}
                        {p.supplier_document_number && (
                          <span className="ml-1.5 text-xs text-text-muted">
                            {p.supplier_document_number}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-text-secondary">
                        {new Date(p.purchase_date + 'T00:00:00').toLocaleDateString('es-PY')}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                        {formatAmount(p.total, p.currency_code)}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-right text-text-secondary">
                        {p.currency_code === 'PYG'
                          ? <span className="text-text-muted">—</span>
                          : formatAmount(p.total_base_currency, 'PYG')}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium ${STATUS_BADGE[p.status]}`}>
                          {STATUS_LABELS[p.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-border-subtle px-4 py-3">
              <p className="text-xs text-text-muted">
                {total} {total === 1 ? 'registro' : 'registros'}
              </p>
              <div className="flex items-center gap-2">
                <button
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  aria-label="Página anterior"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="tabular-nums text-xs text-text-secondary">
                  {page} / {totalPages}
                </span>
                <button
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  aria-label="Página siguiente"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
