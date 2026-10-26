import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { logisticsApi } from '../api/logistics.api';
import { inventoryApi } from '../../inventory/api/inventory.api';

export const useLogisticsInward = (params) => {
  return useQuery({
    queryKey: ['logistics-inward', params],
    queryFn: () => inventoryApi.transactions({ ...params, transaction_type: 'RECEIPT' }),
    placeholderData: (previous) => previous,
  });
};

export const useCreateLogisticsInward = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => logisticsApi.inward.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['logistics-inward'] }),
  });
};

export const useLogisticsOutward = (params) => {
  return useQuery({
    queryKey: ['logistics-outward', params],
    queryFn: () => logisticsApi.dispatch.list(params),
    placeholderData: (previous) => previous,
  });
};

export const useLogisticsDispatch = (params) => {
  return useQuery({
    queryKey: ['logistics-dispatch', params],
    queryFn: () => logisticsApi.dispatch.list(params),
    placeholderData: (previous) => previous,
  });
};

export const useCreateDispatchOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => logisticsApi.dispatch.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-outward'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-dispatch'] });
    },
  });
};

export const useConfirmDispatch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => logisticsApi.dispatch.confirm(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-outward'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-dispatch'] });
    },
  });
};
