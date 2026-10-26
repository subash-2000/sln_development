import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useTransactions } from '../hooks/use-inventory';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const TransactionListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'transaction_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'created_at', label: 'Date', type: 'datetime', sortable: true },
    { key: 'transaction_type', label: 'Type', widthClass: 'w-32' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'reference_document_number', label: 'Source Doc', widthClass: 'w-40' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'created_by_name', label: 'Created By' },
  ];

  const list = useListState({ 
    defaultSortBy: 'created_at', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useTransactions(list.params);

  const renderRowActions = (transaction) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Details', onClick: () => navigate(`/inventory/transactions/${transaction.id}`) },
        { type: 'approve', label: 'Confirm', onClick: () => console.log('Confirm', transaction.id), hidden: transaction.status !== 'DRAFT' },
        { type: 'reject', label: 'Cancel', onClick: () => console.log('Cancel', transaction.id), hidden: ['COMPLETED', 'CANCELLED'].includes(transaction.status), variant: 'danger' },
      ]}
    />
  );

  return (
    <ListPage
      title="Stock Transactions"
      description="Warehouse stock movements, receipts, deliveries and adjustments."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Inventory' }, 
        { label: 'Stock Transactions' }
      ]}
      canCreate={true}
      createTo="/inventory/transactions/new"
      createLabel="New Transaction"
      searchPlaceholder="Search by transaction number or reference..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'CONFIRMED', label: 'Confirmed' },
        { value: 'COMPLETED', label: 'Completed' },
        { value: 'CANCELLED', label: 'Cancelled' },
      ]}
      quickFilterValue={list.status}
      onQuickFilterChange={list.setStatus}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      actions={renderRowActions}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      onRowClick={(transaction) => navigate(`/inventory/transactions/${transaction.id}`)}
      emptyTitle="No stock transactions found"
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

export default TransactionListPage;
