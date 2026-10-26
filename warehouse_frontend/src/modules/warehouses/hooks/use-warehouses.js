import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { warehousesApi } from '../api/warehouses.api';

export const useWarehouses = (params) => {
  return useQuery({
    queryKey: ['warehouses', params],
    queryFn: () => warehousesApi.list(params),
    placeholderData: (previous) => previous,
  });
};

export const useWarehouse = (id) => {
  return useQuery({
    queryKey: ['warehouses', id],
    queryFn: () => warehousesApi.getById(id),
    enabled: !!id,
  });
};

export const useCreateWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: warehousesApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['warehouses'] }),
  });
};

export const useUpdateWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => warehousesApi.update(id, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['warehouses', vars.id] });
    },
  });
};
