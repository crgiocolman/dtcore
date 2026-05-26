import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, X, XCircle } from 'lucide-react'
import { fetchAllSettings, updateSetting } from '../api/settings'
import type { SettingOut } from '../api/settings'

// Keys to skip — not editable from this UI yet
const HIDDEN_KEYS = new Set(['default_warehouse_id'])

const SECTIONS: { title: string; keys: string[] }[] = [
  { title: 'Negocio', keys: ['business_name', 'business_document'] },
  { title: 'Moneda', keys: ['default_currency_code'] },
  { title: 'Ventas', keys: ['sale_requires_customer', 'default_tax_rate'] },
  { title: 'Stock', keys: ['allow_negative_stock', 'low_stock_default_threshold'] },
]

// ---- Helpers ----

type DraftMap = Record<string, string | boolean>

function initDraft(s: SettingOut): string | boolean {
  if (s.value_type === 'bool') return s.value === true
  if (s.value_type === 'json') return JSON.stringify(s.value, null, 2)
  return s.value == null ? '' : String(s.value)
}

function toApiValue(draft: string | boolean, valueType: SettingOut['value_type']): unknown {
  if (valueType === 'bool') return draft as boolean
  if (valueType === 'int') {
    const n = parseInt(draft as string, 10)
    if (isNaN(n)) throw new Error('Valor entero inválido')
    return n
  }
  if (valueType === 'decimal') {
    const n = parseFloat(draft as string)
    if (isNaN(n)) throw new Error('Valor decimal inválido')
    return n
  }
  if (valueType === 'json') {
    try {
      return JSON.parse(draft as string)
    } catch {
      throw new Error('JSON inválido')
    }
  }
  return draft as string
}

