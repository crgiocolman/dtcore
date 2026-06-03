import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ClipboardList,
  Loader2,
  Plus,
  Trash2,
  X,
  XCircle,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchWarehouses, type WarehouseOut } from '../../admin/api/warehouses'
import { fetchProduct, searchProducts, type ProductSearchResult } from '../../products/api/products'
import { fetchUnits, type ProductUnitOut } from '../../products/api/units'
import type { UnitType } from '../../admin/api/unit_catalog'
import {
  addAdjustmentItem,
  cancelAdjustment,
  confirmAdjustment,
  createAdjustment,
  deleteAdjustment,
  fetchAdjustment,
  fetchAdjustmentAudit,
  removeAdjustmentItem,
  updateAdjustment,
  type AdjustmentAuditEntry,
  type AdjustmentItemOut,
  type AdjustmentOut,
  type AdjustmentReason,
  type StockDirection,
} from '../api/adjustments'
import { useItemFormShortcuts } from '../../purchases/hooks/useItemFormShortcuts'
import { formatQuantity } from '../../../lib/format'
import { parseApiError as _parseErr } from '../../../lib/parseApiError'

// ---- Helpers ----

function parseApiError(err: unknown): string {
  const parsed = _parseErr(err)
  if (parsed.code === 'insufficient_stock') {
    const name = (parsed.details.product_name as string) ?? 'producto'
    return `Stock insuficiente para "${name}": disponible ${parsed.details.available}, solicitado ${parsed.details.requested}`
  }
  return parsed.message
}

