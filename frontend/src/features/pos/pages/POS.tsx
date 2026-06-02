import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  HelpCircle,
  Keyboard,
  Loader2,
  Minus,
  Plus,
  Trash2,
  User,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../../../lib/api'
import { useKeyboardShortcuts } from '../../../lib/hooks/useKeyboardShortcuts'
import { formatQuantity } from '../../../lib/format'
import { parseApiError as _parseErr } from '../../../lib/parseApiError'
import { fetchWarehouses } from '../../admin/api/warehouses'
import type { UnitType } from '../../admin/api/unit_catalog'
import { fetchContacts, type ContactOut } from '../../contacts/api/contacts'
import { fetchPriceHistory } from '../../products/api/prices'
import { searchProducts, type ProductSearchResult } from '../../products/api/products'
import { fetchUnits, type ProductUnitOut } from '../../products/api/units'
import { useAuthStore } from '../../auth/store'
import { useSettings } from '../../settings/hooks/useSettings'
import {
  addSaleItem,
  addSalePayment,
  confirmSale,
  createSale,
  type DiscountType,
  type PaymentMethod,
} from '../api/sales'

// ─── Types ────────────────────────────────────────────────────────────────────

interface CartItem {
  localId: string
  product_id: string
  product_unit_id: string
  product_name: string
  unit_name: string
  unit_type: UnitType
  quantity: string
  unit_price: string
  tax_rate: string
  tax_included: boolean
  discount_amount: string
}

interface HeaderDiscount {
  amount: string
  type: DiscountType
  percent: string
}

interface PendingPayment {
  localId: string
  method: PaymentMethod
  amount: string
  reference: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseApiError(err: unknown): string {
  return _parseErr(err).message
}

function fmtPYG(value: number): string {
  if (isNaN(value)) return '₲ —'
  return '₲ ' + new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(value)
}

function computeCartTotals(items: CartItem[], headerDiscountAmount: number) {
  let itemsSubtotal = 0
  let taxTotal = 0
  let itemsTotal = 0
  for (const item of items) {
    const qty = parseFloat(item.quantity) || 0
    const price = parseFloat(item.unit_price) || 0
    const rate = parseFloat(item.tax_rate) || 0
    const disc = parseFloat(item.discount_amount) || 0
    const gross = qty * price - disc
    if (item.tax_included && rate > 0) {
      const base = gross / (1 + rate / 100)
      itemsSubtotal += base
      taxTotal += gross - base
      itemsTotal += gross
    } else {
      const tax = gross * rate / 100
      itemsSubtotal += gross
      taxTotal += tax
      itemsTotal += gross + tax
    }
  }
  const hDisc = Math.max(0, headerDiscountAmount)
  const total = Math.max(0, itemsTotal - hDisc)
  return { itemsSubtotal, taxTotal, itemsTotal, headerDiscountAmount: hDisc, total }
}

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  cash: 'Efectivo',
  transfer: 'Transferencia',
  card: 'Tarjeta',
  check: 'Cheque',
  other: 'Otro',
}

const PAYMENT_METHODS: PaymentMethod[] = ['cash', 'transfer', 'card', 'check', 'other']

// ─── HelpModal ────────────────────────────────────────────────────────────────