function keyToLabel(key: string): string {
  return key
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

// ---- Toast ----

interface ToastState {
  message: string
  type: 'success' | 'error'
  id: number
}

function Toast({ toast, onClose }: { toast: ToastState; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500)
    return () => clearTimeout(t)
  }, [toast.id, onClose])

  const Icon = toast.type === 'success' ? CheckCircle2 : XCircle
  const iconColor = toast.type === 'success' ? 'text-success-500' : 'text-danger-500'

  return (
    <div className="fixed bottom-6 right-6 z-50 flex min-w-[280px] items-center gap-3 rounded-lg border border-border bg-bg-elevated px-4 py-3 shadow-lg">
      <Icon className={`h-5 w-5 flex-shrink-0 ${iconColor}`} />
      <span className="flex-1 text-sm text-text-primary">{toast.message}</span>
      <button onClick={onClose} className="text-text-muted hover:text-text-primary">
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

// ---- SettingField ----

interface FieldProps {
  setting: SettingOut
  draft: string | boolean
  onChange: (key: string, val: string | boolean) => void
}

function SettingField({ setting, draft, onChange }: FieldProps) {
  const { key, value_type, description } = setting
  const label = keyToLabel(key)

  if (value_type === 'bool') {
    return (
      <div className="flex items-start gap-3">
        <input
          id={key}
          type="checkbox"
          checked={draft as boolean}
          onChange={(e) => onChange(key, e.target.checked)}
          className="mt-0.5 h-4 w-4 cursor-pointer rounded border-border bg-bg-input accent-primary-500 focus:ring-2 focus:ring-border-focus focus:ring-offset-2 focus:ring-offset-bg-surface"
        />
        <div>
          <label htmlFor={key} className="cursor-pointer text-sm font-medium text-text-primary">
            {label}
          </label>
          {description && <p className="mt-0.5 text-xs text-text-muted">{description}</p>}
        </div>
      </div>
    )
  }

  if (value_type === 'json') {
    return (
      <div>
        <label className="label" htmlFor={key}>
          {label}
        </label>
        {description && <p className="mb-1.5 text-xs text-text-muted">{description}</p>}
        <textarea
          id={key}
          className="input font-mono text-xs"
          rows={4}
          value={draft as string}
          onChange={(e) => onChange(key, e.target.value)}
        />
      </div>
    )
  }

  return (
    <div>
      <label className="label" htmlFor={key}>
        {label}
      </label>
      {description && <p className="mb-1.5 text-xs text-text-muted">{description}</p>}
      <input
        id={key}
        className="input"
        type={value_type === 'int' || value_type === 'decimal' ? 'number' : 'text'}
        step={value_type === 'decimal' ? 'any' : undefined}
        value={draft as string}
        onChange={(e) => onChange(key, e.target.value)}
      />
    </div>
  )
}

// ---- SectionCard ----

interface SectionCardProps {
  title: string
  sectionKeys: string[]
  settingsMap: Record<string, SettingOut>
  drafts: DraftMap
  onDraftChange: (key: string, val: string | boolean) => void
  onSave: (keys: string[]) => Promise<void>
  saving: boolean
}

function SectionCard({
  title,
  sectionKeys,
  settingsMap,
  drafts,
  onDraftChange,
  onSave,
  saving,
}: SectionCardProps) {
  const keys = sectionKeys.filter((k) => k in settingsMap && !HIDDEN_KEYS.has(k))
  if (keys.length === 0) return null

  return (
    <div className="card space-y-4">
      <h2 className="border-b border-border-subtle pb-3 text-lg font-semibold text-text-primary">
        {title}
      </h2>
      <div className="space-y-4">
        {keys.map((k) => (
          <SettingField
            key={k}
            setting={settingsMap[k]}
            draft={drafts[k]}
            onChange={onDraftChange}
          />
        ))}
      </div>
      <div className="flex justify-end pt-2">
        <button className="btn-primary" disabled={saving} onClick={() => onSave(keys)}>
          {saving ? 'Guardando…' : 'Guardar'}
        </button>
      </div>
    </div>
  )
}

// ---- Page ----

export function Settings() {
  const [settingsMap, setSettingsMap] = useState<Record<string, SettingOut>>({})
  const [drafts, setDrafts] = useState<DraftMap>({})
  const [loading, setLoading] = useState(true)
  const [savingSections, setSavingSections] = useState<Record<string, boolean>>({})
  const [toast, setToast] = useState<ToastState | null>(null)

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type, id: Date.now() })
  }, [])

  useEffect(() => {
    fetchAllSettings()
      .then((list) => {
        const map: Record<string, SettingOut> = {}
        const draftInit: DraftMap = {}
        for (const s of list) {
          map[s.key] = s
          draftInit[s.key] = initDraft(s)
        }
        setSettingsMap(map)
        setDrafts(draftInit)
      })
      .catch(() => showToast('No se pudo cargar la configuración', 'error'))
      .finally(() => setLoading(false))
  }, [showToast])

  const handleDraftChange = useCallback((key: string, val: string | boolean) => {
    setDrafts((prev) => ({ ...prev, [key]: val }))
  }, [])

  const handleSave = useCallback(
    async (keys: string[]) => {
      const sectionId = keys.join(',')
      setSavingSections((prev) => ({ ...prev, [sectionId]: true }))
      try {
        for (const key of keys) {
          const setting = settingsMap[key]
          const apiValue = toApiValue(drafts[key], setting.value_type)
          const updated = await updateSetting(key, apiValue)
          setSettingsMap((prev) => ({ ...prev, [key]: updated }))
        }
        showToast('Configuración guardada', 'success')
      } catch (err) {
        let detail = err instanceof Error ? err.message : 'Error al guardar'
        try {
          const parsed = JSON.parse(detail)
          if (parsed?.detail) detail = parsed.detail
        } catch {
          // keep original message
        }
        showToast(detail, 'error')
      } finally {
        setSavingSections((prev) => ({ ...prev, [sectionId]: false }))
      }
    },
    [settingsMap, drafts, showToast],
  )

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-text-muted">Cargando configuración…</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Configuración</h1>
        <p className="mt-1 text-sm text-text-secondary">Ajustes generales del sistema</p>
      </div>

      {SECTIONS.map((section) => {
        const sectionId = section.keys.join(',')
        return (
          <SectionCard
            key={section.title}
            title={section.title}
            sectionKeys={section.keys}
            settingsMap={settingsMap}
            drafts={drafts}
            onDraftChange={handleDraftChange}
            onSave={handleSave}
            saving={!!savingSections[sectionId]}
          />
        )
      })}

      {toast && <Toast toast={toast} onClose={() => setToast(null)} />}
    </div>
  )
}
