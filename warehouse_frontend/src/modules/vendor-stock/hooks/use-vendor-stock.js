import { useQuery } from '@tanstack/react-query';
import { vendorStockApi } from '../api/vendor-stock.api';

export const useVendorStock = (params) => useQuery({
  queryKey: ['vendor-stock', params],
  queryFn: () => vendorStockApi.list(params),
  placeholderData: (previous) => previous,
});
