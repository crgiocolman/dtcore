import { useEffect } from 'react'
import { CheckCircle2, Info, AlertTriangle, XCircle, X } from 'lucide-react'
import { create } from 'zustand'

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

type ToastVariant = 'success' | 'error' | 'warning' | 'info'

interface ToastItem {
  id: number
  message: string
  variant: ToastVariant
}

interface ToastStore {
  toasts: ToastItem[]
  add: (message: string, variant: ToastVariant) => void
  remove: (id: number) => void
}

let _nextId = 0

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  add: (message, variant) =>
    set((s) => ({
      toasts: [...s.toasts.slice(-4), { id: ++_nextId, message, variant }],
    })),
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const toast = {
  success: (message: string) => useToastStore.getState().add(message, 'success'),
  error: (message: string) => useToastStore.getState().add(message, 'error'),
  warning: (message: string) => useToastStore.getState().add(message, 'warning'),
  info: (message: string) => useToastStore.getState().add(message, 'info'),
}

// ---------------------------------------------------------------------------
// Single toast item
// ---------------------------------------------------------------------------

const VARIANTS = {
  success: {
    Icon: CheckCircle2,
    iconClass: 'text-success-500',
    autoDismiss: 5000,
  },
  error: {
    Icon: XCircle,
    iconClass: 'text-danger-500',
    autoDismiss: null, // error: no auto-dismiss
  },
  warning: {
    Icon: AlertTriangle,
    iconClass: 'text-warning-500',
    autoDismiss: 5000,
  },
  info: {
    Icon: Info,
    iconClass: 'text-primary-400',
    autoDismiss: 5000,
  },
}

function ToastItem({ item }: { item: ToastItem }) {
  const remove = useToastStore((s) => s.remove)
  const { Icon, iconClass, autoDismiss } = VARIANTS[item.variant]

  useEffect(() => {
    if (autoDismiss === null) return
    const t = setTimeout(() => remove(item.id), autoDismiss)
    return () => clearTimeout(t)
  }, [item.id, autoDismiss, remove])

  return (
    <div className="flex min-w-[280px] max-w-sm items-start gap-3 rounded-lg border border-border bg-bg-elevated px-4 py-3 shadow-lg">
      <Icon className={`mt-0.5 h-5 w-5 flex-shrink-0 ${iconClass}`} />
      <span className="flex-1 text-sm text-text-primary">{item.message}</span>
      <button
        onClick={() => remove(item.id)}
        className="ml-1 mt-0.5 text-text-muted hover:text-text-primary"
        aria-label="Cerrar"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Container — mount once in App.tsx
// ---------------------------------------------------------------------------

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <ToastItem key={t.id} item={t} />
      ))}
    </div>
  )
}
