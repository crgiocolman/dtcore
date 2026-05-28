import { useEffect, useState } from 'react'
import { Pencil, Plus, X } from 'lucide-react'
import {
  createUnitCatalog,
  fetchUnitCatalog,
  updateUnitCatalog,
  UNIT_TYPE_LABELS,
  type UnitCatalogOut,
  type UnitCatalogCreate,
  type UnitCatalogUpdate,
  type UnitType,
} from '../api/unit_catalog'

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

// ---- Toggle ----

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
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

// ---- Unit form modal ----

interface UnitFormState {
  code: string
  name: string
  symbol: string
  unit_type: UnitType
}

type UnitFormErrors = Partial<Record<keyof UnitFormState, string>>

const UNIT_TYPES: UnitType[] = ['weight', 'length', 'volume', 'count', 'package']

function UnitModal({
  entry,
  saving,
  onSave,
  onClose,
}: {
  entry: UnitCatalogOut | null
  saving: boolean
  onSave: (data: UnitFormState) => void
  onClose: () => void
}) {
  const isEdit = entry !== null
  const [form, setForm] = useState<UnitFormState>({
    code: entry?.code ?? '',
    name: entry?.name ?? '',
    symbol: entry?.symbol ?? '',
    unit_type: entry?.unit_type ?? 'count',
  })
  const [errors, setErrors] = useState<UnitFormErrors>({})

  const set = <K extends keyof UnitFormState>(key: K, value: UnitFormState[K]) => {
    setForm((p) => ({ ...p, [key]: value }))
    setErrors((p) => ({ ...p, [key]: undefined }))
  }

  const validate = (): boolean => {
    const errs: UnitFormErrors = {}
    if (!isEdit) {
      if (!form.code.trim()) errs.code = 'Campo requerido'
      else if (!/^[a-z0-9_]+$/.test(form.code.trim())) errs.code = 'Solo letras minúsculas, números y _'
    }
    if (!form.name.trim()) errs.name = 'Campo requerido'
    if (!form.symbol.trim()) errs.symbol = 'Campo requerido'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div className="card w-full max-w-md space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">
            {isEdit ? 'Editar unidad' : 'Nueva unidad'}
          </h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label" htmlFor="modal-code">
                Código{' '}
                {!isEdit && <span className="text-danger-500">*</span>}
              </label>
              {isEdit ? (
                <p className="mt-1 font-mono text-sm text-text-secondary">{entry.code}</p>
              ) : (
                <>
                  <input
                    id="modal-code"
                    className={`input font-mono ${errors.code ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                    type="text"
                    placeholder="ej. kg, box, roll"
                    value={form.code}
                    onChange={(e) => set('code', e.target.value.toLowerCase())}
                    autoFocus
                  />
                  {errors.code && <p className="mt-1 text-xs text-danger-500">{errors.code}</p>}
                </>
              )}
            </div>

            <div>
              <label className="label" htmlFor="modal-symbol">
                Símbolo <span className="text-danger-500">*</span>
              </label>
              <input
                id="modal-symbol"
                className={`input ${errors.symbol ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                type="text"
                placeholder="ej. kg, u, caja"
                value={form.symbol}
                onChange={(e) => set('symbol', e.target.value)}
                autoFocus={isEdit}
              />
              {errors.symbol && <p className="mt-1 text-xs text-danger-500">{errors.symbol}</p>}
            </div>
          </div>

          <div>
            <label className="label" htmlFor="modal-name">
              Nombre <span className="text-danger-500">*</span>
            </label>
            <input
              id="modal-name"
              className={`input ${errors.name ? 'border-danger-500 focus:ring-danger-500' : ''}`}
              type="text"
              placeholder="ej. Kilogramo, Caja, Rollo"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
            />
            {errors.name && <p className="mt-1 text-xs text-danger-500">{errors.name}</p>}
          </div>

          <div>
            <label className="label" htmlFor="modal-type">
              Tipo
            </label>
            <select
              id="modal-type"
              className="input"
              value={form.unit_type}
              onChange={(e) => set('unit_type', e.target.value as UnitType)}
            >
              {UNIT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {UNIT_TYPE_LABELS[t]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={saving}
            onClick={() => validate() && onSave(form)}
          >
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Page ----

export function UnitCatalog() {
  const [entries, setEntries] = useState<UnitCatalogOut[]>([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<UnitType | ''>('')
  const [modal, setModal] = useState<UnitCatalogOut | null | 'new'>(null)
  const [saving, setSaving] = useState(false)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  useEffect(() => {
    fetchUnitCatalog()
      .then(setEntries)
      .catch(() => setApiError('No se pudo cargar el catálogo de unidades'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async (data: UnitFormState) => {
    setSaving(true)
    setApiError(null)
    try {
      if (modal === 'new') {
        const payload: UnitCatalogCreate = {
          id: crypto.randomUUID(),
          code: data.code.trim(),
          name: data.name.trim(),
          symbol: data.symbol.trim(),
          unit_type: data.unit_type,
        }
        const created = await createUnitCatalog(payload)
        setEntries((prev) => [...prev, created])
      } else if (modal) {
        const payload: UnitCatalogUpdate = {
          name: data.name.trim(),
          symbol: data.symbol.trim(),
          unit_type: data.unit_type,
        }
        const updated = await updateUnitCatalog(modal.id, payload)
        setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
      }
      setModal(null)
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (entry: UnitCatalogOut) => {
    if (togglingId) return
    setTogglingId(entry.id)
    setApiError(null)
    try {
      const updated = await updateUnitCatalog(entry.id, { is_active: !entry.is_active })
      setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setTogglingId(null)
    }
  }

  const filtered = filterType ? entries.filter((e) => e.unit_type === filterType) : entries

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-text-muted">Cargando…</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Catálogo de unidades</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Unidades de medida disponibles para productos y transacciones
          </p>
        </div>
        <button
          type="button"
          className="btn-primary flex flex-shrink-0 items-center gap-1.5"
          onClick={() => setModal('new')}
        >
          <Plus className="h-4 w-4" />
          Nueva unidad
        </button>
      </div>

      {apiError && (
        <div className="rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
          {apiError}
        </div>
      )}

      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <label className="text-sm text-text-secondary">Filtrar por tipo:</label>
          <select
            className="input w-auto"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as UnitType | '')}
          >
            <option value="">Todos</option>
            {UNIT_TYPES.map((t) => (
              <option key={t} value={t}>
                {UNIT_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>

        {filtered.length === 0 ? (
          <p className="text-sm text-text-muted">No hay unidades que coincidan con el filtro.</p>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-subtle">
                  <th className="pb-2 text-left text-xs font-medium text-text-secondary">Código</th>
                  <th className="pb-2 text-left text-xs font-medium text-text-secondary">Nombre</th>
                  <th className="pb-2 text-left text-xs font-medium text-text-secondary">Símbolo</th>
                  <th className="pb-2 text-left text-xs font-medium text-text-secondary">Tipo</th>
                  <th className="pb-2 text-left text-xs font-medium text-text-secondary">Estado</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {filtered.map((e) => (
                  <tr key={e.id} className={!e.is_active ? 'opacity-60' : undefined}>
                    <td className="py-2.5 pr-4 font-mono text-text-secondary">{e.code}</td>
                    <td className="py-2.5 pr-4 text-text-primary">{e.name}</td>
                    <td className="py-2.5 pr-4 font-mono text-text-secondary">{e.symbol}</td>
                    <td className="py-2.5 pr-4 text-text-secondary">
                      {UNIT_TYPE_LABELS[e.unit_type]}
                    </td>
                    <td className="py-2.5 pr-4">
                      <Toggle
                        checked={e.is_active}
                        onChange={() => handleToggle(e)}
                        disabled={togglingId === e.id}
                      />
                    </td>
                    <td className="py-2.5 text-right">
                      <button
                        type="button"
                        className="btn-ghost px-2 py-1"
                        aria-label={`Editar ${e.name}`}
                        onClick={() => setModal(e)}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal !== null && (
        <UnitModal
          entry={modal === 'new' ? null : modal}
          saving={saving}
          onSave={handleSave}
          onClose={() => {
            setModal(null)
            setApiError(null)
          }}
        />
      )}
    </div>
  )
}
