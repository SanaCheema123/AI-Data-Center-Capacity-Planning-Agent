import { useEffect, useState } from 'react'
import { AlertTriangle, BarChart3, Database, Gauge, Server, Zap } from 'lucide-react'
import type { ForecastFrequency, ForecastModelType, ResourceType } from '../types/api'
import { useForecast, useRunForecast, useSettings } from '../hooks/useApi'
import { usePermissions } from '../hooks/usePermissions'
import { useScope } from '../hooks/useScope'
import { PageHeader } from '../components/PageHeader'
import { MetricCard } from '../components/MetricCard'
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, SectionTitle } from '../components/ui'
import { ForecastChart } from '../components/ForecastChart'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const meta: Record<'gpu' | 'power', { title: string; subtitle: string; unit: string; icon: typeof Server; reportType: string }> = {
  gpu: { title: 'GPU Demand Forecasting', subtitle: 'Monitor historical GPU utilization, forecast future demand, and identify expansion timing.', unit: ' GPUs', icon: Server, reportType: 'gpu' },
  power: { title: 'Power Capacity Planning', subtitle: 'Track current load, projected electricity demand, cooling impact, and future power headroom.', unit: ' MW', icon: Zap, reportType: 'power' },
}
const format = (value?: number | null, digits = 1) => value == null ? '—' : Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(value)

