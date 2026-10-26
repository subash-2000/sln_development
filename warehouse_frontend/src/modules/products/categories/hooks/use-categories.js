import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { categoriesApi } from '../api/categories.api';

export const useCategories = (params) => {
  return useQuery({
    queryKey: ['product-categories', params],
    queryFn: () => categoriesApi.list(params),
    placeholderData: (previous) => previous,
  });
};

export const useCategory = (id) => {
  return useQuery({
    queryKey: ['product-categories', id],
    queryFn: () => categoriesApi.getById(id),
    enabled: !!id,
  });
};

export const useCreateCategory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: categoriesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-categories'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });
};

export const useUpdateCategory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => categoriesApi.update(id, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['product-categories'] });
      queryClient.invalidateQueries({ queryKey: ['product-categories', vars.id] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });
};