function HelpModal({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const shortcuts = [
    ['F1', 'Mostrar esta ayuda'],
    ['F2', 'Seleccionar cliente'],
    ['F3', 'Aplicar descuento'],
    ['F4', 'Abrir cobro (pagar)'],
    ['F9', 'Cancelar venta (limpiar carrito)'],
    ['Esc', 'Cerrar modal / limpiar campo activo'],
    ['↑ / ↓', 'Navegar resultados de búsqueda'],
    ['Enter', 'Seleccionar resultado / confirmar'],
    ['Tab', 'Avanzar campo (búsqueda → cantidad → unidad)'],
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5 text-text-secondary" />
            <h3 className="text-lg font-semibold text-text-primary">Atajos de teclado</h3>
          </div>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-border-subtle">
            {shortcuts.map(([key, desc]) => (
              <tr key={key}>
                <td className="py-2 pr-4">
                  <kbd className="rounded border border-border bg-bg-elevated px-2 py-0.5 text-xs font-mono text-text-primary">
                    {key}
                  </kbd>
                </td>
                <td className="py-2 text-text-secondary">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── CustomerModal ────────────────────────────────────────────────────────────

function CustomerModal({
  onSelect,
  onClose,
}: {
  onSelect: (id: string, name: string) => void
  onClose: () => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ContactOut[]>([])
  const [loading, setLoading] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => { inputRef.current?.focus() }, [])

  useEffect(() => {
    clearTimeout(timerRef.current)
    if (query.length < 1) {
      setLoading(true)
      timerRef.current = setTimeout(() => {
        fetchContacts({ contact_type: 'customer', page_size: 20 })
          .then(r => { setResults(r.items); setHighlight(0) })
          .catch(() => {})
          .finally(() => setLoading(false))
      }, 0)
      return
    }
    setLoading(true)
    timerRef.current = setTimeout(() => {
      fetchContacts({ contact_type: 'customer', search: query, page_size: 20 })
        .then(r => { setResults(r.items); setHighlight(0) })
        .catch(() => {})
        .finally(() => setLoading(false))
    }, 200)
    return () => clearTimeout(timerRef.current)
  }, [query])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key === 'ArrowDown') { e.preventDefault(); setHighlight(h => Math.min(h + 1, results.length - 1)) }
      if (e.key === 'ArrowUp') { e.preventDefault(); setHighlight(h => Math.max(h - 1, 0)) }
      if (e.key === 'Enter' && results[highlight]) {
        const c = results[highlight]
        onSelect(c.id, c.business_name)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [results, highlight, onSelect, onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-sm space-y-3" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-text-secondary" />
            <h3 className="text-base font-semibold text-text-primary">Seleccionar cliente</h3>
          </div>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-4 w-4" />
          </button>
        </div>
        <input
          ref={inputRef}
          className="input text-sm"
          placeholder="Buscar por nombre o documento…"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <div className="max-h-56 overflow-auto rounded border border-border-subtle">
          {loading && (
            <div className="flex items-center justify-center py-6 text-text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          )}
          {!loading && results.length === 0 && (
            <p className="py-6 text-center text-sm text-text-muted">Sin resultados</p>
          )}
          {!loading && results.map((c, idx) => (
            <button
              key={c.id}
              type="button"
              className={`w-full px-3 py-2 text-left text-sm transition-colors ${
                idx === highlight ? 'bg-primary-500/10 text-text-primary' : 'text-text-secondary hover:bg-bg-base'
              }`}
              onClick={() => onSelect(c.id, c.business_name)}
            >
              <span className="font-medium text-text-primary">{c.business_name}</span>
              {c.document_number && (
                <span className="ml-2 text-xs text-text-muted">{c.document_number}</span>
              )}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="btn-secondary w-full text-sm"
          onClick={() => onSelect('', '')}
        >
          Sin cliente
        </button>
      </div>
    </div>
  )
}

// ─── DiscountModal ────────────────────────────────────────────────────────────

function DiscountModal({
  focusedItem,
  headerDiscount,
  onSaveHeader,
  onSaveItem,
  onClose,
}: {
  focusedItem: CartItem | null
  headerDiscount: HeaderDiscount
  onSaveHeader: (discount: HeaderDiscount) => void
  onSaveItem: (localId: string, discountAmount: string) => void
  onClose: () => void
}) {
  const [tab, setTab] = useState<'header' | 'item'>(focusedItem ? 'item' : 'header')
  const [hType, setHType] = useState<DiscountType>(headerDiscount.type)
  const [hAmount, setHAmount] = useState(headerDiscount.amount === '0' ? '' : headerDiscount.amount)
  const [hPercent, setHPercent] = useState(headerDiscount.percent)
  const [iAmount, setIAmount] = useState(focusedItem?.discount_amount ?? '')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 50) }, [tab])
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleApply = () => {
    if (tab === 'header') {
      if (hType === 'amount') {
        onSaveHeader({ amount: hAmount || '0', type: 'amount', percent: '' })
      } else {
        const pct = parseFloat(hPercent) || 0
        onSaveHeader({ amount: '0', type: 'percent', percent: String(pct) })
      }
    } else if (focusedItem) {
      onSaveItem(focusedItem.localId, iAmount || '0')
    }
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-sm space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-text-primary">Descuento</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 rounded border border-border-subtle p-0.5">
          <button
            type="button"
            className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === 'header' ? 'bg-bg-elevated text-text-primary' : 'text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => setTab('header')}
          >
            Cabecera
          </button>
          {focusedItem && (
            <button
              type="button"
              className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === 'item' ? 'bg-bg-elevated text-text-primary' : 'text-text-secondary hover:text-text-primary'
              }`}
              onClick={() => setTab('item')}
            >
              {focusedItem.product_name}
            </button>
          )}
        </div>

        {tab === 'header' && (
          <div className="space-y-3">
            <div className="flex gap-3">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
                <input
                  type="radio"
                  checked={hType === 'amount'}
                  onChange={() => setHType('amount')}
                  className="accent-primary-500"
                />
                Monto (₲)
              </label>
              <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
                <input
                  type="radio"
                  checked={hType === 'percent'}
                  onChange={() => setHType('percent')}
                  className="accent-primary-500"
                />
                Porcentaje (%)
              </label>
            </div>
            {hType === 'amount' ? (
              <input
                ref={inputRef}
                className="input tabular-nums"
                type="number"
                min="0"
                step="any"
                placeholder="Monto en ₲"
                value={hAmount}
                onChange={e => setHAmount(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleApply() }}
              />
            ) : (
              <input
                ref={inputRef}
                className="input tabular-nums"
                type="number"
                min="0"
                max="100"
                step="any"
                placeholder="Porcentaje ej. 10"
                value={hPercent}
                onChange={e => setHPercent(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleApply() }}
              />
            )}
          </div>
        )}

        {tab === 'item' && focusedItem && (
          <div className="space-y-3">
            <p className="text-xs text-text-muted">Descuento sobre: <span className="text-text-secondary">{focusedItem.product_name}</span></p>
            <input
              ref={inputRef}
              className="input tabular-nums"
              type="number"
              min="0"
              step="any"
              placeholder="Monto en ₲"
              value={iAmount}
              onChange={e => setIAmount(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleApply() }}
            />
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button type="button" className="btn-primary" onClick={handleApply}>Aplicar</button>
        </div>
      </div>
    </div>
  )
}

// ─── PaymentModal ─────────────────────────────────────────────────────────────

function PaymentModal({
  total,
  confirming,
  confirmError,
  pendingSaleCreated,
  onConfirm,
  onClose,
}: {
  total: number
  confirming: boolean
  confirmError: string | null
  pendingSaleCreated: boolean
  onConfirm: (payments: PendingPayment[]) => void
  onClose: () => void
}) {
  const [payments, setPayments] = useState<PendingPayment[]>([
    { localId: crypto.randomUUID(), method: 'cash', amount: String(total > 0 ? Math.round(total) : ''), reference: '' },
  ])

  const paymentSum = payments.reduce((s, p) => s + (parseFloat(p.amount) || 0), 0)
  const diff = total - paymentSum
  const canConfirm = Math.abs(diff) < 0.5 && paymentSum > 0

  const addPayment = () => {
    setPayments(prev => [...prev, { localId: crypto.randomUUID(), method: 'cash', amount: '', reference: '' }])
  }

  const updatePayment = (localId: string, field: keyof PendingPayment, value: string) => {
    setPayments(prev => prev.map(p => p.localId === localId ? { ...p, [field]: value } : p))
  }

  const removePayment = (localId: string) => {
    if (payments.length <= 1) return
    setPayments(prev => prev.filter(p => p.localId !== localId))
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape' && !confirming) onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [confirming, onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="card w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Cobrar venta</h3>
          {!confirming && (
            <button type="button" onClick={onClose} className="btn-ghost p-1">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Total to pay */}
        <div className="rounded border border-border-subtle bg-bg-elevated px-4 py-3 text-center">
          <p className="text-xs text-text-muted mb-1">Total a cobrar</p>
          <p className="text-3xl font-bold tabular-nums text-text-primary">{fmtPYG(total)}</p>
        </div>

        {/* Payment rows */}
        <div className="space-y-2">
          {payments.map((p, idx) => (
            <div key={p.localId} className="flex items-center gap-2">
              <select
                className="input text-sm w-36 flex-shrink-0"
                value={p.method}
                onChange={e => updatePayment(p.localId, 'method', e.target.value)}
                disabled={confirming}
              >
                {PAYMENT_METHODS.map(m => (
                  <option key={m} value={m}>{PAYMENT_LABELS[m]}</option>
                ))}
              </select>
              <input
                className="input tabular-nums text-sm flex-1"
                type="number"
                min="0"
                step="any"
                placeholder="Monto ₲"
                value={p.amount}
                onChange={e => updatePayment(p.localId, 'amount', e.target.value)}
                disabled={confirming}
                autoFocus={idx === 0}
              />
              <input
                className="input text-sm w-28 flex-shrink-0"
                type="text"
                placeholder="Ref. (opcional)"
                value={p.reference}
                onChange={e => updatePayment(p.localId, 'reference', e.target.value)}
                disabled={confirming}
              />
              {payments.length > 1 && (
                <button
                  type="button"
                  className="btn-ghost p-1 text-danger-500"
                  onClick={() => removePayment(p.localId)}
                  disabled={confirming}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Add payment row */}
        <button
          type="button"
          className="btn-secondary flex w-full items-center justify-center gap-1.5 text-sm"
          onClick={addPayment}
          disabled={confirming}
        >
          <Plus className="h-4 w-4" />
          Agregar forma de pago
        </button>

        {/* Sum vs total */}
        <div className="flex justify-between border-t border-border-subtle pt-2 text-sm">
          <span className="text-text-secondary">Pagado</span>
          <span className={`tabular-nums font-medium ${canConfirm ? 'text-success-500' : 'text-warning-500'}`}>
            {fmtPYG(paymentSum)}
          </span>
        </div>
        {!canConfirm && paymentSum > 0 && (
          <p className="text-xs text-warning-500 tabular-nums">
            {diff > 0 ? `Faltan ${fmtPYG(diff)}` : `Excede en ${fmtPYG(-diff)}`}
          </p>
        )}

        {/* Error */}
        {confirmError && (
          <div className="flex items-start gap-2 rounded border border-danger-500/30 bg-danger-500/10 px-3 py-2 text-sm text-danger-500">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            {confirmError}
          </div>
        )}
        {pendingSaleCreated && confirmError && (
          <p className="text-xs text-text-muted">
            La venta fue registrada. Podés reintentar la confirmación.
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-secondary flex-1"
            onClick={onClose}
            disabled={confirming}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="btn-accent flex flex-1 items-center justify-center gap-2 text-base font-semibold"
            onClick={() => onConfirm(payments)}
            disabled={!canConfirm || confirming}
          >
            {confirming ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Procesando…</>
            ) : (
              <><Check className="h-4 w-4" /> Cobrar</>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── SuccessModal ─────────────────────────────────────────────────────────────

function SuccessModal({ saleNumber, onClose }: { saleNumber: string; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape' || e.key === 'Enter') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="card w-full max-w-sm space-y-4 text-center">
        <div className="flex justify-center">
          <CheckCircle2 className="h-14 w-14 text-success-500" />
        </div>
        <h3 className="text-xl font-bold text-text-primary">¡Venta confirmada!</h3>
        <p className="text-sm text-text-secondary">
          Número de venta:{' '}
          <span className="font-mono font-semibold text-text-primary">{saleNumber}</span>
        </p>
        <button type="button" className="btn-primary w-full text-base" onClick={onClose}>
          Nueva venta
        </button>
      </div>
    </div>
  )
}

// ─── POS ──────────────────────────────────────────────────────────────────────

export function POS() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const { businessName } = useSettings()

  // Init
  const [warehouseId, setWarehouseId] = useState('')
  const [saleRequiresCustomer, setSaleRequiresCustomer] = useState(false)
  const [initError, setInitError] = useState<string | null>(null)

  // Cart
  const [cartItems, setCartItems] = useState<CartItem[]>([])
  const [customerId, setCustomerId] = useState<string | null>(null)
  const [customerName, setCustomerName] = useState<string | null>(null)
  const [headerDiscount, setHeaderDiscount] = useState<HeaderDiscount>({ amount: '0', type: 'amount', percent: '' })
  const [focusedItemId, setFocusedItemId] = useState<string | null>(null)

  // Inline qty edit
  const [editingQtyId, setEditingQtyId] = useState<string | null>(null)
  const [editingQtyValue, setEditingQtyValue] = useState('')

  // Add-item row
  const [productQuery, setProductQuery] = useState('')
  const [productResults, setProductResults] = useState<ProductSearchResult[]>([])
  const [showSearchDrop, setShowSearchDrop] = useState(false)
  const [searchHighlight, setSearchHighlight] = useState(-1)
  const [selectedProduct, setSelectedProduct] = useState<ProductSearchResult | null>(null)
  const [productUnits, setProductUnits] = useState<ProductUnitOut[]>([])
  const [newItemUnit, setNewItemUnit] = useState('')
  const [newItemQty, setNewItemQty] = useState('1')
  const [newItemPrice, setNewItemPrice] = useState('')
  const [addItemError, setAddItemError] = useState<string | null>(null)
  const [loadingPrice, setLoadingPrice] = useState(false)

  // Pending sale (for confirm retry)
  const [pendingSaleId, setPendingSaleId] = useState<string | null>(null)
  const [paymentConfirming, setPaymentConfirming] = useState(false)
  const [paymentError, setPaymentError] = useState<string | null>(null)

  // Modals
  const [showHelp, setShowHelp] = useState(false)
  const [showCustomer, setShowCustomer] = useState(false)
  const [showDiscount, setShowDiscount] = useState(false)
  const [showPayment, setShowPayment] = useState(false)
  const [successSaleNumber, setSuccessSaleNumber] = useState<string | null>(null)

  // Refs for tab order
  const productSearchRef = useRef<HTMLInputElement>(null)
  const qtyRef = useRef<HTMLInputElement>(null)
  const unitRef = useRef<HTMLSelectElement>(null)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>()

  // Load on mount
  useEffect(() => {
    Promise.all([
      fetchWarehouses(),
      apiFetch<{ key: string; value: unknown }>('/settings/sale_requires_customer'),
    ])
      .then(([whs, setting]) => {
        const def = whs.find(w => w.is_default) ?? whs[0]
        if (def) setWarehouseId(def.id)
        setSaleRequiresCustomer(setting.value === true)
      })
      .catch(() => setInitError('No se pudo cargar la configuración del POS'))

    productSearchRef.current?.focus()
  }, [])

  // Debounced product search
  useEffect(() => {
    clearTimeout(searchTimerRef.current)
    if (productQuery.length < 2) {
      setProductResults([])
      setShowSearchDrop(false)
      return
    }
    searchTimerRef.current = setTimeout(() => {
      searchProducts(productQuery)
        .then(r => {
          setProductResults(r.slice(0, 8))
          setShowSearchDrop(r.length > 0)
          setSearchHighlight(0)
        })
        .catch(() => {})
    }, 200)
    return () => clearTimeout(searchTimerRef.current)
  }, [productQuery])

  // Global F-key shortcuts
  const anyModalOpen = showHelp || showCustomer || showDiscount || showPayment || !!successSaleNumber

  useKeyboardShortcuts({
    F1: () => setShowHelp(true),
    F2: () => { if (!anyModalOpen) setShowCustomer(true) },
    F3: () => { if (!anyModalOpen) setShowDiscount(true) },
    F4: () => { if (!anyModalOpen && cartItems.length > 0) setShowPayment(true) },
    F9: () => { if (!anyModalOpen) handleClearCart() },
  })

  // ── Handlers ──────────────────────────────────────────────────────────────

  const loadUnitPrice = useCallback(async (productId: string, unitId: string) => {
    setLoadingPrice(true)
    try {
      const prices = await fetchPriceHistory(productId, unitId, 'PYG')
      if (prices.length > 0) {
        setNewItemPrice(String(parseFloat(prices[0].price)))
      } else {
        setNewItemPrice('')
      }
    } catch {
      setNewItemPrice('')
    } finally {
      setLoadingPrice(false)
    }
  }, [])

  const handleSelectProduct = useCallback(async (product: ProductSearchResult) => {
    setSelectedProduct(product)
    setProductQuery(product.name)
    setShowSearchDrop(false)
    setSearchHighlight(-1)
    setNewItemQty('1')
    setAddItemError(null)

    const units = await fetchUnits(product.id, true).catch(() => [])
    setProductUnits(units)

    const defaultUnit = units.find(u => u.is_default_sale_unit) ?? units[0]
    if (defaultUnit) {
      setNewItemUnit(defaultUnit.id)
      await loadUnitPrice(product.id, defaultUnit.id)
    } else {
      setNewItemUnit('')
      setNewItemPrice('')
    }

    setTimeout(() => { qtyRef.current?.focus(); qtyRef.current?.select() }, 50)
  }, [loadUnitPrice])

  const handleUnitChange = useCallback(async (unitId: string) => {
    setNewItemUnit(unitId)
    if (selectedProduct) {
      await loadUnitPrice(selectedProduct.id, unitId)
    }
  }, [selectedProduct, loadUnitPrice])

  const handleAddItem = useCallback(() => {
    if (!selectedProduct || !newItemUnit) {
      setAddItemError('Seleccioná un producto y unidad')
      return
    }
    const qty = parseFloat(newItemQty)
    if (isNaN(qty) || qty <= 0) { setAddItemError('Cantidad inválida'); return }
    const price = parseFloat(newItemPrice)
    if (isNaN(price) || price < 0) { setAddItemError('Precio inválido'); return }

    const unit = productUnits.find(u => u.id === newItemUnit)
    const unitType = (unit?.unit_catalog?.unit_type ?? 'count') as UnitType
    const unitName = unit?.unit_catalog?.name ?? unit?.unit_catalog_id ?? '—'

    const newItem: CartItem = {
      localId: crypto.randomUUID(),
      product_id: selectedProduct.id,
      product_unit_id: newItemUnit,
      product_name: selectedProduct.name,
      unit_name: unitName,
      unit_type: unitType,
      quantity: String(qty),
      unit_price: String(price),
      tax_rate: selectedProduct.tax_rate,
      tax_included: selectedProduct.tax_included_in_price,
      discount_amount: '0',
    }

    setCartItems(prev => [...prev, newItem])
    setFocusedItemId(newItem.localId)

    // Clear add-item row
    setProductQuery('')
    setSelectedProduct(null)
    setProductUnits([])
    setNewItemUnit('')
    setNewItemQty('1')
    setNewItemPrice('')
    setAddItemError(null)
    productSearchRef.current?.focus()
  }, [selectedProduct, newItemUnit, newItemQty, newItemPrice, productUnits])

  const handleRemoveItem = (localId: string) => {
    setCartItems(prev => prev.filter(i => i.localId !== localId))
    if (focusedItemId === localId) setFocusedItemId(null)
  }

  const handleUpdateItemQty = (localId: string, value: string) => {
    setCartItems(prev => prev.map(i => i.localId === localId ? { ...i, quantity: value } : i))
  }

  const handleClearCart = () => {
    setCartItems([])
    setCustomerId(null)
    setCustomerName(null)
    setHeaderDiscount({ amount: '0', type: 'amount', percent: '' })
    setFocusedItemId(null)
    setPendingSaleId(null)
    setPaymentError(null)
    productSearchRef.current?.focus()
  }

  const handleSelectCustomer = (id: string, name: string) => {
    setCustomerId(id || null)
    setCustomerName(name || null)
    setShowCustomer(false)
    productSearchRef.current?.focus()
  }

  const handleSaveHeaderDiscount = (discount: HeaderDiscount) => {
    setHeaderDiscount(discount)
  }

  const handleSaveItemDiscount = (localId: string, discountAmount: string) => {
    setCartItems(prev => prev.map(i => i.localId === localId ? { ...i, discount_amount: discountAmount } : i))
  }

  const handleConfirmSale = async (payments: PendingPayment[]) => {
    if (!warehouseId) { setPaymentError('No se pudo determinar el depósito'); return }
    setPaymentConfirming(true)
    setPaymentError(null)

    try {
      let saleId = pendingSaleId

      if (!saleId) {
        const hDiscAmount = headerDiscount.type === 'amount'
          ? parseFloat(headerDiscount.amount) || 0
          : 0

        const newSaleId = crypto.randomUUID()
        await createSale({
          id: newSaleId,
          customer_id: customerId || null,
          sale_date: new Date().toISOString(),
          warehouse_id: warehouseId,
          currency_code: 'PYG',
          exchange_rate: 1,
          header_discount_amount: hDiscAmount,
          header_discount_type: headerDiscount.type,
          header_discount_percent:
            headerDiscount.type === 'percent' ? parseFloat(headerDiscount.percent) || null : null,
        })
        saleId = newSaleId

        for (const item of cartItems) {
          await addSaleItem(saleId, {
            id: crypto.randomUUID(),
            product_id: item.product_id,
            product_unit_id: item.product_unit_id,
            quantity: parseFloat(item.quantity),
            unit_price: parseFloat(item.unit_price),
            discount_amount: parseFloat(item.discount_amount) || 0,
            discount_type: 'amount',
            tax_rate: parseFloat(item.tax_rate),
          })
        }

        for (const payment of payments) {
          await addSalePayment(saleId, {
            id: crypto.randomUUID(),
            payment_method: payment.method,
            amount: parseFloat(payment.amount),
            reference: payment.reference || null,
          })
        }

        setPendingSaleId(saleId)
      }

      const result = await confirmSale(saleId)

      setShowPayment(false)
      setPendingSaleId(null)
      setSuccessSaleNumber(result.sale_number ?? saleId.slice(0, 8))
    } catch (err) {
      const parsed = _parseErr(err)
      if (parsed.code === 'insufficient_stock') {
        const name = (parsed.details.product_name as string)
          ?? cartItems.find(i => i.product_id === parsed.details.product_id)?.product_name
          ?? 'Producto'
        const avail = Math.round(parseFloat((parsed.details.available as string) || '0'))
        const req = Math.round(parseFloat((parsed.details.requested as string) || '0'))
        setPaymentError(`Stock insuficiente — ${name}: disponible ${avail}, solicitado ${req}`)
      } else {
        setPaymentError(parsed.message)
      }
    } finally {
      setPaymentConfirming(false)
    }
  }

  // ── Search input keyboard handler ──────────────────────────────────────────

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSearchHighlight(h => Math.min(h + 1, productResults.length - 1))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSearchHighlight(h => Math.max(h - 1, 0))
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      if (showSearchDrop && productResults.length > 0) {
        const idx = searchHighlight >= 0 ? searchHighlight : 0
        handleSelectProduct(productResults[idx])
      }
      return
    }
    if (e.key === 'Escape') {
      setProductQuery('')
      setSelectedProduct(null)
      setShowSearchDrop(false)
      setProductUnits([])
      setNewItemUnit('')
      setNewItemPrice('')
      setAddItemError(null)
      return
    }
    if (e.key === 'Tab' && selectedProduct) {
      e.preventDefault()
      qtyRef.current?.focus()
      qtyRef.current?.select()
    }
  }

  // ── Qty + unit keydown ─────────────────────────────────────────────────────

  const handleQtyKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); handleAddItem() }
    if (e.key === 'Tab') { /* native tab to unit select */ }
  }

  const handleUnitKeyDown = (e: React.KeyboardEvent<HTMLSelectElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); handleAddItem() }
  }

  // ── Computed ───────────────────────────────────────────────────────────────

  const hDiscAmount = headerDiscount.type === 'amount'
    ? parseFloat(headerDiscount.amount) || 0
    : 0
  const totals = computeCartTotals(cartItems, hDiscAmount)

  // For percent header discount, compute the actual amount after item totals
  const effectiveHDisc = headerDiscount.type === 'percent'
    ? totals.itemsTotal * (parseFloat(headerDiscount.percent) || 0) / 100
    : hDiscAmount
  const finalTotal = Math.max(0, totals.itemsTotal - effectiveHDisc)

  const focusedCartItem = focusedItemId ? cartItems.find(i => i.localId === focusedItemId) ?? null : null
  const canCheckout = cartItems.length > 0 && (!saleRequiresCustomer || !!customerId) && !!warehouseId

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-bg-base">

      {/* Minimal header */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-border-subtle bg-bg-surface px-4 py-2">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-sm text-text-muted transition-colors hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Salir POS
          </button>
          <span className="text-border-subtle">|</span>
          <span className="text-sm font-semibold text-text-primary">DTCore</span>
          {businessName && businessName !== 'DTCore' && (
            <span className="text-xs text-text-muted">— {businessName}</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowHelp(true)}
            className="flex items-center gap-1.5 text-xs text-text-muted transition-colors hover:text-text-primary"
          >
            <HelpCircle className="h-4 w-4" />
            F1 Ayuda
          </button>
          <span className="text-xs text-text-muted">{user?.full_name}</span>
        </div>
      </header>

      {initError && (
        <div className="flex items-center gap-2 bg-danger-500/10 px-4 py-2 text-sm text-danger-500">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {initError}
        </div>
      )}

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT: search + cart */}
        <div className="flex flex-1 flex-col overflow-hidden">

          {/* Add-item row */}
          <div className="border-b border-border-subtle bg-bg-surface px-4 py-3">
            {addItemError && (
              <p className="mb-2 text-xs text-danger-500">{addItemError}</p>
            )}
            <div className="flex items-center gap-2">
              {/* Product search */}
              <div className="relative flex-1">
                <input
                  ref={productSearchRef}
                  className="input pr-8 text-sm"
                  type="text"
                  placeholder="Buscar producto — SKU, código de barras o nombre…"
                  value={productQuery}
                  onChange={e => {
                    setProductQuery(e.target.value)
                    setSelectedProduct(null)
                  }}
                  onKeyDown={handleSearchKeyDown}
                  onBlur={() => setTimeout(() => setShowSearchDrop(false), 150)}
                  onFocus={() => productResults.length > 0 && setShowSearchDrop(true)}
                  autoComplete="off"
                />
                {showSearchDrop && productResults.length > 0 && (
                  <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-64 overflow-auto rounded border border-border bg-bg-elevated shadow-lg">
                    {productResults.map((r, idx) => (
                      <button
                        key={r.id}
                        type="button"
                        className={`w-full px-3 py-2.5 text-left text-sm transition-colors ${
                          idx === searchHighlight
                            ? 'bg-primary-500/10 text-text-primary'
                            : 'text-text-secondary hover:bg-bg-base'
                        }`}
                        onMouseDown={e => { e.preventDefault(); handleSelectProduct(r) }}
                      >
                        <span className="font-medium text-text-primary">{r.name}</span>
                        <span className="ml-2 text-xs text-text-muted">{r.sku}</span>
                        {r.barcode && <span className="ml-2 text-xs text-text-muted">{r.barcode}</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Qty */}
              <input
                ref={qtyRef}
                className="input w-20 tabular-nums text-sm text-right"
                type="number"
                min="0.0001"
                step="any"
                placeholder="Cant."
                value={newItemQty}
                onChange={e => setNewItemQty(e.target.value)}
                onKeyDown={handleQtyKeyDown}
                disabled={!selectedProduct}
              />

              {/* Unit */}
              <select
                ref={unitRef}
                className="input w-32 text-sm"
                value={newItemUnit}
                onChange={e => handleUnitChange(e.target.value)}
                onKeyDown={handleUnitKeyDown}
                disabled={!selectedProduct || productUnits.length === 0}
              >
                <option value="">Unidad…</option>
                {productUnits.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.unit_catalog?.name ?? u.unit_catalog_id}
                  </option>
                ))}
              </select>

              {/* Price */}
              <div className="relative w-36">
                <input
                  className="input w-full tabular-nums text-sm text-right"
                  type="number"
                  min="0"
                  step="any"
                  placeholder="Precio ₲"
                  value={newItemPrice}
                  onChange={e => setNewItemPrice(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleAddItem() }}
                  disabled={!selectedProduct}
                />
                {loadingPrice && (
                  <Loader2 className="absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 animate-spin text-text-muted" />
                )}
              </div>

              {/* Add button */}
              <button
                type="button"
                className="btn-primary flex items-center gap-1.5 text-sm"
                onClick={handleAddItem}
                disabled={!selectedProduct || !newItemUnit || !newItemQty || !newItemPrice}
              >
                <Plus className="h-4 w-4" />
                Agregar
              </button>
            </div>

            {selectedProduct && (
              <p className="mt-1.5 text-xs text-text-muted">
                {selectedProduct.tax_included_in_price ? 'Precio incluye IVA' : 'Precio sin IVA'} ·
                IVA {selectedProduct.tax_rate}% ·
                Enter para agregar · Esc para limpiar
              </p>
            )}
          </div>

          {/* Cart */}
          <div className="flex-1 overflow-auto">
            {cartItems.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
                <p className="text-sm text-text-muted">El carrito está vacío</p>
                <p className="text-xs text-text-muted">Buscá un producto arriba para comenzar</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-bg-surface">
                  <tr className="border-b border-border-subtle">
                    <th className="px-4 py-2 text-left text-xs font-medium text-text-secondary">Producto</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-text-secondary">Unidad</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-text-secondary">Cantidad</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-text-secondary">Precio unit.</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-text-secondary">IVA</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-text-secondary">Descuento</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-text-secondary">Total</th>
                    <th className="px-4 py-2 w-10" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {cartItems.map(item => {
                    const qty = parseFloat(item.quantity) || 0
                    const price = parseFloat(item.unit_price) || 0
                    const rate = parseFloat(item.tax_rate) || 0
                    const disc = parseFloat(item.discount_amount) || 0
                    const gross = qty * price - disc
                    const lineTotal = item.tax_included ? gross : gross * (1 + rate / 100)
                    const isFocused = focusedItemId === item.localId

                    return (
                      <tr
                        key={item.localId}
                        className={`cursor-pointer transition-colors ${
                          isFocused ? 'bg-bg-elevated' : 'hover:bg-bg-surface'
                        }`}
                        onClick={() => setFocusedItemId(isFocused ? null : item.localId)}
                      >
                        <td className="px-4 py-3 text-text-primary">{item.product_name}</td>
                        <td className="px-4 py-3 text-text-secondary">{item.unit_name}</td>
                        <td className="px-4 py-3 text-right tabular-nums text-text-primary">
                          {editingQtyId === item.localId ? (
                            <input
                              className="input w-20 tabular-nums text-sm text-right"
                              type="number"
                              min="0.0001"
                              step="any"
                              value={editingQtyValue}
                              onChange={e => setEditingQtyValue(e.target.value)}
                              onBlur={() => {
                                const v = parseFloat(editingQtyValue)
                                if (!isNaN(v) && v > 0) handleUpdateItemQty(item.localId, String(v))
                                setEditingQtyId(null)
                              }}
                              onKeyDown={e => {
                                if (e.key === 'Enter') {
                                  const v = parseFloat(editingQtyValue)
                                  if (!isNaN(v) && v > 0) handleUpdateItemQty(item.localId, String(v))
                                  setEditingQtyId(null)
                                }
                                if (e.key === 'Escape') setEditingQtyId(null)
                              }}
                              autoFocus
                              onClick={e => e.stopPropagation()}
                            />
                          ) : (
                            <button
                              type="button"
                              className="rounded px-2 py-0.5 tabular-nums hover:bg-bg-elevated"
                              onClick={e => {
                                e.stopPropagation()
                                setEditingQtyId(item.localId)
                                setEditingQtyValue(item.quantity)
                              }}
                              title="Clic para editar"
                            >
                              {formatQuantity(item.quantity, item.unit_type)}
                            </button>
                          )}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-right text-text-primary">
                          {fmtPYG(price)}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-right text-text-secondary">
                          {item.tax_rate}%
                        </td>
                        <td className="px-4 py-3 tabular-nums text-right text-text-secondary">
                          {disc > 0 ? fmtPYG(disc) : '—'}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-right font-medium text-text-primary">
                          {fmtPYG(lineTotal)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            className="btn-ghost px-1 py-1 text-danger-500"
                            onClick={e => { e.stopPropagation(); handleRemoveItem(item.localId) }}
                            aria-label="Eliminar ítem"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Cart footer hint */}
          {cartItems.length > 0 && (
            <div className="border-t border-border-subtle bg-bg-surface px-4 py-1.5">
              <p className="text-xs text-text-muted">
                Clic en cantidad para editar · Clic en fila para seleccionar (F3 descuento) · F9 limpiar
              </p>
            </div>
          )}
        </div>

        {/* RIGHT: customer + summary + cobrar */}
        <div className="flex w-80 flex-shrink-0 flex-col border-l border-border-subtle bg-bg-surface">

          {/* Customer section */}
          <div className="border-b border-border-subtle p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                <User className="h-3.5 w-3.5" />
                Cliente
                {saleRequiresCustomer && <span className="text-danger-500">*</span>}
              </span>
              <button
                type="button"
                onClick={() => setShowCustomer(true)}
                className="text-xs text-primary-500 hover:text-primary-600 transition-colors"
              >
                F2 cambiar
              </button>
            </div>
            {customerName ? (
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-primary">{customerName}</span>
                <button
                  type="button"
                  onClick={() => { setCustomerId(null); setCustomerName(null) }}
                  className="btn-ghost p-0.5 text-text-muted"
                  title="Quitar cliente"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowCustomer(true)}
                className="text-sm text-text-muted hover:text-text-primary transition-colors"
              >
                {saleRequiresCustomer ? 'Requerido — clic para seleccionar' : 'Sin cliente'}
              </button>
            )}
          </div>

          {/* Summary */}
          <div className="flex-1 overflow-auto p-4 space-y-2">
            <div className="flex justify-between text-sm text-text-secondary">
              <span>Subtotal</span>
              <span className="tabular-nums">{fmtPYG(totals.itemsSubtotal)}</span>
            </div>
            <div className="flex justify-between text-sm text-text-secondary">
              <span>IVA</span>
              <span className="tabular-nums">{fmtPYG(totals.taxTotal)}</span>
            </div>
            {effectiveHDisc > 0 && (
              <div className="flex justify-between text-sm text-text-secondary">
                <button
                  type="button"
                  className="flex items-center gap-1 hover:text-text-primary transition-colors"
                  onClick={() => setShowDiscount(true)}
                  title="F3 — editar descuento"
                >
                  Descuento
                  {headerDiscount.type === 'percent' && ` (${headerDiscount.percent}%)`}
                </button>
                <span className="tabular-nums text-warning-500">-{fmtPYG(effectiveHDisc)}</span>
              </div>
            )}
            {effectiveHDisc === 0 && cartItems.length > 0 && (
              <button
                type="button"
                onClick={() => setShowDiscount(true)}
                className="flex items-center gap-1 text-xs text-text-muted hover:text-text-primary transition-colors"
              >
                <Minus className="h-3 w-3" />
                F3 agregar descuento
              </button>
            )}

            {cartItems.length > 0 && (
              <div className="border-t border-border-subtle pt-3 mt-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-text-primary">Total</span>
                  <span className="text-3xl font-bold tabular-nums text-text-primary">
                    {fmtPYG(finalTotal)}
                  </span>
                </div>
                <p className="text-xs text-text-muted mt-1 text-right">
                  {cartItems.length} ítem{cartItems.length !== 1 ? 's' : ''}
                </p>
              </div>
            )}

            {cartItems.length === 0 && (
              <div className="flex flex-1 items-center justify-center py-8">
                <p className="text-sm text-text-muted">Sin ítems</p>
              </div>
            )}
          </div>

          {/* Cobrar button */}
          <div className="border-t border-border-subtle p-4">
            {saleRequiresCustomer && !customerId && cartItems.length > 0 && (
              <p className="mb-2 text-xs text-danger-500">Se requiere cliente para esta venta</p>
            )}
            <button
              type="button"
              className="btn-accent w-full py-3 text-lg font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={() => setShowPayment(true)}
              disabled={!canCheckout}
            >
              Cobrar (F4)
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}

      {showCustomer && (
        <CustomerModal
          onSelect={handleSelectCustomer}
          onClose={() => setShowCustomer(false)}
        />
      )}

      {showDiscount && (
        <DiscountModal
          focusedItem={focusedCartItem}
          headerDiscount={headerDiscount}
          onSaveHeader={handleSaveHeaderDiscount}
          onSaveItem={handleSaveItemDiscount}
          onClose={() => setShowDiscount(false)}
        />
      )}

      {showPayment && (
        <PaymentModal
          total={finalTotal}
          confirming={paymentConfirming}
          confirmError={paymentError}
          pendingSaleCreated={!!pendingSaleId}
          onConfirm={handleConfirmSale}
          onClose={() => {
            if (!paymentConfirming) {
              setShowPayment(false)
              setPaymentError(null)
            }
          }}
        />
      )}

      {successSaleNumber && (
        <SuccessModal
          saleNumber={successSaleNumber}
          onClose={() => {
            setSuccessSaleNumber(null)
            handleClearCart()
            productSearchRef.current?.focus()
          }}
        />
      )}
    </div>
  )
}
