import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { locationsApi } from '../api/locations.api';

export const useLocations = (params) => {
  return useQuery({
    queryKey: ['locations', params],
    queryFn: () => locationsApi.list(params),
    placeholderData: (previous) => previous,
  });
};

export const useLocation = (id) => {
  return useQuery({
    queryKey: ['locations', id],
    queryFn: () => locationsApi.getById(id),
    enabled: !!id,
  });
};

export const useCreateLocation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: locationsApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['locations'] }),
  });
};

export const useUpdateLocation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => locationsApi.update(id, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
      queryClient.invalidateQueries({ queryKey: ['locations', vars.id] });
    },
  });
};
