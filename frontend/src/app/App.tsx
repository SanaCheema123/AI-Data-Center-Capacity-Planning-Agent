import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '../layouts/AppShell'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { LoadingState } from '../components/ui'

const LandingPage=lazy(()=>import('../pages/LandingPage').then(m=>({default:m.LandingPage})))
const LoginPage=lazy(()=>import('../pages/LoginPage').then(m=>({default:m.LoginPage})))
const RegisterPage=lazy(()=>import('../pages/RegisterPage').then(m=>({default:m.RegisterPage})))
const PublicInfoPage=lazy(()=>import('../pages/PublicInfoPage').then(m=>({default:m.PublicInfoPage})))
const DashboardPage=lazy(()=>import('../pages/DashboardPage').then(m=>({default:m.DashboardPage})))
const ResourceForecastPage=lazy(()=>import('../pages/ResourceForecastPage').then(m=>({default:m.ResourceForecastPage})))
const StorageNetworkPage=lazy(()=>import('../pages/StorageNetworkPage').then(m=>({default:m.StorageNetworkPage})))
const ScenariosPage=lazy(()=>import('../pages/ScenariosPage').then(m=>({default:m.ScenariosPage})))
const ProcurementPage=lazy(()=>import('../pages/ProcurementPage').then(m=>({default:m.ProcurementPage})))
const AlertsPage=lazy(()=>import('../pages/AlertsPage').then(m=>({default:m.AlertsPage})))
const ReportsPage=lazy(()=>import('../pages/ReportsPage').then(m=>({default:m.ReportsPage})))
const SettingsPage=lazy(()=>import('../pages/SettingsPage').then(m=>({default:m.SettingsPage})))
const NotFoundPage=lazy(()=>import('../pages/NotFoundPage').then(m=>({default:m.NotFoundPage})))

const loading=<div className="p-6"><LoadingState label="Loading page…"/></div>
export function App(){return <Suspense fallback={loading}><Routes><Route path="/" element={<LandingPage/>}/><Route path="/features" element={<PublicInfoPage section="features"/>}/><Route path="/solutions" element={<PublicInfoPage section="solutions"/>}/><Route path="/pricing" element={<PublicInfoPage section="pricing"/>}/><Route path="/contact" element={<PublicInfoPage section="contact"/>}/><Route path="/login" element={<LoginPage/>}/><Route path="/register" element={<RegisterPage/>}/><Route element={<ProtectedRoute><AppShell/></ProtectedRoute>}><Route path="/dashboard" element={<DashboardPage/>}/><Route path="/gpu-forecasting" element={<ResourceForecastPage resource="gpu"/>}/><Route path="/power-capacity" element={<ResourceForecastPage resource="power"/>}/><Route path="/storage-network" element={<StorageNetworkPage/>}/><Route path="/scenarios" element={<ScenariosPage/>}/><Route path="/procurement" element={<ProcurementPage/>}/><Route path="/alerts" element={<AlertsPage/>}/><Route path="/reports" element={<ReportsPage/>}/><Route path="/settings" element={<SettingsPage/>}/></Route><Route path="/home" element={<Navigate to="/dashboard" replace/>}/><Route path="*" element={<NotFoundPage/>}/></Routes></Suspense>}
