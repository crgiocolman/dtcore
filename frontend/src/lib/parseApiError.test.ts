import { describe, it, expect, vi } from 'vitest'

// Mock api module before importing parseApiError
vi.mock('./api', () => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.name = 'ApiError'
      this.status = status
    }
  },
}))

import { parseApiError } from './parseApiError'
import { ApiError } from './api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeApiError(status: number, body: unknown): ApiError {
  return new ApiError(status, JSON.stringify(body))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('parseApiError', () => {
  it('extrae body estructurado { detail: { code, message, ...extras } }', () => {
    const err = makeApiError(422, {
      detail: {
        code: 'insufficient_stock',
        message: 'Stock insuficiente para Arroz: disponible 2, solicitado 5',
        product_name: 'Arroz',
        available: '2',
        requested: '5',
      },
    })
    const result = parseApiError(err)
    expect(result.code).toBe('insufficient_stock')
    expect(result.message).toContain('Stock insuficiente')
    expect(result.details.product_name).toBe('Arroz')
    expect(result.details.available).toBe('2')
    expect(result.httpStatus).toBe(422)
    expect(result.isNetworkError).toBe(false)
  })

  it('extrae conflicting_product_id en error 409 de restore', () => {
    const err = makeApiError(409, {
      detail: {
        code: 'sku_conflict_on_restore',
        message: "El SKU 'ABC' ya está en uso",
        conflicting_product_id: 'uuid-123',
        conflicting_value: 'ABC',
      },
    })
    const result = parseApiError(err)
    expect(result.code).toBe('sku_conflict_on_restore')
    expect(result.details.conflicting_product_id).toBe('uuid-123')
    expect(result.httpStatus).toBe(409)
  })

  it('maneja detail como string (fallback)', () => {
    const err = makeApiError(404, { detail: 'Producto no encontrado' })
    const result = parseApiError(err)
    expect(result.code).toBe('api_error')
    expect(result.message).toBe('Producto no encontrado')
    expect(result.httpStatus).toBe(404)
    expect(result.isNetworkError).toBe(false)
  })

  it('detecta error de red (TypeError sin respuesta)', () => {
    const err = new TypeError('Failed to fetch')
    const result = parseApiError(err)
    expect(result.isNetworkError).toBe(true)
    expect(result.message).toBe('Sin conexión con el servidor. Verificá que la red esté disponible.')
    expect(result.httpStatus).toBe(0)
  })

  it('detecta timeout (AbortError)', () => {
    const err = new DOMException('The user aborted a request.', 'AbortError')
    const result = parseApiError(err)
    expect(result.code).toBe('timeout_error')
    expect(result.message).toBe('El servidor está tardando en responder. Reintentá.')
    expect(result.isNetworkError).toBe(false)
    expect(result.httpStatus).toBe(0)
  })

  it('maneja body JSON malformado con 5xx → mensaje amigable', () => {
    const err = new ApiError(500, 'Internal Server Error (not JSON)')
    const result = parseApiError(err)
    expect(result.code).toBe('unknown_error')
    expect(result.message).toBe('El servidor tuvo un problema. Reintentá en unos segundos.')
    expect(result.isNetworkError).toBe(false)
  })

  it('maneja body JSON malformado con 4xx → mensaje original', () => {
    const err = new ApiError(400, 'Bad Request')
    const result = parseApiError(err)
    expect(result.code).toBe('unknown_error')
    expect(result.message).toBe('Bad Request')
    expect(result.isNetworkError).toBe(false)
  })

  it('maneja body parseable pero sin detail', () => {
    const err = makeApiError(400, { error: 'something weird' })
    const result = parseApiError(err)
    expect(result.code).toBe('unknown_error')
  })

  it('maneja HTTPException normalizado (code=http_error)', () => {
    const err = makeApiError(401, { detail: { code: 'http_error', message: 'Token inválido o expirado' } })
    const result = parseApiError(err)
    expect(result.code).toBe('http_error')
    expect(result.message).toBe('Token inválido o expirado')
  })
})
