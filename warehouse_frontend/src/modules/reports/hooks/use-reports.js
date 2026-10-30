import { useQuery } from '@tanstack/react-query';
import { reportsApi } from '../api/reports.api';

export const useVehicleReports = (params) =>
  useQuery({
    queryKey: ['reports', 'vehicles', params],
    queryFn: () => reportsApi.getVehicleReports(params),
    placeholderData: (previous) => previous,
  });

export const useInwardReports = (params) =>
  useQuery({
    queryKey: ['reports', 'inward', params],
    queryFn: () => reportsApi.getInwardReports(params),
    placeholderData: (previous) => previous,
  });

export const useOutwardReports = (params) =>
  useQuery({
    queryKey: ['reports', 'outward', params],
    queryFn: () => reportsApi.getOutwardReports(params),
    placeholderData: (previous) => previous,
  });

export const useDailyStockReports = (params) =>
  useQuery({
    queryKey: ['reports', 'daily-stock', params],
    queryFn: () => reportsApi.getDailyStockReports(params),
    placeholderData: (previous) => previous,
  });

export const useInvoiceReports = (params) =>
  useQuery({
    queryKey: ['reports', 'invoices', params],
    queryFn: () => reportsApi.getInvoiceReports(params),
    placeholderData: (previous) => previous,
  });

export const useSupplierStockReports = (params) =>
  useQuery({
    queryKey: ['reports', 'supplier-stock', params],
    queryFn: () => reportsApi.getSupplierStockReports(params),
    placeholderData: (previous) => previous,
  });

