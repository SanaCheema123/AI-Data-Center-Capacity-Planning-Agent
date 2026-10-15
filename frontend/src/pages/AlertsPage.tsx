import { useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Search,
  Siren,
} from 'lucide-react'
import {
  useAlerts,
  useEvaluateAlerts,
  useUpdateAlert,
} from '../hooks/useApi'
import { useScope } from '../hooks/useScope'
import { usePermissions } from '../hooks/usePermissions'
import { PageHeader } from '../components/PageHeader'
import { MetricCard } from '../components/MetricCard'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionTitle,
} from '../components/ui'
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

const riskColors: Record<string, string> = {
  Critical: '#f43f5e',
  High: '#fb923c',
  Medium: '#a48ae0',
  Low: '#60a5fa',
  Resolved: '#34d399',
}

const formatNumber = (
  value?: number | null,
  maximumFractionDigits = 2,
) => {
  if (value == null || Number.isNaN(Number(value))) {
    return '—'
  }

  return Intl.NumberFormat(undefined, {
    maximumFractionDigits,
  }).format(Number(value))
}

const formatPercent = (
  value?: number | null,
) => {
  if (value == null || Number.isNaN(Number(value))) {
    return '—'
  }

  return `${formatNumber(value, 1)}%`
}

const severityTone = (
  severity?: string,
): 'red' | 'amber' | 'purple' | 'blue' => {
  if (severity === 'critical') return 'red'
  if (severity === 'high') return 'amber'
  if (severity === 'medium') return 'purple'
  return 'blue'
}

