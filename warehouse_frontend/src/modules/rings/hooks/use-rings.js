import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ringsApi } from '../api/rings.api';

export const useRingsDocuments = (params) =>
  useQuery({
    queryKey: ['rings-documents', params],
    queryFn: () => ringsApi.listDocuments(params),
    placeholderData: (previous) => previous,
  });

export const useRingsSupplierTypes = (vendorId) =>
  useQuery({
    queryKey: ['rings-supplier-types', vendorId],
    queryFn: () => ringsApi.supplierTypes(vendorId),
    enabled: !!vendorId,
  });

export const useCreateRingsInward = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ringsApi.createInward,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rings-documents'] });
      queryClient.invalidateQueries({ queryKey: ['rings-stock'] });
    },
  });
};

export const useCreateRingsPick = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ringsApi.createPick,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rings-documents'] });
      queryClient.invalidateQueries({ queryKey: ['rings-stock'] });
    },
  });
};

export const useDispatchRingsPick = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => ringsApi.dispatchPick(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rings-documents'] });
      queryClient.invalidateQueries({ queryKey: ['rings-stock'] });
      queryClient.invalidateQueries({ queryKey: ['rings-sales'] });
    },
  });
};

export const useRingsStock = (params) =>
  useQuery({
    queryKey: ['rings-stock', params],
    queryFn: () => ringsApi.stock(params),
  });

export const useRingsDayClose = (params, enabled = true) =>
  useQuery({
    queryKey: ['rings-day-close', params],
    queryFn: () => ringsApi.dayClose(params),
    enabled,
  });

export const useRingsSales = (params) =>
  useQuery({
    queryKey: ['rings-sales', params],
    queryFn: () => ringsApi.sales(params),
  });
