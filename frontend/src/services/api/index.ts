import { apiClient } from './client'
import type { Alert, CSVImportResult, DashboardSummary, DataCenter, DataSource, DataSourceSyncResult, ForecastResponse, ForecastRunPayload, NotificationSettings, ProcurementItem, Recommendation, ReportCatalogItem, ReportItem, ResourceType, Scenario, ScenarioComparison, Setting, TokenResponse, User } from '../../types/api'
const scope=(dataCenterId?:number|null)=>dataCenterId?{data_center_id:dataCenterId}:{}

async function downloadBlob(url:string, filename:string){
  const response=await apiClient.get<Blob>(url,{responseType:'blob'})
  const objectUrl=URL.createObjectURL(response.data)
  const link=document.createElement('a');link.href=objectUrl;link.download=filename;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(objectUrl)
}

export const api={
 login: async(email:string,password:string)=> (await apiClient.post<TokenResponse>('/auth/login',{email,password})).data,
 register: async(email:string,full_name:string,password:string)=> (await apiClient.post<User>('/auth/register',{email,full_name,password})).data,
 me: async()=> (await apiClient.get<User>('/auth/me')).data,
 summary: async(dataCenterId?:number|null)=> (await apiClient.get<DashboardSummary>('/dashboard/summary',{params:scope(dataCenterId)})).data,
 centers: async()=> (await apiClient.get<DataCenter[]>('/data-centers')).data,
 sources: async()=> (await apiClient.get<DataSource[]>('/data-sources')).data,
 createSource: async(payload:{name:string;source_type:string;configuration?:Record<string,unknown>})=> (await apiClient.post<DataSource>('/data-sources',payload)).data,
 syncSource: async(id:number)=> (await apiClient.post<DataSourceSyncResult>(`/data-sources/${id}/sync`)).data,
 importCsv: async(file:File)=>{const form=new FormData();form.append('file',file);return (await apiClient.post<CSVImportResult>('/data-sources/csv/import',form)).data},
 alerts: async(dataCenterId?:number|null)=> (await apiClient.get<Alert[]>('/alerts',{params:scope(dataCenterId)})).data,
 evaluateAlerts: async(dataCenterId?:number|null)=> (await apiClient.post<Alert[]>('/alerts/evaluate',{data_center_id:dataCenterId??null})).data,
 updateAlert: async(id:number,status:string)=> (await apiClient.patch<Alert>(`/alerts/${id}`,{status})).data,
 procurement: async(dataCenterId?:number|null)=> (await apiClient.get<ProcurementItem[]>('/procurement',{params:scope(dataCenterId)})).data,
 generateProcurement: async(dataCenterId?:number|null)=> (await apiClient.post<ProcurementItem[]>('/procurement/generate',{data_center_id:dataCenterId??null})).data,
 updateProcurement: async(id:number,payload:{status?:string;priority?:string})=> (await apiClient.patch<ProcurementItem>(`/procurement/${id}`,payload)).data,
 reports: async(dataCenterId?:number|null)=> (await apiClient.get<ReportItem[]>('/reports',{params:scope(dataCenterId)})).data,
 reportCatalog: async()=> (await apiClient.get<ReportCatalogItem[]>('/reports/catalog')).data,
 generateReport: async(reportType:string,dataCenterId?:number|null)=> (await apiClient.post<ReportItem>('/reports/generate',{report_type:reportType,data_center_id:dataCenterId??null})).data,
 downloadReport: async(id:number,kind:'pdf'|'csv',title='capacity-report')=>downloadBlob(`/reports/${id}/${kind}`,`${title.replace(/[^a-z0-9-_]+/gi,'-').toLowerCase()}.${kind}`),
 scenarios: async(dataCenterId?:number|null)=> (await apiClient.get<Scenario[]>('/scenarios',{params:scope(dataCenterId)})).data,
 scenarioCompare: async(dataCenterId?:number|null)=> (await apiClient.get<ScenarioComparison[]>('/scenarios/compare',{params:scope(dataCenterId)})).data,
 runScenarios: async(dataCenterId?:number|null)=> (await apiClient.post<ScenarioComparison[]>('/scenarios/run',null,{params:scope(dataCenterId)})).data,
 createScenario: async(payload:{name:string;description?:string;planning_horizon_months:number;data_center_id?:number|null;gpu_multiplier:number;power_multiplier:number;storage_multiplier:number;network_multiplier:number;budget_limit?:number|null})=> (await apiClient.post<Scenario>('/scenarios',payload)).data,
 recommendations: async(dataCenterId?:number|null)=> (await apiClient.get<Recommendation[]>('/ai/recommendations',{params:scope(dataCenterId)})).data,
 settings: async()=> (await apiClient.get<Setting[]>('/settings')).data,
 updateSetting: async(key:string,value:Record<string,unknown>)=> (await apiClient.patch<Setting>(`/settings/${key}`,{value})).data,
 notifications: async()=> (await apiClient.get<NotificationSettings>('/settings/notifications/me')).data,
 updateNotifications: async(payload:Partial<NotificationSettings>)=> (await apiClient.patch<NotificationSettings>('/settings/notifications/me',payload)).data,
 forecast: async(resource:ResourceType, dataCenterId?:number|null)=> (await apiClient.get<ForecastResponse>(`/${resource}/forecast`,{params:scope(dataCenterId)})).data,
 runForecast: async(resource:ResourceType,payload:ForecastRunPayload)=> (await apiClient.post<ForecastResponse>(`/${resource}/forecast/run`,payload)).data,
}
