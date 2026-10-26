import React from 'react';
import { useListState } from '../../../hooks/use-list-state';
import { useLedger } from '../hooks/use-inventory';
import ListPage from '../../../components/tables/ListPage';

const LedgerListPage = () => {
  const initialColumns = [
    { key: 'posting_date', label: 'Posted Date', type: 'datetime', sortable: true },
    { key: 'product_name', label: 'Product' },
    { key: 'sku', label: 'SKU', widthClass: 'w-32' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'location_name', label: 'Location' },
    { key: 'entry_type', label: 'Entry Type', widthClass: 'w-32' },
    { key: 'quantity_delta', label: 'Delta', type: 'quantity', widthClass: 'w-24' },
    { key: 'running_balance', label: 'Balance', type: 'quantity', widthClass: 'w-24' },
    { key: 'reference', label: 'Reference', widthClass: 'w-40' },
  ];

  const list = useListState({ 
    defaultSortBy: 'posting_date', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useLedger(list.params);

  const handleExport = () => {
    console.log('Exporting stock ledger...');
  };

  return (
    <ListPage
      title="Stock Ledger"
      description="Detailed historical record of all inventory movements and running balances."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Inventory' }, 
        { label: 'Stock Ledger' }
      ]}
      canCreate={false}
      searchPlaceholder="Search by reference, product or SKU..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      onExport={handleExport}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      emptyTitle="No ledger entries found"
      pagination={{
        currentPage: list.page,
        pageSize: list.pageSize,
        totalRecords: data?.pagination?.total || 0,
        onPageChange: list.setPage,
        onPageSizeChange: list.setPageSize,
      }}
    />
  );
};

export default LedgerListPage;
