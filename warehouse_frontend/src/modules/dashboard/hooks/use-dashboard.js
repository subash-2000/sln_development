import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../api/dashboard.api';

/** Poll dashboard metrics so the home page stays near real-time. */
export const useDashboardSummary = (options = {}) => {
  const { refetchInterval = 30_000, ...rest } = options;
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => dashboardApi.summary(),
    refetchInterval,
    refetchOnWindowFocus: true,
    ...rest,
  });
};
