import { useEffect, useRef } from 'react'

interface UseKeyboardShortcutsOptions {
  /** If false, listeners are not attached. Default: true */
  enabled?: boolean
  /** If true, shortcuts do not fire when focus is inside an input or textarea. Default: false */
  ignoreInputs?: boolean
}

/**
 * Attaches global keydown shortcuts to window.
 * bindings: maps KeyboardEvent.key → handler (e.g. 'F1', 'Escape', 'Enter').
 * Handlers are called with e.preventDefault() before invocation.
 * Cleans up automatically on unmount.
 */
export function useKeyboardShortcuts(
  bindings: Record<string, () => void>,
  options: UseKeyboardShortcutsOptions = {},
): void {
  const { enabled = true, ignoreInputs = false } = options
  const bindingsRef = useRef(bindings)
  bindingsRef.current = bindings

  useEffect(() => {
    if (!enabled) return

    const handler = (e: KeyboardEvent) => {
      if (ignoreInputs) {
        const target = e.target as HTMLElement
        if (
          target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable
        ) {
          return
        }
      }
      const fn = bindingsRef.current[e.key]
      if (fn) {
        e.preventDefault()
        fn()
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [enabled, ignoreInputs])
}
