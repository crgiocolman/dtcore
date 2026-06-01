import { useCallback, useEffect, useState } from 'react'
import { fetchPurchases } from '../api/purchases'
import type { PurchaseListOut, PurchaseListParams, PurchaseStatus } from '../api/purchases'

const PAGE_SIZE = 20

interface UsePurchasesState {
  data: PurchaseListOut | null
  loading: boolean
  error: string | null
}

interface UsePurchasesResult extends UsePurchasesState {
  page: number
  status: PurchaseStatus | ''
  supplierId: string
  dateFrom: string
  dateTo: string
  setPage: (p: number) => void
  setStatus: (s: PurchaseStatus | '') => void
  setSupplierId: (id: string) => void
  setDateFrom: (d: string) => void
  setDateTo: (d: string) => void
  reload: () => void
}

export function usePurchases(): UsePurchasesResult {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<PurchaseStatus | ''>('')
  const [supplierId, setSupplierId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [state, setState] = useState<UsePurchasesState>({ data: null, loading: true, error: null })

  const load = useCallback((params: PurchaseListParams) => {
    setState((s) => ({ ...s, loading: true, error: null }))
    fetchPurchases(params)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Error al cargar compras'
        setState((s) => ({ ...s, loading: false, error: msg }))
      })
  }, [])

  useEffect(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      status: status || undefined,
      supplier_id: supplierId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
  }, [page, status, supplierId, dateFrom, dateTo, load])

  const handleSetStatus = useCallback((s: PurchaseStatus | '') => {
    setStatus(s)
    setPage(1)
  }, [])

  const handleSetSupplierId = useCallback((id: string) => {
    setSupplierId(id)
    setPage(1)
  }, [])

  const handleSetDateFrom = useCallback((d: string) => {
    setDateFrom(d)
    setPage(1)
  }, [])

  const handleSetDateTo = useCallback((d: string) => {
    setDateTo(d)
    setPage(1)
  }, [])

  const reload = useCallback(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      status: status || undefined,
      supplier_id: supplierId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
  }, [page, status, supplierId, dateFrom, dateTo, load])

  return {
    ...state,
    page,
    status,
    supplierId,
    dateFrom,
    dateTo,
    setPage,
    setStatus: handleSetStatus,
    setSupplierId: handleSetSupplierId,
    setDateFrom: handleSetDateFrom,
    setDateTo: handleSetDateTo,
    reload,
  }
}
