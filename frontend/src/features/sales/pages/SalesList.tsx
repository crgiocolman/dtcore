import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Loader2,
  ShoppingCart,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { fetchContacts, type ContactOut } from '../../contacts/api/contacts'
import {
  cancelSale,
  getSale,
  type SaleListItem,
  type SaleOut,
  type SaleStatus,
} from '../../pos/api/sales'
import { useSales } from '../hooks/useSales'

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<SaleStatus | '', string> = {
  '': 'Todos los estados',
  draft: 'Borrador',
  confirmed: 'Confirmada',
  cancelled: 'Cancelada',
}

const STATUS_BADGE: Record<SaleStatus, string> = {
  draft: 'text-text-secondary',
  confirmed: 'text-success-500',
  cancelled: 'text-danger-500',
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: 'Efectivo',
  transfer: 'Transferencia',
  card: 'Tarjeta',
  check: 'Cheque',
  other: 'Otro',
}

function fmtPYG(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '—'
  return '₲ ' + new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(num)
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-PY', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('es-PY', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ─── SaleDetailModal ──────────────────────────────────────────────────────────

function SaleDetailModal({
  sale: listItem,
  onClose,
  onCancelled,
}: {
  sale: SaleListItem
  onClose: () => void
  onCancelled: () => void
}) {
  const [detail, setDetail] = useState<SaleOut | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)

  useEffect(() => {
    getSale(listItem.id)
      .then(setDetail)
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : 'Error al cargar detalle')
      })
  }, [listItem.id])

  const handleCancel = async () => {
    if (!cancelReason.trim()) { setCancelError('El motivo es obligatorio'); return }
    setCancelling(true)
    setCancelError(null)
    try {
      await cancelSale(listItem.id, cancelReason.trim())
      onCancelled()
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : 'Error al cancelar')
      setCancelling(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="card flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden p-0"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-4">
          <div>
            <p className="text-xs text-text-muted">Venta</p>
            <h2 className="text-lg font-semibold text-text-primary">
              {listItem.sale_number ?? <span className="italic text-text-muted text-base">Sin número</span>}
            </h2>
          </div>
          <button type="button" className="btn-ghost p-1.5" onClick={onClose}>
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {/* Summary row */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
            <div>
              <p className="text-xs text-text-muted mb-0.5">Fecha</p>
              <p className="text-text-primary tabular-nums">{fmtDateTime(listItem.sale_date)}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-0.5">Cliente</p>
              <p className="text-text-primary">{listItem.customer_name ?? <span className="italic text-text-muted">Sin cliente</span>}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-0.5">Estado</p>
              <p className={`font-medium ${STATUS_BADGE[listItem.status]}`}>
                {STATUS_LABELS[listItem.status]}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-0.5">Total</p>
              <p className="text-text-primary font-semibold tabular-nums">{fmtPYG(listItem.total)}</p>
            </div>
          </div>

          {listItem.cancelled_reason && (
            <div className="rounded border border-danger-500/30 bg-danger-500/5 px-3 py-2 text-sm">
              <p className="text-xs font-medium text-danger-500 mb-0.5">Motivo de cancelación</p>
              <p className="text-text-secondary">{listItem.cancelled_reason}</p>
            </div>
          )}

          {/* Detail: loading / error / content */}
          {!detail && !loadError && (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
            </div>
          )}

          {loadError && (
            <div className="flex items-center gap-2 rounded border border-danger-500/30 bg-danger-500/5 px-3 py-2 text-sm text-danger-500">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {loadError}
            </div>
          )}

          {detail && (
            <>
              {/* Items */}
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Items ({detail.items.length})
                </p>
                <div className="overflow-x-auto rounded border border-border-subtle">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border-subtle bg-bg-elevated">
                        <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Producto</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Unidad</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Cant.</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Precio u.</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Descuento</th>
                        <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {detail.items.map((item) => (
                        <tr key={item.id}>
                          <td className="px-3 py-2 text-text-primary">
                            {item.product_name ?? (
                              <span className="font-mono text-xs text-text-muted">{item.product_id.slice(0, 8)}</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-text-secondary">{item.unit_name ?? '—'}</td>
                          <td className="px-3 py-2 tabular-nums text-right text-text-primary">
                            {parseFloat(item.quantity)}
                          </td>
                          <td className="px-3 py-2 tabular-nums text-right text-text-secondary">
                            {fmtPYG(item.unit_price)}
                          </td>
                          <td className="px-3 py-2 tabular-nums text-right text-text-muted">
                            {parseFloat(item.discount_amount) > 0 ? fmtPYG(item.discount_amount) : '—'}
                          </td>
                          <td className="px-3 py-2 tabular-nums text-right font-medium text-text-primary">
                            {fmtPYG(item.total)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Totals */}
              <div className="flex justify-end">
                <div className="w-56 space-y-1 text-sm">
                  <div className="flex justify-between text-text-secondary">
                    <span>Subtotal</span>
                    <span className="tabular-nums">{fmtPYG(detail.items_subtotal)}</span>
                  </div>
                  <div className="flex justify-between text-text-secondary">
                    <span>IVA</span>
                    <span className="tabular-nums">{fmtPYG(detail.tax_total)}</span>
                  </div>
                  {parseFloat(detail.header_discount_amount) > 0 && (
                    <div className="flex justify-between text-text-secondary">
                      <span>Descuento</span>
                      <span className="tabular-nums">− {fmtPYG(detail.header_discount_amount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between border-t border-border-subtle pt-1 font-semibold text-text-primary">
                    <span>Total</span>
                    <span className="tabular-nums">{fmtPYG(detail.total)}</span>
                  </div>
                </div>
              </div>

              {/* Payments */}
              {detail.payments.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                    Pagos
                  </p>
                  <div className="overflow-x-auto rounded border border-border-subtle">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border-subtle bg-bg-elevated">
                          <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Método</th>
                          <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Monto</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Referencia</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle">
                        {detail.payments.map((p) => (
                          <tr key={p.id}>
                            <td className="px-3 py-2 text-text-primary">
                              {PAYMENT_METHOD_LABELS[p.payment_method] ?? p.payment_method}
                            </td>
                            <td className="px-3 py-2 tabular-nums text-right font-medium text-text-primary">
                              {fmtPYG(p.amount)}
                            </td>
                            <td className="px-3 py-2 text-text-muted">{p.reference ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border-subtle px-5 py-3">
          {showCancelConfirm ? (
            <div className="space-y-3">
              <p className="text-sm font-medium text-text-primary">
                Confirmar cancelación de la venta {listItem.sale_number}
              </p>
              <textarea
                className="input w-full resize-none text-sm"
                rows={2}
                placeholder="Motivo de cancelación (obligatorio)"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                autoFocus
              />
              {cancelError && (
                <p className="flex items-center gap-1.5 text-xs text-danger-500">
                  <AlertCircle className="h-3.5 w-3.5" />
                  {cancelError}
                </p>
              )}
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  className="btn-secondary text-sm"
                  onClick={() => { setShowCancelConfirm(false); setCancelReason(''); setCancelError(null) }}
                  disabled={cancelling}
                >
                  Volver
                </button>
                <button
                  type="button"
                  className="btn-danger text-sm"
                  onClick={handleCancel}
                  disabled={cancelling || !cancelReason.trim()}
                >
                  {cancelling ? (
                    <span className="flex items-center gap-1.5">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Cancelando…
                    </span>
                  ) : (
                    'Confirmar cancelación'
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <p className="text-xs text-text-muted tabular-nums">
                Registrada {fmtDateTime(listItem.created_at)}
              </p>
              <div className="flex items-center gap-2">
                <button type="button" className="btn-secondary text-sm" onClick={onClose}>
                  Cerrar
                </button>
                {listItem.status === 'confirmed' && (
                  <button
                    type="button"
                    className="btn-danger text-sm"
                    onClick={() => setShowCancelConfirm(true)}
                  >
                    Cancelar venta
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── SalesList ─────────────────────────────────────────────────────────────────

export function SalesList() {
  const {
    data, loading, error,
    page, status, customerId, dateFrom, dateTo,
    setPage, setStatus, setCustomerId, setDateFrom, setDateTo,
    reload,
  } = useSales()

  const items = data?.items ?? []
  const totalPages = data?.total_pages ?? 1
  const total = data?.total ?? 0

  const [customers, setCustomers] = useState<ContactOut[]>([])
  useEffect(() => {
    fetchContacts({ contact_type: 'customer', page_size: 100 })
      .then((r) => setCustomers(r.items))
      .catch(() => {})
  }, [])

  const [selectedSale, setSelectedSale] = useState<SaleListItem | null>(null)

  const hasFilters = status || customerId || dateFrom || dateTo

  return (
    <div className="flex h-full flex-col">
      {/* Page header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Ventas</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Historial de ventas registradas
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          className="input w-auto min-w-[180px]"
          value={status}
          onChange={(e) => setStatus(e.target.value as SaleStatus | '')}
        >
          {(Object.keys(STATUS_LABELS) as Array<SaleStatus | ''>).map((key) => (
            <option key={key} value={key}>{STATUS_LABELS[key]}</option>
          ))}
        </select>

        <select
          className="input w-auto min-w-[200px]"
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
        >
          <option value="">Todos los clientes</option>
          {customers.map((c) => (
            <option key={c.id} value={c.id}>{c.business_name}</option>
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

      {/* Table card */}
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
            <ShoppingCart className="h-12 w-12 text-text-muted" />
            <p className="text-sm text-text-muted">
              {hasFilters
                ? 'Sin resultados para los filtros aplicados'
                : 'No hay ventas registradas'}
            </p>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-bg-surface">
                  <tr className="border-b border-border-subtle">
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary"># Venta</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Fecha</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Cliente</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary">Total</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {items.map((s) => (
                    <tr
                      key={s.id}
                      className="cursor-pointer transition-colors hover:bg-bg-elevated/50"
                      onClick={() => setSelectedSale(s)}
                    >
                      <td className="px-4 py-3 tabular-nums text-text-primary">
                        {s.sale_number ?? (
                          <span className="italic text-text-muted">Sin número</span>
                        )}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-text-secondary">
                        {fmtDate(s.sale_date)}
                      </td>
                      <td className="px-4 py-3 text-text-primary">
                        {s.customer_name ?? <span className="text-text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-right font-medium text-text-primary">
                        {fmtPYG(s.total)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium ${STATUS_BADGE[s.status]}`}>
                          {STATUS_LABELS[s.status]}
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

      {/* Detail modal */}
      {selectedSale && (
        <SaleDetailModal
          sale={selectedSale}
          onClose={() => setSelectedSale(null)}
          onCancelled={() => {
            setSelectedSale(null)
            reload()
          }}
        />
      )}
    </div>
  )
}
