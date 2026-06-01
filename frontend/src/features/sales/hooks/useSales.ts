import { useCallback, useEffect, useState } from 'react'
import {
  fetchSales,
  type SaleListOut,
  type SaleListParams,
  type SaleStatus,
} from '../../pos/api/sales'

const PAGE_SIZE = 20

interface UseSalesState {
  data: SaleListOut | null
  loading: boolean
  error: string | null
}

interface UseSalesResult extends UseSalesState {
  page: number
  status: SaleStatus | ''
  customerId: string
  dateFrom: string
  dateTo: string
  setPage: (p: number) => void
  setStatus: (s: SaleStatus | '') => void
  setCustomerId: (id: string) => void
  setDateFrom: (d: string) => void
  setDateTo: (d: string) => void
  reload: () => void
}

export function useSales(): UseSalesResult {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<SaleStatus | ''>('')
  const [customerId, setCustomerId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [state, setState] = useState<UseSalesState>({ data: null, loading: true, error: null })

  const load = useCallback((params: SaleListParams) => {
    setState((s) => ({ ...s, loading: true, error: null }))
    fetchSales(params)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Error al cargar ventas'
        setState((s) => ({ ...s, loading: false, error: msg }))
      })
  }, [])

  useEffect(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      status: status || undefined,
      customer_id: customerId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
  }, [page, status, customerId, dateFrom, dateTo, load])

  const handleSetStatus = useCallback((s: SaleStatus | '') => { setStatus(s); setPage(1) }, [])
  const handleSetCustomerId = useCallback((id: string) => { setCustomerId(id); setPage(1) }, [])
  const handleSetDateFrom = useCallback((d: string) => { setDateFrom(d); setPage(1) }, [])
  const handleSetDateTo = useCallback((d: string) => { setDateTo(d); setPage(1) }, [])

  const reload = useCallback(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      status: status || undefined,
      customer_id: customerId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
  }, [page, status, customerId, dateFrom, dateTo, load])

  return {
    ...state,
    page,
    status,
    customerId,
    dateFrom,
    dateTo,
    setPage,
    setStatus: handleSetStatus,
    setCustomerId: handleSetCustomerId,
    setDateFrom: handleSetDateFrom,
    setDateTo: handleSetDateTo,
    reload,
  }
}