export function ResourceForecastPage({ resource }: { resource: ResourceType }) {
  const { dataCenterId } = useScope()
  const permissions = usePermissions()
  const settings = useSettings()
  const forecast = useForecast(resource, dataCenterId)
  const run = useRunForecast(resource)
  const page = meta[resource as 'gpu' | 'power']
  const data = forecast.data
  const forecastSetting = settings.data?.find((item) => item.key === 'forecast')?.value
  const [model, setModel] = useState<ForecastModelType>('prophet')
  const [horizon, setHorizon] = useState<number | undefined>()
  const [confidence, setConfidence] = useState<number | undefined>()
  const [frequency, setFrequency] = useState<ForecastFrequency>('monthly')

  useEffect(() => {
    if (!forecastSetting) return
    const configuredModel = forecastSetting.default_model
    const configuredHorizon = Number(forecastSetting.horizon_months)
    const configuredConfidence = Number(forecastSetting.confidence_interval)
    if (configuredModel === 'prophet' || configuredModel === 'xgboost') setModel(configuredModel)
    if (Number.isFinite(configuredHorizon) && configuredHorizon > 0) setHorizon(configuredHorizon)
    if (Number.isFinite(configuredConfidence) && configuredConfidence >= 0.5 && configuredConfidence < 1) setConfidence(configuredConfidence)
  }, [forecastSetting])

  useEffect(() => {
    if (data?.frequency === 'daily' || data?.frequency === 'weekly' || data?.frequency === 'monthly') setFrequency(data.frequency)
  }, [data?.frequency])

  const configured = horizon !== undefined && confidence !== undefined
  const runForecast = () => {
    if (!configured || !permissions.canAnalyze) return
    run.mutate({ model, data_center_id: dataCenterId, horizon, frequency, confidence })
  }
  if (!page) return null

  return <>
    <PageHeader
      title={page.title}
      subtitle={page.subtitle}
      onRun={permissions.canAnalyze ? runForecast : undefined}
      runDisabled={run.isPending || !configured}
      reportType={page.reportType}
    />
    {run.isPending && <div role="status" className="mb-3 rounded-xl bg-lavender-50 px-4 py-3 text-sm font-semibold text-purple">Forecast is running…</div>}
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      {resource === 'gpu' ? <>
        <MetricCard title="Current GPU Utilization" value={`${format(data?.capacity.utilization_percent)}%`} subtitle="latest measured demand / capacity" icon={page.icon} spark={data?.points.map((point) => point.predicted)} />
        <MetricCard title="Installed GPUs" value={`${format(data?.capacity.current_capacity, 0)} GPUs`} subtitle="available GPU capacity" icon={Database} tone="purple" />
      </> : <>
        <MetricCard title="Current Load" value={`${format(data?.capacity.current_usage)} MW`} subtitle="latest measured demand" icon={page.icon} spark={data?.points.map((point) => point.predicted)} />
        <MetricCard title="Maximum Capacity" value={`${format(data?.capacity.current_capacity)} MW`} subtitle="design power capacity" icon={Database} tone="purple" />
      </>}
      <MetricCard title="Forecast Peak Demand" value={`${format(data?.capacity.peak_demand)}${page.unit}`} subtitle="within forecast horizon" icon={BarChart3} tone="pink" spark={data?.points.map((point) => point.predicted)} />
      <MetricCard title="Available Headroom" value={`${format(data?.capacity.headroom)}${page.unit}`} subtitle={data ? `${format(data.capacity.utilization_percent)}% utilized` : '—'} icon={Gauge} tone="green" />
      <MetricCard title="Predicted Shortage Date" value={data?.capacity.shortage_date ? new Date(data.capacity.shortage_date).toLocaleDateString() : 'None'} subtitle="capacity exhaustion" icon={AlertTriangle} tone="red" />
    </div>

    <div className="mt-3 grid gap-3 xl:grid-cols-[1fr_330px]">
      <Card className="p-4">
        <SectionTitle title={`${page.title} Forecast`} subtitle="Persisted forecast output with confidence range and capacity limit" />
        {forecast.isLoading ? <LoadingState /> : forecast.isError ? <ErrorState message="No persisted forecast was found for this scope. Run a forecast if your role allows it." /> : data ? <ForecastChart data={data} height={350} /> : <EmptyState />}
      </Card>
      <Card className="p-4">
        <SectionTitle title="Model & Forecast Settings" />
        {settings.isLoading ? <LoadingState /> : !forecastSetting ? <ErrorState message="Forecast settings are not configured on the backend." /> : permissions.canAnalyze ? <>
          <div className="grid grid-cols-2 gap-2">
            <Button onClick={() => setModel('prophet')} variant="secondary" aria-pressed={model === 'prophet'} className={model === 'prophet' ? 'border-pink bg-lavender-50 text-pink' : ''}>Prophet</Button>
            <Button onClick={() => setModel('xgboost')} variant="secondary" aria-pressed={model === 'xgboost'} className={model === 'xgboost' ? 'border-pink bg-lavender-50 text-pink' : ''}>XGBoost</Button>
          </div>
          <div className="mt-4 grid gap-3 text-sm">
            <label>Confidence Interval<select value={confidence ?? ''} onChange={(event) => setConfidence(Number(event.target.value))} className="mt-1 w-full rounded-lg border p-2"><option value={.5}>50%</option><option value={.7}>70%</option><option value={.8}>80%</option><option value={.9}>90%</option><option value={.95}>95%</option></select></label>
            <label>Forecast Horizon<select value={horizon ?? ''} onChange={(event) => setHorizon(Number(event.target.value))} className="mt-1 w-full rounded-lg border p-2"><option value={1}>1 month</option><option value={3}>3 months</option><option value={6}>6 months</option><option value={12}>12 months</option><option value={24}>24 months</option></select></label>
            <label>Frequency<select value={frequency} onChange={(event) => setFrequency(event.target.value as ForecastFrequency)} className="mt-1 w-full rounded-lg border p-2"><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label>
          </div>
        </> : <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Viewer access is read-only. Forecast controls require Analyst, Infrastructure Planner, or Admin.</div>}
        {data && <div className="mt-5 rounded-xl bg-olive-50 p-4"><div className="text-xs font-bold text-slate-500">Recommended Expansion</div><div className="mt-1 text-lg font-extrabold">{data.capacity.required_expansion > 0 ? `Add ${format(data.capacity.required_expansion)}${page.unit}` : 'No expansion required'}</div><div className="mt-1 text-xs text-slate-500">From backend run #{data.run_id} using {data.model_engine}</div></div>}
      </Card>
    </div>

    <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <Card className="p-4"><SectionTitle title="Forecast Accuracy" />{data ? <div className="grid grid-cols-2 gap-3">{Object.entries(data.accuracy).map(([key, value]) => <div key={key} className="rounded-xl bg-slate-50 p-3"><div className="text-lg font-extrabold">{format(Number(value), 2)}</div><div className="text-xs uppercase text-slate-400">{key}</div></div>)}</div> : <EmptyState />}</Card>
      <Card className="p-4 xl:col-span-2"><SectionTitle title="Demand Distribution" />{data ? <div className="h-48"><ResponsiveContainer><BarChart data={data.points.map((point) => ({ period: new Date(point.timestamp).toLocaleDateString(undefined, { month: 'short', year: '2-digit' }), demand: point.predicted }))}><CartesianGrid stroke="#e4e8d6" /><XAxis dataKey="period" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="demand" fill="#745fc0" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div> : <EmptyState />}</Card>
      <Card className="p-4"><SectionTitle title="Key Insights & Recommendations" />{data ? <div className="space-y-2 text-sm"><div className="rounded-xl bg-lavender-50 p-3"><Badge tone={data.capacity.required_expansion > 0 ? 'red' : 'green'}>{data.capacity.required_expansion > 0 ? 'Action needed' : 'Healthy'}</Badge><p className="mt-2">Peak demand is {format(data.capacity.peak_demand)} {data.unit} against {format(data.capacity.current_capacity)} capacity.</p></div><div className="rounded-xl bg-olive-50 p-3">Model engine: <strong>{data.model_engine}</strong></div></div> : <EmptyState />}</Card>
    </div>
  </>
}
