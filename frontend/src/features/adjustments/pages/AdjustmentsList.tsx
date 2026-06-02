import { ChevronLeft, ChevronRight, Plus, SlidersHorizontal } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchWarehouses, type WarehouseOut } from '../../admin/api/warehouses'
import type { AdjustmentReason, AdjustmentStatus } from '../api/adjustments'
import { useAdjustments } from '../hooks/useAdjustments'

const STATUS_LABELS: Record<AdjustmentStatus | '', string> = {
  '': 'Todos los estados',
  draft: 'Borrador',
  confirmed: 'Confirmado',
  cancelled: 'Cancelado',
}

const STATUS_BADGE: Record<AdjustmentStatus, string> = {
  draft: 'text-text-secondary',
  confirmed: 'text-success-500',
  cancelled: 'text-danger-500',
}

const REASON_LABELS: Record<AdjustmentReason, string> = {
  inventory_count: 'Conteo de inventario',
  damage: 'Daño / Deterioro',
  loss: 'Pérdida',
  expired: 'Vencimiento',
  correction: 'Corrección',
  other: 'Otro',
}

export function AdjustmentsList() {
  const navigate = useNavigate()
  const {
    data, loading, error,
    page, status, warehouseId, dateFrom, dateTo,
    setPage, setStatus, setWarehouseId, setDateFrom, setDateTo,
  } = useAdjustments()

  const items = data?.items ?? []
  const totalPages = data?.total_pages ?? 1
  const total = data?.total ?? 0

  const [warehouses, setWarehouses] = useState<WarehouseOut[]>([])
  const [warehouseNames, setWarehouseNames] = useState<Map<string, string>>(new Map())

  useEffect(() => {
    fetchWarehouses()
      .then((ws) => {
        setWarehouses(ws)
        setWarehouseNames(new Map(ws.map((w) => [w.id, w.name])))
      })
      .catch(() => { /* non-critical */ })
  }, [])

  const hasFilters = status || warehouseId || dateFrom || dateTo

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Ajustes de stock</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Ajustes manuales de inventario por conteo, daño, pérdida u otros motivos
          </p>
        </div>
        <button
          className="btn-primary flex flex-shrink-0 items-center gap-1.5"
          onClick={() => navigate('/ajustes/nuevo')}
        >
          <Plus className="h-4 w-4" />
          Nuevo ajuste
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          className="input w-auto min-w-[180px]"
          value={status}
          onChange={(e) => setStatus(e.target.value as AdjustmentStatus | '')}
        >
          {(Object.keys(STATUS_LABELS) as Array<AdjustmentStatus | ''>).map((key) => (
            <option key={key} value={key}>{STATUS_LABELS[key]}</option>
          ))}
        </select>

        <select
          className="input w-auto min-w-[200px]"
          value={warehouseId}
          onChange={(e) => setWarehouseId(e.target.value)}
        >
          <option value="">Todos los depósitos</option>
          {warehouses.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <input
            className="input w-auto"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            aria-label="Fecha desde"
          />
          <span className="text-sm text-text-muted">—</span>
          <input
            className="input w-auto"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            aria-label="Fecha hasta"
          />
        </div>
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
            <SlidersHorizontal className="h-12 w-12 text-text-muted" />
            <p className="text-sm text-text-muted">
              {hasFilters
                ? 'Sin resultados para los filtros aplicados'
                : 'No hay ajustes registrados'}
            </p>
            {!hasFilters && (
              <button
                className="btn-secondary flex items-center gap-1.5 text-sm"
                onClick={() => navigate('/ajustes/nuevo')}
              >
                <Plus className="h-4 w-4" />
                Registrar primer ajuste
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-bg-surface">
                  <tr className="border-b border-border-subtle">
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary"># Ajuste</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Depósito</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Fecha</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Motivo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {items.map((adj) => (
                    <tr
                      key={adj.id}
                      className="cursor-pointer transition-colors hover:bg-bg-elevated/50"
                      onClick={() => navigate(`/ajustes/${adj.id}`)}
                    >
                      <td className="px-4 py-3 tabular-nums text-text-primary">
                        {adj.adjustment_number}
                      </td>
                      <td className="px-4 py-3 text-text-primary">
                        {warehouseNames.get(adj.warehouse_id) ?? (
                          <span className="text-text-muted">{adj.warehouse_id.slice(0, 8)}…</span>
                        )}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-text-secondary">
                        {new Date(adj.adjustment_date + 'T00:00:00').toLocaleDateString('es-PY')}
                      </td>
                      <td className="px-4 py-3 text-text-secondary">
                        {REASON_LABELS[adj.reason]}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium ${STATUS_BADGE[adj.status]}`}>
                          {STATUS_LABELS[adj.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-border-subtle px-4 py-3">
              <p className="text-xs text-text-muted">
                {total} {total === 1 ? 'registro' : 'registros'}
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
