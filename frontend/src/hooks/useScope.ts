import { useContext } from 'react'
import { ScopeContext } from '../contexts/scopeContext'

/** Access the selected data-center scope. Must be used within <ScopeProvider>. */
export function useScope(){
  const v=useContext(ScopeContext)
  if(!v) throw new Error('useScope must be used within ScopeProvider')
  return v
}
