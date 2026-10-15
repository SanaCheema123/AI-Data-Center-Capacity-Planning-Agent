import { CalendarDays, Download, Play } from 'lucide-react'
import { Button } from './ui'
import {
  useCenters,
  useGenerateReport,
  useSummary,
} from '../hooks/useApi'
import { useScope } from '../hooks/useScope'
import { api } from '../services/api'
import { emitAppError } from '../events/appError'
import { usePermissions } from '../hooks/usePermissions'

type PageHeaderProps = {
  title: string
  subtitle: string
  onRun?: () => void
  runLabel?: string
  runDisabled?: boolean
  reportType?: string
  nowrapActions?: boolean
}

export function PageHeader({
  title,
  subtitle,
  onRun,
  runLabel = 'Run Forecast',
  runDisabled = false,
  reportType,
  nowrapActions = false,
}: PageHeaderProps) {
  const centers = useCenters()

  const {
    dataCenterId,
    setDataCenterId,
  } = useScope()

  const summary = useSummary(dataCenterId)
  const generate = useGenerateReport()
  const permissions = usePermissions()

  const dateLabel =
    summary.data?.latest_metric_at
      ? `Data through ${new Date(
          summary.data.latest_metric_at,
        ).toLocaleDateString(undefined, {
          month: 'short',
          year: 'numeric',
        })}`
      : 'No metric timestamp'

  const exportReport = () => {
    if (!reportType) return

    generate.mutate(
      {
        type: reportType,
        dc: dataCenterId,
      },
      {
        onSuccess: report =>
          void api
            .downloadReport(
              report.id,
              'pdf',
              report.title,
            )
            .catch(error =>
              emitAppError(
                error,
                'Report download failed.',
              ),
            ),
      },
    )
  }

  return (
    <div className="mb-4 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div className="min-w-0 flex-1">
        <h1 className="text-2xl font-extrabold tracking-tight text-navy lg:text-[28px]">
          {title}
        </h1>

        <p className="mt-0.5 text-sm text-[#6b7355]">
          {subtitle}
        </p>
      </div>

      <div
        className={
          nowrapActions
            ? 'flex shrink-0 flex-nowrap items-center justify-end gap-2'
            : 'flex shrink-0 flex-wrap items-center justify-end gap-2'
        }
      >
        <div className="app-control inline-flex items-center gap-2 whitespace-nowrap rounded-xl border px-3 py-2 text-sm font-semibold text-navy">
          <CalendarDays size={16} />

          {summary.isLoading
            ? 'Loading date…'
            : dateLabel}
        </div>

        <select
          aria-label="Data center"
          value={dataCenterId ?? ''}
          onChange={e =>
            setDataCenterId(
              e.target.value
                ? Number(e.target.value)
                : null,
            )
          }
          disabled={
            centers.isLoading
            || centers.isError
          }
          className="app-control whitespace-nowrap rounded-xl border px-3 py-2 text-sm font-semibold text-navy disabled:opacity-60"
        >
          <option value="">
            All Data Centers
          </option>

          {centers.data?.map(center => (
            <option
              key={center.id}
              value={center.id}
            >
              {center.name}
            </option>
          ))}
        </select>

        {reportType &&
          permissions.canAnalyze && (
            <Button
              variant="secondary"
              disabled={generate.isPending}
              onClick={exportReport}
              className="whitespace-nowrap"
            >
              <Download size={16} />

              {generate.isPending
                ? 'Generating…'
                : 'Export PDF'}
            </Button>
          )}

        {onRun && (
          <Button
            disabled={runDisabled}
            onClick={onRun}
            className="whitespace-nowrap"
          >
            <Play size={16} />
            {runLabel}
          </Button>
        )}
      </div>
    </div>
  )
}