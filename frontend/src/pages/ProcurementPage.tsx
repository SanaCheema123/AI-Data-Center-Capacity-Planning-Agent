import {
  useMemo,
  useState,
} from 'react'
import {
  Database,
  Network,
  Search,
  ShoppingCart,
  Server,
  Wallet,
  Zap,
} from 'lucide-react'
import {
  useGenerateProcurement,
  useProcurement,
  useRecommendations,
  useUpdateProcurement,
} from '../hooks/useApi'
import { useScope } from '../hooks/useScope'
import { usePermissions } from '../hooks/usePermissions'
import { PageHeader } from '../components/PageHeader'
import { MetricCard } from '../components/MetricCard'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionTitle,
} from '../components/ui'

const formatNumber = (
  value?: number | null,
  maximumFractionDigits = 1,
) => {
  if (
    value == null
    || Number.isNaN(Number(value))
  ) {
    return '—'
  }

  return Intl.NumberFormat(undefined, {
    maximumFractionDigits,
  }).format(Number(value))
}

const formatCurrency = (
  value?: number | null,
) => {
  if (value == null) {
    return 'Cost not configured'
  }

  return Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export function ProcurementPage() {
  const { dataCenterId } = useScope()
  const permissions = usePermissions()

  const q = useProcurement(dataCenterId)
  const recommendations =
    useRecommendations(dataCenterId)

  const generate =
    useGenerateProcurement()

  const update =
    useUpdateProcurement()

  const [search, setSearch] =
    useState('')

  const [priority, setPriority] =
    useState('all')

  const [status, setStatus] =
    useState('all')

  const rows = useMemo(() => {
    const term = search
      .trim()
      .toLowerCase()

    return (q.data || []).filter(item => {
      const matchesSearch =
        !term
        || item.resource_type
          .toLowerCase()
          .includes(term)
        || item.reason
          ?.toLowerCase()
          .includes(term)

      const matchesPriority =
        priority === 'all'
        || item.priority === priority

      const matchesStatus =
        status === 'all'
        || item.status === status

      return (
        matchesSearch
        && matchesPriority
        && matchesStatus
      )
    })
  }, [
    q.data,
    search,
    priority,
    status,
  ])

  const byResource = (resource: string) =>
    q.data?.find(
      item =>
        item.resource_type === resource
        && item.status !== 'completed'
        && item.status !== 'cancelled',
    )

  const costedItems =
    q.data?.filter(
      item =>
        item.estimated_cost != null
        && item.status !== 'cancelled',
    ) ?? []

  const totalBudget = costedItems.reduce(
    (total, item) =>
      total
      + Number(
        item.estimated_cost || 0,
      ),
    0,
  )

  const hasAnyCost =
    costedItems.length > 0

  return (
    <>
      <PageHeader
        title="Procurement Recommendations"
        subtitle="Plan and prioritize infrastructure purchases based on forecast demand, configured planning thresholds, and capacity headroom."
        runLabel={
          generate.isPending
            ? 'Generating...'
            : 'Generate Plan'
        }
        onRun={
          permissions.canPlan
            ? () =>
                generate.mutate(
                  dataCenterId,
                )
            : undefined
        }
        runDisabled={
          generate.isPending
        }
        reportType="procurement"
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          title="Required GPU Expansion"
          value={
            byResource('gpu')
              ? `${formatNumber(
                  byResource('gpu')
                    ?.quantity,
                )} units`
              : 'No expansion'
          }
          icon={Server}
        />

        <MetricCard
          title="Required Storage Expansion"
          value={
            byResource('storage')
              ? `${formatNumber(
                  byResource('storage')
                    ?.quantity,
                )} units`
              : 'No expansion'
          }
          icon={Database}
          tone="pink"
        />

        <MetricCard
          title="Power Upgrade Need"
          value={
            byResource('power')
              ? `${formatNumber(
                  byResource('power')
                    ?.quantity,
                )} units`
              : 'No expansion'
          }
          icon={Zap}
          tone="purple"
        />

        <MetricCard
          title="Network Upgrade Need"
          value={
            byResource('network')
              ? `${formatNumber(
                  byResource('network')
                    ?.quantity,
                )} units`
              : 'No expansion'
          }
          icon={Network}
        />

        <MetricCard
          title="Total Estimated Budget"
          value={
            hasAnyCost
              ? Intl.NumberFormat(
                  undefined,
                  {
                    style: 'currency',
                    currency: 'USD',
                    notation: 'compact',
                    maximumFractionDigits: 1,
                  },
                ).format(
                  totalBudget,
                )
              : 'Cost not configured'
          }
          icon={Wallet}
          tone="pink"
        />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1fr_330px]">
        <Card className="overflow-hidden">
          <div className="p-4">
            <SectionTitle title="Procurement Recommendations" />

            <p className="mb-4 text-xs leading-5 text-slate-500">
              Items are generated when forecast
              utilization reaches or exceeds the
              configured planning threshold. The system
              does not wait for physical capacity to be
              exhausted.
            </p>

            <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
              <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
                <Search size={16} />

                <input
                  aria-label="Search procurement"
                  value={search}
                  onChange={event =>
                    setSearch(
                      event.target.value,
                    )
                  }
                  placeholder="Search items..."
                  className="min-w-0 flex-1 bg-transparent outline-none"
                />
              </label>

              <select
                aria-label="Priority filter"
                value={priority}
                onChange={event =>
                  setPriority(
                    event.target.value,
                  )
                }
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="all">
                  All priorities
                </option>

                <option value="high">
                  High
                </option>

                <option value="medium">
                  Medium
                </option>

                <option value="low">
                  Low
                </option>
              </select>

              <select
                aria-label="Status filter"
                value={status}
                onChange={event =>
                  setStatus(
                    event.target.value,
                  )
                }
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="all">
                  All statuses
                </option>

                {[
                  'planned',
                  'approved',
                  'in_review',
                  'ordered',
                  'completed',
                  'cancelled',
                ].map(value => (
                  <option
                    key={value}
                    value={value}
                  >
                    {value.replace(
                      /_/g,
                      ' ',
                    )}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {q.isLoading ? (
            <LoadingState />
          ) : q.isError ? (
            <div className="p-4">
              <ErrorState message="Unable to load procurement recommendations." />
            </div>
          ) : rows.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1180px] text-left text-sm">
                <thead className="bg-slate-50 text-xs text-slate-500">
                  <tr>
                    {[
                      'Item',
                      'Current Capacity',
                      'Required Capacity',
                      'Quantity',
                      'Required By',
                      'Priority',
                      'Status',
                      'Estimated Cost',
                      'Planning Basis',
                    ].map(header => (
                      <th
                        key={header}
                        className="px-4 py-3"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {rows.map(item => (
                    <tr
                      key={item.id}
                      className="border-t border-slate-100"
                    >
                      <td className="px-4 py-3 font-bold capitalize">
                        <span className="mr-2 inline-grid h-8 w-8 place-items-center rounded-lg bg-olive-50 text-primary">
                          <ShoppingCart
                            size={15}
                          />
                        </span>

                        {item.resource_type}{' '}
                        expansion
                      </td>

                      <td className="px-4 py-3">
                        {formatNumber(
                          item.current_capacity,
                        )}
                      </td>

                      <td className="px-4 py-3">
                        {formatNumber(
                          item.required_capacity,
                        )}
                      </td>

                      <td className="px-4 py-3 font-semibold">
                        {formatNumber(
                          item.quantity,
                        )}
                      </td>

                      <td className="px-4 py-3">
                        {item.required_by
                          ? new Date(
                              item.required_by,
                            ).toLocaleDateString()
                          : '—'}
                      </td>

                      <td className="px-4 py-3">
                        <select
                          aria-label={`${item.resource_type} priority`}
                          disabled={
                            update.isPending
                            || !permissions.canPlan
                          }
                          value={
                            item.priority
                          }
                          onChange={event =>
                            update.mutate({
                              id: item.id,
                              payload: {
                                priority:
                                  event.target
                                    .value,
                              },
                            })
                          }
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs"
                        >
                          <option value="high">
                            High
                          </option>

                          <option value="medium">
                            Medium
                          </option>

                          <option value="low">
                            Low
                          </option>
                        </select>
                      </td>

                      <td className="px-4 py-3">
                        <select
                          aria-label={`${item.resource_type} status`}
                          disabled={
                            update.isPending
                            || !permissions.canPlan
                          }
                          value={
                            item.status
                          }
                          onChange={event =>
                            update.mutate({
                              id: item.id,
                              payload: {
                                status:
                                  event.target
                                    .value,
                              },
                            })
                          }
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs"
                        >
                          {[
                            'planned',
                            'approved',
                            'in_review',
                            'ordered',
                            'completed',
                            'cancelled',
                          ].map(value => (
                            <option
                              key={value}
                              value={value}
                            >
                              {value.replace(
                                /_/g,
                                ' ',
                              )}
                            </option>
                          ))}
                        </select>
                      </td>

                      <td className="px-4 py-3 font-bold">
                        {formatCurrency(
                          item.estimated_cost,
                        )}
                      </td>

                      <td className="max-w-[320px] px-4 py-3 text-xs leading-5 text-slate-500">
                        {item.reason
                          || 'Generated from forecast capacity and configured planning threshold.'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-4">
              <EmptyState
                title="No matching procurement items"
                description={
                  q.data?.length
                    ? 'Adjust search or filters.'
                    : 'No forecast currently exceeds its configured planning threshold. Generate the plan again after running the latest forecasts.'
                }
              />
            </div>
          )}
        </Card>

        <Card className="p-4">
          <SectionTitle title="AI Recommendation Summary" />

          <div className="space-y-3">
            {recommendations.data?.length ? (
              recommendations.data.map(
                item => (
                  <div
                    key={
                      item.resource_type
                    }
                    className="rounded-xl bg-slate-50 p-3 text-sm"
                  >
                    <div className="font-bold capitalize">
                      {item.resource_type}:{' '}
                      {item.recommendation}
                    </div>

                    <div className="mt-1 text-xs leading-5 text-slate-500">
                      {item.reason}
                    </div>

                    {item.supporting_metrics
                      ?.forecast_utilization_percent
                      != null && (
                      <div className="mt-2 rounded-lg bg-white px-2 py-2 text-xs">
                        Forecast utilization:{' '}
                        <strong>
                          {formatNumber(
                            Number(
                              item
                                .supporting_metrics
                                .forecast_utilization_percent,
                            ),
                            1,
                          )}
                          %
                        </strong>

                        {item
                          .supporting_metrics
                          .planning_threshold_percent
                          != null && (
                          <>
                            {' '}
                            · Threshold:{' '}
                            <strong>
                              {formatNumber(
                                Number(
                                  item
                                    .supporting_metrics
                                    .planning_threshold_percent,
                                ),
                                1,
                              )}
                              %
                            </strong>
                          </>
                        )}
                      </div>
                    )}

                    <div className="mt-2 flex flex-wrap gap-1">
                      {item.dependencies.map(
                        dependency => (
                          <Badge
                            key={
                              dependency
                            }
                            tone="purple"
                          >
                            {dependency}
                          </Badge>
                        ),
                      )}
                    </div>
                  </div>
                ),
              )
            ) : (
              <EmptyState title="No recommendations" />
            )}
          </div>
        </Card>
      </div>
    </>
  )
}