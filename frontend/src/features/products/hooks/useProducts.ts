import { useCallback, useEffect, useRef, useState } from 'react'
import type { ProductListOut, ProductListParams } from '../api/products'
import { fetchProducts } from '../api/products'

const PAGE_SIZE = 20

interface UseProductsState {
  data: ProductListOut | null
  loading: boolean
  error: string | null
}

interface UseProductsResult extends UseProductsState {
  page: number
  search: string
  categoryId: string
  showDeleted: boolean
  setPage: (p: number) => void
  setSearch: (s: string) => void
  setCategoryId: (id: string) => void
  setShowDeleted: (v: boolean) => void
  reload: () => void
}

export function useProducts(): UseProductsResult {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [showDeleted, setShowDeleted] = useState(false)
  const [state, setState] = useState<UseProductsState>({ data: null, loading: true, error: null })

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback((params: ProductListParams) => {
    setState((s) => ({ ...s, loading: true, error: null }))
    fetchProducts(params)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Error al cargar productos'
        setState((s) => ({ ...s, loading: false, error: msg }))
      })
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      load({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        category_id: categoryId || undefined,
        include_deleted: showDeleted || undefined,
      })
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [page, search, categoryId, showDeleted, load])

  const handleSetSearch = useCallback((s: string) => {
    setSearch(s)
    setPage(1)
  }, [])

  const handleSetCategoryId = useCallback((id: string) => {
    setCategoryId(id)
    setPage(1)
  }, [])

  const handleSetShowDeleted = useCallback((v: boolean) => {
    setShowDeleted(v)
    setPage(1)
  }, [])

  const reload = useCallback(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      search: search || undefined,
      category_id: categoryId || undefined,
      include_deleted: showDeleted || undefined,
    })
  }, [page, search, categoryId, showDeleted, load])

  return {
    ...state,
    page,
    search,
    categoryId,
    showDeleted,
    setPage,
    setSearch: handleSetSearch,
    setCategoryId: handleSetCategoryId,
    setShowDeleted: handleSetShowDeleted,
    reload,
  }
}
