import { ApiError } from './api'

export interface ParsedApiError {
  code: string
  message: string
  details: Record<string, unknown>
  httpStatus: number
  isNetworkError: boolean
}

const NETWORK_ERROR: ParsedApiError = {
  code: 'network_error',
  message: 'Sin conexión con el servidor. Verificá que la red esté disponible.',
  details: {},
  httpStatus: 0,
  isNetworkError: true,
}

const TIMEOUT_ERROR: ParsedApiError = {
  code: 'timeout_error',
  message: 'El servidor está tardando en responder. Reintentá.',
  details: {},
  httpStatus: 0,
  isNetworkError: false,
}

export function parseApiError(err: unknown): ParsedApiError {
  // Request aborted by AbortController (timeout)
  if (err instanceof Error && err.name === 'AbortError') {
    return TIMEOUT_ERROR
  }

  // Network / connection error (fetch threw before getting a response)
  if (err instanceof TypeError) {
    return NETWORK_ERROR
  }

  const status = err instanceof ApiError ? err.status : 0
  const rawMessage = err instanceof Error ? err.message : String(err)

  // Try to parse the body as JSON
  let body: unknown
  try {
    body = JSON.parse(rawMessage)
  } catch {
    const message =
      status >= 500
        ? 'El servidor tuvo un problema. Reintentá en unos segundos.'
        : rawMessage || 'Error inesperado'
    return {
      code: 'unknown_error',
      message,
      details: {},
      httpStatus: status,
      isNetworkError: false,
    }
  }

  // Structured detail: { detail: { code, message, ...extras } }
  const detail = (body as Record<string, unknown>)?.detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const d = detail as Record<string, unknown>
    const { code, message, ...rest } = d
    return {
      code: typeof code === 'string' ? code : 'api_error',
      message: typeof message === 'string' ? message : rawMessage,
      details: rest,
      httpStatus: status,
      isNetworkError: false,
    }
  }

  // Plain string detail: { detail: "mensaje" }
  if (typeof detail === 'string') {
    return {
      code: 'api_error',
      message: detail,
      details: {},
      httpStatus: status,
      isNetworkError: false,
    }
  }

  return {
    code: 'unknown_error',
    message: 'Error inesperado',
    details: {},
    httpStatus: status,
    isNetworkError: false,
  }
}
