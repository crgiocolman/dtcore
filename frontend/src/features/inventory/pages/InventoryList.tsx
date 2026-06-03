import { AlertTriangle, ChevronDown, ChevronUp, ChevronsUpDown, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatCurrency } from '../../../lib/format'
import { flattenTree, fetchCategoryTree } from '../../products/api/categories'
import { type InventoryItem, type SortKey, fetchInventory } from '../api/inventory'

function formatQty(value: string): string {
  const n = parseFloat(value)
  if (isNaN(n)) return '—'
  return n % 1 === 0 ? String(n) : n.toFixed(4).replace(/\.?0+$/, '')
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`
}

type SortDir = 'asc' | 'desc'
interface Sort { key: SortKey; dir: SortDir }

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ChevronsUpDown className="w-3.5 h-3.5 opacity-40" />
  return dir === 'asc'
    ? <ChevronUp className="w-3.5 h-3.5 text-primary-500" />
    : <ChevronDown className="w-3.5 h-3.5 text-primary-500" />
}

function StockBadge({ item }: { item: InventoryItem }) {
  const qty = parseFloat(item.quantity_base)
  if (qty === 0) {
    return (
      <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-danger-500/15 text-danger-500">
        Sin stock
      </span>
    )
  }
  if (item.is_low_stock) {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium bg-warning-500/15 text-warning-500">
        <AlertTriangle className="w-3 h-3" />
        Stock bajo
      </span>
    )
  }
  return null
}

export function InventoryList() {
  const navigate = useNavigate()

  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [withStockOnly, setWithStockOnly] = useState(false)
  const [lowStockOnly, setLowStockOnly] = useState(false)
  const [sort, setSort] = useState<Sort>({ key: 'product_name', dir: 'asc' })
  const [page, setPage] = useState(1)
  const [data, setData] = useState<{ items: InventoryItem[]; total: number; total_pages: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Array<{ id: string; label: string }>>([])

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // Reset page when filters change
  useEffect(() => { setPage(1) }, [debouncedSearch, categoryId, withStockOnly, lowStockOnly, sort])

  // Load categories
  useEffect(() => {
    fetchCategoryTree()
      .then((tree) => setCategories(flattenTree(tree)))
      .catch(() => setCategories([]))
  }, [])

  // Load inventory
  useEffect(() => {
    setLoading(true)
    fetchInventory({
      search: debouncedSearch || undefined,
      category_id: categoryId || undefined,
      with_stock_only: withStockOnly || undefined,
      low_stock_only: lowStockOnly || undefined,
      sort_by: sort.key,
      sort_dir: sort.dir,
      page,
      page_size: 50,
    })
      .then((r) => setData({ items: r.items, total: r.total, total_pages: r.total_pages }))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [debouncedSearch, categoryId, withStockOnly, lowStockOnly, sort, page])

  function toggleSort(key: SortKey) {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: 'asc' }
    )
  }

  function th(label: string, key: SortKey) {
    return (
      <th
        className="py-2.5 pr-4 text-left font-medium text-text-secondary cursor-pointer select-none hover:text-text-primary transition-colors"
        onClick={() => toggleSort(key)}
      >
        <span className="inline-flex items-center gap-1">
          {label}
          <SortIcon active={sort.key === key} dir={sort.dir} />
        </span>
      </th>
    )
  }

  function thRight(label: string, key: SortKey) {
    return (
      <th
        className="py-2.5 pr-4 text-right font-medium text-text-secondary tabular-nums cursor-pointer select-none hover:text-text-primary transition-colors"
        onClick={() => toggleSort(key)}
      >
        <span className="inline-flex items-center justify-end gap-1 w-full">
          {label}
          <SortIcon active={sort.key === key} dir={sort.dir} />
        </span>
      </th>
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-text-primary">Inventario</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            className="input pl-9 text-sm w-full"
            placeholder="Buscar por nombre, SKU…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="input text-sm w-48"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
        >
          <option value="">Todas las categorías</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer select-none">
          <input
            type="checkbox"
            checked={withStockOnly}
            onChange={(e) => setWithStockOnly(e.target.checked)}
            className="accent-primary-500"
          />
          Solo con stock
        </label>

        <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer select-none">
          <input
            type="checkbox"
            checked={lowStockOnly}
            onChange={(e) => setLowStockOnly(e.target.checked)}
            className="accent-warning-500"
          />
          Solo stock bajo
        </label>
      </div>

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle">
              {th('SKU', 'product_sku')}
              {th('Nombre', 'product_name')}
              {th('Categoría', 'category_name')}
              <th className="py-2.5 pr-4 text-left font-medium text-text-secondary">Unidad</th>
              {thRight('Stock actual', 'quantity_base')}
              {thRight('Costo CPP (Gs)', 'avg_cost_base')}
              {thRight('Valor total (Gs)', 'total_value')}
              {thRight('Última act.', 'last_movement_at')}
              <th className="py-2.5 text-left font-medium text-text-secondary">Estado</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-border-subtle last:border-0">
                  {Array.from({ length: 9 }).map((_, j) => (
                    <td key={j} className="py-3 pr-4">
                      <div className="h-4 bg-bg-elevated animate-pulse rounded" />
                    </td>
                  ))}
                </tr>
              ))
            ) : !data || data.items.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-sm text-text-muted">
                  Sin resultados
                </td>
              </tr>
            ) : (
              data.items.map((item) => {
                const totalValue = parseFloat(item.quantity_base) * parseFloat(item.avg_cost_base)
                return (
                  <tr
                    key={item.product_id}
                    className="border-b border-border-subtle last:border-0 hover:bg-bg-elevated transition-colors cursor-pointer"
                    onClick={() => navigate(`/inventario/${item.product_id}`)}
                  >
                    <td className="py-2.5 pr-4 font-mono text-xs text-text-secondary">
                      {item.product_sku}
                    </td>
                    <td className="py-2.5 pr-4 text-text-primary font-medium">
                      {item.product_name}
                    </td>
                    <td className="py-2.5 pr-4 text-text-secondary">
                      {item.category_name ?? <span className="text-text-muted">—</span>}
                    </td>
                    <td className="py-2.5 pr-4 text-text-secondary">
                      {item.base_unit_symbol ?? '—'}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums font-medium text-text-primary">
                      {formatQty(item.quantity_base)}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-text-secondary">
                      {formatCurrency(item.avg_cost_base)}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-text-primary">
                      {formatCurrency(totalValue)}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-text-secondary text-xs">
                      {formatDateTime(item.last_movement_at)}
                    </td>
                    <td className="py-2.5">
                      <StockBadge item={item} />
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm text-text-secondary">
          <span>
            {data.total} producto{data.total !== 1 ? 's' : ''}
          </span>
          <div className="flex items-center gap-2">
            <button
              className="btn-secondary py-1 px-3 text-xs disabled:opacity-40"
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 1}
            >
              Anterior
            </button>
            <span className="tabular-nums">
              {page} / {data.total_pages}
            </span>
            <button
              className="btn-secondary py-1 px-3 text-xs disabled:opacity-40"
              onClick={() => setPage((p) => p + 1)}
              disabled={page === data.total_pages}
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
