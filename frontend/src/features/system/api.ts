import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../../services/api/client'
import type { HealthResponse } from '../../types/system'

async function getHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health')
  return data
}

export function useHealth() {
  return useQuery({ queryKey: ['system', 'health'], queryFn: getHealth })
}
