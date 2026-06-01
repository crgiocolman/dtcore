import { type KeyboardEvent } from 'react'

/**
 * Atajos de teclado para el formulario de agregar ítems.
 * Enter confirma el ítem, Escape limpia el formulario.
 * Aplicar en inputs type="text" y type="number" (NO en <select>).
 * Reutilizable en POS (Fase 5).
 */
export function useItemFormShortcuts(onAdd: () => void, onClear: () => void) {
  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault()
      onAdd()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onClear()
    }
  }
  return { onKeyDown }
}
