import { useMemo, useState, useCallback, useEffect, useRef } from 'react';
import { useDebouncedValue } from './use-debounced-value';
import { useAuthStore } from '../store/auth.store';

export const useListState = ({
  defaultPageSize = 25,
  defaultSortBy,
  defaultSortOrder = 'asc',
  defaultStatus = 'ALL',
  initialColumns = [],
} = {}) => {
  const { companyContext, vendorContext } = useAuthStore();
  const [searchInput, setSearchInputState] = useState('');
  const search = useDebouncedValue(searchInput, 400);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeState] = useState(defaultPageSize);
  const [sortBy, setSortBy] = useState(defaultSortBy);
  const [sortOrder, setSortOrder] = useState(defaultSortOrder);
  const [status, setStatusState] = useState(defaultStatus);
  const [filters, setFiltersState] = useState({});
  const [columns, setColumns] = useState(initialColumns);

  // Automatically reset to page 1 whenever the company context filter changes
  const prevCompanyRef = useRef(companyContext);
  useEffect(() => {
    if (prevCompanyRef.current !== companyContext) {
      prevCompanyRef.current = companyContext;
      setPage(1);
    }
  }, [companyContext]);

  const prevVendorRef = useRef(vendorContext);
  useEffect(() => {
    if (prevVendorRef.current !== vendorContext) {
      prevVendorRef.current = vendorContext;
      setPage(1);
    }
  }, [vendorContext]);

  const setSearchInput = useCallback((value) => {
    setSearchInputState(value);
    setPage(1);
  }, []);

  const setPageSize = useCallback((value) => {
    setPageSizeState(value);
    setPage(1);
  }, []);

  const setStatus = useCallback((value) => {
    setStatusState(value);
    setPage(1);
  }, []);

  const setFilters = useCallback((value) => {
    setFiltersState(value);
    setPage(1);
  }, []);

  const handleSort = useCallback((key, order) => {
    if (order === 'asc' || order === 'desc') {
      setSortBy(key);
      setSortOrder(order);
      setPage(1);
      return;
    }
    setSortBy((prevSortBy) => {
      if (prevSortBy === key) {
        setSortOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
        return prevSortBy;
      }
      setSortOrder('asc');
      return key;
    });
    setPage(1);
  }, []);

  const toggleColumn = useCallback((key) => {
    setColumns((prev) =>
      prev.map((col) =>
        col.key === key ? { ...col, visible: col.visible === false } : col
      )
    );
  }, []);

  const clearFilters = useCallback(() => {
    setSearchInputState('');
    setStatusState(defaultStatus);
    setFiltersState({});
    setPage(1);
  }, [defaultStatus]);

  const hasActiveFilters = useMemo(() => {
    return Object.keys(filters).length > 0 || Boolean(vendorContext);
  }, [filters, vendorContext]);

  const params = useMemo(
    () => ({
      page,
      page_size: pageSize,
      search,
      sort_by: sortBy,
      sort_order: sortOrder,
      status: status === 'ALL' ? undefined : status,
      company_id: companyContext,
      ...(vendorContext ? { vendor_id: vendorContext } : {}),
      ...filters,
    }),
    [page, pageSize, search, sortBy, sortOrder, status, filters, companyContext, vendorContext]
  );

  return {
    searchInput,
    setSearchInput,
    page,
    setPage,
    pageSize,
    setPageSize,
    sortBy,
    sortOrder,
    handleSort,
    status,
    setStatus,
    filters,
    setFilters,
    clearFilters,
    hasActiveFilters,
    columns,
    setColumns,
    toggleColumn,
    params,
  };
};
