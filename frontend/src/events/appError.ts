import { apiErrorMessage } from '../services/api/client'

const EVENT = 'capacity-app-error'

/** Dispatch a global, accessible error notification consumed by <GlobalFeedback />. */
export function emitAppError(error: unknown, fallback?: string) {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: apiErrorMessage(error, fallback) }))
}
