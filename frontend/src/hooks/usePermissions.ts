import { useMe } from './useApi'

const ANALYSIS_ROLES = new Set(['Admin', 'Infrastructure Planner', 'Analyst'])
const PLANNING_ROLES = new Set(['Admin', 'Infrastructure Planner'])

export function usePermissions() {
  const me = useMe()
  const roles = new Set(me.data?.roles.map((role) => role.name) ?? [])
  const hasAny = (allowed: Set<string>) => [...roles].some((role) => allowed.has(role))
  return {
    isLoading: me.isLoading,
    canAnalyze: hasAny(ANALYSIS_ROLES),
    canPlan: hasAny(PLANNING_ROLES),
    canManageSystem: hasAny(PLANNING_ROLES),
    roles,
  }
}