export function AlertsPage() {
  const { dataCenterId } = useScope()
  const permissions = usePermissions()

  const q = useAlerts(dataCenterId)
  const evaluate = useEvaluateAlerts()
  const update = useUpdateAlert()

  const data = useMemo(
    () => q.data || [],
    [q.data],
  )

  const [selected, setSelected] =
    useState<number | null>(null)

  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('all')

  const counts = (level: string) =>
    data.filter(
      alert =>
        alert.severity === level
        && alert.status !== 'resolved',
    ).length

  const resolved = data.filter(
    alert => alert.status === 'resolved',
  ).length

  const pie = useMemo(
    () =>
      [
        {
          name: 'Critical',
          value: counts('critical'),
        },
        {
          name: 'High',
          value: counts('high'),
        },
        {
          name: 'Medium',
          value: counts('medium'),
        },
        {
          name: 'Low',
          value: counts('low'),
        },
        {
          name: 'Resolved',
          value: resolved,
        },
      ].filter(item => item.value > 0),
    [data, resolved],
  )

  const rows = useMemo(() => {
    const term = search
      .trim()
      .toLowerCase()

    return data.filter(alert => {
      const matchesSeverity =
        severity === 'all'
        || alert.severity === severity

      const matchesSearch =
        !term
        || alert.title
          .toLowerCase()
          .includes(term)
        || alert.description
          .toLowerCase()
          .includes(term)
        || alert.resource_type
          .toLowerCase()
          .includes(term)

      return matchesSeverity && matchesSearch
    })
  }, [data, search, severity])

  const detail = data.find(
    alert =>
      alert.id
      === (selected ?? rows[0]?.id),
  )

  return (
    <>
      <PageHeader
        title="Capacity Alerts"
        subtitle="View and manage GPU, power, storage, and network alerts generated from forecast thresholds."
        runLabel={
          evaluate.isPending
            ? 'Evaluating...'
            : 'Evaluate Alerts'
        }
        onRun={
          permissions.canAnalyze
            ? () => evaluate.mutate(dataCenterId)
            : undefined
        }
        runDisabled={evaluate.isPending}
        reportType="shortage_risk"
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Critical Alerts"
          value={`${counts('critical')}`}
          icon={Siren}
          tone="red"
        />

        <MetricCard
          title="High Alerts"
          value={`${counts('high')}`}
          icon={AlertTriangle}
          tone="pink"
        />

        <MetricCard
          title="Medium Alerts"
          value={`${counts('medium')}`}
          icon={Info}
          tone="purple"
        />

        <MetricCard
          title="Resolved Alerts"
          value={`${resolved}`}
          icon={CheckCircle2}
          tone="green"
        />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1fr_340px]">
        <Card className="p-4">
          <SectionTitle title="Alerts by Risk Level" />

          {pie.length ? (
            <div className="grid min-h-[280px] items-center gap-6 md:grid-cols-[300px_1fr]">
              <div className="h-64">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={pie}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={58}
                      outerRadius={92}
                      paddingAngle={2}
                    >
                      {pie.map(item => (
                        <Cell
                          key={item.name}
                          fill={
                            riskColors[item.name]
                          }
                        />
                      ))}
                    </Pie>

                    <Tooltip
                      formatter={value => [
                        `${value}`,
                        'Alerts',
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-3">
                {pie.map(item => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between rounded-xl border border-slate-100 bg-white px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{
                          backgroundColor:
                            riskColors[item.name],
                        }}
                      />

                      <span className="font-medium text-slate-700">
                        {item.name}
                      </span>
                    </div>

                    <strong className="text-slate-900">
                      {item.value}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState
              title="No capacity alerts"
              description="Evaluate alerts to compare the latest forecasts with configured thresholds."
            />
          )}
        </Card>

        {detail ? (
          <Card className="p-4">
            <SectionTitle title="Alert Detail" />

            <Badge
              tone={severityTone(
                detail.severity,
              )}
            >
              {detail.severity}
            </Badge>

            <h3 className="mt-3 text-lg font-extrabold">
              {detail.title}
            </h3>

            <p className="mt-1 text-sm leading-6 text-slate-500">
              {detail.description}
            </p>

            <dl className="mt-4 space-y-2 text-sm">
              {[
                [
                  'Resource',
                  detail.resource_type,
                ],
                [
                  'Current',
                  formatNumber(
                    detail.current_value,
                  ),
                ],
                [
                  'Forecast',
                  formatNumber(
                    detail.forecast_value,
                  ),
                ],
                [
                  'Threshold',
                  formatPercent(
                    detail.threshold_value,
                  ),
                ],
                [
                  'Shortage',
                  detail.predicted_shortage_at
                    ? new Date(
                        detail.predicted_shortage_at,
                      ).toLocaleString()
                    : 'No physical shortage in selected horizon',
                ],
                [
                  'Status',
                  detail.status,
                ],
              ].map(([key, value]) => (
                <div
                  key={String(key)}
                  className="flex justify-between gap-3 rounded-lg bg-slate-50 p-2"
                >
                  <dt className="text-slate-500">
                    {key}
                  </dt>

                  <dd className="max-w-[190px] text-right font-bold capitalize">
                    {String(value)}
                  </dd>
                </div>
              ))}
            </dl>

            {permissions.canPlan ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  'acknowledged',
                  'investigating',
                  'monitoring',
                  'resolved',
                ]
                  .filter(
                    state =>
                      state !== detail.status,
                  )
                  .map(state => (
                    <Button
                      key={state}
                      variant="secondary"
                      disabled={
                        update.isPending
                      }
                      onClick={() =>
                        update.mutate({
                          id: detail.id,
                          status: state,
                        })
                      }
                    >
                      {state.replace(
                        /_/g,
                        ' ',
                      )}
                    </Button>
                  ))}
              </div>
            ) : (
              <p className="mt-4 text-xs text-slate-500">
                Alert status changes require
                Infrastructure Planner or Admin.
              </p>
            )}
          </Card>
        ) : (
          <Card className="p-4">
            <EmptyState title="Select an alert" />
          </Card>
        )}
      </div>

      <Card className="mt-3 overflow-hidden">
        <div className="p-4">
          <SectionTitle title="Alert Center" />

          <div className="grid gap-2 md:grid-cols-[1fr_auto]">
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm">
              <Search size={16} />

              <input
                aria-label="Search alerts"
                value={search}
                onChange={event =>
                  setSearch(
                    event.target.value,
                  )
                }
                placeholder="Search alerts..."
                className="min-w-0 flex-1 bg-transparent outline-none"
              />
            </label>

            <select
              aria-label="Severity filter"
              value={severity}
              onChange={event =>
                setSeverity(
                  event.target.value,
                )
              }
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="all">
                All severities
              </option>

              {[
                'critical',
                'high',
                'medium',
                'low',
              ].map(level => (
                <option
                  key={level}
                  value={level}
                >
                  {level}
                </option>
              ))}
            </select>
          </div>
        </div>

        {q.isLoading ? (
          <LoadingState />
        ) : q.isError ? (
          <div className="p-4">
            <ErrorState message="Unable to load alerts." />
          </div>
        ) : rows.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1060px] text-left text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>
                  {[
                    'Severity',
                    'Alert Title',
                    'Resource',
                    'Current Value',
                    'Forecast Value',
                    'Threshold',
                    'Predicted Shortage',
                    'Triggered',
                    'Status',
                  ].map(header => (
                    <th
                      className="p-3"
                      key={header}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {rows.map(alert => (
                  <tr
                    role="button"
                    aria-selected={
                      detail?.id
                      === alert.id
                    }
                    onClick={() =>
                      setSelected(alert.id)
                    }
                    tabIndex={0}
                    onKeyDown={event => {
                      if (
                        event.key === 'Enter'
                        || event.key === ' '
                      ) {
                        event.preventDefault()
                        setSelected(alert.id)
                      }
                    }}
                    className={`cursor-pointer border-t border-slate-100 hover:bg-olive-50/40 ${
                      detail?.id === alert.id
                        ? 'bg-olive-50/60'
                        : ''
                    }`}
                    key={alert.id}
                  >
                    <td className="p-3">
                      <Badge
                        tone={severityTone(
                          alert.severity,
                        )}
                      >
                        {alert.severity}
                      </Badge>
                    </td>

                    <td className="p-3">
                      <div className="font-bold">
                        {alert.title}
                      </div>

                      <div className="max-w-xs text-xs text-slate-500">
                        {alert.description}
                      </div>
                    </td>

                    <td className="p-3 capitalize">
                      {alert.resource_type}
                    </td>

                    <td className="p-3">
                      {formatNumber(
                        alert.current_value,
                      )}
                    </td>

                    <td className="p-3">
                      {formatNumber(
                        alert.forecast_value,
                      )}
                    </td>

                    <td className="p-3">
                      {formatPercent(
                        alert.threshold_value,
                      )}
                    </td>

                    <td className="p-3">
                      {alert.predicted_shortage_at
                        ? new Date(
                            alert.predicted_shortage_at,
                          ).toLocaleDateString()
                        : '—'}
                    </td>

                    <td className="p-3">
                      {new Date(
                        alert.triggered_at,
                      ).toLocaleDateString()}
                    </td>

                    <td className="p-3">
                      <Badge
                        tone={
                          alert.status
                          === 'resolved'
                            ? 'green'
                            : 'pink'
                        }
                      >
                        {alert.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-4">
            <EmptyState
              title="No capacity alerts"
              description="Evaluate alerts to compare the latest forecasts with configured thresholds."
            />
          </div>
        )}
      </Card>
    </>
  )
}