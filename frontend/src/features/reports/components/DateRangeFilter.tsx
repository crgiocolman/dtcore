import { useState } from 'react'

export interface DateRange {
  dateFrom: string
  dateTo: string
}

type Preset = 'this_month' | 'last_month' | 'last_30' | 'this_year'

const PRESETS: { id: Preset; label: string }[] = [
  { id: 'this_month', label: 'Este mes' },
  { id: 'last_month', label: 'Mes pasado' },
  { id: 'last_30', label: 'Últimos 30 días' },
  { id: 'this_year', label: 'Este año' },
]

function isoDate(d: Date): string {
  return d.toISOString().split('T')[0]
}

export function getPresetRange(preset: Preset): DateRange {
  const today = new Date()
  const y = today.getFullYear()
  const m = today.getMonth()
  switch (preset) {
    case 'this_month':
      return { dateFrom: isoDate(new Date(y, m, 1)), dateTo: isoDate(new Date(y, m + 1, 0)) }
    case 'last_month':
      return { dateFrom: isoDate(new Date(y, m - 1, 1)), dateTo: isoDate(new Date(y, m, 0)) }
    case 'last_30': {
      const from = new Date(today)
      from.setDate(from.getDate() - 29)
      return { dateFrom: isoDate(from), dateTo: isoDate(today) }
    }
    case 'this_year':
      return { dateFrom: isoDate(new Date(y, 0, 1)), dateTo: isoDate(new Date(y, 11, 31)) }
  }
}

export function thisMonthRange(): DateRange {
  return getPresetRange('this_month')
}

interface Props {
  value: DateRange
  onChange: (range: DateRange) => void
}

export function DateRangeFilter({ value, onChange }: Props) {
  const [activePreset, setActivePreset] = useState<Preset | null>('this_month')

  function applyPreset(preset: Preset) {
    setActivePreset(preset)
    onChange(getPresetRange(preset))
  }

  function handleDateChange(field: 'dateFrom' | 'dateTo', val: string) {
    setActivePreset(null)
    onChange({ ...value, [field]: val })
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex gap-1">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`btn-secondary text-xs py-1.5 px-3 ${
              activePreset === p.id ? 'ring-1 ring-primary-500 text-primary-500' : ''
            }`}
            onClick={() => applyPreset(p.id)}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <input
          type="date"
          className="input text-sm"
          value={value.dateFrom}
          onChange={(e) => handleDateChange('dateFrom', e.target.value)}
        />
        <span className="text-text-muted text-sm">—</span>
        <input
          type="date"
          className="input text-sm"
          value={value.dateTo}
          onChange={(e) => handleDateChange('dateTo', e.target.value)}
        />
      </div>
    </div>
  )
}
