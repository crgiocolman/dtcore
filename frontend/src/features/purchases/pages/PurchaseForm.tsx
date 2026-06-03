import { AlertCircle, ArrowLeft, Check, CheckCircle2, ClipboardList, Loader2, Plus, Trash2, X, XCircle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { UnitType } from '../../admin/api/unit_catalog'
import { fetchCurrencies, fetchExchangeRates, type CurrencyOut } from '../../admin/api/currencies'
import { fetchWarehouses, type WarehouseOut } from '../../admin/api/warehouses'
import { fetchContacts, type ContactOut } from '../../contacts/api/contacts'
import { fetchProduct, searchProducts, type ProductSearchResult } from '../../products/api/products'
import { fetchUnits, type ProductUnitOut } from '../../products/api/units'
import {
  addPurchaseItem,
  cancelPurchase,
  confirmPurchase,
  createPurchase,
  deletePurchase,
  fetchPurchase,
  fetchPurchaseAudit,
  removePurchaseItem,
  updatePurchase,
  type PurchaseAuditEntry,
  type PurchaseItemOut,
  type PurchaseOut,
} from '../api/purchases'
import { useItemFormShortcuts } from '../hooks/useItemFormShortcuts'
import { formatExchangeRate, formatQuantity } from '../../../lib/format'
import { parseApiError as _parseErr } from '../../../lib/parseApiError'

function parseApiError(err: unknown): string {
  return _parseErr(err).message
}

function formatAmt(value: string | number, code: string): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '—'
  if (code === 'PYG') return '₲ ' + new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(n)
  return code + ' ' + new Intl.NumberFormat('es-PY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function fmtDate(d: string): string {
  return new Date(d + 'T00:00:00').toLocaleDateString('es-PY')
}

// ---- Local types ----

interface HeaderState {
  supplier_id: string
  supplier_document_number: string
  purchase_date: string
  warehouse_id: string
  currency_code: string
  exchange_rate: string
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
  unit_cost: string
  tax_rate: string
  tax_included: boolean
}

function computePendingTotals(items: PendingItem[], exchangeRate: number) {
  let subtotal = 0, taxTotal = 0, total = 0
  for (const item of items) {
    const qty = parseFloat(item.quantity) || 0
    const cost = parseFloat(item.unit_cost) || 0
    const rate = parseFloat(item.tax_rate) || 0
    if (item.tax_included) {
      const t = qty * cost
      const base = t / (1 + rate / 100)
      subtotal += base; taxTotal += t - base; total += t
    } else {
      const base = qty * cost
      const tax = base * rate / 100
      subtotal += base; taxTotal += tax; total += base + tax
    }
  }
  return { subtotal, taxTotal, total, totalBase: total * exchangeRate }
}

// ---- Modals ----

function ConfirmPurchaseModal({
  items,
  pendingItems,
  purchaseItems,
  productNames,
  unitNames,
  unitTypes,
  currency,
  confirming,
  error,
  onConfirm,
  onClose,
}: {
  items: 'pending' | 'saved'
  pendingItems: PendingItem[]
  purchaseItems: PurchaseItemOut[]
  productNames: Map<string, string>
  unitNames: Map<string, string>
  unitTypes: Map<string, UnitType>
  currency: string
  confirming: boolean
  error?: string | null
  onConfirm: () => void
  onClose: () => void
}) {
  const displayItems =
    items === 'pending'
      ? pendingItems.map(i => ({
          name: i.product_name,
          unit: i.unit_name,
          unitType: i.unit_type,
          qty: i.quantity,
          cost: i.unit_cost,
          total: String(
            (parseFloat(i.quantity) || 0) * (parseFloat(i.unit_cost) || 0),
          ),
        }))
      : purchaseItems.map(i => ({
          name: productNames.get(i.product_id) ?? i.product_id.slice(0, 8),
          unit: unitNames.get(i.product_unit_id) ?? '—',
          unitType: unitTypes.get(i.product_unit_id) ?? ('count' as UnitType),
          qty: i.quantity,
          cost: i.unit_cost,
          total: i.total,
        }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-lg space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Confirmar compra</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1"><X className="h-5 w-5" /></button>
        </div>
        <p className="text-sm text-text-secondary">
          Al confirmar, el stock se actualizará con los siguientes ítems:
        </p>
        <div className="max-h-48 overflow-auto rounded border border-border-subtle">
          <table className="w-full text-sm">
            <thead className="bg-bg-elevated">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Producto</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary">Unidad</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Cant.</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {displayItems.map((item, idx) => (
                <tr key={idx}>
                  <td className="px-3 py-2 text-text-primary">{item.name}</td>
                  <td className="px-3 py-2 text-text-secondary">{item.unit}</td>
                  <td className="px-3 py-2 tabular-nums text-right text-text-primary">
                    {formatQuantity(item.qty, item.unitType)}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-right text-text-primary">
                    {formatAmt(item.total, currency)}
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
          <button type="button" className="btn-secondary" onClick={onClose} disabled={confirming}>Cancelar</button>
          <button type="button" className="btn-primary flex items-center gap-1.5" onClick={onConfirm} disabled={confirming}>
            {confirming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {confirming ? 'Confirmando…' : 'Confirmar compra'}
          </button>
        </div>
      </div>
    </div>
  )
}

function CancelPurchaseModal({
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
      <div className="card w-full max-w-sm space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Cancelar compra</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1"><X className="h-5 w-5" /></button>
        </div>
        <p className="text-sm text-text-secondary">
          Se generarán movimientos compensatorios en el stock. Esta acción no se puede deshacer.
        </p>
        <div>
          <label className="label">Motivo de cancelación <span className="text-danger-500">*</span></label>
          <textarea
            className="input resize-none"
            rows={3}
            placeholder="Indicar el motivo…"
            value={reason}
            onChange={e => onReasonChange(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={cancelling}>Volver</button>
          <button
            type="button"
            className="btn-danger"
            onClick={onConfirm}
            disabled={cancelling || !reason.trim()}
          >
            {cancelling ? 'Cancelando…' : 'Cancelar compra'}
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
      <div className="card w-full max-w-sm space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Eliminar borrador</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1"><X className="h-5 w-5" /></button>
        </div>
        <p className="text-sm text-text-secondary">
          Los datos de este borrador no se pueden recuperar.
        </p>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={deleting}>Volver</button>
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
  supplier_id: '',
  supplier_document_number: '',
  purchase_date: today(),
  warehouse_id: '',
  currency_code: 'PYG',
  exchange_rate: '1',
  notes: '',
}

export function PurchaseForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isNew = !id

  // Purchase + items
  const [purchase, setPurchase] = useState<PurchaseOut | null>(null)
  const [items, setItems] = useState<PurchaseItemOut[]>([])
  const [pendingItems, setPendingItems] = useState<PendingItem[]>([])
  const [productNames, setProductNames] = useState<Map<string, string>>(new Map())
  const [unitNames, setUnitNames] = useState<Map<string, string>>(new Map())
  const [unitTypes, setUnitTypes] = useState<Map<string, UnitType>>(new Map())

  // Reference data
  const [suppliers, setSuppliers] = useState<ContactOut[]>([])
  const [warehouses, setWarehouses] = useState<WarehouseOut[]>([])
  const [currencies, setCurrencies] = useState<CurrencyOut[]>([])

  // Header form
  const [header, setHeader] = useState<HeaderState>(DEFAULT_HEADER)
  const [headerErrors, setHeaderErrors] = useState<Partial<Record<keyof HeaderState, string>>>({})
  const [headerDirty, setHeaderDirty] = useState(false)

  // Supplier combobox
  const [supplierInput, setSupplierInput] = useState('')
  const [showSupplierDrop, setShowSupplierDrop] = useState(false)

  // Add-item row
  const [productSearch, setProductSearch] = useState('')
  const [productResults, setProductResults] = useState<ProductSearchResult[]>([])
  const [showProductDrop, setShowProductDrop] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState<ProductSearchResult | null>(null)
  const [productUnits, setProductUnits] = useState<ProductUnitOut[]>([])
  const [newItemUnit, setNewItemUnit] = useState('')
  const [newItemTaxRate, setNewItemTaxRate] = useState('10')
  const [newItemQty, setNewItemQty] = useState('')
  const [newItemCost, setNewItemCost] = useState('')
  const [addingItem, setAddingItem] = useState(false)
  const [newItemError, setNewItemError] = useState<string | null>(null)

  // Audit log
  const [auditEntries, setAuditEntries] = useState<PurchaseAuditEntry[]>([])

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
  // Tracks that a product was just selected — blocks the debounce that fires when
  // productSearch changes to result.name, preventing the dropdown from reopening.
  // Reset synchronously in onChange before the state update, so the next effect
  // run (triggered by typing) sees false immediately.
  const productJustSelected = useRef(false)

  // Load reference data on mount
  useEffect(() => {
    Promise.all([
      fetchContacts({ contact_type: 'supplier', page_size: 100 }),
      fetchWarehouses(),
      fetchCurrencies(),
    ]).then(([contacts, whs, currList]) => {
      setSuppliers(contacts.items)
      setWarehouses(whs)
      setCurrencies(currList.filter(c => c.is_active))
      if (isNew) {
        const defaultWh = whs.find(w => w.is_default) ?? whs[0]
        if (defaultWh) setHeader(h => ({ ...h, warehouse_id: defaultWh.id }))
      }
    }).catch(() => {})
  }, [isNew])

  // Load existing purchase
  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchPurchase(id)
      .then(async p => {
        setPurchase(p)
        setItems(p.items)
        setHeader({
          supplier_id: p.supplier_id,
          supplier_document_number: p.supplier_document_number ?? '',
          purchase_date: p.purchase_date,
          warehouse_id: p.warehouse_id,
          currency_code: p.currency_code,
          exchange_rate: String(parseFloat(p.exchange_rate)),
          notes: p.notes ?? '',
        })
        setSupplierInput(p.supplier_name ?? '')
        // Load product + unit names
        const uniquePids = [...new Set(p.items.map(i => i.product_id))]
        const pNames = new Map<string, string>()
        const uNames = new Map<string, string>()
        const uTypes = new Map<string, UnitType>()
        await Promise.all(uniquePids.map(async pid => {
          const [product, units] = await Promise.all([fetchProduct(pid), fetchUnits(pid, false)])
          pNames.set(pid, product.name)
          units.forEach(u => {
            uNames.set(u.id, u.unit_catalog?.name ?? u.unit_catalog_id)
            uTypes.set(u.id, (u.unit_catalog?.unit_type ?? 'count') as UnitType)
          })
        }))
        setProductNames(pNames)
        setUnitNames(uNames)
        setUnitTypes(uTypes)
        fetchPurchaseAudit(id).then(setAuditEntries).catch(() => {})
      })
      .catch(err => setApiError(parseApiError(err)))
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
        .then(r => { setProductResults(r.slice(0, 8)); setShowProductDrop(r.length > 0) })
        .catch(() => {})
    }, 300)
    return () => clearTimeout(searchRef.current)
  }, [productSearch])

  // ---- Handlers ----

  const setHeaderField = <K extends keyof HeaderState>(key: K, value: HeaderState[K]) => {
    setHeader(h => ({ ...h, [key]: value }))
    setHeaderErrors(e => ({ ...e, [key]: undefined }))
    if (id) setHeaderDirty(true)
  }

  const handleCurrencyChange = async (code: string) => {
    setHeaderField('currency_code', code)
    if (code === 'PYG') {
      setHeaderField('exchange_rate', '1')
    } else {
      try {
        const rates = await fetchExchangeRates(code)
        if (rates.length > 0) {
          setHeader(h => ({ ...h, exchange_rate: String(parseFloat(rates[0].rate_to_base)) }))
          if (id) setHeaderDirty(true)
        }
      } catch {}
    }
  }

  const validateHeader = (): boolean => {
    const errs: Partial<Record<keyof HeaderState, string>> = {}
    if (!header.supplier_id) errs.supplier_id = 'Seleccionar proveedor'
    if (!header.purchase_date) errs.purchase_date = 'Campo requerido'
    if (!header.warehouse_id) errs.warehouse_id = 'Campo requerido'
    if (header.currency_code !== 'PYG') {
      const r = parseFloat(header.exchange_rate)
      if (isNaN(r) || r <= 0) errs.exchange_rate = 'Debe ser mayor a 0'
    }
    setHeaderErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSaveHeader = async () => {
    if (!validateHeader() || !id) return
    setSaving(true)
    setApiError(null)
    try {
      const updated = await updatePurchase(id, {
        supplier_id: header.supplier_id,
        supplier_document_number: header.supplier_document_number || null,
        purchase_date: header.purchase_date,
        warehouse_id: header.warehouse_id,
        currency_code: header.currency_code,
        exchange_rate: parseFloat(header.exchange_rate),
        notes: header.notes || null,
      })
      setPurchase(updated)
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
    setNewItemTaxRate(String(parseFloat(result.tax_rate)))
    const units = await fetchUnits(result.id, true).catch(() => [])
    setProductUnits(units)
    const def = units.find(u => u.is_default_purchase_unit) ?? units[0]
    setNewItemUnit(def?.id ?? '')
  }

  const clearItemForm = () => {
    setProductSearch('')
    setSelectedProduct(null)
    setProductUnits([])
    setNewItemUnit('')
    setNewItemTaxRate('10')
    setNewItemQty('')
    setNewItemCost('')
    setNewItemError(null)
    productInputRef.current?.focus()
  }

  const handleAddItem = async () => {
    if (!selectedProduct || !newItemUnit) { setNewItemError('Seleccioná un producto y unidad'); return }
    const qty = parseFloat(newItemQty)
    const cost = parseFloat(newItemCost)
    if (isNaN(qty) || qty <= 0) { setNewItemError('Cantidad inválida'); return }
    if (isNaN(cost) || cost < 0) { setNewItemError('Costo inválido'); return }
    setNewItemError(null)
    setAddingItem(true)
    const unit = productUnits.find(u => u.id === newItemUnit)
    const unitType = (unit?.unit_catalog?.unit_type ?? 'count') as UnitType
    const taxRate = parseFloat(newItemTaxRate)

    try {
      if (isNew) {
        setPendingItems(prev => [...prev, {
          localId: crypto.randomUUID(),
          product_id: selectedProduct.id,
          product_unit_id: newItemUnit,
          product_name: selectedProduct.name,
          unit_name: unit?.unit_catalog?.name ?? newItemUnit,
          unit_type: unitType,
          quantity: newItemQty,
          unit_cost: newItemCost,
          tax_rate: newItemTaxRate,
          tax_included: selectedProduct.tax_included_in_price,
        }])
      } else {
        const created = await addPurchaseItem(id!, {
          id: crypto.randomUUID(),
          product_id: selectedProduct.id,
          product_unit_id: newItemUnit,
          quantity: qty,
          unit_cost: cost,
          tax_rate: isNaN(taxRate) ? undefined : taxRate,
        })
        const updated = await fetchPurchase(id!)
        setPurchase(updated)
        setItems(updated.items)
        if (!productNames.has(selectedProduct.id)) {
          setProductNames(m => new Map(m).set(selectedProduct.id, selectedProduct.name))
        }
        if (unit) {
          if (!unitNames.has(unit.id)) {
            setUnitNames(m => new Map(m).set(unit.id, unit.unit_catalog?.name ?? unit.unit_catalog_id))
          }
          if (!unitTypes.has(unit.id)) {
            setUnitTypes(m => new Map(m).set(unit.id, unitType))
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
    if (isNew) { setPendingItems(p => p.filter(i => i.localId !== itemId)); return }
    setApiError(null)
    try {
      await removePurchaseItem(id!, itemId)
      const updated = await fetchPurchase(id!)
      setPurchase(updated)
      setItems(updated.items)
    } catch (err) {
      setApiError(parseApiError(err))
    }
  }

  const buildCreatePayload = () => ({
    id: crypto.randomUUID(),
    supplier_id: header.supplier_id,
    supplier_document_number: header.supplier_document_number || null,
    purchase_date: header.purchase_date,
    warehouse_id: header.warehouse_id,
    currency_code: header.currency_code,
    exchange_rate: parseFloat(header.exchange_rate),
    notes: header.notes || null,
  })

  const saveNewDraft = async (): Promise<string> => {
    const payload = buildCreatePayload()
    const created = await createPurchase(payload)
    for (const item of pendingItems) {
      await addPurchaseItem(created.id, {
        id: crypto.randomUUID(),
        product_id: item.product_id,
        product_unit_id: item.product_unit_id,
        quantity: parseFloat(item.quantity),
        unit_cost: parseFloat(item.unit_cost),
        tax_rate: parseFloat(item.tax_rate),
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
      navigate(`/compras/${newId}`)
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
        await confirmPurchase(newId)
        setShowConfirm(false)
        navigate(`/compras/${newId}`)
      } else {
        const confirmed = await confirmPurchase(id!)
        setShowConfirm(false)
        setPurchase(confirmed)
        setItems(confirmed.items)
        fetchPurchaseAudit(id!).then(setAuditEntries).catch(() => {})
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
      const cancelled = await cancelPurchase(id!, cancelReason)
      setPurchase(cancelled)
      setShowCancel(false)
      fetchPurchaseAudit(id!).then(setAuditEntries).catch(() => {})
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setCancelling(false)
    }
  }

  const handleDeleteDraft = async () => {
    setDeleting(true)
    try {
      await deletePurchase(id!)
      navigate('/compras')
    } catch (err) {
      setApiError(parseApiError(err))
      setDeleting(false)
    }
  }

  const { onKeyDown: onItemInputKeyDown } = useItemFormShortcuts(handleAddItem, clearItemForm)

  // ---- Derived values ----

  const isDraft = isNew || purchase?.status === 'draft'
  const isConfirmed = purchase?.status === 'confirmed'
  const isCancelled = purchase?.status === 'cancelled'
  const status = purchase?.status

  const filteredSuppliers = suppliers.filter(s =>
    s.business_name.toLowerCase().includes(supplierInput.toLowerCase()) ||
    (s.document_number?.toLowerCase().includes(supplierInput.toLowerCase()) ?? false),
  ).slice(0, 8)

  const canConfirm = Boolean(
    header.supplier_id &&
    header.purchase_date &&
    header.warehouse_id &&
    (header.currency_code === 'PYG' || parseFloat(header.exchange_rate) > 0) &&
    (isNew ? pendingItems.length > 0 : items.length > 0 && isDraft),
  )

  const exchangeRate = parseFloat(header.exchange_rate) || 1
  const pendingTotals = computePendingTotals(pendingItems, exchangeRate)

  const warehouseName = warehouses.find(w => w.id === (purchase?.warehouse_id ?? header.warehouse_id))?.name ?? '—'

  const STATUS_LABEL: Record<string, string> = {
    draft: 'Borrador', confirmed: 'Confirmada', cancelled: 'Cancelada',
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
            onClick={() => navigate('/compras')}
            className="mb-2 flex items-center gap-1 text-sm text-text-muted transition-colors hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver a compras
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-text-primary">
              {isNew ? 'Nueva compra' : purchase?.purchase_number ?? 'Borrador'}
            </h1>
            {status && (
              <span className={`text-sm font-medium ${STATUS_COLOR[status]}`}>
                {STATUS_LABEL[status]}
              </span>
            )}
          </div>
          {isCancelled && purchase?.cancelled_reason && (
            <p className="mt-1 text-xs text-text-muted">
              Motivo: {purchase.cancelled_reason}
            </p>
          )}
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
              <h2 className="text-base font-medium text-text-primary">Datos de la compra</h2>
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
                {/* Supplier */}
                <div className="col-span-2 relative">
                  <label className="label">
                    Proveedor <span className="text-danger-500">*</span>
                  </label>
                  <input
                    className={`input ${headerErrors.supplier_id ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                    type="text"
                    placeholder="Buscar proveedor por nombre o RUC…"
                    value={supplierInput}
                    onChange={e => {
                      setSupplierInput(e.target.value)
                      setHeaderField('supplier_id', '')
                      setShowSupplierDrop(true)
                    }}
                    onFocus={() => !header.supplier_id && setShowSupplierDrop(true)}
                    onBlur={() => setTimeout(() => setShowSupplierDrop(false), 150)}
                  />
                  {headerErrors.supplier_id && (
                    <p className="mt-1 text-xs text-danger-500">{headerErrors.supplier_id}</p>
                  )}
                  {showSupplierDrop && filteredSuppliers.length > 0 && (
                    <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-auto rounded border border-border bg-bg-elevated shadow-lg">
                      {filteredSuppliers.map(s => (
                        <button
                          key={s.id}
                          type="button"
                          className="w-full px-3 py-2 text-left text-sm hover:bg-bg-base"
                          onMouseDown={e => {
                            e.preventDefault()
                            setSupplierInput(s.business_name)
                            setHeaderField('supplier_id', s.id)
                            setShowSupplierDrop(false)
                          }}
                        >
                          <span className="text-text-primary">{s.business_name}</span>
                          {s.document_number && (
                            <span className="ml-2 text-xs text-text-muted">{s.document_number}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Fecha */}
                <div>
                  <label className="label">
                    Fecha <span className="text-danger-500">*</span>
                  </label>
                  <input
                    className={`input ${headerErrors.purchase_date ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                    type="date"
                    value={header.purchase_date}
                    onChange={e => setHeaderField('purchase_date', e.target.value)}
                  />
                  {headerErrors.purchase_date && (
                    <p className="mt-1 text-xs text-danger-500">{headerErrors.purchase_date}</p>
                  )}
                </div>

                {/* Nro factura proveedor */}
                <div>
                  <label className="label">
                    Nro. factura proveedor{' '}
                    <span className="font-normal text-text-muted">(opcional)</span>
                  </label>
                  <input
                    className="input"
                    type="text"
                    placeholder="ej. 001-001-000123"
                    value={header.supplier_document_number}
                    onChange={e => setHeaderField('supplier_document_number', e.target.value)}
                  />
                </div>

                {/* Depósito */}
                <div>
                  <label className="label">
                    Depósito <span className="text-danger-500">*</span>
                  </label>
                  <select
                    className={`input ${headerErrors.warehouse_id ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                    value={header.warehouse_id}
                    onChange={e => setHeaderField('warehouse_id', e.target.value)}
                  >
                    <option value="">Seleccionar depósito…</option>
                    {warehouses.map(w => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                  {headerErrors.warehouse_id && (
                    <p className="mt-1 text-xs text-danger-500">{headerErrors.warehouse_id}</p>
                  )}
                </div>

                {/* Moneda */}
                <div>
                  <label className="label">Moneda</label>
                  <select
                    className="input"
                    value={header.currency_code}
                    onChange={e => handleCurrencyChange(e.target.value)}
                  >
                    {currencies.map(c => (
                      <option key={c.code} value={c.code}>{c.code} — {c.name}</option>
                    ))}
                  </select>
                </div>

                {/* Tipo de cambio */}
                {header.currency_code !== 'PYG' && (
                  <div>
                    <label className="label">
                      Tipo de cambio (₲ por 1 {header.currency_code}){' '}
                      <span className="text-danger-500">*</span>
                    </label>
                    <input
                      className={`input tabular-nums ${headerErrors.exchange_rate ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                      type="number"
                      min="0.000001"
                      step="any"
                      placeholder="ej. 7800"
                      value={header.exchange_rate}
                      onChange={e => setHeaderField('exchange_rate', e.target.value)}
                    />
                    {headerErrors.exchange_rate && (
                      <p className="mt-1 text-xs text-danger-500">{headerErrors.exchange_rate}</p>
                    )}
                  </div>
                )}

                {/* Notas */}
                <div className="col-span-2">
                  <label className="label">
                    Notas <span className="font-normal text-text-muted">(opcional)</span>
                  </label>
                  <textarea
                    className="input resize-none"
                    rows={2}
                    placeholder="Observaciones, referencia de pedido, etc."
                    value={header.notes}
                    onChange={e => setHeaderField('notes', e.target.value)}
                  />
                </div>
              </div>
            ) : (
              /* Read-only header */
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                <div>
                  <dt className="label">Proveedor</dt>
                  <dd className="text-text-primary">{purchase?.supplier_name ?? '—'}</dd>
                </div>
                <div>
                  <dt className="label">Fecha</dt>
                  <dd className="text-text-primary">{fmtDate(purchase?.purchase_date ?? '')}</dd>
                </div>
                {purchase?.supplier_document_number && (
                  <div>
                    <dt className="label">Nro. factura proveedor</dt>
                    <dd className="text-text-primary">{purchase.supplier_document_number}</dd>
                  </div>
                )}
                <div>
                  <dt className="label">Depósito</dt>
                  <dd className="text-text-primary">{warehouseName}</dd>
                </div>
                <div>
                  <dt className="label">Moneda</dt>
                  <dd className="text-text-primary">
                    {purchase?.currency_code}
                    {purchase?.currency_code !== 'PYG' && (
                      <span className="ml-2 text-text-secondary">
                        TC: ₲ {formatExchangeRate(purchase?.exchange_rate ?? '0')}
                      </span>
                    )}
                  </dd>
                </div>
                {purchase?.notes && (
                  <div className="col-span-2">
                    <dt className="label">Notas</dt>
                    <dd className="text-text-primary">{purchase.notes}</dd>
                  </div>
                )}
                {isConfirmed && purchase?.confirmed_at && (
                  <div>
                    <dt className="label">Confirmada</dt>
                    <dd className="text-text-primary">
                      {new Date(purchase.confirmed_at).toLocaleDateString('es-PY')}
                    </dd>
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

            {/* Items table */}
            {(isNew ? pendingItems.length : items.length) > 0 ? (
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle">
                      <th className="px-4 pb-2 pt-0 text-left text-xs font-medium text-text-secondary">Producto</th>
                      <th className="px-4 pb-2 pt-0 text-left text-xs font-medium text-text-secondary">Unidad</th>
                      <th className="px-4 pb-2 pt-0 text-right text-xs font-medium text-text-secondary">Cantidad</th>
                      <th className="px-4 pb-2 pt-0 text-right text-xs font-medium text-text-secondary">Costo unit.</th>
                      <th className="px-4 pb-2 pt-0 text-right text-xs font-medium text-text-secondary">IVA</th>
                      <th className="px-4 pb-2 pt-0 text-right text-xs font-medium text-text-secondary">Total</th>
                      {isDraft && <th className="px-4 pb-2 pt-0" />}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {isNew
                      ? pendingItems.map(item => {
                          const qty = parseFloat(item.quantity) || 0
                          const cost = parseFloat(item.unit_cost) || 0
                          const rate = parseFloat(item.tax_rate) || 0
                          const total = item.tax_included
                            ? qty * cost
                            : qty * cost * (1 + rate / 100)
                          return (
                            <tr key={item.localId}>
                              <td className="px-4 py-3 text-text-primary">{item.product_name}</td>
                              <td className="px-4 py-3 text-text-secondary">{item.unit_name}</td>
                              <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                                {formatQuantity(item.quantity, item.unit_type)}
                              </td>
                              <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                                {formatAmt(item.unit_cost, header.currency_code)}
                              </td>
                              <td className="px-4 py-3 tabular-nums text-right text-text-secondary">
                                {item.tax_rate}%
                              </td>
                              <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                                {formatAmt(total, header.currency_code)}
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
                          )
                        })
                      : items.map(item => (
                          <tr key={item.id}>
                            <td className="px-4 py-3 text-text-primary">
                              {productNames.get(item.product_id) ?? item.product_id.slice(0, 8) + '…'}
                            </td>
                            <td className="px-4 py-3 text-text-secondary">
                              {unitNames.get(item.product_unit_id) ?? '—'}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                              {formatQuantity(item.quantity, unitTypes.get(item.product_unit_id) ?? 'count')}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                              {formatAmt(item.unit_cost, purchase?.currency_code ?? 'PYG')}
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-secondary">
                              {item.tax_rate}%
                            </td>
                            <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                              {formatAmt(item.total, purchase?.currency_code ?? 'PYG')}
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
              !isDraft && (
                <p className="px-4 pb-4 text-sm text-text-muted">Sin ítems.</p>
              )
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
                      onChange={e => { productJustSelected.current = false; setProductSearch(e.target.value); setSelectedProduct(null) }}
                      onBlur={() => setTimeout(() => setShowProductDrop(false), 150)}
                      onFocus={() => productResults.length > 0 && setShowProductDrop(true)}
                      onKeyDown={onItemInputKeyDown}
                    />
                    {showProductDrop && productResults.length > 0 && (
                      <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-auto rounded border border-border bg-bg-elevated shadow-lg">
                        {productResults.map(r => (
                          <button
                            key={r.id}
                            type="button"
                            className="w-full px-3 py-2 text-left text-sm hover:bg-bg-base"
                            onMouseDown={e => { e.preventDefault(); handleSelectProduct(r) }}
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
                      onChange={e => setNewItemUnit(e.target.value)}
                      disabled={productUnits.length === 0}
                    >
                      <option value="">Unidad…</option>
                      {productUnits.map(u => (
                        <option key={u.id} value={u.id}>
                          {u.unit_catalog?.name ?? u.unit_catalog_id}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* IVA select */}
                  <div className="col-span-2">
                    <select
                      className="input text-sm"
                      value={newItemTaxRate}
                      onChange={e => setNewItemTaxRate(e.target.value)}
                    >
                      <option value="0">0% (exento)</option>
                      <option value="5">5%</option>
                      <option value="10">10%</option>
                    </select>
                  </div>

                  {/* Quantity */}
                  <div className="col-span-2">
                    <input
                      className="input tabular-nums text-sm"
                      type="number"
                      min="0.0001"
                      step="any"
                      placeholder="Cant."
                      value={newItemQty}
                      onChange={e => setNewItemQty(e.target.value)}
                      onKeyDown={onItemInputKeyDown}
                    />
                  </div>

                  {/* Cost */}
                  <div className="col-span-2">
                    <input
                      className="input tabular-nums text-sm"
                      type="number"
                      min="0"
                      step="any"
                      placeholder={`Costo (${header.currency_code})`}
                      value={newItemCost}
                      onChange={e => setNewItemCost(e.target.value)}
                      onKeyDown={onItemInputKeyDown}
                    />
                  </div>
                </div>

                {/* IVA hint */}
                {selectedProduct && (
                  <p className="mt-1 text-xs text-text-muted">
                    {selectedProduct.tax_included_in_price ? 'Precio incluye IVA' : 'Precio sin IVA'} · Enter para agregar, Esc para limpiar
                  </p>
                )}

                <button
                  type="button"
                  className="btn-secondary mt-3 flex items-center gap-1.5 text-sm"
                  onClick={handleAddItem}
                  disabled={addingItem || !selectedProduct || !newItemUnit || !newItemQty || !newItemCost}
                >
                  {addingItem ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  {addingItem ? 'Agregando…' : 'Agregar ítem'}
                </button>
              </div>
            )}
          </div>

          {/* Totals */}
          <div className="card">
            <div className="ml-auto max-w-xs space-y-2 text-sm">
              {(() => {
                const curr = purchase?.currency_code ?? header.currency_code
                const sub = purchase ? purchase.subtotal : String(pendingTotals.subtotal)
                const tax = purchase ? purchase.tax_total : String(pendingTotals.taxTotal)
                const tot = purchase ? purchase.total : String(pendingTotals.total)
                const totBase = purchase ? purchase.total_base_currency : String(pendingTotals.totalBase)
                const showBase = curr !== 'PYG'
                return (
                  <>
                    <div className="flex justify-between text-text-secondary">
                      <span>Subtotal</span>
                      <span className="tabular-nums">{formatAmt(sub, curr)}</span>
                    </div>
                    <div className="flex justify-between text-text-secondary">
                      <span>IVA</span>
                      <span className="tabular-nums">{formatAmt(tax, curr)}</span>
                    </div>
                    <div className="flex justify-between border-t border-border-subtle pt-2 font-medium text-text-primary">
                      <span>Total</span>
                      <span className="tabular-nums">{formatAmt(tot, curr)}</span>
                    </div>
                    {showBase && (
                      <div className="flex justify-between text-text-secondary">
                        <span>Total (₲)</span>
                        <span className="tabular-nums">{formatAmt(totBase, 'PYG')}</span>
                      </div>
                    )}
                  </>
                )
              })()}
            </div>
          </div>

          {/* Audit log */}
          {!isNew && auditEntries.length > 0 && (
            <div className="card space-y-3">
              <h2 className="text-base font-medium text-text-primary">Historial</h2>
              <ol className="space-y-3">
                {auditEntries.map(entry => {
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
                          {isCreate ? 'Creada' : isConfirmEntry ? 'Confirmada' : 'Cancelada'}
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
            <button type="button" className="btn-secondary" onClick={() => navigate('/compras')}>
              {isDraft ? 'Cancelar' : 'Volver'}
            </button>
            <div className="flex gap-2">
              {isConfirmed && (
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => setShowCancel(true)}
                >
                  Cancelar compra
                </button>
              )}
              {isDraft && (
                <>
                  {isNew && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleSaveDraft}
                      disabled={saving || !header.supplier_id || !header.warehouse_id}
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
                      if (isNew) {
                        if (!validateHeader()) return
                        setShowConfirm(true)
                      } else {
                        setShowConfirm(true)
                      }
                    }}
                  >
                    Confirmar compra
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showConfirm && (
        <ConfirmPurchaseModal
          items={isNew ? 'pending' : 'saved'}
          pendingItems={pendingItems}
          purchaseItems={items}
          productNames={productNames}
          unitNames={unitNames}
          unitTypes={unitTypes}
          currency={purchase?.currency_code ?? header.currency_code}
          confirming={confirming}
          error={confirmError}
          onConfirm={handleConfirm}
          onClose={() => { if (!confirming) { setShowConfirm(false); setConfirmError(null) } }}
        />
      )}
      {showCancel && (
        <CancelPurchaseModal
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
