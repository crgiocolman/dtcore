import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Pencil, Plus, Trash2, X } from 'lucide-react'
import { fetchCategoryTree, flattenTree } from '../api/categories'
import {
  createProduct,
  deleteProduct,
  fetchProduct,
  updateProduct,
  type ProductOut,
} from '../api/products'
import {
  createUnit,
  deleteUnit,
  fetchUnits,
  toggleUnitActive,
  updateUnit,
  type ProductUnitOut,
} from '../api/units'
import { createPrice, fetchPriceHistory, type PriceOut } from '../api/prices'
import { fetchCurrencies, type CurrencyOut } from '../../admin/api/currencies'

// ---- Helpers ----

function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) return 'Error desconocido'
  try {
    const parsed = JSON.parse(err.message)
    if (typeof parsed?.detail === 'object' && parsed.detail !== null) {
      return parsed.detail.message ?? err.message
    }
    return parsed?.detail ?? err.message
  } catch {
    return err.message
  }
}

interface StructuredError {
  code?: string
  message: string
  unit_id?: string
}

function parseApiErrorStructured(err: unknown): StructuredError {
  if (!(err instanceof Error)) return { message: 'Error desconocido' }
  try {
    const parsed = JSON.parse(err.message)
    if (typeof parsed?.detail === 'object' && parsed.detail !== null) {
      return {
        code: parsed.detail.code,
        message: parsed.detail.message ?? err.message,
        unit_id: parsed.detail.unit_id,
      }
    }
    return { message: parsed?.detail ?? err.message }
  } catch {
    return { message: err.message }
  }
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatPrice(value: string, decimals: number): string {
  const n = parseFloat(value)
  if (isNaN(n)) return '—'
  return new Intl.NumberFormat('es-PY', { maximumFractionDigits: decimals }).format(n)
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

// ---- Delete product modal ----

function DeleteModal({
  name,
  deleting,
  onConfirm,
  onClose,
}: {
  name: string
  deleting: boolean
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Eliminar producto</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">
          ¿Eliminar{' '}
          <span className="font-medium text-text-primary">{name}</span>? Esta acción no se puede
          deshacer.
        </p>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={onConfirm}
            disabled={deleting}
          >
            {deleting ? 'Eliminando…' : 'Eliminar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Confirm toggle modal ----

function ConfirmToggleModal({
  message,
  loading,
  onConfirm,
  onClose,
}: {
  message: string
  loading: boolean
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Inactivar unidad</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">{message}</p>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Guardando…' : 'Continuar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Reactivate unit modal ----

function ReactivateModal({
  unitName,
  reactivating,
  onConfirm,
  onClose,
}: {
  unitName: string
  reactivating: boolean
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Unidad existente</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">
          Ya existe una unidad{' '}
          <span className="font-medium text-text-primary">"{unitName}"</span> inactiva para este
          producto. ¿Querés reactivarla?
        </p>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={onConfirm}
            disabled={reactivating}
          >
            {reactivating ? 'Reactivando…' : 'Reactivar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Unit modal ----

interface UnitFormState {
  unit_name: string
  factor_to_base: string
  is_default_sale_unit: boolean
  is_default_purchase_unit: boolean
  barcode: string
}

type UnitFormErrors = Partial<Record<keyof UnitFormState, string>>

const DEFAULT_UNIT_FORM: UnitFormState = {
  unit_name: '',
  factor_to_base: '1',
  is_default_sale_unit: false,
  is_default_purchase_unit: false,
  barcode: '',
}

function UnitModal({
  initial,
  factorLocked,
  saving,
  onSave,
  onClose,
}: {
  initial: UnitFormState
  factorLocked: boolean
  saving: boolean
  onSave: (data: UnitFormState) => void
  onClose: () => void
}) {
  const [form, setForm] = useState<UnitFormState>(initial)
  const [errors, setErrors] = useState<UnitFormErrors>({})

  const set = <K extends keyof UnitFormState>(key: K, value: UnitFormState[K]) => {
    setForm((p) => ({ ...p, [key]: value }))
    setErrors((p) => ({ ...p, [key]: undefined }))
  }

  const validate = (): boolean => {
    const errs: UnitFormErrors = {}
    if (!form.unit_name.trim()) errs.unit_name = 'Campo requerido'
    const factor = parseFloat(form.factor_to_base)
    if (isNaN(factor) || factor <= 0) errs.factor_to_base = 'Debe ser mayor a 0'
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
            {initial.unit_name ? 'Editar unidad' : 'Agregar unidad'}
          </h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="label">Nombre de unidad</label>
            <input
              className={`input ${errors.unit_name ? 'border-danger-500 focus:ring-danger-500' : ''}`}
              type="text"
              placeholder="ej. Caja, Docena, kg"
              value={form.unit_name}
              onChange={(e) => set('unit_name', e.target.value)}
            />
            {errors.unit_name && (
              <p className="mt-1 text-xs text-danger-500">{errors.unit_name}</p>
            )}
          </div>

          <div>
            <label className="label">Factor (respecto a unidad base)</label>
            <input
              className={`input tabular-nums ${errors.factor_to_base ? 'border-danger-500 focus:ring-danger-500' : ''}`}
              type="number"
              step="any"
              min="0.0001"
              placeholder="1"
              value={form.factor_to_base}
              onChange={(e) => set('factor_to_base', e.target.value)}
              disabled={factorLocked}
            />
            {factorLocked && (
              <p className="mt-1 text-xs text-text-muted">No editable: tiene movimientos o precios</p>
            )}
            {errors.factor_to_base && (
              <p className="mt-1 text-xs text-danger-500">{errors.factor_to_base}</p>
            )}
          </div>

          <div>
            <label className="label">Código de barras</label>
            <input
              className="input"
              type="text"
              placeholder="Opcional"
              value={form.barcode}
              onChange={(e) => set('barcode', e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-6">
          <label className="flex cursor-pointer items-center gap-2 select-none">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border accent-primary-500"
              checked={form.is_default_sale_unit}
              onChange={(e) => set('is_default_sale_unit', e.target.checked)}
            />
            <span className="text-sm text-text-secondary">Unidad de venta por defecto</span>
          </label>
          <label className="flex cursor-pointer items-center gap-2 select-none">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border accent-primary-500"
              checked={form.is_default_purchase_unit}
              onChange={(e) => set('is_default_purchase_unit', e.target.checked)}
            />
            <span className="text-sm text-text-secondary">Unidad de compra por defecto</span>
          </label>
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
            {saving ? 'Guardando…' : 'Guardar unidad'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Price modal ----

interface PriceFormState {
  price: string
  effective_from: string
  notes: string
}

type PriceFormErrors = Partial<Record<keyof PriceFormState, string>>

function PriceModal({
  unitName,
  currencyCode,
  currencySymbol,
  saving,
  onSave,
  onClose,
}: {
  unitName: string
  currencyCode: string
  currencySymbol: string
  saving: boolean
  onSave: (data: PriceFormState) => void
  onClose: () => void
}) {
  const [form, setForm] = useState<PriceFormState>({
    price: '',
    effective_from: today(),
    notes: '',
  })
  const [errors, setErrors] = useState<PriceFormErrors>({})

  const set = <K extends keyof PriceFormState>(key: K, value: string) => {
    setForm((p) => ({ ...p, [key]: value }))
    setErrors((p) => ({ ...p, [key]: undefined }))
  }

  const validate = (): boolean => {
    const errs: PriceFormErrors = {}
    const p = parseFloat(form.price)
    if (form.price.trim() === '' || isNaN(p) || p < 0) errs.price = 'Ingrese un precio válido (≥ 0)'
    if (!form.effective_from) errs.effective_from = 'Campo requerido'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Cambiar precio</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="text-sm text-text-secondary">
          <span className="font-medium text-text-primary">{unitName}</span>
          {' · '}
          <span className="font-medium text-text-primary">{currencyCode}</span>
        </p>

        <div className="space-y-3">
          <div>
            <label className="label">
              Precio ({currencySymbol})
            </label>
            <input
              className={`input tabular-nums ${errors.price ? 'border-danger-500 focus:ring-danger-500' : ''}`}
              type="number"
              min="0"
              step="any"
              placeholder="0"
              value={form.price}
              onChange={(e) => set('price', e.target.value)}
              autoFocus
            />
            {errors.price && <p className="mt-1 text-xs text-danger-500">{errors.price}</p>}
          </div>

          <div>
            <label className="label">Vigente desde</label>
            <input
              className={`input ${errors.effective_from ? 'border-danger-500 focus:ring-danger-500' : ''}`}
              type="date"
              value={form.effective_from}
              onChange={(e) => set('effective_from', e.target.value)}
            />
            {errors.effective_from && (
              <p className="mt-1 text-xs text-danger-500">{errors.effective_from}</p>
            )}
          </div>

          <div>
            <label className="label">
              Notas{' '}
              <span className="font-normal text-text-muted">(opcional)</span>
            </label>
            <textarea
              className="input resize-none"
              rows={2}
              placeholder="Ajuste de precio por inflación, etc."
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
            />
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
            {saving ? 'Guardando…' : 'Guardar precio'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Main form state ----

interface ProductFormState {
  sku: string
  barcode: string
  name: string
  description: string
  category_id: string
  base_unit: string
  tax_rate: string
  tax_included_in_price: boolean
  track_stock: boolean
  low_stock_threshold: string
  is_active: boolean
}

type ProductFormErrors = Partial<Record<keyof ProductFormState, string>>

const DEFAULT_FORM: ProductFormState = {
  sku: '',
  barcode: '',
  name: '',
  description: '',
  category_id: '',
  base_unit: '',
  tax_rate: '10.00',
  tax_included_in_price: true,
  track_stock: true,
  low_stock_threshold: '',
  is_active: true,
}

function fromProduct(p: ProductOut): ProductFormState {
  return {
    sku: p.sku,
    barcode: p.barcode ?? '',
    name: p.name,
    description: p.description ?? '',
    category_id: p.category_id ?? '',
    base_unit: p.base_unit,
    tax_rate: p.tax_rate,
    tax_included_in_price: p.tax_included_in_price,
    track_stock: p.track_stock,
    low_stock_threshold: p.low_stock_threshold ?? '',
    is_active: p.is_active,
  }
}

// For create mode: a unit managed locally before product is saved
interface LocalUnit {
  id: string // client-generated UUID
  unit_name: string
  factor_to_base: string
  is_default_sale_unit: boolean
  is_default_purchase_unit: boolean
  barcode: string
  is_active: true
}

function localUnitFromForm(id: string, f: UnitFormState): LocalUnit {
  return { id, ...f, is_active: true }
}

function unitFormFromLocal(u: LocalUnit): UnitFormState {
  return {
    unit_name: u.unit_name,
    factor_to_base: u.factor_to_base,
    is_default_sale_unit: u.is_default_sale_unit,
    is_default_purchase_unit: u.is_default_purchase_unit,
    barcode: u.barcode,
  }
}

function unitFormFromSaved(u: ProductUnitOut): UnitFormState {
  return {
    unit_name: u.unit_name,
    factor_to_base: u.factor_to_base,
    is_default_sale_unit: u.is_default_sale_unit,
    is_default_purchase_unit: u.is_default_purchase_unit,
    barcode: u.barcode ?? '',
  }
}

// ---- Page ----

export function ProductForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)

  // Main form
  const [form, setForm] = useState<ProductFormState>(DEFAULT_FORM)
  const [errors, setErrors] = useState<ProductFormErrors>({})
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Category tree
  const [categoryTree, setCategoryTree] = useState<ReturnType<typeof flattenTree>>([])
  useEffect(() => {
    fetchCategoryTree()
      .then((tree) => setCategoryTree(flattenTree(tree)))
      .catch(() => {})
  }, [])

  // Units (edit mode: from server; create mode: local)
  const [savedUnits, setSavedUnits] = useState<ProductUnitOut[]>([])
  const [localUnits, setLocalUnits] = useState<LocalUnit[]>([]) // create mode only
  const [unitModal, setUnitModal] = useState<{
    mode: 'add' | 'edit'
    editId?: string // for edit mode: server unit id; for local: local unit id
    initial: UnitFormState
    factorLocked: boolean
  } | null>(null)
  const [savingUnit, setSavingUnit] = useState(false)
  const [unitError, setUnitError] = useState<string | null>(null)
  const [deleteUnitId, setDeleteUnitId] = useState<string | null>(null)
  const [deletingUnit, setDeletingUnit] = useState(false)
  const [togglingUnitId, setTogglingUnitId] = useState<string | null>(null)
  const [confirmToggle, setConfirmToggle] = useState<{
    unit: ProductUnitOut
    message: string
  } | null>(null)
  const [reactivateModal, setReactivateModal] = useState<{
    unitName: string
    conflictingUnitId: string
  } | null>(null)
  const [reactivating, setReactivating] = useState(false)

  // Currencies + prices (edit mode only)
  const [currencies, setCurrencies] = useState<CurrencyOut[]>([])
  const [prices, setPrices] = useState<Record<string, PriceOut | null | undefined>>({})
  const [priceModal, setPriceModal] = useState<{
    unitId: string
    unitName: string
    currencyCode: string
    currencySymbol: string
  } | null>(null)
  const [savingPrice, setSavingPrice] = useState(false)
  const [priceError, setPriceError] = useState<string | null>(null)

  // Load product in edit mode
  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([fetchProduct(id), fetchUnits(id), fetchCurrencies()])
      .then(([product, units, currencyList]) => {
        setForm(fromProduct(product))
        setSavedUnits(units)
        const activeCurrencies = currencyList.filter((c) => c.is_active)
        setCurrencies(activeCurrencies)
        // Load current price per unit×currency
        loadPrices(id, units, activeCurrencies)
      })
      .catch((err) => setApiError(parseApiError(err)))
      .finally(() => setLoading(false))
  }, [id])

  function loadPrices(
    productId: string,
    units: ProductUnitOut[],
    activeCurrencies: CurrencyOut[],
  ) {
    // Mark all as loading
    const loading: Record<string, undefined> = {}
    for (const u of units) {
      for (const c of activeCurrencies) {
        loading[`${u.id}:${c.code}`] = undefined
      }
    }
    setPrices(loading)

    const today = new Date().toISOString().slice(0, 10)
    const tasks = units.flatMap((u) =>
      activeCurrencies.map(async (c) => {
        const history = await fetchPriceHistory(productId, u.id, c.code)
        const current = history.find((h) => h.effective_from <= today) ?? null
        return { key: `${u.id}:${c.code}`, price: current }
      }),
    )

    Promise.allSettled(tasks).then((results) => {
      const map: Record<string, PriceOut | null> = {}
      results.forEach((r) => {
        if (r.status === 'fulfilled') map[r.value.key] = r.value.price
      })
      setPrices(map)
    })
  }

  const set = <K extends keyof ProductFormState>(key: K, value: ProductFormState[K]) => {
    setForm((p) => ({ ...p, [key]: value }))
    setErrors((p) => ({ ...p, [key]: undefined }))
  }

  const validate = (): boolean => {
    const errs: ProductFormErrors = {}
    if (!form.sku.trim()) errs.sku = 'Campo requerido'
    if (!form.name.trim()) errs.name = 'Campo requerido'
    if (!form.base_unit.trim()) errs.base_unit = 'Campo requerido'
    const rate = parseFloat(form.tax_rate)
    if (isNaN(rate) || ![0, 5, 10].includes(rate)) errs.tax_rate = 'Debe ser 0, 5 o 10'
    if (form.track_stock && form.low_stock_threshold !== '') {
      const t = parseFloat(form.low_stock_threshold)
      if (isNaN(t) || t < 0) errs.low_stock_threshold = 'Debe ser un número ≥ 0'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    setSaving(true)
    setApiError(null)

    const payload = {
      sku: form.sku.trim(),
      barcode: form.barcode.trim() || null,
      name: form.name.trim(),
      description: form.description.trim() || null,
      category_id: form.category_id || null,
      base_unit: form.base_unit.trim(),
      track_stock: form.track_stock,
      tax_rate: form.tax_rate,
      tax_included_in_price: form.tax_included_in_price,
      low_stock_threshold:
        form.track_stock && form.low_stock_threshold.trim()
          ? form.low_stock_threshold.trim()
          : null,
      is_active: form.is_active,
    }

    try {
      if (isEdit && id) {
        await updateProduct(id, payload)
        navigate('/productos')
      } else {
        const productId = crypto.randomUUID()
        await createProduct({ id: productId, ...payload })
        // Create local units
        for (const u of localUnits) {
          await createUnit(productId, {
            id: u.id,
            unit_name: u.unit_name,
            factor_to_base: u.factor_to_base,
            is_default_sale_unit: u.is_default_sale_unit,
            is_default_purchase_unit: u.is_default_purchase_unit,
            barcode: u.barcode || null,
          })
        }
        navigate('/productos')
      }
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!id) return
    setDeleting(true)
    try {
      await deleteProduct(id)
      navigate('/productos')
    } catch (err) {
      setApiError(parseApiError(err))
      setShowDelete(false)
    } finally {
      setDeleting(false)
    }
  }

  // Unit modal save
  const handleUnitSave = async (data: UnitFormState) => {
    if (!unitModal) return
    setSavingUnit(true)
    setUnitError(null)

    if (!isEdit) {
      // Create mode: update local state
      if (unitModal.mode === 'add') {
        const newUnit = localUnitFromForm(crypto.randomUUID(), data)
        setLocalUnits((prev) => [...prev, newUnit])
      } else {
        setLocalUnits((prev) =>
          prev.map((u) =>
            u.id === unitModal.editId ? localUnitFromForm(u.id, data) : u,
          ),
        )
      }
      setSavingUnit(false)
      setUnitModal(null)
      return
    }

    // Edit mode: API call
    try {
      if (unitModal.mode === 'add') {
        const created = await createUnit(id!, {
          id: crypto.randomUUID(),
          unit_name: data.unit_name,
          factor_to_base: data.factor_to_base,
          is_default_sale_unit: data.is_default_sale_unit,
          is_default_purchase_unit: data.is_default_purchase_unit,
          barcode: data.barcode || null,
        })
        setSavedUnits((prev) => [...prev, created])
        // Load prices for new unit
        for (const c of currencies) {
          setPrices((p) => ({ ...p, [`${created.id}:${c.code}`]: null }))
        }
        setUnitModal(null)
      } else {
        const updated = await updateUnit(id!, unitModal.editId!, {
          unit_name: data.unit_name,
          factor_to_base: data.factor_to_base,
          is_default_sale_unit: data.is_default_sale_unit,
          is_default_purchase_unit: data.is_default_purchase_unit,
          barcode: data.barcode || null,
        })
        setSavedUnits((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
        setUnitModal(null)
      }
    } catch (err) {
      const structured = parseApiErrorStructured(err)
      if (structured.code === 'exists_inactive' && structured.unit_id) {
        setReactivateModal({ unitName: data.unit_name, conflictingUnitId: structured.unit_id })
        setUnitModal(null)
      } else {
        setUnitError(structured.message)
      }
    } finally {
      setSavingUnit(false)
    }
  }

  const handleUnitToggle = async (unit: ProductUnitOut) => {
    if (togglingUnitId) return
    // Confirm before deactivating a default unit
    if (unit.is_active && (unit.is_default_sale_unit || unit.is_default_purchase_unit)) {
      const defaults = [
        unit.is_default_sale_unit ? 'venta' : null,
        unit.is_default_purchase_unit ? 'compra' : null,
      ]
        .filter(Boolean)
        .join(' y ')
      setConfirmToggle({
        unit,
        message: `Esta unidad es el default de ${defaults}. Si la inactivás, el default pasa a la unidad base. ¿Continuar?`,
      })
      return
    }
    await doToggleUnit(unit)
  }

  const doToggleUnit = async (unit: ProductUnitOut) => {
    if (!id) return
    setTogglingUnitId(unit.id)
    setUnitError(null)
    try {
      const updated = await toggleUnitActive(id, unit.id)
      setSavedUnits((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
    } catch (err) {
      setUnitError(parseApiError(err))
    } finally {
      setTogglingUnitId(null)
      setConfirmToggle(null)
    }
  }

  const handleReactivate = async () => {
    if (!reactivateModal || !id) return
    setReactivating(true)
    setUnitError(null)
    try {
      const updated = await toggleUnitActive(id, reactivateModal.conflictingUnitId)
      setSavedUnits((prev) => {
        const exists = prev.find((u) => u.id === updated.id)
        return exists ? prev.map((u) => (u.id === updated.id ? updated : u)) : [...prev, updated]
      })
      setReactivateModal(null)
    } catch (err) {
      setUnitError(parseApiError(err))
    } finally {
      setReactivating(false)
    }
  }

  const handleUnitDelete = async (unitId: string) => {
    setDeletingUnit(true)
    setUnitError(null)
    if (!isEdit) {
      setLocalUnits((prev) => prev.filter((u) => u.id !== unitId))
      setDeleteUnitId(null)
      setDeletingUnit(false)
      return
    }
    try {
      await deleteUnit(id!, unitId)
      setSavedUnits((prev) => prev.filter((u) => u.id !== unitId))
      setPrices((prev) => {
        const next = { ...prev }
        Object.keys(next).forEach((k) => {
          if (k.startsWith(`${unitId}:`)) delete next[k]
        })
        return next
      })
      setDeleteUnitId(null)
    } catch (err) {
      setUnitError(parseApiError(err))
      setDeleteUnitId(null)
    } finally {
      setDeletingUnit(false)
    }
  }

  const handlePriceSave = async (data: PriceFormState) => {
    if (!priceModal || !id) return
    setSavingPrice(true)
    setPriceError(null)
    try {
      const created = await createPrice(id, priceModal.unitId, {
        id: crypto.randomUUID(),
        currency_code: priceModal.currencyCode,
        price: parseFloat(data.price).toFixed(4),
        effective_from: data.effective_from,
        notes: data.notes.trim() || null,
      })
      setPrices((prev) => ({
        ...prev,
        [`${priceModal.unitId}:${priceModal.currencyCode}`]: created,
      }))
      setPriceModal(null)
    } catch (err) {
      setPriceError(parseApiError(err))
    } finally {
      setSavingPrice(false)
    }
  }

  const displayUnits = isEdit ? savedUnits : localUnits

  // Only show prices for active units
  const priceRows = useMemo(
    () =>
      savedUnits
        .filter((u) => u.is_active)
        .flatMap((u) =>
          currencies.map((c) => ({
            unitId: u.id,
            unitName: u.unit_name,
            currencyCode: c.code,
            currencySymbol: c.symbol,
            decimals: c.decimal_places,
            priceEntry: prices[`${u.id}:${c.code}`],
          })),
        ),
    [savedUnits, currencies, prices],
  )

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-text-muted">Cargando…</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6 flex flex-shrink-0 items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={() => navigate('/productos')}
            className="mb-2 flex items-center gap-1 text-sm text-text-muted transition-colors hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver a productos
          </button>
          <h1 className="text-2xl font-semibold text-text-primary">
            {isEdit ? 'Editar producto' : 'Nuevo producto'}
          </h1>
        </div>
        {isEdit && (
          <button
            type="button"
            className="btn-danger flex flex-shrink-0 items-center gap-1.5"
            onClick={() => setShowDelete(true)}
          >
            <Trash2 className="h-4 w-4" />
            Eliminar
          </button>
        )}
      </div>

      {/* Scrollable form */}
      <form className="flex-1 overflow-y-auto" onSubmit={handleSubmit} noValidate>
        <div className="max-w-2xl space-y-6 pb-6">
          {apiError && (
            <div className="rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
              {apiError}
            </div>
          )}

          {/* Datos principales */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Datos del producto</h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label" htmlFor="sku">
                  SKU <span className="text-danger-500">*</span>
                </label>
                <input
                  id="sku"
                  className={`input font-mono ${errors.sku ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                  type="text"
                  placeholder="ej. PROD-001"
                  value={form.sku}
                  onChange={(e) => set('sku', e.target.value)}
                />
                {errors.sku && <p className="mt-1 text-xs text-danger-500">{errors.sku}</p>}
              </div>

              <div>
                <label className="label" htmlFor="barcode">
                  Código de barras{' '}
                  <span className="font-normal text-text-muted">(opcional)</span>
                </label>
                <input
                  id="barcode"
                  className="input font-mono"
                  type="text"
                  placeholder="ej. 7891234567890"
                  value={form.barcode}
                  onChange={(e) => set('barcode', e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="label" htmlFor="name">
                Nombre <span className="text-danger-500">*</span>
              </label>
              <input
                id="name"
                className={`input ${errors.name ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                type="text"
                placeholder="ej. Caja de cartón 60×40×40"
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
              />
              {errors.name && <p className="mt-1 text-xs text-danger-500">{errors.name}</p>}
            </div>

            <div>
              <label className="label" htmlFor="description">
                Descripción{' '}
                <span className="font-normal text-text-muted">(opcional)</span>
              </label>
              <textarea
                id="description"
                className="input resize-none"
                rows={2}
                placeholder="Detalles adicionales del producto"
                value={form.description}
                onChange={(e) => set('description', e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label" htmlFor="category">
                  Categoría{' '}
                  <span className="font-normal text-text-muted">(opcional)</span>
                </label>
                <select
                  id="category"
                  className="input"
                  value={form.category_id}
                  onChange={(e) => set('category_id', e.target.value)}
                >
                  <option value="">Sin categoría</option>
                  {categoryTree.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label" htmlFor="base_unit">
                  Unidad base <span className="text-danger-500">*</span>
                </label>
                <input
                  id="base_unit"
                  className={`input ${errors.base_unit ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                  type="text"
                  placeholder="ej. unidad, kg, litro"
                  value={form.base_unit}
                  onChange={(e) => set('base_unit', e.target.value)}
                />
                {errors.base_unit && (
                  <p className="mt-1 text-xs text-danger-500">{errors.base_unit}</p>
                )}
              </div>
            </div>
          </div>

          {/* Impuestos */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Impuestos</h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label" htmlFor="tax_rate">
                  Tasa IVA
                </label>
                <select
                  id="tax_rate"
                  className="input"
                  value={form.tax_rate}
                  onChange={(e) => set('tax_rate', e.target.value)}
                >
                  <option value="0.00">0% — Exento</option>
                  <option value="5.00">5%</option>
                  <option value="10.00">10%</option>
                </select>
                {errors.tax_rate && (
                  <p className="mt-1 text-xs text-danger-500">{errors.tax_rate}</p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Toggle
                checked={form.tax_included_in_price}
                onChange={(v) => set('tax_included_in_price', v)}
              />
              <span className="text-sm text-text-secondary">
                Precio de góndola incluye IVA
              </span>
            </div>
          </div>

          {/* Stock */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Stock</h2>

            <div className="flex items-center gap-3">
              <Toggle
                checked={form.track_stock}
                onChange={(v) => set('track_stock', v)}
              />
              <span className="text-sm text-text-secondary">
                Controlar stock de este producto
              </span>
            </div>

            {form.track_stock && (
              <div className="max-w-xs">
                <label className="label" htmlFor="low_stock_threshold">
                  Umbral de stock bajo{' '}
                  <span className="font-normal text-text-muted">(opcional)</span>
                </label>
                <input
                  id="low_stock_threshold"
                  className={`input tabular-nums ${errors.low_stock_threshold ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                  type="number"
                  min="0"
                  step="any"
                  placeholder="ej. 10"
                  value={form.low_stock_threshold}
                  onChange={(e) => set('low_stock_threshold', e.target.value)}
                />
                {errors.low_stock_threshold && (
                  <p className="mt-1 text-xs text-danger-500">{errors.low_stock_threshold}</p>
                )}
              </div>
            )}
          </div>

          {/* Estado */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Estado</h2>
            <div className="flex items-center gap-3">
              <Toggle checked={form.is_active} onChange={(v) => set('is_active', v)} />
              <span className="text-sm text-text-secondary">
                {form.is_active ? 'Producto activo' : 'Producto inactivo'}
              </span>
            </div>
          </div>

          {/* Unidades */}
          <div className="card space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-medium text-text-primary">Unidades</h2>
              <button
                type="button"
                className="btn-secondary flex items-center gap-1.5 text-sm"
                onClick={() =>
                  setUnitModal({
                    mode: 'add',
                    initial: DEFAULT_UNIT_FORM,
                    factorLocked: false,
                  })
                }
              >
                <Plus className="h-4 w-4" />
                Agregar unidad
              </button>
            </div>

            {unitError && (
              <div className="rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
                {unitError}
              </div>
            )}

            {displayUnits.length === 0 ? (
              <p className="text-sm text-text-muted">
                Sin unidades. Agregá al menos una unidad base (factor = 1).
              </p>
            ) : (
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle">
                      <th className="pb-2 text-left text-xs font-medium text-text-secondary">Nombre</th>
                      <th className="pb-2 text-right text-xs font-medium text-text-secondary">Factor</th>
                      <th className="pb-2 text-center text-xs font-medium text-text-secondary">Venta</th>
                      <th className="pb-2 text-center text-xs font-medium text-text-secondary">Compra</th>
                      <th className="pb-2 text-left text-xs font-medium text-text-secondary">Estado</th>
                      <th className="pb-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {displayUnits.map((u) => {
                      const isDeleting = deleteUnitId === u.id
                      const isBase = parseFloat(u.factor_to_base) === 1
                      const canHardDelete = isEdit
                        ? (u as ProductUnitOut).can_hard_delete
                        : true
                      return (
                        <tr
                          key={u.id}
                          className={!u.is_active ? 'opacity-60' : undefined}
                        >
                          <td className="py-2 pr-4 text-text-primary">{u.unit_name}</td>
                          <td className="py-2 pr-4 text-right tabular-nums text-text-secondary">
                            {u.factor_to_base}
                          </td>
                          <td className="py-2 pr-4 text-center">
                            {u.is_default_sale_unit ? (
                              <span className="text-xs font-medium text-success-500">Sí</span>
                            ) : (
                              <span className="text-xs text-text-muted">—</span>
                            )}
                          </td>
                          <td className="py-2 pr-4 text-center">
                            {u.is_default_purchase_unit ? (
                              <span className="text-xs font-medium text-success-500">Sí</span>
                            ) : (
                              <span className="text-xs text-text-muted">—</span>
                            )}
                          </td>
                          <td className="py-2 pr-4">
                            {u.is_active ? (
                              <span className="text-xs font-medium text-success-500">Activa</span>
                            ) : (
                              <span className="rounded-full bg-bg-elevated px-2 py-0.5 text-xs font-medium text-text-muted">
                                Inactiva
                              </span>
                            )}
                          </td>
                          <td className="py-2">
                            {isDeleting ? (
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-text-secondary">¿Eliminar?</span>
                                <button
                                  type="button"
                                  className="btn-danger px-2 py-0.5 text-xs"
                                  disabled={deletingUnit}
                                  onClick={() => handleUnitDelete(u.id)}
                                >
                                  {deletingUnit ? '…' : 'Sí'}
                                </button>
                                <button
                                  type="button"
                                  className="btn-ghost px-2 py-0.5 text-xs"
                                  onClick={() => setDeleteUnitId(null)}
                                >
                                  No
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  className="btn-ghost px-2 py-1"
                                  aria-label={`Editar ${u.unit_name}`}
                                  onClick={() =>
                                    setUnitModal({
                                      mode: 'edit',
                                      editId: u.id,
                                      initial: isEdit
                                        ? unitFormFromSaved(u as ProductUnitOut)
                                        : unitFormFromLocal(u as LocalUnit),
                                      factorLocked: false,
                                    })
                                  }
                                >
                                  <Pencil className="h-4 w-4" />
                                </button>
                                {isEdit && !isBase && (
                                  <Toggle
                                    checked={u.is_active}
                                    onChange={() => handleUnitToggle(u as ProductUnitOut)}
                                    disabled={togglingUnitId === u.id}
                                  />
                                )}
                                {canHardDelete && (
                                  <button
                                    type="button"
                                    className="btn-ghost px-2 py-1 text-danger-500 hover:text-danger-500"
                                    aria-label={`Eliminar ${u.unit_name}`}
                                    onClick={() => {
                                      setUnitError(null)
                                      setDeleteUnitId(u.id)
                                    }}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
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
          </div>

          {/* Precios — edit mode only */}
          {isEdit && (
            <div className="card space-y-4">
              <h2 className="text-base font-medium text-text-primary">Precios vigentes</h2>

              {priceError && (
                <div className="rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
                  {priceError}
                </div>
              )}

              {currencies.length === 0 || savedUnits.length === 0 ? (
                <p className="text-sm text-text-muted">
                  {savedUnits.length === 0
                    ? 'Agregá unidades para poder cargar precios.'
                    : 'No hay monedas activas configuradas.'}
                </p>
              ) : (
                <div className="overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border-subtle">
                        <th className="pb-2 text-left text-xs font-medium text-text-secondary">Unidad</th>
                        <th className="pb-2 text-left text-xs font-medium text-text-secondary">Moneda</th>
                        <th className="pb-2 text-right text-xs font-medium text-text-secondary">Precio vigente</th>
                        <th className="pb-2" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {priceRows.map((row) => (
                        <tr key={`${row.unitId}:${row.currencyCode}`}>
                          <td className="py-2 pr-4 text-text-primary">{row.unitName}</td>
                          <td className="py-2 pr-4 text-text-secondary">{row.currencyCode}</td>
                          <td className="py-2 pr-4 text-right tabular-nums">
                            {row.priceEntry === undefined ? (
                              <span className="text-xs text-text-muted">…</span>
                            ) : row.priceEntry === null ? (
                              <span className="text-text-muted">—</span>
                            ) : (
                              <span className="text-text-primary">
                                {row.currencySymbol}{' '}
                                {formatPrice(row.priceEntry.price, row.decimals)}
                              </span>
                            )}
                          </td>
                          <td className="py-2 text-right">
                            <button
                              type="button"
                              className="btn-ghost px-2 py-1 text-xs"
                              onClick={() =>
                                setPriceModal({
                                  unitId: row.unitId,
                                  unitName: row.unitName,
                                  currencyCode: row.currencyCode,
                                  currencySymbol: row.currencySymbol,
                                })
                              }
                            >
                              Cambiar precio
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Acciones */}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/productos')}
              disabled={saving}
            >
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear producto'}
            </button>
          </div>
        </div>
      </form>

      {/* Modals */}
      {showDelete && (
        <DeleteModal
          name={form.name || form.sku}
          deleting={deleting}
          onConfirm={handleDelete}
          onClose={() => setShowDelete(false)}
        />
      )}

      {unitModal && (
        <UnitModal
          initial={unitModal.initial}
          factorLocked={unitModal.factorLocked}
          saving={savingUnit}
          onSave={handleUnitSave}
          onClose={() => {
            setUnitModal(null)
            setUnitError(null)
          }}
        />
      )}

      {priceModal && (
        <PriceModal
          unitName={priceModal.unitName}
          currencyCode={priceModal.currencyCode}
          currencySymbol={priceModal.currencySymbol}
          saving={savingPrice}
          onSave={handlePriceSave}
          onClose={() => {
            setPriceModal(null)
            setPriceError(null)
          }}
        />
      )}

      {confirmToggle && (
        <ConfirmToggleModal
          message={confirmToggle.message}
          loading={togglingUnitId !== null}
          onConfirm={() => doToggleUnit(confirmToggle.unit)}
          onClose={() => setConfirmToggle(null)}
        />
      )}

      {reactivateModal && (
        <ReactivateModal
          unitName={reactivateModal.unitName}
          reactivating={reactivating}
          onConfirm={handleReactivate}
          onClose={() => setReactivateModal(null)}
        />
      )}
    </div>
  )
}
