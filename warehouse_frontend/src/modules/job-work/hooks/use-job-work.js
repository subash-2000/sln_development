import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { jobWorkApi } from '../api/job-work.api';

export const useJobWorkRegister = (params) =>
  useQuery({
    queryKey: ['job-work-register', params],
    queryFn: () => jobWorkApi.list(params),
    placeholderData: (previous) => previous,
  });

export const useJobWorkDCS = (params) =>
  useQuery({
    queryKey: ['job-work-dcs', params],
    queryFn: () => jobWorkApi.list({ ...params, dcs_only: true }),
    placeholderData: (previous) => previous,
  });

export const useJobWorkOrder = (id) =>
  useQuery({
    queryKey: ['job-work-order', id],
    queryFn: () => jobWorkApi.getById(id),
    enabled: Boolean(id),
  });

export const useCreateJobWorkOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: jobWorkApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-work-register'] });
      queryClient.invalidateQueries({ queryKey: ['job-work-dcs'] });
    },
  });
};

export const useIssueJobWorkMaterials = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => jobWorkApi.issueMaterials(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['job-work-register'] });
      queryClient.invalidateQueries({ queryKey: ['job-work-dcs'] });
      queryClient.invalidateQueries({ queryKey: ['job-work-order', variables.id] });
    },
  });
};
