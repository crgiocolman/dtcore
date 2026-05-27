import { ChevronLeft, ChevronRight, Package, Pencil, Plus, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  buildCategoryMap,
  fetchCategoryTree,
  flattenTree,
  type CategoryTreeNode,
} from '../api/categories'
import { fetchPriceHistory } from '../api/prices'
import { fetchUnits } from '../api/units'
import { useProducts } from '../hooks/useProducts'

function formatPYG(value: string): string {
  return (
    '₲ ' +
    new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(parseFloat(value))
  )
}

type PriceEntry = string | null | undefined // undefined = loading, null = not found, string = value

export function ProductsList() {
  const navigate = useNavigate()
  const { data, loading, error, page, search, categoryId, showInactive, setPage, setSearch, setCategoryId, setShowInactive } =
    useProducts()

  const items = data?.items ?? []
  const totalPages = data?.total_pages ?? 1
  const total = data?.total ?? 0

  // Category tree — loaded once
  const [categoryTree, setCategoryTree] = useState<CategoryTreeNode[]>([])
  useEffect(() => {
    fetchCategoryTree()
      .then(setCategoryTree)
      .catch(() => { /* non-critical */ })
  }, [])

  const categoryMap = useMemo(() => buildCategoryMap(categoryTree), [categoryTree])
  const flatCategories = useMemo(() => flattenTree(categoryTree), [categoryTree])

  // Price enrichment — runs after each product page load
  const [prices, setPrices] = useState<Record<string, PriceEntry>>({})
  useEffect(() => {
    if (items.length === 0) {
      setPrices({})
      return
    }
    // Mark all as loading
    setPrices(Object.fromEntries(items.map((p) => [p.id, undefined])))

    const today = new Date().toISOString().slice(0, 10)

    Promise.allSettled(
      items.map(async (product) => {
        const units = await fetchUnits(product.id)
        const defaultUnit = units.find((u) => u.is_default_sale_unit)
        if (!defaultUnit) return { id: product.id, price: null as string | null }
        const history = await fetchPriceHistory(product.id, defaultUnit.id, 'PYG')
        const current = history.find((h) => h.effective_from <= today)
        return { id: product.id, price: current?.price ?? null }
      }),
    ).then((results) => {
      const map: Record<string, string | null> = {}
      results.forEach((result, i) => {
        map[items[i].id] =
          result.status === 'fulfilled' ? result.value.price : null
      })
      setPrices(map)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  const hasFilters = search || categoryId || showInactive

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Productos</h1>
          <p className="mt-1 text-sm text-text-secondary">Catálogo de productos y unidades</p>
        </div>
        <button
          className="btn-primary flex flex-shrink-0 items-center gap-1.5"
          onClick={() => navigate('/productos/nuevo')}
        >
          <Plus className="h-4 w-4" />
          Nuevo producto
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            className="input pl-9"
            type="text"
            placeholder="Buscar por SKU, código de barras o nombre…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="input w-auto min-w-[180px]"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
        >
          <option value="">Todas las categorías</option>
          {flatCategories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.label}
            </option>
          ))}
        </select>

        <label className="flex cursor-pointer items-center gap-2 select-none">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-border accent-primary-500"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
          />
          <span className="text-sm text-text-secondary">Mostrar inactivos</span>
        </label>
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
            <Package className="h-12 w-12 text-text-muted" />
            <p className="text-sm text-text-muted">
              {hasFilters
                ? 'Sin resultados para los filtros aplicados'
                : 'No hay productos registrados'}
            </p>
            {!hasFilters && (
              <button
                className="btn-secondary flex items-center gap-1.5 text-sm"
                onClick={() => navigate('/productos/nuevo')}
              >
                <Plus className="h-4 w-4" />
                Agregar primer producto
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-bg-surface">
                  <tr className="border-b border-border-subtle">
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">SKU</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Nombre</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Categoría</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Unidad base</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary">Precio PYG</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Estado</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {items.map((p) => {
                    const priceEntry = prices[p.id]
                    return (
                      <tr
                        key={p.id}
                        className="cursor-pointer transition-colors hover:bg-bg-elevated/50"
                        onClick={() => navigate(`/productos/${p.id}`)}
                      >
                        <td className="px-4 py-3 font-mono text-xs text-text-secondary tabular-nums">
                          {p.sku}
                        </td>
                        <td className="px-4 py-3 text-text-primary">
                          <span className="font-medium">{p.name}</span>
                          {p.barcode && (
                            <div className="mt-0.5 font-mono text-xs text-text-muted">
                              {p.barcode}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-text-secondary">
                          {p.category_id ? (
                            categoryMap.get(p.category_id) ?? (
                              <span className="text-text-muted">—</span>
                            )
                          ) : (
                            <span className="text-text-muted">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-text-secondary">{p.base_unit}</td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {priceEntry === undefined ? (
                            <span className="text-text-muted text-xs">…</span>
                          ) : priceEntry === null ? (
                            <span className="text-text-muted">—</span>
                          ) : (
                            <span className="text-text-primary">{formatPYG(priceEntry)}</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`text-xs font-medium ${
                              p.is_active ? 'text-success-500' : 'text-text-muted'
                            }`}
                          >
                            {p.is_active ? 'Activo' : 'Inactivo'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <button
                            className="btn-ghost px-2 py-1"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/productos/${p.id}`)
                            }}
                            aria-label={`Editar ${p.name}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-border-subtle px-4 py-3">
              <p className="text-xs text-text-muted">
                {total} {total === 1 ? 'producto' : 'productos'}
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
