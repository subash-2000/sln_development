import { useQuery } from '@tanstack/react-query';

export const useListQuery = ({ queryKey, queryFn, params, enabled = true }) => {
  const query = useQuery({
    queryKey: [...queryKey, params],
    queryFn: () => queryFn(params),
    placeholderData: (previous) => previous,
    enabled,
  });

  return {
    items: query.data?.items ?? [],
    paginationMeta: query.data?.pagination,
    ...query,
  };
};
