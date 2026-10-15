import type { LucideIcon } from 'lucide-react'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import { Card } from './ui'

type MetricTone='blue'|'pink'|'purple'|'green'|'red'
export function MetricCard({title,value,subtitle,change,icon:Icon,tone='blue',spark}:{title:string,value:string,subtitle?:string,change?:string,icon:LucideIcon,tone?:MetricTone,spark?:number[]}){
  const tones:Record<MetricTone,string>={blue:'bg-olive-50 text-olive-700',pink:'bg-lavender-50 text-lavender-700',purple:'bg-lavender-50 text-lavender-700',green:'bg-emerald-50 text-emerald-700',red:'bg-rose-50 text-rose-700'}
  return <Card className="min-h-[132px] p-4">
    <div className="flex items-start gap-3">
      <div className={`rounded-xl p-2.5 ${tones[tone]}`}><Icon size={22}/></div>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-bold text-navy">{title}</div>
        <div className="mt-1 text-[25px] font-extrabold tracking-tight text-[#3a451c]">{value}</div>
        {subtitle&&<div className="text-xs text-slate-500">{subtitle}</div>}
      </div>
    </div>
    {(change || (spark&&spark.length>1))&&<div className="mt-2 flex items-end justify-between gap-2">
      {change?<div className={`text-xs font-bold ${change.startsWith('-')?'text-rose-500':'text-emerald-600'}`}>{change}</div>:<span/>}
      {spark&&spark.length>1&&<div className="h-9 w-28"><ResponsiveContainer width="100%" height="100%"><AreaChart data={spark.map((v,i)=>({i,v}))}><Area dataKey="v" type="monotone" stroke="currentColor" fill="currentColor" fillOpacity={.08} strokeWidth={2}/></AreaChart></ResponsiveContainer></div>}
    </div>}
  </Card>
}
