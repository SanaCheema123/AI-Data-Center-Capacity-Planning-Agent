import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'

const EVENT = 'capacity-app-error'

/**
 * Global, accessible mutation-error toast.
 * (`emitAppError` lives in `events/appError.ts` so this file stays
 * component-only for react-refresh.)
 */
export function GlobalFeedback() {
  const [message, setMessage] = useState<string | null>(null)
  const timer = useRef<number | null>(null)
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail
      setMessage(detail || 'The requested action failed.')
      if (timer.current) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setMessage(null), 7000)
    }
    window.addEventListener(EVENT, handler)
    return () => {
      window.removeEventListener(EVENT, handler)
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [])
  if (!message) return null
  return <div role="alert" aria-live="assertive" className="fixed bottom-5 right-5 z-[100] flex max-w-md items-start gap-3 rounded-2xl border border-rose-200 bg-white p-4 text-sm text-slate-700 shadow-2xl"><AlertTriangle className="mt-0.5 shrink-0 text-rose-500" size={18} aria-hidden="true" /><div className="flex-1"><strong className="block text-navy">Action failed</strong><span>{message}</span></div><button type="button" aria-label="Dismiss error" onClick={() => setMessage(null)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"><X size={16} /></button></div>
}
