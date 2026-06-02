import { useEffect, useState } from 'react'
import { toast } from '../../../components/Toast'
import { parseApiError } from '../../../lib/parseApiError'
import {
  fetchLowStock,
  fetchProfitByProduct,
  fetchSalesByPeriod,
  fetchStockValue,
  fetchTopProducts,
  type LowStockOut,
  type ProfitByProductOut,
  type SalesByPeriodOut,
  type StockValueOut,
  type TopProductsOut,
} from '../api/reports'

function getMonthRange(): { dateFrom: string; dateTo: string } {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const dateFrom = new Date(year, month, 1).toISOString().split('T')[0]
  const dateTo = new Date(year, month + 1, 0).toISOString().split('T')[0]
  return { dateFrom, dateTo }
}

export interface DashboardState {
  salesByPeriod: SalesByPeriodOut | null
  topProducts: TopProductsOut | null
  profit: ProfitByProductOut | null
  lowStock: LowStockOut | null
  stockValue: StockValueOut | null
  loading: boolean
}

export function useDashboard(): DashboardState {
  const [state, setState] = useState<DashboardState>({
    salesByPeriod: null,
    topProducts: null,
    profit: null,
    lowStock: null,
    stockValue: null,
    loading: true,
  })

  useEffect(() => {
    const { dateFrom, dateTo } = getMonthRange()

    Promise.allSettled([
      fetchSalesByPeriod({ date_from: dateFrom, date_to: dateTo, group_by: 'day' }),
      fetchTopProducts({ date_from: dateFrom, date_to: dateTo, limit: 10 }),
      fetchProfitByProduct({ date_from: dateFrom, date_to: dateTo }),
      fetchLowStock(),
      fetchStockValue(),
    ]).then(([salesRes, topRes, profitRes, lowRes, valueRes]) => {
      const failed = [salesRes, topRes, profitRes, lowRes, valueRes].filter(
        (r) => r.status === 'rejected',
      )
      if (failed.length > 0) {
        const first = (failed[0] as PromiseRejectedResult).reason
        const parsed = parseApiError(first)
        toast.warning(
          parsed.isNetworkError
            ? 'Sin conexión con el servidor'
            : `No se pudieron cargar algunos datos del dashboard: ${parsed.message}`,
        )
      }
      setState({
        salesByPeriod: salesRes.status === 'fulfilled' ? (salesRes.value as SalesByPeriodOut) : null,
        topProducts: topRes.status === 'fulfilled' ? (topRes.value as TopProductsOut) : null,
        profit: profitRes.status === 'fulfilled' ? (profitRes.value as ProfitByProductOut) : null,
        lowStock: lowRes.status === 'fulfilled' ? (lowRes.value as LowStockOut) : null,
        stockValue: valueRes.status === 'fulfilled' ? (valueRes.value as StockValueOut) : null,
        loading: false,
      })
    })
  }, [])

  return state
}
