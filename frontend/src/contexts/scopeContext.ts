import { createContext } from 'react'

type ScopeValue={dataCenterId:number|null;setDataCenterId:(v:number|null)=>void}
export const ScopeContext=createContext<ScopeValue|undefined>(undefined)
