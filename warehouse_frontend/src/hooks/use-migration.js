import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { migrationApi } from '../services/api/migration.api';

export const useImport = () => {
  return useMutation({
    mutationFn: ({ type, file, mapping }) => migrationApi.import(type, file, mapping),
  });
};

export const useExport = () => {
  return useMutation({
    mutationFn: ({ type, format }) => migrationApi.export(type, format),
  });
};

export const useImportBatches = () => {
  return useQuery({
    queryKey: ['import-batches'],
    queryFn: migrationApi.getBatches,
  });
};
