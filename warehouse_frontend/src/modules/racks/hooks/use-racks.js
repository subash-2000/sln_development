import { useQuery } from '@tanstack/react-query';
import { racksApi } from '../api/racks.api';

export const useRacks = (params) => {
  return useQuery({
    queryKey: ['racks', params],
    queryFn: () => racksApi.list(params),
    placeholderData: (previous) => previous,
  });
};
