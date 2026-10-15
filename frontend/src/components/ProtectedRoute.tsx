import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useMe } from '../hooks/useApi'
import { LoadingState } from './ui'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation()
  const token = localStorage.getItem('access_token')
  const me = useMe()
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (me.isLoading) return <div className="grid min-h-screen place-items-center bg-olive-50"><LoadingState label="Verifying session…" /></div>
  if (me.isError) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <>{children}</>
}
