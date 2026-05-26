import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Pencil, Plus, Trash2, X, XCircle } from 'lucide-react'
import {
  createExchangeRate,
  deleteExchangeRate,
  fetchCurrencies,
  fetchExchangeRates,
  toggleCurrency,
  updateExchangeRate,
} from '../api/currencies'
import type { CurrencyOut, ExchangeRateOut } from '../api/currencies'

// ---- Toast ----

interface ToastState {
  message: string
  type: 'success' | 'error'
  id: number
}

function Toast({ toast, onClose }: { toast: ToastState; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500)
    return () => clearTimeout(t)
  }, [toast.id, onClose])

  const Icon = toast.type === 'success' ? CheckCircle2 : XCircle
  const iconColor = toast.type === 'success' ? 'text-success-500' : 'text-danger-500'

  return (
    <div className="fixed bottom-6 right-6 z-50 flex min-w-[280px] items-center gap-3 rounded-lg border border-border bg-bg-elevated px-4 py-3 shadow-lg">
      <Icon className={`h-5 w-5 flex-shrink-0 ${iconColor}`} />
      <span className="flex-1 text-sm text-text-primary">{toast.message}</span>
      <button onClick={onClose} className="text-text-muted hover:text-text-primary">
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

// ---- Toggle switch ----

interface ToggleProps {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}

function Toggle({ checked, onChange, disabled }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={(e) => {
        e.stopPropagation()
        if (!disabled) onChange(!checked)
      }}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-bg-surface disabled:opacity-50 ${
        checked ? 'bg-primary-500' : 'border border-border bg-bg-elevated'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-text-primary shadow transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

// ---- Helpers ----

function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) return 'Error desconocido'
  try {
    const parsed = JSON.parse(err.message)
    return parsed?.detail ?? err.message
  } catch {
    return err.message
  }
}

function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-')
  return `${d}/${m}/${y}`
}

function formatRate(rateStr: string): string {
  const n = parseFloat(rateStr)
  if (isNaN(n)) return rateStr
  return n.toLocaleString('es-PY', { minimumFractionDigits: 2, maximumFractionDigits: 6 })
}

// ---- AddRateModal ----

interface AddRateModalProps {
  currency: CurrencyOut
  onClose: () => void
  onSaved: (rate: ExchangeRateOut) => void
  onError: (msg: string) => void
}

