import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { productsApi } from '../../api/products.api';

export const useUomMasterList = () =>
  useQuery({
    queryKey: ['uoms-master'],
    queryFn: async () => {
      const data = await productsApi.listUoms();
      return Array.isArray(data) ? data : [];
    },
  });

export const useUomCategories = () =>
  useQuery({
    queryKey: ['uom-categories'],
    queryFn: async () => {
      const data = await productsApi.listUomCategories();
      return Array.isArray(data) ? data : [];
    },
  });

export const useUom = (id) =>
  useQuery({
    queryKey: ['uom', id],
    queryFn: () => productsApi.getUom(id),
    enabled: Boolean(id),
  });

export const useCreateUom = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: productsApi.createUom,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uoms-master'] });
      queryClient.invalidateQueries({ queryKey: ['uoms'] });
    },
  });
};

export const useUpdateUom = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => productsApi.updateUom(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['uoms-master'] });
      queryClient.invalidateQueries({ queryKey: ['uom', id] });
      queryClient.invalidateQueries({ queryKey: ['uoms'] });
    },
  });
};
