import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import type { ForecastRunPayload, NotificationSettings, ResourceType } from '../types/api'
export const useMe=()=>useQuery({queryKey:['me'],queryFn:api.me})
export const useSummary=(dc?:number|null)=>useQuery({queryKey:['summary',dc??'all'],queryFn:()=>api.summary(dc)})
export const useCenters=()=>useQuery({queryKey:['centers'],queryFn:api.centers})
export const useSources=()=>useQuery({queryKey:['sources'],queryFn:api.sources})
export const useCreateSource=()=>{const qc=useQueryClient();return useMutation({mutationFn:(payload:{name:string;source_type:string;configuration?:Record<string,unknown>})=>api.createSource(payload),onSuccess:()=>qc.invalidateQueries({queryKey:['sources']})})}
export const useSyncSource=()=>{const qc=useQueryClient();return useMutation({mutationFn:(id:number)=>api.syncSource(id),onSuccess:()=>{qc.invalidateQueries({queryKey:['sources']});qc.invalidateQueries({queryKey:['summary']});qc.invalidateQueries({queryKey:['forecast']});qc.invalidateQueries({queryKey:['centers']});qc.invalidateQueries({queryKey:['alerts']});qc.invalidateQueries({queryKey:['procurement']});qc.invalidateQueries({queryKey:['scenario-compare']});qc.invalidateQueries({queryKey:['recommendations']})}})}
export const useAlerts=(dc?:number|null)=>useQuery({queryKey:['alerts',dc??'all'],queryFn:()=>api.alerts(dc)})
export const useProcurement=(dc?:number|null)=>useQuery({queryKey:['procurement',dc??'all'],queryFn:()=>api.procurement(dc)})
export const useReports=(dc?:number|null)=>useQuery({queryKey:['reports',dc??'all'],queryFn:()=>api.reports(dc)})
export const useReportCatalog=()=>useQuery({queryKey:['report-catalog'],queryFn:api.reportCatalog})
export const useScenarios=(dc?:number|null)=>useQuery({queryKey:['scenarios',dc??'all'],queryFn:()=>api.scenarios(dc)})
export const useScenarioCompare=(dc?:number|null)=>useQuery({queryKey:['scenario-compare',dc??'all'],queryFn:()=>api.scenarioCompare(dc),retry:0})
export const useRecommendations=(dc?:number|null)=>useQuery({queryKey:['recommendations',dc??'all'],queryFn:()=>api.recommendations(dc),retry:0})
export const useSettings=()=>useQuery({queryKey:['settings'],queryFn:api.settings})
export const useNotifications=()=>useQuery({queryKey:['notifications'],queryFn:api.notifications})
export const useForecast=(r:ResourceType,dc?:number|null)=>useQuery({queryKey:['forecast',r,dc??'all'],queryFn:()=>api.forecast(r,dc),retry:0})
export const useRunForecast=(r:ResourceType)=>{const qc=useQueryClient();return useMutation({mutationFn:(p:ForecastRunPayload)=>api.runForecast(r,p),onSuccess:()=>{qc.invalidateQueries({queryKey:['forecast',r]});qc.invalidateQueries({queryKey:['recommendations']});qc.invalidateQueries({queryKey:['scenario-compare']});qc.invalidateQueries({queryKey:['summary']})}})}
export const useRunScenarios=()=>{const qc=useQueryClient();return useMutation({mutationFn:(dc?:number|null)=>api.runScenarios(dc),onSuccess:()=>{qc.invalidateQueries({queryKey:['scenario-compare']});qc.invalidateQueries({queryKey:['scenarios']})}})}
export const useGenerateProcurement=()=>{const qc=useQueryClient();return useMutation({mutationFn:(dc?:number|null)=>api.generateProcurement(dc),onSuccess:()=>{qc.invalidateQueries({queryKey:['procurement']});qc.invalidateQueries({queryKey:['summary']})}})}
export const useEvaluateAlerts=()=>{const qc=useQueryClient();return useMutation({mutationFn:(dc?:number|null)=>api.evaluateAlerts(dc),onSuccess:()=>{qc.invalidateQueries({queryKey:['alerts']});qc.invalidateQueries({queryKey:['summary']})}})}
export const useUpdateAlert=()=>{const qc=useQueryClient();return useMutation({mutationFn:({id,status}:{id:number;status:string})=>api.updateAlert(id,status),onSuccess:()=>{qc.invalidateQueries({queryKey:['alerts']});qc.invalidateQueries({queryKey:['summary']})}})}
export const useGenerateReport=()=>{const qc=useQueryClient();return useMutation({mutationFn:({type,dc}:{type:string;dc?:number|null})=>api.generateReport(type,dc),onSuccess:()=>qc.invalidateQueries({queryKey:['reports']})})}
export const useUpdateSetting=()=>{const qc=useQueryClient();return useMutation({mutationFn:({key,value}:{key:string;value:Record<string,unknown>})=>api.updateSetting(key,value),onSuccess:()=>qc.invalidateQueries({queryKey:['settings']})})}
export const useUpdateNotifications=()=>{const qc=useQueryClient();return useMutation({mutationFn:(payload:Partial<NotificationSettings>)=>api.updateNotifications(payload),onSuccess:()=>qc.invalidateQueries({queryKey:['notifications']})})}

export const useImportCsv=()=>{const qc=useQueryClient();return useMutation({mutationFn:(file:File)=>api.importCsv(file),onSuccess:()=>{qc.invalidateQueries({queryKey:['sources']});qc.invalidateQueries({queryKey:['summary']});qc.invalidateQueries({queryKey:['forecast']});qc.invalidateQueries({queryKey:['centers']});qc.invalidateQueries({queryKey:['alerts']});qc.invalidateQueries({queryKey:['procurement']});qc.invalidateQueries({queryKey:['scenario-compare']});qc.invalidateQueries({queryKey:['recommendations']})}})}

export const useCreateScenario=()=>{const qc=useQueryClient();return useMutation({mutationFn:api.createScenario,onSuccess:()=>{qc.invalidateQueries({queryKey:['scenarios']});qc.invalidateQueries({queryKey:['scenario-compare']})}})}
export const useUpdateProcurement=()=>{const qc=useQueryClient();return useMutation({mutationFn:({id,payload}:{id:number;payload:{status?:string;priority?:string}})=>api.updateProcurement(id,payload),onSuccess:()=>qc.invalidateQueries({queryKey:['procurement']})})}