function AddRateModal({ currency, onClose, onSaved, onError }: AddRateModalProps) {
  const today = new Date().toISOString().split('T')[0]
  const [rateValue, setRateValue] = useState('')
  const [effectiveDate, setEffectiveDate] = useState(today)
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const rate = parseFloat(rateValue)
    if (!rateValue || isNaN(rate) || rate <= 0) {
      onError('La tasa debe ser un número mayor a 0')
      return
    }

    setSaving(true)
    try {
      const result = await createExchangeRate(currency.code, {
        id: crypto.randomUUID(),
        rate_to_base: rate,
        effective_date: effectiveDate,
        notes: notes.trim() || undefined,
      })
      onSaved(result)
      onClose()
    } catch (err) {
      onError(parseApiError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            Nuevo tipo de cambio — {currency.code}
          </h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="modal-rate">
              Tasa ({currency.code}/PYG)
            </label>
            <p className="mb-1.5 text-xs text-text-muted">
              Cuántos Gs vale 1 {currency.symbol}
            </p>
            <input
              id="modal-rate"
              className="input"
              type="number"
              step="any"
              min="0.000001"
              placeholder="ej. 7350"
              value={rateValue}
              onChange={(e) => setRateValue(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="label" htmlFor="modal-date">
              Fecha de vigencia
            </label>
            <input
              id="modal-date"
              className="input"
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="label" htmlFor="modal-notes">
              Notas{' '}
              <span className="font-normal text-text-muted">(opcional)</span>
            </label>
            <input
              id="modal-notes"
              className="input"
              type="text"
              placeholder="ej. Cotización BCP mediodía"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---- EditRateModal ----

interface EditRateModalProps {
  rate: ExchangeRateOut
  currencySymbol: string
  onClose: () => void
  onSaved: (rate: ExchangeRateOut) => void
  onError: (msg: string) => void
}

function EditRateModal({ rate, currencySymbol, onClose, onSaved, onError }: EditRateModalProps) {
  const [rateValue, setRateValue] = useState(parseFloat(rate.rate_to_base).toString())
  const [notes, setNotes] = useState(rate.notes ?? '')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const parsed = parseFloat(rateValue)
    if (!rateValue || isNaN(parsed) || parsed <= 0) {
      onError('La tasa debe ser un número mayor a 0')
      return
    }
    setSaving(true)
    try {
      const result = await updateExchangeRate(rate.id, {
        rate_to_base: parsed,
        notes: notes.trim() || null,
      })
      onSaved(result)
      onClose()
    } catch (err) {
      onError(parseApiError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div className="card w-full max-w-md space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Editar tipo de cambio</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="label">Moneda</p>
            <p className="mt-1 text-sm text-text-primary">{rate.currency_code}</p>
          </div>
          <div>
            <p className="label">Fecha de vigencia</p>
            <p className="mt-1 text-sm text-text-primary">{formatDate(rate.effective_date)}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="edit-rate">
              Tasa ({rate.currency_code}/PYG)
            </label>
            <p className="mb-1.5 text-xs text-text-muted">
              Cuántos Gs vale 1 {currencySymbol}
            </p>
            <input
              id="edit-rate"
              className="input"
              type="number"
              step="any"
              min="0.000001"
              value={rateValue}
              onChange={(e) => setRateValue(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="label" htmlFor="edit-notes">
              Notas <span className="font-normal text-text-muted">(opcional)</span>
            </label>
            <input
              id="edit-notes"
              className="input"
              type="text"
              placeholder="ej. Cotización BCP mediodía"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---- DeleteRateModal ----

interface DeleteRateModalProps {
  rate: ExchangeRateOut
  onClose: () => void
  onDeleted: (rateId: string, currencyCode: string) => void
  onError: (msg: string) => void
}

function DeleteRateModal({ rate, onClose, onDeleted, onError }: DeleteRateModalProps) {
  const [deleting, setDeleting] = useState(false)

  const handleConfirm = async () => {
    setDeleting(true)
    try {
      await deleteExchangeRate(rate.id)
      onDeleted(rate.id, rate.currency_code)
      onClose()
    } catch (err) {
      onError(parseApiError(err))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Eliminar tipo de cambio</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">
          ¿Eliminar tasa del{' '}
          <span className="font-medium text-text-primary">{formatDate(rate.effective_date)}</span>?
          Esta acción no se puede deshacer.
        </p>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button type="button" className="btn-danger" onClick={handleConfirm} disabled={deleting}>
            {deleting ? 'Eliminando…' : 'Eliminar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- CurrencyCard ----

interface CurrencyCardProps {
  currency: CurrencyOut
  selected: boolean
  toggling: boolean
  onClick: () => void
  onToggle: (is_active: boolean) => void
}

function CurrencyCard({ currency, selected, toggling, onClick, onToggle }: CurrencyCardProps) {
  const isPYG = currency.code === 'PYG'

  return (
    <div
      className={`card cursor-pointer transition-colors ${
        selected ? 'border-primary-500/50 bg-bg-elevated' : 'hover:bg-bg-elevated/50'
      } ${!currency.is_active ? 'opacity-60' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5">
            <span className="text-base font-bold text-text-primary">{currency.code}</span>
            <span className="text-sm text-text-secondary">{currency.symbol}</span>
          </div>
          <p className="truncate text-sm text-text-secondary">{currency.name}</p>
          <p className="text-xs text-text-muted">{currency.decimal_places} decimales</p>
        </div>
        <div className="flex flex-shrink-0 flex-col items-end gap-1">
          <Toggle
            checked={currency.is_active}
            onChange={onToggle}
            disabled={toggling || isPYG}
          />
          <span className="text-xs text-text-muted">
            {isPYG ? 'Base' : currency.is_active ? 'Activa' : 'Inactiva'}
          </span>
        </div>
      </div>
    </div>
  )
}

// ---- ExchangeRatePanel ----

interface RatePanelProps {
  currency: CurrencyOut
  rates: ExchangeRateOut[]
  loadingRates: boolean
  onAddRate: () => void
  onEditRate: (rate: ExchangeRateOut) => void
  onDeleteRate: (rate: ExchangeRateOut) => void
}

function ExchangeRatePanel({ currency, rates, loadingRates, onAddRate, onEditRate, onDeleteRate }: RatePanelProps) {
  const isBase = currency.code === 'PYG'

  return (
    <div className="card flex h-full flex-col">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            {currency.code} — Tipos de cambio
          </h2>
          <p className="text-xs text-text-muted">
            Historial de tasas respecto al Guaraní (PYG)
          </p>
        </div>
        {!isBase && (
          <button
            className="btn-primary flex flex-shrink-0 items-center gap-1.5"
            onClick={onAddRate}
          >
            <Plus className="h-4 w-4" />
            Nueva tasa
          </button>
        )}
      </div>

      {isBase ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-text-muted">
            PYG es la moneda base del sistema. Tasa implícita: 1 Gs = 1 Gs.
          </p>
        </div>
      ) : loadingRates ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-text-muted">Cargando…</p>
        </div>
      ) : rates.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3">
          <p className="text-sm text-text-muted">Sin tipos de cambio registrados.</p>
          <button
            className="btn-secondary flex items-center gap-1.5 text-sm"
            onClick={onAddRate}
          >
            <Plus className="h-4 w-4" />
            Agregar primera tasa
          </button>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-bg-surface">
              <tr className="border-b border-border-subtle">
                <th className="pb-2 text-left text-xs font-medium text-text-secondary">Fecha</th>
                <th className="pb-2 text-right text-xs font-medium text-text-secondary tabular-nums">
                  1 {currency.symbol} =
                </th>
                <th className="pb-2 pl-4 text-left text-xs font-medium text-text-secondary">Notas</th>
                <th className="pb-2 pl-4 text-right text-xs font-medium text-text-secondary">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {rates.map((r, i) => (
                <tr key={r.id} className={i === 0 ? 'text-text-primary' : 'text-text-secondary'}>
                  <td className="py-2.5">{formatDate(r.effective_date)}</td>
                  <td className="py-2.5 text-right tabular-nums">Gs {formatRate(r.rate_to_base)}</td>
                  <td className="py-2.5 pl-4 text-text-muted">
                    {r.notes ?? <span className="text-border">—</span>}
                  </td>
                  <td className="py-2.5 pl-4">
                    <div className={`flex justify-end gap-1 ${r.can_edit ? '' : 'invisible'}`}>
                      <button
                        type="button"
                        onClick={() => onEditRate(r)}
                        className="rounded p-1 text-text-muted hover:bg-bg-elevated hover:text-text-primary"
                        title="Editar tasa"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onDeleteRate(r)}
                        className="rounded p-1 text-text-muted hover:bg-bg-elevated hover:text-danger-500"
                        title="Eliminar tasa"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
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

// ---- Page ----

export function Currencies() {
  const [currencies, setCurrencies] = useState<CurrencyOut[]>([])
  const [loadingPage, setLoadingPage] = useState(true)
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [ratesMap, setRatesMap] = useState<Record<string, ExchangeRateOut[]>>({})
  const [loadingRates, setLoadingRates] = useState(false)
  const [toggling, setToggling] = useState<Record<string, boolean>>({})
  const [showModal, setShowModal] = useState(false)
  const [editingRate, setEditingRate] = useState<ExchangeRateOut | null>(null)
  const [deletingRate, setDeletingRate] = useState<ExchangeRateOut | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type, id: Date.now() })
  }, [])

  useEffect(() => {
    fetchCurrencies()
      .then((list) => {
        setCurrencies(list)
        if (list.length > 0) setSelectedCode(list[0].code)
      })
      .catch(() => showToast('No se pudo cargar la lista de monedas', 'error'))
      .finally(() => setLoadingPage(false))
  }, [showToast])

  useEffect(() => {
    if (!selectedCode || ratesMap[selectedCode] !== undefined) return
    setLoadingRates(true)
    fetchExchangeRates(selectedCode)
      .then((rates) => setRatesMap((prev) => ({ ...prev, [selectedCode]: rates })))
      .catch(() => showToast('No se pudo cargar los tipos de cambio', 'error'))
      .finally(() => setLoadingRates(false))
  }, [selectedCode, ratesMap, showToast])

  const handleToggle = useCallback(
    async (code: string, is_active: boolean) => {
      setToggling((prev) => ({ ...prev, [code]: true }))
      try {
        const updated = await toggleCurrency(code, is_active)
        setCurrencies((prev) => prev.map((c) => (c.code === code ? updated : c)))
        showToast(is_active ? `${code} activada` : `${code} desactivada`, 'success')
      } catch (err) {
        showToast(parseApiError(err), 'error')
      } finally {
        setToggling((prev) => ({ ...prev, [code]: false }))
      }
    },
    [showToast],
  )

  const handleRateSaved = useCallback(
    (rate: ExchangeRateOut) => {
      setRatesMap((prev) => {
        const existing = prev[rate.currency_code] ?? []
        const sorted = [rate, ...existing].sort((a, b) =>
          b.effective_date.localeCompare(a.effective_date),
        )
        const newIsLatest = sorted[0].id === rate.id
        return {
          ...prev,
          [rate.currency_code]: newIsLatest
            ? sorted.map((r, i) => ({ ...r, can_edit: i === 0 }))
            : sorted,
        }
      })
      showToast('Tipo de cambio guardado', 'success')
    },
    [showToast],
  )

  const handleRateUpdated = useCallback(
    (updated: ExchangeRateOut) => {
      setRatesMap((prev) => ({
        ...prev,
        [updated.currency_code]: (prev[updated.currency_code] ?? []).map((r) =>
          r.id === updated.id ? { ...updated, can_edit: true } : r,
        ),
      }))
      showToast('Tipo de cambio actualizado', 'success')
    },
    [showToast],
  )

  const handleRateDeleted = useCallback(
    (_rateId: string, currencyCode: string) => {
      setRatesMap((prev) => {
        const { [currencyCode]: _, ...rest } = prev
        return rest
      })
      showToast('Tipo de cambio eliminado', 'success')
    },
    [showToast],
  )

  const selectedCurrency = currencies.find((c) => c.code === selectedCode)

  if (loadingPage) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-text-muted">Cargando monedas…</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Monedas</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Activá o desactivá monedas y registrá tipos de cambio históricos
        </p>
      </div>

      <div className="flex min-h-0 flex-1 gap-6">
        <div className="w-64 flex-shrink-0 space-y-3 overflow-y-auto">
          {currencies.map((c) => (
            <CurrencyCard
              key={c.code}
              currency={c}
              selected={selectedCode === c.code}
              toggling={!!toggling[c.code]}
              onClick={() => setSelectedCode(c.code)}
              onToggle={(is_active) => handleToggle(c.code, is_active)}
            />
          ))}
        </div>

        <div className="min-w-0 flex-1">
          {selectedCurrency ? (
            <ExchangeRatePanel
              currency={selectedCurrency}
              rates={ratesMap[selectedCurrency.code] ?? []}
              loadingRates={loadingRates && ratesMap[selectedCurrency.code] === undefined}
              onAddRate={() => setShowModal(true)}
              onEditRate={setEditingRate}
              onDeleteRate={setDeletingRate}
            />
          ) : (
            <div className="card flex h-full items-center justify-center">
              <p className="text-sm text-text-muted">
                Seleccioná una moneda para ver sus tipos de cambio
              </p>
            </div>
          )}
        </div>
      </div>

      {showModal && selectedCurrency && (
        <AddRateModal
          currency={selectedCurrency}
          onClose={() => setShowModal(false)}
          onSaved={handleRateSaved}
          onError={(msg) => showToast(msg, 'error')}
        />
      )}

      {editingRate && selectedCurrency && (
        <EditRateModal
          rate={editingRate}
          currencySymbol={selectedCurrency.symbol}
          onClose={() => setEditingRate(null)}
          onSaved={handleRateUpdated}
          onError={(msg) => showToast(msg, 'error')}
        />
      )}

      {deletingRate && (
        <DeleteRateModal
          rate={deletingRate}
          onClose={() => setDeletingRate(null)}
          onDeleted={handleRateDeleted}
          onError={(msg) => showToast(msg, 'error')}
        />
      )}

      {toast && <Toast toast={toast} onClose={() => setToast(null)} />}
    </div>
  )
}
