import { useQuery } from '@tanstack/react-query';
import { inventoryApi } from '../api/inventory.api';

export const useStock = (params) => useQuery({
  queryKey: ['inventory', 'stock', params],
  queryFn: () => inventoryApi.stock(params),
  placeholderData: (previous) => previous,
});

export const useTransactions = (params) => useQuery({
  queryKey: ['inventory', 'transactions', params],
  queryFn: () => inventoryApi.transactions(params),
  placeholderData: (previous) => previous,
});

export const useTransaction = (id) => useQuery({
  queryKey: ['inventory', 'transaction', id],
  queryFn: () => inventoryApi.transaction(id),
  enabled: Boolean(id),
  staleTime: 0,
  refetchOnMount: 'always',
});

export const useLedger = (params) => useQuery({
  queryKey: ['inventory', 'ledger', params],
  queryFn: () => inventoryApi.ledger(params),
  placeholderData: (previous) => previous,
});
