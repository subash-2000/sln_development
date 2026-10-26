import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { returnsApi } from '../api/returns.api';

export const useReturns = (params) =>
  useQuery({
    queryKey: ['returns', params],
    queryFn: () => returnsApi.list(params),
    placeholderData: (previous) => previous,
  });

export const useReturn = (id) =>
  useQuery({
    queryKey: ['return', id],
    queryFn: () => returnsApi.getById(id),
    enabled: Boolean(id),
  });

export const useCreateReturn = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: returnsApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['returns'] }),
  });
};

export const useReturnActions = () => {
  const queryClient = useQueryClient();
  const invalidate = (id) => {
    queryClient.invalidateQueries({ queryKey: ['returns'] });
    queryClient.invalidateQueries({ queryKey: ['return', id] });
  };
  return {
    receive: useMutation({
      mutationFn: returnsApi.receive,
      onSuccess: (_, id) => invalidate(id),
    }),
    inspect: useMutation({
      mutationFn: ({ id, data }) => returnsApi.inspect(id, data),
      onSuccess: (_, { id }) => invalidate(id),
    }),
    complete: useMutation({
      mutationFn: returnsApi.complete,
      onSuccess: (_, id) => invalidate(id),
    }),
    cancel: useMutation({
      mutationFn: returnsApi.cancel,
      onSuccess: (_, id) => invalidate(id),
    }),
  };
};
