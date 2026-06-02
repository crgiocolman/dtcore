import { Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '../../../lib/format'
import { fetchSalesByPeriod, type SalesByPeriodOut } from '../api/reports'
import { csvFilename, downloadCSV } from '../lib/csv'
import type { DateRange } from './DateRangeFilter'

const PRIMARY_500 = '#3B82F6'
const CHART_GRID = '#1F2C4A'
const CHART_TEXT = '#94A3B8'
const TOOLTIP_STYLE = {
  backgroundColor: '#111A2E',
  border: '1px solid #1F2C4A',
  borderRadius: 6,
  color: '#E8EEF7',
}

type GroupBy = 'day' | 'week' | 'month'

const GROUP_BY_LABELS: Record<GroupBy, string> = { day: 'Día', week: 'Semana', month: 'Mes' }

function formatPeriodLabel(period: string, groupBy: GroupBy): string {
  const parts = period.split('-')
  if (groupBy === 'month') return `${parts[1]}/${parts[0]}`
  return `${parts[2]}/${parts[1]}`
}

function formatYAxis(value: number): string {
  if (value === 0) return '0'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`
  return String(value)
}

export function SalesReport({ dateRange }: { dateRange: DateRange }) {
  const [data, setData] = useState<SalesByPeriodOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [groupBy, setGroupBy] = useState<GroupBy>('day')

  useEffect(() => {
    setLoading(true)
    setData(null)
    fetchSalesByPeriod({
      date_from: dateRange.dateFrom,
      date_to: dateRange.dateTo,
      group_by: groupBy,
    })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [dateRange.dateFrom, dateRange.dateTo, groupBy])

  const barData =
    data?.items.map((i) => ({
      date: formatPeriodLabel(i.period, groupBy),
      total: parseFloat(i.total_pyg),
    })) ?? []

  const totalVentas = data?.items.reduce((s, i) => s + parseFloat(i.total_pyg), 0) ?? 0
  const totalOps = data?.items.reduce((s, i) => s + i.sale_count, 0) ?? 0

  function handleExport() {
    if (!data) return
    downloadCSV(
      data.items.map((i) => ({
        Período: i.period,
        'Cant. ventas': i.sale_count,
        'Total (Gs)': formatCurrency(i.total_pyg),
      })),
      csvFilename('ventas_por_periodo', dateRange.dateFrom, dateRange.dateTo)
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1">
          {(Object.keys(GROUP_BY_LABELS) as GroupBy[]).map((g) => (
            <button
              key={g}
              type="button"
              className={`btn-secondary text-xs py-1.5 px-3 ${
                groupBy === g ? 'ring-1 ring-primary-500 text-primary-500' : ''
              }`}
              onClick={() => setGroupBy(g)}
            >
              {GROUP_BY_LABELS[g]}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="btn-secondary text-sm flex items-center gap-1.5"
          onClick={handleExport}
          disabled={!data || data.items.length === 0}
        >
          <Download className="w-4 h-4" />
          Exportar CSV
        </button>
      </div>

      {loading ? (
        <div className="card h-64 animate-pulse bg-bg-elevated" />
      ) : !data || barData.length === 0 ? (
        <div className="card py-12 text-center text-sm text-text-muted">
          Sin ventas en el período seleccionado
        </div>
      ) : (
        <div className="card">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={barData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={CHART_GRID} />
              <XAxis
                dataKey="date"
                tick={{ fill: CHART_TEXT, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={formatYAxis}
                tick={{ fill: CHART_TEXT, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={48}
              />
              <Tooltip
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={(value: any) => [`Gs ${formatCurrency(Number(value))}`, 'Ventas']}
                contentStyle={TOOLTIP_STYLE}
                labelStyle={{ color: CHART_TEXT }}
                itemStyle={{ color: '#E8EEF7' }}
                cursor={{ fill: 'rgba(59,130,246,0.08)' }}
              />
              <Bar dataKey="total" fill={PRIMARY_500} radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="text-left py-2.5 pr-4 font-medium text-text-secondary">Período</th>
                <th className="text-right py-2.5 pr-4 font-medium text-text-secondary tabular-nums">
                  Operaciones
                </th>
                <th className="text-right py-2.5 font-medium text-text-secondary tabular-nums">
                  Total (Gs)
                </th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr
                  key={item.period}
                  className="border-b border-border-subtle last:border-0 hover:bg-bg-elevated transition-colors"
                >
                  <td className="py-2.5 pr-4 text-text-primary">{item.period}</td>
                  <td className="py-2.5 pr-4 text-right tabular-nums text-text-primary">
                    {item.sale_count}
                  </td>
                  <td className="py-2.5 text-right tabular-nums text-text-primary">
                    Gs {formatCurrency(item.total_pyg)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-border">
                <td className="py-2.5 pr-4 font-semibold text-text-primary">Total</td>
                <td className="py-2.5 pr-4 text-right tabular-nums font-semibold text-text-primary">
                  {totalOps}
                </td>
                <td className="py-2.5 text-right tabular-nums font-semibold text-text-primary">
                  Gs {formatCurrency(totalVentas)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}
