import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { branchesApi } from '../api/branches.api';

export const useBranches = (params) => {
  return useQuery({
    queryKey: ['branches', params],
    queryFn: () => branchesApi.list(params),
    placeholderData: (previousData) => previousData,
  });
};

export const useBranch = (id) => {
  return useQuery({
    queryKey: ['branches', id],
    queryFn: () => branchesApi.getById(id),
    enabled: !!id,
  });
};

export const useCreateBranch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: branchesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['branches'] });
    },
  });
};

export const useUpdateBranch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => branchesApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['branches'] });
      queryClient.invalidateQueries({ queryKey: ['branches', variables.id] });
    },
  });
};