function formatCostPYG(value: string | number | null): string {
  if (value === null || value === undefined || value === '') return '—'
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '—'
  return '₲ ' + new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(n)
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function fmtDate(d: string): string {
  return new Date(d + 'T00:00:00').toLocaleDateString('es-PY')
}

// ---- Constants ----

const REASON_LABELS: Record<AdjustmentReason, string> = {
  inventory_count: 'Conteo de inventario',
  damage: 'Daño / Deterioro',
  loss: 'Pérdida',
  expired: 'Vencimiento',
  correction: 'Corrección',
  other: 'Otro',
}

const DIRECTION_LABELS: Record<StockDirection, string> = {
  in: 'Ingreso',
  out: 'Egreso',
}

const DIRECTION_BADGE: Record<StockDirection, string> = {
  in: 'text-success-500',
  out: 'text-danger-500',
}

// ---- Local types ----

interface HeaderState {
  warehouse_id: string
  adjustment_date: string
  reason: AdjustmentReason | ''
  notes: string
}

interface PendingItem {
  localId: string
  product_id: string
  product_unit_id: string
  product_name: string
  unit_name: string
  unit_type: UnitType
  quantity: string
  direction: StockDirection
  unit_cost_base: string
  notes: string
}

// ---- Modals ----

function ConfirmAdjustmentModal({
  pendingItems,
  savedItems,
  productNames,
  unitNames,
  unitTypes,
  isNew,
  confirming,
  error,
  onConfirm,
  onClose,
}: {
  pendingItems: PendingItem[]
  savedItems: AdjustmentItemOut[]
  productNames: Map<string, string>
  unitNames: Map<string, string>
  unitTypes: Map<string, UnitType>
  isNew: boolean
  confirming: boolean
  error?: string | null
  onConfirm: () => void
  onClose: () => void
}) {
  const displayItems = isNew
    ? pendingItems.map((i) => ({
        name: i.product_name,
        unit: i.unit_name,
        unitType: i.unit_type,
        qty: i.quantity,
        direction: i.direction as StockDirection,
      }))
    : savedItems.map((i) => ({
        name: productNames.get(i.product_id) ?? i.product_id.slice(0, 8),
        unit: unitNames.get(i.product_unit_id) ?? '—',
        unitType: (unitTypes.get(i.product_unit_id) ?? 'count') as UnitType,
        qty: i.quantity,
        direction: i.direction,
      }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-lg space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Confirmar ajuste</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">
          El stock se actualizará con los siguientes ítems. Esta acción no se puede deshacer.
        </p>
        <div className="max-h-48 overflow-auto rounded border border-border-subtle">
          <table className="w-full text-sm">
            <thead className="bg-bg-elevated">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Producto</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Unidad</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Dirección</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Cantidad</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {displayItems.map((item, idx) => (
                <tr key={idx}>
                  <td className="px-3 py-2 text-text-primary">{item.name}</td>
                  <td className="px-3 py-2 text-text-secondary">{item.unit}</td>
                  <td className={`px-3 py-2 text-xs font-medium ${DIRECTION_BADGE[item.direction]}`}>
                    {DIRECTION_LABELS[item.direction]}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-right text-text-primary">
                    {formatQuantity(item.qty, item.unitType)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {error && (
          <div className="flex items-start gap-2 rounded border border-danger-500/30 bg-danger-500/10 px-3 py-2 text-sm text-danger-500">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={confirming}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary flex items-center gap-1.5"
            onClick={onConfirm}
            disabled={confirming}
          >
            {confirming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {confirming ? 'Confirmando…' : 'Confirmar ajuste'}
          </button>
        </div>
      </div>
    </div>
  )
}

function CancelAdjustmentModal({
  reason,
  cancelling,
  onReasonChange,
  onConfirm,
  onClose,
}: {
  reason: string
  cancelling: boolean
  onReasonChange: (v: string) => void
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Cancelar ajuste</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">
          Se generarán movimientos compensatorios en el stock. Esta acción no se puede deshacer.
        </p>
        <div>
          <label className="label">
            Motivo de cancelación <span className="text-danger-500">*</span>
          </label>
          <textarea
            className="input resize-none"
            rows={3}
            placeholder="Indicar el motivo…"
            value={reason}
            onChange={(e) => onReasonChange(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={cancelling}>
            Volver
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={onConfirm}
            disabled={cancelling || !reason.trim()}
          >
            {cancelling ? 'Cancelando…' : 'Cancelar ajuste'}
          </button>
        </div>
      </div>
    </div>
  )
}

function DeleteDraftModal({
  deleting,
  onConfirm,
  onClose,
}: {
  deleting: boolean
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Eliminar borrador</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">
          Los datos de este borrador no se pueden recuperar.
        </p>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={deleting}>
            Volver
          </button>
          <button type="button" className="btn-danger" onClick={onConfirm} disabled={deleting}>
            {deleting ? 'Eliminando…' : 'Eliminar borrador'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Main component ----

const DEFAULT_HEADER: HeaderState = {
  warehouse_id: '',
  adjustment_date: today(),
  reason: '',
  notes: '',
}

export function AdjustmentForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isNew = !id

  // Adjustment + items
  const [adjustment, setAdjustment] = useState<AdjustmentOut | null>(null)
  const [items, setItems] = useState<AdjustmentItemOut[]>([])
  const [pendingItems, setPendingItems] = useState<PendingItem[]>([])
  const [productNames, setProductNames] = useState<Map<string, string>>(new Map())
  const [unitNames, setUnitNames] = useState<Map<string, string>>(new Map())
  const [unitTypes, setUnitTypes] = useState<Map<string, UnitType>>(new Map())

  // Reference data
  const [warehouses, setWarehouses] = useState<WarehouseOut[]>([])

  // Header form
  const [header, setHeader] = useState<HeaderState>(DEFAULT_HEADER)
  const [headerErrors, setHeaderErrors] = useState<Partial<Record<keyof HeaderState, string>>>({})
  const [headerDirty, setHeaderDirty] = useState(false)

  // Add-item row
  const [productSearch, setProductSearch] = useState('')
  const [productResults, setProductResults] = useState<ProductSearchResult[]>([])
  const [showProductDrop, setShowProductDrop] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState<ProductSearchResult | null>(null)
  const [productUnits, setProductUnits] = useState<ProductUnitOut[]>([])
  const [newItemUnit, setNewItemUnit] = useState('')
  const [newItemDirection, setNewItemDirection] = useState<StockDirection>('in')
  const [newItemQty, setNewItemQty] = useState('')
  const [newItemCost, setNewItemCost] = useState('')
  const [newItemNotes, setNewItemNotes] = useState('')
  const [addingItem, setAddingItem] = useState(false)
  const [newItemError, setNewItemError] = useState<string | null>(null)

  // Audit
  const [auditEntries, setAuditEntries] = useState<AdjustmentAuditEntry[]>([])

  // UI
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  // Modals
  const [showConfirm, setShowConfirm] = useState(false)
  const [confirmError, setConfirmError] = useState<string | null>(null)
  const [showCancel, setShowCancel] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const searchRef = useRef<ReturnType<typeof setTimeout>>(undefined)
  const productInputRef = useRef<HTMLInputElement>(null)
  const productJustSelected = useRef(false)

  // Load warehouses on mount
  useEffect(() => {
    fetchWarehouses()
      .then((ws) => {
        setWarehouses(ws)
        if (isNew) {
          const def = ws.find((w) => w.is_default) ?? ws[0]
          if (def) setHeader((h) => ({ ...h, warehouse_id: def.id }))
        }
      })
      .catch(() => {})
  }, [isNew])

  // Load existing adjustment
  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchAdjustment(id)
      .then(async (adj) => {
        setAdjustment(adj)
        setItems(adj.items)
        setHeader({
          warehouse_id: adj.warehouse_id,
          adjustment_date: adj.adjustment_date,
          reason: adj.reason,
          notes: adj.notes ?? '',
        })
        // Hydrate product + unit names
        const uniquePids = [...new Set(adj.items.map((i) => i.product_id))]
        const pNames = new Map<string, string>()
        const uNames = new Map<string, string>()
        const uTypes = new Map<string, UnitType>()
        await Promise.all(
          uniquePids.map(async (pid) => {
            const [product, units] = await Promise.all([fetchProduct(pid), fetchUnits(pid, false)])
            pNames.set(pid, product.name)
            units.forEach((u) => {
              uNames.set(u.id, u.unit_catalog?.name ?? u.unit_catalog_id)
              uTypes.set(u.id, (u.unit_catalog?.unit_type ?? 'count') as UnitType)
            })
          }),
        )
        setProductNames(pNames)
        setUnitNames(uNames)
        setUnitTypes(uTypes)
        fetchAdjustmentAudit(id).then(setAuditEntries).catch(() => {})
      })
      .catch((err) => setApiError(parseApiError(err)))
      .finally(() => setLoading(false))
  }, [id])

  // Debounced product search
  useEffect(() => {
    if (productSearch.length < 2 || productJustSelected.current) {
      setProductResults([])
      setShowProductDrop(false)
      return
    }
    clearTimeout(searchRef.current)
    searchRef.current = setTimeout(() => {
      searchProducts(productSearch)
        .then((r) => {
          setProductResults(r.slice(0, 8))
          setShowProductDrop(r.length > 0)
        })
        .catch(() => {})
    }, 300)
    return () => clearTimeout(searchRef.current)
  }, [productSearch])

  // ---- Handlers ----

  const setHeaderField = <K extends keyof HeaderState>(key: K, value: HeaderState[K]) => {
    setHeader((h) => ({ ...h, [key]: value }))
    setHeaderErrors((e) => ({ ...e, [key]: undefined }))
    if (id) setHeaderDirty(true)
  }

  const validateHeader = (): boolean => {
    const errs: Partial<Record<keyof HeaderState, string>> = {}
    if (!header.warehouse_id) errs.warehouse_id = 'Campo requerido'
    if (!header.adjustment_date) errs.adjustment_date = 'Campo requerido'
    if (!header.reason) errs.reason = 'Campo requerido'
    setHeaderErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSaveHeader = async () => {
    if (!validateHeader() || !id) return
    setSaving(true)
    setApiError(null)
    try {
      const updated = await updateAdjustment(id, {
        warehouse_id: header.warehouse_id,
        adjustment_date: header.adjustment_date,
        reason: header.reason as AdjustmentReason,
        notes: header.notes || null,
      })
      setAdjustment(updated)
      setHeaderDirty(false)
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setSaving(false)
    }
  }

  const handleSelectProduct = async (result: ProductSearchResult) => {
    productJustSelected.current = true
    setSelectedProduct(result)
    setProductSearch(result.name)
    setShowProductDrop(false)
    setProductResults([])
    const units = await fetchUnits(result.id, true).catch(() => [])
    setProductUnits(units)
    const def = units.find((u) => u.is_default_purchase_unit) ?? units[0]
    setNewItemUnit(def?.id ?? '')
  }

  const clearItemForm = () => {
    setProductSearch('')
    setSelectedProduct(null)
    setProductUnits([])
    setNewItemUnit('')
    setNewItemQty('')
    setNewItemCost('')
    setNewItemNotes('')
    setNewItemError(null)
    productInputRef.current?.focus()
  }

  const handleAddItem = async () => {
    if (!selectedProduct || !newItemUnit) {
      setNewItemError('Seleccioná un producto y unidad')
      return
    }
    const qty = parseFloat(newItemQty)
    if (isNaN(qty) || qty <= 0) {
      setNewItemError('Cantidad inválida')
      return
    }
    if (newItemDirection === 'in') {
      const cost = parseFloat(newItemCost)
      if (isNaN(cost) || cost < 0) {
        setNewItemError('Costo inválido')
        return
      }
    }
    setNewItemError(null)
    setAddingItem(true)

    const unit = productUnits.find((u) => u.id === newItemUnit)
    const unitType = (unit?.unit_catalog?.unit_type ?? 'count') as UnitType

    try {
      if (isNew) {
        setPendingItems((prev) => [
          ...prev,
          {
            localId: crypto.randomUUID(),
            product_id: selectedProduct.id,
            product_unit_id: newItemUnit,
            product_name: selectedProduct.name,
            unit_name: unit?.unit_catalog?.name ?? newItemUnit,
            unit_type: unitType,
            quantity: newItemQty,
            direction: newItemDirection,
            unit_cost_base: newItemCost,
            notes: newItemNotes,
          },
        ])
      } else {
        await addAdjustmentItem(id!, {
          id: crypto.randomUUID(),
          product_id: selectedProduct.id,
          product_unit_id: newItemUnit,
          quantity: qty,
          direction: newItemDirection,
          unit_cost_base:
            newItemDirection === 'in' ? (parseFloat(newItemCost) || null) : null,
          notes: newItemNotes || null,
        })
        const updated = await fetchAdjustment(id!)
        setAdjustment(updated)
        setItems(updated.items)
        if (!productNames.has(selectedProduct.id)) {
          setProductNames((m) => new Map(m).set(selectedProduct.id, selectedProduct.name))
        }
        if (unit) {
          if (!unitNames.has(unit.id)) {
            setUnitNames((m) =>
              new Map(m).set(unit.id, unit.unit_catalog?.name ?? unit.unit_catalog_id),
            )
          }
          if (!unitTypes.has(unit.id)) {
            setUnitTypes((m) => new Map(m).set(unit.id, unitType))
          }
        }
      }
      clearItemForm()
    } catch (err) {
      setNewItemError(parseApiError(err))
    } finally {
      setAddingItem(false)
    }
  }

  const handleRemoveItem = async (itemId: string) => {
    if (isNew) {
      setPendingItems((p) => p.filter((i) => i.localId !== itemId))
      return
    }
    setApiError(null)
    try {
      await removeAdjustmentItem(id!, itemId)
      const updated = await fetchAdjustment(id!)
      setAdjustment(updated)
      setItems(updated.items)
    } catch (err) {
      setApiError(parseApiError(err))
    }
  }

  const saveNewDraft = async (): Promise<string> => {
    const created = await createAdjustment({
      id: crypto.randomUUID(),
      warehouse_id: header.warehouse_id,
      adjustment_date: header.adjustment_date,
      reason: header.reason as AdjustmentReason,
      notes: header.notes || null,
    })
    for (const item of pendingItems) {
      await addAdjustmentItem(created.id, {
        id: crypto.randomUUID(),
        product_id: item.product_id,
        product_unit_id: item.product_unit_id,
        quantity: parseFloat(item.quantity),
        direction: item.direction,
        unit_cost_base:
          item.direction === 'in' ? (parseFloat(item.unit_cost_base) || null) : null,
        notes: item.notes || null,
      })
    }
    return created.id
  }

  const handleSaveDraft = async () => {
    if (!validateHeader()) return
    setSaving(true)
    setApiError(null)
    try {
      const newId = await saveNewDraft()
      navigate(`/ajustes/${newId}`)
    } catch (err) {
      setApiError(parseApiError(err))
      setSaving(false)
    }
  }

  const handleConfirm = async () => {
    setConfirming(true)
    setConfirmError(null)
    try {
      if (isNew) {
        const newId = await saveNewDraft()
        await confirmAdjustment(newId)
        setShowConfirm(false)
        navigate(`/ajustes/${newId}`)
      } else {
        const confirmed = await confirmAdjustment(id!)
        setShowConfirm(false)
        setAdjustment(confirmed)
        setItems(confirmed.items)
        fetchAdjustmentAudit(id!).then(setAuditEntries).catch(() => {})
      }
    } catch (err) {
      setConfirmError(parseApiError(err))
    } finally {
      setConfirming(false)
    }
  }

  const handleCancel = async () => {
    if (!cancelReason.trim()) return
    setCancelling(true)
    setApiError(null)
    try {
      const cancelled = await cancelAdjustment(id!, cancelReason)
      setAdjustment(cancelled)
      setShowCancel(false)
      fetchAdjustmentAudit(id!).then(setAuditEntries).catch(() => {})
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setCancelling(false)
    }
  }

  const handleDeleteDraft = async () => {
    setDeleting(true)
    try {
      await deleteAdjustment(id!)
      navigate('/ajustes')
    } catch (err) {
      setApiError(parseApiError(err))
      setDeleting(false)
    }
  }

  const { onKeyDown: onItemInputKeyDown } = useItemFormShortcuts(handleAddItem, clearItemForm)

  // ---- Derived values ----

  const isDraft = isNew || adjustment?.status === 'draft'
  const isConfirmed = adjustment?.status === 'confirmed'
  const status = adjustment?.status

  const canConfirm = Boolean(
    header.warehouse_id &&
      header.adjustment_date &&
      header.reason &&
      (isNew ? pendingItems.length > 0 : items.length > 0 && isDraft),
  )

  const warehouseName =
    warehouses.find((w) => w.id === (adjustment?.warehouse_id ?? header.warehouse_id))?.name ?? '—'

  const STATUS_LABEL: Record<string, string> = {
    draft: 'Borrador',
    confirmed: 'Confirmado',
    cancelled: 'Cancelado',
  }
  const STATUS_COLOR: Record<string, string> = {
    draft: 'text-text-secondary',
    confirmed: 'text-success-500',
    cancelled: 'text-danger-500',
  }

  // ---- Render ----

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-text-muted">Cargando…</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Page header */}
      <div className="mb-6 flex flex-shrink-0 items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={() => navigate('/ajustes')}
            className="mb-2 flex items-center gap-1 text-sm text-text-muted transition-colors hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver a ajustes
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-text-primary">
              {isNew ? 'Nuevo ajuste' : adjustment?.adjustment_number ?? 'Borrador'}
            </h1>
            {status && (
              <span className={`text-sm font-medium ${STATUS_COLOR[status]}`}>
                {STATUS_LABEL[status]}
              </span>
            )}
          </div>
        </div>
        {!isNew && isDraft && (
          <button
            type="button"
            className="btn-danger flex flex-shrink-0 items-center gap-1.5"
            onClick={() => setShowDeleteModal(true)}
          >
            <Trash2 className="h-4 w-4" />
            Eliminar borrador
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl space-y-6 pb-6">
          {apiError && (
            <div className="flex items-start gap-2 rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              {apiError}
            </div>
          )}

          {/* Header card */}
          <div className="card space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-medium text-text-primary">Datos del ajuste</h2>
              {!isNew && isDraft && headerDirty && (
                <button
                  type="button"
                  className="btn-secondary flex items-center gap-1.5 text-sm"
                  onClick={handleSaveHeader}
                  disabled={saving}
                >
                  {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                  {saving ? 'Guardando…' : 'Guardar cambios'}
                </button>
              )}
            </div>

            {isDraft ? (
              <div className="grid grid-cols-2 gap-4">
                {/* Depósito */}
                <div>
                  <label className="label">
                    Depósito <span className="text-danger-500">*</span>
                  </label>
                  <select
                    className={`input ${headerErrors.warehouse_id ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                    value={header.warehouse_id}
                    onChange={(e) => setHeaderField('warehouse_id', e.target.value)}
                  >
                    <option value="">Seleccionar depósito…</option>
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name}
                      </option>
                    ))}
                  </select>
                  {headerErrors.warehouse_id && (
                    <p className="mt-1 text-xs text-danger-500">{headerErrors.warehouse_id}</p>
                  )}
                </div>

                {/* Fecha */}
                <div>
                  <label className="label">
                    Fecha <span className="text-danger-500">*</span>
                  </label>
                  <input
                    className={`input ${headerErrors.adjustment_date ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                    type="date"
                    value={header.adjustment_date}
                    onChange={(e) => setHeaderField('adjustment_date', e.target.value)}
                  />
                  {headerErrors.adjustment_date && (
                    <p className="mt-1 text-xs text-danger-500">{headerErrors.adjustment_date}</p>
                  )}
                </div>

                {/* Motivo */}
                <div>
                  <label className="label">
                    Motivo <span className="text-danger-500">*</span>
                  </label>
                  <select
                    className={`input ${headerErrors.reason ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                    value={header.reason}
                    onChange={(e) => setHeaderField('reason', e.target.value as AdjustmentReason)}
                  >
                    <option value="">Seleccionar motivo…</option>
                    {(Object.keys(REASON_LABELS) as AdjustmentReason[]).map((key) => (
                      <option key={key} value={key}>
                        {REASON_LABELS[key]}
                      </option>
                    ))}
                  </select>
                  {headerErrors.reason && (
                    <p className="mt-1 text-xs text-danger-500">{headerErrors.reason}</p>
                  )}
                </div>

                {/* Notas */}
                <div className="col-span-2">
                  <label className="label">
                    Notas <span className="font-normal text-text-muted">(opcional)</span>
                  </label>
                  <textarea
                    className="input resize-none"
                    rows={2}
                    placeholder="Observaciones, referencia, etc."
                    value={header.notes}
                    onChange={(e) => setHeaderField('notes', e.target.value)}
                  />
                </div>
              </div>
            ) : (
              /* Read-only header */
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                <div>
                  <dt className="label">Depósito</dt>
                  <dd className="text-text-primary">{warehouseName}</dd>
                </div>
                <div>
                  <dt className="label">Fecha</dt>
                  <dd className="text-text-primary">
                    {adjustment ? fmtDate(adjustment.adjustment_date) : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="label">Motivo</dt>
                  <dd className="text-text-primary">
                    {adjustment ? REASON_LABELS[adjustment.reason] : '—'}
                  </dd>
                </div>
                {adjustment?.notes && (
                  <div className="col-span-2">
                    <dt className="label">Notas</dt>
                    <dd className="text-text-primary">{adjustment.notes}</dd>
                  </div>
                )}
              </dl>
            )}
          </div>

          {/* Items card */}
          <div className="card space-y-4 p-0">
            <div className="px-4 pt-4">
              <h2 className="text-base font-medium text-text-primary">Ítems</h2>
            </div>

            {(isNew ? pendingItems.length : items.length) > 0 ? (
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle">
                      <th className="px-4 pb-2 pt-0 text-left text-xs font-medium text-text-secondary">Producto</th>
                      <th className="px-4 pb-2 pt-0 text-left text-xs font-medium text-text-secondary">Unidad</th>
                      <th className="px-4 pb-2 pt-0 text-left text-xs font-medium text-text-secondary">Dirección</th>
                      <th className="px-4 pb-2 pt-0 text-right text-xs font-medium text-text-secondary">Cantidad</th>
                      <th className="px-4 pb-2 pt-0 text-right text-xs font-medium text-text-secondary">Costo unit. (₲)</th>
                      {isDraft && <th className="px-4 pb-2 pt-0" />}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {isNew
                      ? pendingItems.map((item) => (
                          <tr key={item.localId}>
                            <td className="px-4 py-3 text-text-primary">
                              {item.product_name}
                              {item.notes && (
                                <p className="text-xs text-text-muted">{item.notes}</p>
                              )}
                            </td>
                            <td className="px-4 py-3 text-text-secondary">{item.unit_name}</td>
                            <td className={`px-4 py-3 text-xs font-medium ${DIRECTION_BADGE[item.direction]}`}>
                              {DIRECTION_LABELS[item.direction]}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                              {formatQuantity(item.quantity, item.unit_type)}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-secondary">
                              {item.direction === 'in'
                                ? formatCostPYG(item.unit_cost_base)
                                : <span className="text-text-muted">—</span>}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button
                                type="button"
                                className="btn-ghost px-2 py-1 text-danger-500 hover:text-danger-500"
                                onClick={() => handleRemoveItem(item.localId)}
                                aria-label="Eliminar ítem"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </td>
                          </tr>
                        ))
                      : items.map((item) => (
                          <tr key={item.id}>
                            <td className="px-4 py-3 text-text-primary">
                              {productNames.get(item.product_id) ??
                                item.product_id.slice(0, 8) + '…'}
                              {item.notes && (
                                <p className="text-xs text-text-muted">{item.notes}</p>
                              )}
                            </td>
                            <td className="px-4 py-3 text-text-secondary">
                              {unitNames.get(item.product_unit_id) ?? '—'}
                            </td>
                            <td className={`px-4 py-3 text-xs font-medium ${DIRECTION_BADGE[item.direction]}`}>
                              {DIRECTION_LABELS[item.direction]}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                              {formatQuantity(
                                item.quantity,
                                unitTypes.get(item.product_unit_id) ?? 'count',
                              )}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-secondary">
                              {item.direction === 'in'
                                ? formatCostPYG(item.unit_cost_base)
                                : <span className="text-text-muted">—</span>}
                            </td>
                            {isDraft && (
                              <td className="px-4 py-3 text-right">
                                <button
                                  type="button"
                                  className="btn-ghost px-2 py-1 text-danger-500 hover:text-danger-500"
                                  onClick={() => handleRemoveItem(item.id)}
                                  aria-label="Eliminar ítem"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </td>
                            )}
                          </tr>
                        ))}
                  </tbody>
                </table>
              </div>
            ) : (
              !isDraft && <p className="px-4 pb-4 text-sm text-text-muted">Sin ítems.</p>
            )}

            {/* Add item row (draft only) */}
            {isDraft && (
              <div className="border-t border-border-subtle px-4 pb-4 pt-3">
                <p className="mb-3 text-xs font-medium text-text-secondary">Agregar ítem</p>
                {newItemError && (
                  <p className="mb-2 text-xs text-danger-500">{newItemError}</p>
                )}
                <div className="grid grid-cols-12 gap-2">
                  {/* Product search */}
                  <div className="relative col-span-4">
                    <input
                      ref={productInputRef}
                      className="input text-sm"
                      type="text"
                      placeholder="Buscar producto (SKU, nombre)…"
                      value={productSearch}
                      onChange={(e) => {
                        productJustSelected.current = false
                        setProductSearch(e.target.value)
                        setSelectedProduct(null)
                      }}
                      onBlur={() => setTimeout(() => setShowProductDrop(false), 150)}
                      onFocus={() => productResults.length > 0 && setShowProductDrop(true)}
                      onKeyDown={onItemInputKeyDown}
                    />
                    {showProductDrop && productResults.length > 0 && (
                      <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-auto rounded border border-border bg-bg-elevated shadow-lg">
                        {productResults.map((r) => (
                          <button
                            key={r.id}
                            type="button"
                            className="w-full px-3 py-2 text-left text-sm hover:bg-bg-base"
                            onMouseDown={(e) => {
                              e.preventDefault()
                              handleSelectProduct(r)
                            }}
                          >
                            <span className="text-text-primary">{r.name}</span>
                            <span className="ml-2 text-xs text-text-muted">{r.sku}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Unit select */}
                  <div className="col-span-2">
                    <select
                      className="input text-sm"
                      value={newItemUnit}
                      onChange={(e) => setNewItemUnit(e.target.value)}
                      disabled={productUnits.length === 0}
                    >
                      <option value="">Unidad…</option>
                      {productUnits.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.unit_catalog?.name ?? u.unit_catalog_id}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Direction select */}
                  <div className="col-span-2">
                    <select
                      className="input text-sm"
                      value={newItemDirection}
                      onChange={(e) => {
                        setNewItemDirection(e.target.value as StockDirection)
                        if (e.target.value === 'out') setNewItemCost('')
                      }}
                    >
                      <option value="in">Ingreso (+)</option>
                      <option value="out">Egreso (−)</option>
                    </select>
                  </div>

                  {/* Quantity */}
                  <div className="col-span-2">
                    <input
                      className="input tabular-nums text-sm"
                      type="number"
                      min="0.0001"
                      step="any"
                      placeholder="Cantidad"
                      value={newItemQty}
                      onChange={(e) => setNewItemQty(e.target.value)}
                      onKeyDown={onItemInputKeyDown}
                    />
                  </div>

                  {/* Cost (only for direction=in) */}
                  <div className="col-span-2">
                    <input
                      className="input tabular-nums text-sm disabled:opacity-40"
                      type="number"
                      min="0"
                      step="any"
                      placeholder="Costo (₲)"
                      value={newItemCost}
                      onChange={(e) => setNewItemCost(e.target.value)}
                      onKeyDown={onItemInputKeyDown}
                      disabled={newItemDirection === 'out'}
                    />
                  </div>
                </div>

                {/* Notes for item */}
                <div className="mt-2">
                  <input
                    className="input text-sm"
                    type="text"
                    placeholder="Nota sobre este ítem (opcional)"
                    value={newItemNotes}
                    onChange={(e) => setNewItemNotes(e.target.value)}
                    onKeyDown={onItemInputKeyDown}
                  />
                </div>

                <p className="mt-1 text-xs text-text-muted">
                  Enter para agregar · Esc para limpiar
                  {newItemDirection === 'out' && (
                    <> · Egreso no requiere costo</>
                  )}
                </p>

                <button
                  type="button"
                  className="btn-secondary mt-3 flex items-center gap-1.5 text-sm"
                  onClick={handleAddItem}
                  disabled={
                    addingItem ||
                    !selectedProduct ||
                    !newItemUnit ||
                    !newItemQty ||
                    (newItemDirection === 'in' && !newItemCost)
                  }
                >
                  {addingItem ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  {addingItem ? 'Agregando…' : 'Agregar ítem'}
                </button>
              </div>
            )}
          </div>

          {/* Audit log */}
          {!isNew && auditEntries.length > 0 && (
            <div className="card space-y-3">
              <h2 className="text-base font-medium text-text-primary">Historial</h2>
              <ol className="space-y-3">
                {auditEntries.map((entry) => {
                  const isCreate = entry.action === 'create'
                  const isConfirmEntry = entry.action === 'confirm'
                  return (
                    <li key={entry.id} className="flex items-start gap-3">
                      <div className="mt-0.5 flex-shrink-0">
                        {isCreate && <ClipboardList className="h-4 w-4 text-text-muted" />}
                        {isConfirmEntry && <CheckCircle2 className="h-4 w-4 text-success-500" />}
                        {entry.action === 'cancel' && <XCircle className="h-4 w-4 text-danger-500" />}
                      </div>
                      <div>
                        <p className="text-sm text-text-primary">
                          {isCreate ? 'Creado' : isConfirmEntry ? 'Confirmado' : 'Cancelado'}
                          {' '}
                          <span className="text-text-secondary">por {entry.user_name}</span>
                        </p>
                        <p className="text-xs text-text-muted">
                          {new Date(entry.created_at).toLocaleString('es-PY')}
                        </p>
                        {entry.changes?.reason && (
                          <p className="mt-0.5 text-xs text-text-secondary">
                            Motivo: {String(entry.changes.reason)}
                          </p>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ol>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between gap-3">
            <button type="button" className="btn-secondary" onClick={() => navigate('/ajustes')}>
              {isDraft ? 'Cancelar' : 'Volver'}
            </button>
            <div className="flex gap-2">
              {isConfirmed && (
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => setShowCancel(true)}
                >
                  Cancelar ajuste
                </button>
              )}
              {isDraft && (
                <>
                  {isNew && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleSaveDraft}
                      disabled={saving || !header.warehouse_id || !header.reason}
                    >
                      {saving ? 'Guardando…' : 'Guardar como borrador'}
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={!canConfirm || confirming}
                    onClick={() => {
                      setConfirmError(null)
                      if (isNew && !validateHeader()) return
                      setShowConfirm(true)
                    }}
                  >
                    Confirmar ajuste
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showConfirm && (
        <ConfirmAdjustmentModal
          pendingItems={pendingItems}
          savedItems={items}
          productNames={productNames}
          unitNames={unitNames}
          unitTypes={unitTypes}
          isNew={isNew}
          confirming={confirming}
          error={confirmError}
          onConfirm={handleConfirm}
          onClose={() => {
            if (!confirming) {
              setShowConfirm(false)
              setConfirmError(null)
            }
          }}
        />
      )}
      {showCancel && (
        <CancelAdjustmentModal
          reason={cancelReason}
          cancelling={cancelling}
          onReasonChange={setCancelReason}
          onConfirm={handleCancel}
          onClose={() => setShowCancel(false)}
        />
      )}
      {showDeleteModal && (
        <DeleteDraftModal
          deleting={deleting}
          onConfirm={handleDeleteDraft}
          onClose={() => setShowDeleteModal(false)}
        />
      )}
    </div>
  )
}
