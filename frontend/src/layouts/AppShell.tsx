import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from '../components/Sidebar'
import { TopHeader } from '../components/TopHeader'
import { ScopeProvider } from '../contexts/ScopeProvider'
export function AppShell(){const [mobileOpen,setMobileOpen]=useState(false);return <ScopeProvider><div className="min-h-screen bg-gradient-to-br from-olive-50 via-white to-lavender-50 text-navy"><Sidebar mobileOpen={mobileOpen} onClose={()=>setMobileOpen(false)}/><div className="lg:pl-[220px]"><TopHeader onMenu={()=>setMobileOpen(true)}/><main className="px-3 pb-8 pt-4 sm:px-4 md:px-6 xl:px-7"><Outlet/></main></div></div></ScopeProvider>}
