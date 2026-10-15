import type { ReactNode } from 'react'
import { useMemo, useState } from 'react'
import { ScopeContext } from './scopeContext'

export function ScopeProvider({children}:{children:ReactNode}){const [dataCenterId,setDataCenterId]=useState<number|null>(null);const value=useMemo(()=>({dataCenterId,setDataCenterId}),[dataCenterId]);return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>}
