import { useQuery } from '@tanstack/react-query';
import { binsApi } from '../api/bins.api';

export const useBins = (params) => {
  return useQuery({
    queryKey: ['bins', params],
    queryFn: () => binsApi.list(params),
    placeholderData: (previous) => previous,
  });
};
