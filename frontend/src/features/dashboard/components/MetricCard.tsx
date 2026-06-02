import type { ReactNode } from 'react'

interface MetricCardProps {
  label: string
  value: ReactNode
  subtitle?: string
  valueClassName?: string
}

export function MetricCard({ label, value, subtitle, valueClassName }: MetricCardProps) {
  return (
    <div className="card flex flex-col gap-2">
      <span className="text-sm text-text-secondary">{label}</span>
      <div className={`text-2xl font-bold tabular-nums text-text-primary ${valueClassName ?? ''}`}>
        {value}
      </div>
      {subtitle && <div className="text-xs text-text-muted">{subtitle}</div>}
    </div>
  )
}
