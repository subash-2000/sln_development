import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { transportersApi } from '../api/transporters.api';

export const useTransporters = (params) =>
  useQuery({
    queryKey: ['transporters', params],
    queryFn: () => transportersApi.list(params),
    placeholderData: (previous) => previous,
  });

export const useTransporter = (id) =>
  useQuery({
    queryKey: ['transporters', id],
    queryFn: () => transportersApi.getById(id),
    enabled: Boolean(id),
  });

export const useCreateTransporter = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: transportersApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['transporters'] }),
  });
};

export const useUpdateTransporter = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => transportersApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
      queryClient.invalidateQueries({ queryKey: ['transporters', id] });
    },
  });
};
