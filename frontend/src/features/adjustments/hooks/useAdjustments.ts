import { useCallback, useEffect, useState } from 'react'
import { fetchAdjustments } from '../api/adjustments'
import type { AdjustmentListOut, AdjustmentListParams, AdjustmentStatus } from '../api/adjustments'

const PAGE_SIZE = 20

interface UseAdjustmentsState {
  data: AdjustmentListOut | null
  loading: boolean
  error: string | null
}

interface UseAdjustmentsResult extends UseAdjustmentsState {
  page: number
  status: AdjustmentStatus | ''
  warehouseId: string
  dateFrom: string
  dateTo: string
  setPage: (p: number) => void
  setStatus: (s: AdjustmentStatus | '') => void
  setWarehouseId: (id: string) => void
  setDateFrom: (d: string) => void
  setDateTo: (d: string) => void
  reload: () => void
}

export function useAdjustments(): UseAdjustmentsResult {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<AdjustmentStatus | ''>('')
  const [warehouseId, setWarehouseId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [state, setState] = useState<UseAdjustmentsState>({ data: null, loading: true, error: null })

  const load = useCallback((params: AdjustmentListParams) => {
    setState((s) => ({ ...s, loading: true, error: null }))
    fetchAdjustments(params)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Error al cargar ajustes'
        setState((s) => ({ ...s, loading: false, error: msg }))
      })
  }, [])

  useEffect(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      status: status || undefined,
      warehouse_id: warehouseId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
  }, [page, status, warehouseId, dateFrom, dateTo, load])

  const handleSetStatus = useCallback((s: AdjustmentStatus | '') => { setStatus(s); setPage(1) }, [])
  const handleSetWarehouseId = useCallback((id: string) => { setWarehouseId(id); setPage(1) }, [])
  const handleSetDateFrom = useCallback((d: string) => { setDateFrom(d); setPage(1) }, [])
  const handleSetDateTo = useCallback((d: string) => { setDateTo(d); setPage(1) }, [])

  const reload = useCallback(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      status: status || undefined,
      warehouse_id: warehouseId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
  }, [page, status, warehouseId, dateFrom, dateTo, load])

  return {
    ...state,
    page,
    status,
    warehouseId,
    dateFrom,
    dateTo,
    setPage,
    setStatus: handleSetStatus,
    setWarehouseId: handleSetWarehouseId,
    setDateFrom: handleSetDateFrom,
    setDateTo: handleSetDateTo,
    reload,
  }
}
