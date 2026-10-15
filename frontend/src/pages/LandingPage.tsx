import {
  ArrowRight,
  BarChart3,
  Boxes,
  BrainCircuit,
  ChevronRight,
  Cpu,
  Database,
  Gauge,
  GitBranch,
  Network,
  Server,
  ShieldAlert,
  ShoppingCart,
  Sparkles,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui'

const olive = '#6f813b'

const capabilityCards = [
  {
    title: 'Advanced workload modeling',
    text: 'Forecast GPU demand from historical utilization and workload growth.',
    icon: Cpu,
  },
  {
    title: 'Power capacity planning',
    text: 'Project electricity requirements, utilization, headroom, and shortage dates.',
    icon: Zap,
  },
  {
    title: 'Storage & network growth',
    text: 'Model storage expansion and future network-throughput requirements.',
    icon: Database,
  },
  {
    title: 'Expansion scenarios',
    text: 'Compare conservative, base, aggressive, and custom infrastructure plans.',
    icon: GitBranch,
  },
  {
    title: 'Procurement intelligence',
    text: 'Convert capacity gaps into quantities, timing, cost, and dependencies.',
    icon: ShoppingCart,
  },
  {
    title: 'Capacity-shortage alerts',
    text: 'Detect forecast threshold breaches and manage the complete alert lifecycle.',
    icon: ShieldAlert,
  },
]

const stack = ['React.js', 'FastAPI', 'PostgreSQL', 'Python', 'Prophet', 'XGBoost', 'Recharts', 'LangGraph']

function MiniLine({ variant = 0 }: { variant?: number }) {
  const paths = [
    'M4 54 C18 50 26 34 42 38 S67 58 82 39 S105 18 122 27 S146 39 170 10',
    'M4 52 C24 48 36 42 52 35 S84 30 96 26 S128 18 170 8',
    'M4 51 C20 45 31 54 46 41 S69 25 84 34 S108 49 124 29 S147 18 170 12',
  ]
  return (
    <svg viewBox="0 0 174 62" className="h-20 w-full" role="img" aria-label="Illustrative trend preview">
      <defs>
        <linearGradient id={`trend-fill-${variant}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={olive} stopOpacity=".26" />
          <stop offset="1" stopColor={olive} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${paths[variant % paths.length]} L170 62 L4 62 Z`} fill={`url(#trend-fill-${variant})`} />
      <path d={paths[variant % paths.length]} fill="none" stroke={olive} strokeWidth="2.5" strokeLinecap="round" />
      <path d="M4 45 C24 43 44 40 65 36 S104 31 124 24 S150 18 170 15" fill="none" stroke="#745fc0" strokeWidth="1.5" strokeDasharray="4 4" opacity=".85" />
    </svg>
  )
}

function PreviewPanel() {
  return (
    <div className="relative mx-auto w-full max-w-[650px]">
      <div className="absolute -left-10 top-12 h-44 w-44 rounded-full bg-[#cad276]/40 blur-3xl" />
      <div className="absolute -right-8 bottom-8 h-52 w-52 rounded-full bg-[#745f9c]/25 blur-3xl" />
      <div className="relative overflow-hidden rounded-[26px] border border-white/70 bg-white/90 p-4 shadow-[0_30px_75px_rgba(40,47,20,.22)] backdrop-blur">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-[.16em] text-[#70762e]">
              <Sparkles size={14} /> Planning workspace preview
            </div>
            <h3 className="mt-1 text-lg font-black text-slate-900">Capacity Outlook</h3>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-[#d9dcbd] bg-[#f8f9ee] px-3 py-2 text-xs font-bold text-[#59601e]">
            <Gauge size={15} /> Scenario Simulation
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {[
            ['GPU', Cpu],
            ['Power', Zap],
            ['Forecasts', BarChart3],
          ].map(([label, Icon]) => {
            const I = Icon as typeof Cpu
            return (
              <div key={label as string} className="rounded-xl border border-slate-200 bg-white p-2.5">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-800"><I size={15} /> {label as string}</div>
                <div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className="h-full w-2/3 rounded-full bg-[#848a40]" /></div>
              </div>
            )
          })}
        </div>

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {[
            ['GPU Demand Forecast', 0],
            ['Power Capacity Utilization', 1],
            ['Storage Growth Analysis', 2],
            ['Network Traffic Projections', 0],
          ].map(([title, variant]) => (
            <div key={title as string} className="rounded-2xl border border-slate-200 bg-[#fbfcf8] p-3">
              <div className="flex items-center justify-between text-xs font-extrabold text-slate-800">
                <span>{title as string}</span>
                <span className="h-2 w-2 rounded-full bg-[#858b40]" />
              </div>
              <MiniLine variant={variant as number} />
            </div>
          ))}
        </div>
      </div>

      <div className="relative -mt-4 ml-auto mr-3 grid max-w-md grid-cols-3 gap-2 rounded-2xl border border-[#d9dcc5] bg-white p-3 shadow-xl md:mr-7">
        {['Conservative', 'Base case', 'Aggressive'].map((name, index) => (
          <div key={name} className="rounded-xl bg-[#f5f6eb] p-2 text-center">
            <div className="text-[10px] font-extrabold uppercase tracking-wide text-lavender-300">Scenario</div>
            <div className="mt-1 text-xs font-black text-slate-900">{name}</div>
            <div className="mx-auto mt-2 h-1.5 w-4/5 overflow-hidden rounded-full bg-[#dddccf]">
              <div className="h-full rounded-full bg-[#7d833a]" style={{ width: `${55 + index * 15}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function LandingPage() {
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  return (
    <div className="min-h-screen bg-[#f7f7f0] text-slate-950">
      <header className="sticky top-0 z-50 border-b border-[#dfe1cf] bg-[#fbfbf6]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
          <Link to="/" className="flex min-w-0 items-center gap-3" aria-label="AI Data Center Capacity Planning Agent home">
            <div className="relative grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-[#5f6730] via-[#7e8441] to-[#755aa0] text-white shadow-md">
              <BarChart3 size={24} />
              <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full border-2 border-[#fbfbf6] bg-[#a5b355]" />
            </div>
            <div className="min-w-0 leading-tight">
              <div className="truncate text-sm font-black sm:text-base">AI Data Center Capacity</div>
              <div className="truncate text-xs font-bold text-slate-600 sm:text-sm">Planning Agent</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-7 text-sm font-extrabold lg:flex" aria-label="Primary navigation">
            <button type="button" onClick={() => scrollTo('features')} className="hover:text-[#747a31]">Features</button>
            <button type="button" onClick={() => scrollTo('forecasting')} className="hover:text-[#747a31]">Forecasting</button>
            <button type="button" onClick={() => scrollTo('integrations')} className="hover:text-[#747a31]">Integrations</button>
            <button type="button" onClick={() => scrollTo('about')} className="hover:text-[#747a31]">About</button>
          </nav>

          <div className="flex items-center gap-2">
            <Link to="/login" className="hidden sm:block">
              <Button variant="secondary">Sign In</Button>
            </Link>
            <Link to="/contact" className="inline-flex items-center justify-center rounded-xl bg-[#737a30] px-4 py-2.5 text-xs font-black uppercase tracking-wide text-white shadow-md transition hover:bg-[#626827] sm:px-5 sm:text-sm">
              Contact
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-[#dde0c9]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(139,149,74,.16),transparent_28%),radial-gradient(circle_at_90%_25%,rgba(91,103,45,.18),transparent_32%),linear-gradient(110deg,#fafaf4_0%,#f4f5e8_58%,#e7ead0_100%)]" />
          <div className="pointer-events-none absolute left-0 top-0 h-full w-[38%] opacity-30 [background-image:radial-gradient(#7c833b_1px,transparent_1px)] [background-size:32px_32px]" />
          <div className="pointer-events-none absolute right-0 top-0 h-full w-[28%] bg-gradient-to-l from-[#5a6230]/25 to-transparent" />

          <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 py-16 lg:grid-cols-[1.02fr_.98fr] lg:px-8 lg:py-24">
            <div>
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#cfd3a9] bg-white/70 px-3 py-1.5 text-xs font-black uppercase tracking-[.14em] text-[#646b2b]">
                <BrainCircuit size={15} /> Intelligent infrastructure planning
              </div>
              <h1 className="max-w-3xl text-[2.65rem] font-black uppercase leading-[.98] tracking-[-.045em] text-[#111] sm:text-5xl lg:text-[4.15rem]">
                <span className="text-[#7a8038]">Infrastructure pulse.</span><br />
                The future of intelligent capacity planning. <span className="text-[#8067a9]">Optimize for AI data centers.</span>
              </h1>
              <p className="mt-7 max-w-2xl text-base font-medium leading-7 text-slate-700 sm:text-lg">
                Forecast GPU, electricity, storage, and network requirements from historical infrastructure data. Detect future shortages, compare expansion scenarios, and turn capacity gaps into actionable procurement plans.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/register" className="inline-flex items-center gap-2 rounded-xl bg-[#737a30] px-6 py-3.5 text-sm font-black uppercase tracking-wide text-white shadow-md transition hover:bg-[#626827]">
                  Open Platform <ArrowRight size={17} />
                </Link>
                <button type="button" onClick={() => scrollTo('features')} className="inline-flex items-center gap-2 rounded-xl border border-[#747a31] bg-white/75 px-6 py-3.5 text-sm font-black uppercase tracking-wide text-[#35391e] transition hover:bg-white">
                  Learn More <ChevronRight size={17} />
                </button>
              </div>

              <div className="mt-10 grid gap-3 sm:grid-cols-2">
                {capabilityCards.slice(0, 4).map(({ title, text, icon: Icon }) => (
                  <div key={title} className="flex gap-3 rounded-2xl border border-[#d9dbc6] bg-white/75 p-4 shadow-[0_8px_24px_rgba(61,67,30,.08)] backdrop-blur">
                    <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-[#e9ecd2] to-[#ddd5eb] text-[#60672a]"><Icon size={25} /></div>
                    <div><h3 className="text-sm font-black uppercase leading-tight">{title}</h3><p className="mt-1 text-sm leading-5 text-slate-600">{text}</p></div>
                  </div>
                ))}
              </div>
            </div>

            <PreviewPanel />
          </div>
        </section>

        <section id="features" className="scroll-mt-24 bg-[#f7f7f0] py-20">
          <div className="mx-auto max-w-7xl px-5 lg:px-8">
            <div className="mx-auto max-w-3xl text-center">
              <div className="text-xs font-black uppercase tracking-[.2em] text-[#747a31]">Alerting & planning framework</div>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">From telemetry to infrastructure decisions</h2>
              <p className="mt-4 text-base leading-7 text-slate-600">A complete planning workflow covering forecasting, capacity risk, expansion scenarios, procurement, alerts, reporting, and AI-grounded recommendations.</p>
            </div>
            <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {capabilityCards.map(({ title, text, icon: Icon }) => (
                <div key={title} className="group rounded-[22px] border border-[#d7dac1] bg-white p-6 shadow-[0_12px_32px_rgba(58,64,27,.07)] transition hover:-translate-y-1 hover:shadow-[0_20px_45px_rgba(58,64,27,.12)]">
                  <div className="mb-5 inline-flex rounded-2xl bg-[#eef0da] p-3 text-[#69702c]"><Icon size={26} /></div>
                  <h3 className="text-lg font-black uppercase leading-tight">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="forecasting" className="scroll-mt-24 border-y border-[#dfe1cc] bg-white py-20">
          <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 lg:grid-cols-2 lg:px-8">
            <div>
              <div className="text-xs font-black uppercase tracking-[.2em] text-[#747a31]">Forecasting engine</div>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">Prophet and XGBoost behind one forecasting interface</h2>
              <p className="mt-5 text-base leading-7 text-slate-600">GPU, power, storage, and network forecasts share a common backend pipeline for confidence intervals, accuracy metrics, peak-demand detection, capacity headroom, shortage dates, and required expansion.</p>
              <div className="mt-7 space-y-3">
                {[
                  'Forecasts are calculated from PostgreSQL historical metrics.',
                  'Model selection can be changed without rewriting dashboard logic.',
                  'Results are persisted and reused by scenarios, alerts, procurement, reports, and AI.',
                  'Insufficient data is reported instead of hallucinating a forecast.',
                ].map(item => <div key={item} className="flex items-start gap-3 text-sm font-semibold text-slate-700"><span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#7b8237]" />{item}</div>)}
              </div>
              <Link to="/register" className="mt-8 inline-flex items-center gap-2 font-black text-[#68702d]">Open forecasting workspace <ArrowRight size={17} /></Link>
            </div>
            <div className="rounded-[28px] border border-[#d8dbc2] bg-[#f5f6ec] p-5 shadow-xl">
              <div className="grid gap-4 sm:grid-cols-2">
                {[
                  ['GPU demand', Cpu, 0],
                  ['Power capacity', Zap, 1],
                  ['Storage growth', Database, 2],
                  ['Network throughput', Network, 0],
                ].map(([title, Icon, variant]) => {
                  const I = Icon as typeof Cpu
                  return <div key={title as string} className="rounded-2xl border border-white bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-sm font-black"><I size={18} className="text-[#71772f]" />{title as string}</div><MiniLine variant={variant as number} /></div>
                })}
              </div>
            </div>
          </div>
        </section>

        <section id="integrations" className="scroll-mt-24 bg-[#f7f7f0] py-20">
          <div className="mx-auto max-w-7xl px-5 lg:px-8">
            <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-center">
              <div>
                <div className="text-xs font-black uppercase tracking-[.2em] text-[#747a31]">Integrations</div>
                <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">Bring your infrastructure data into one planning layer</h2>
                <p className="mt-5 leading-7 text-slate-600">Use CSV imports today, and connect Prometheus, OpenTelemetry, or authenticated internal APIs through the integration architecture.</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {[
                  ['CSV import', Database, 'Validated historical infrastructure uploads'],
                  ['Prometheus', Gauge, 'GPU, power, storage, network, and system metrics'],
                  ['OpenTelemetry', Network, 'Metrics, logs, and traces integration architecture'],
                  ['Internal APIs', Boxes, 'Authenticated ingestion for enterprise sources'],
                ].map(([title, Icon, text]) => {
                  const I = Icon as typeof Database
                  return <div key={title as string} className="flex gap-4 rounded-2xl border border-[#d8dbc3] bg-white p-5"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#eef0db] text-[#6b722f]"><I size={23}/></div><div><div className="font-black">{title as string}</div><div className="mt-1 text-sm leading-5 text-slate-600">{text as string}</div></div></div>
                })}
              </div>
            </div>

            <div className="mt-14 rounded-[24px] border border-[#cfd3a8] bg-white px-5 py-6 text-center">
              <div className="text-xs font-black uppercase tracking-[.2em] text-[#737a30]">Built with modern technologies</div>
              <div className="mt-6 flex flex-wrap items-center justify-center gap-x-8 gap-y-4">
                {stack.map(item => <span key={item} className="text-base font-black text-slate-700">{item}</span>)}
              </div>
            </div>
          </div>
        </section>

        <section id="about" className="scroll-mt-24 overflow-hidden bg-[#2f3919] py-16 text-white">
          <div className="mx-auto grid max-w-7xl items-center gap-8 px-5 lg:grid-cols-[1fr_auto] lg:px-8">
            <div>
              <div className="text-xs font-black uppercase tracking-[.2em] text-[#c9d080]">Production-oriented capacity intelligence</div>
              <h2 className="mt-3 max-w-3xl text-3xl font-black tracking-tight sm:text-4xl">Plan infrastructure before demand becomes a shortage.</h2>
              <p className="mt-4 max-w-3xl leading-7 text-lavender-100">The platform combines database-backed metrics, open-source forecasting, deterministic capacity calculations, scenario analysis, procurement logic, alerts, reports, and LangGraph orchestration. Gemini and Groq are optional enhancements—the core system remains functional without them.</p>
            </div>
            <div className="flex flex-wrap gap-3 lg:justify-end">
              <Link to="/register" className="inline-flex items-center gap-2 rounded-xl bg-[#dce399] px-6 py-3.5 text-sm font-black uppercase tracking-wide text-[#202514]">Create Account <ArrowRight size={17}/></Link>
              <Link to="/contact" className="inline-flex items-center rounded-xl border border-white/30 px-6 py-3.5 text-sm font-black uppercase tracking-wide text-white hover:bg-white/10">Contact Planning Team</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-[#241c3d] py-10 text-lavender-100">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 sm:grid-cols-2 lg:grid-cols-4 lg:px-8">
          <div>
            <div className="flex items-center gap-3 text-white"><div className="grid h-9 w-9 place-items-center rounded-lg bg-[#737a30]"><Server size={20}/></div><div className="font-black leading-tight">AI Data Center<br/>Capacity Planning Agent</div></div>
            <p className="mt-4 text-sm leading-6 text-lavender-200">Forecast, compare, alert, procure, and report from one planning workspace.</p>
          </div>
          <div><div className="font-black text-white">Product</div><div className="mt-3 space-y-2 text-sm"><button onClick={()=>scrollTo('features')}>Features</button><br/><button onClick={()=>scrollTo('forecasting')}>Forecasting</button><br/><button onClick={()=>scrollTo('integrations')}>Integrations</button></div></div>
          <div><div className="font-black text-white">Platform</div><div className="mt-3 space-y-2 text-sm"><Link to="/login">Sign In</Link><br/><Link to="/register">Create Account</Link><br/><Link to="/contact">Contact</Link></div></div>
          <div><div className="font-black text-white">Core stack</div><p className="mt-3 text-sm leading-6 text-lavender-200">React · FastAPI · PostgreSQL · Python · Prophet · XGBoost · Recharts · LangGraph</p></div>
        </div>
        <div className="mx-auto mt-8 max-w-7xl border-t border-white/10 px-5 pt-6 text-xs text-lavender-300 lg:px-8">AI Data Center Capacity Planning Agent</div>
      </footer>
    </div>
  )
}
