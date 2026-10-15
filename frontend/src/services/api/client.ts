import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { TokenResponse } from '../../types/api'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
export const apiClient = axios.create({baseURL, timeout: 20000})

apiClient.interceptors.request.use((config)=>{
  const token=localStorage.getItem('access_token')
  if(token) config.headers.Authorization=`Bearer ${token}`
  return config
})

type RetryConfig = InternalAxiosRequestConfig & {_retry?:boolean}
let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refreshToken=localStorage.getItem('refresh_token')
  if(!refreshToken) throw new Error('No refresh token')
  if(!refreshPromise){
    refreshPromise=axios.post<TokenResponse>(`${baseURL}/auth/refresh`,{refresh_token:refreshToken})
      .then(({data})=>{
        localStorage.setItem('access_token',data.access_token)
        localStorage.setItem('refresh_token',data.refresh_token)
        return data.access_token
      })
      .finally(()=>{refreshPromise=null})
  }
  const pending = refreshPromise
  if (!pending) throw new Error('Unable to start token refresh')
  return pending
}

apiClient.interceptors.response.use(r=>r, async(error:AxiosError)=>{
  const status=error.response?.status
  const config=error.config as RetryConfig | undefined
  if(status===401 && config && !config._retry && !config.url?.includes('/auth/')){
    config._retry=true
    try{
      const token=await refreshAccessToken()
      config.headers.Authorization=`Bearer ${token}`
      return apiClient(config)
    }catch{
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if(window.location.pathname!=='/login') window.location.assign('/login')
    }
  }
  return Promise.reject(error)
})

export function apiErrorMessage(error:unknown, fallback='Unable to load data.'){
  if(axios.isAxiosError(error)){
    const body=error.response?.data as {error?:{message?:string};detail?:string}|undefined
    return body?.error?.message || body?.detail || error.message || fallback
  }
  return error instanceof Error ? error.message : fallback
}
