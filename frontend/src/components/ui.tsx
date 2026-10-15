import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'
type BadgeTone = 'blue' | 'pink' | 'green' | 'amber' | 'red' | 'purple' | 'slate'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  variant?: ButtonVariant
}

export function Button({ children, variant = 'primary', className = '', type, ...props }: ButtonProps) {
  const styles =
    variant === 'secondary'
      ? 'app-button-secondary border text-navy'
      : variant === 'ghost'
        ? 'app-button-ghost bg-transparent text-navy'
        : 'bg-gradient-to-r from-olive-600 via-olive-500 to-lavender-500 text-white shadow-md hover:brightness-95'
  return (
    <button
      type={type ?? 'button'}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function Badge({ children, tone = 'blue' }: { children: ReactNode; tone?: BadgeTone }) {
  const styles: Record<BadgeTone, string> = {
    blue: 'bg-olive-50 text-olive-700',
    pink: 'bg-lavender-50 text-lavender-700',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    red: 'bg-rose-50 text-rose-700',
    purple: 'bg-lavender-50 text-lavender-700',
    slate: 'bg-slate-100 text-slate-600',
  }
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${styles[tone]}`}>{children}</span>
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`app-card rounded-2xl border shadow-[0_7px_24px_rgba(63,74,32,.08)] ${className}`}>{children}</section>
}

export function SectionTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return <div className="mb-4 flex items-start justify-between gap-4"><div><h2 className="text-[17px] font-extrabold text-navy">{title}</h2>{subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}</div>{action}</div>
}

export function LoadingState({ label = 'Loading data…' }: { label?: string }) {
  return <div role="status" aria-live="polite" className="flex min-h-48 items-center justify-center gap-3 text-sm text-slate-500"><Loader2 className="animate-spin" size={20} aria-hidden="true" />{label}</div>
}

export function ErrorState({ message = 'Unable to load this data.' }: { message?: string }) {
  return <div role="alert" className="flex min-h-40 flex-col items-center justify-center gap-2 rounded-xl border border-rose-100 bg-rose-50/60 p-5 text-center"><AlertTriangle className="text-rose-500" aria-hidden="true" /><strong className="text-navy">Data unavailable</strong><p className="text-sm text-slate-600">{message}</p></div>
}

export function EmptyState({ title = 'No data yet', description = 'Run a forecast or connect a data source to populate this section.' }: { title?: string; description?: string }) {
  return <div className="grid min-h-36 place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50/40 p-5 text-center"><div><div className="font-bold text-navy">{title}</div><p className="mt-1 text-sm text-slate-500">{description}</p></div></div>
}
