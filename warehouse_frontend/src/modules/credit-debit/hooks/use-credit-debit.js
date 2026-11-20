import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { creditDebitApi } from '../api/credit-debit.api';

export const useCreditDebitNotes = (params) => useQuery({ queryKey: ['credit-debit-notes', params], queryFn: () => creditDebitApi.list(params), placeholderData: (old) => old });
export const useCreditDebitSummary = (params) => useQuery({ queryKey: ['credit-debit-summary', params], queryFn: () => creditDebitApi.summary(params) });
export const useCreditDebitActions = () => {
  const client = useQueryClient();
  const done = () => { client.invalidateQueries({ queryKey: ['credit-debit-notes'] }); client.invalidateQueries({ queryKey: ['credit-debit-summary'] }); };
  return {
    create: useMutation({ mutationFn: creditDebitApi.create, onSuccess: done }),
    update: useMutation({ mutationFn: ({ id, data }) => creditDebitApi.update(id, data), onSuccess: done }),
    confirm: useMutation({ mutationFn: creditDebitApi.confirm, onSuccess: done }),
    cancel: useMutation({ mutationFn: ({ id, reason }) => creditDebitApi.cancel(id, reason), onSuccess: done }),
  };
};
