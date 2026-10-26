import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useReturns } from '../hooks/use-returns';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
const ReturnsListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'return_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'return_date', label: 'Date', type: 'date', sortable: true },
    { key: 'return_type', label: 'Type', widthClass: 'w-28' },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'customer_name', label: 'Customer' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({
    defaultSortBy: 'return_date',
    defaultSortOrder: 'desc',
    initialColumns,
  });

  const { data, isLoading, isFetching, error, refetch } = useReturns(list.params);

  const renderRowActions = (order) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Details', onClick: () => navigate(`/returns/list/${order.id}`) },
        { type: 'edit', label: 'Edit Order', onClick: () => navigate(`/returns/list/${order.id}/edit`), hidden: order.status !== 'DRAFT' },
        {
          type: 'approve',
          label: 'Open & process',
          onClick: () => navigate(`/returns/list/${order.id}`),
          hidden: order.status === 'COMPLETED' || order.status === 'CANCELLED',
        },
        { type: 'reject', label: 'Cancel', onClick: () => console.log('Cancel', order.id), hidden: ['COMPLETED', 'CANCELLED'].includes(order.status), variant: 'danger' },
      ]}
    />
  );

  return (
    <ListPage
      title="Rejection & Returns"
      description="Track material returns from customers and rejections back to suppliers."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Returns' }, 
        { label: 'Rejection & Returns' }
      ]}
      createTo="/returns/list/new"
      createLabel="New Return"
      canCreate={true}
      searchPlaceholder="Search by return number, supplier or customer..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      hasActiveFilters={list.hasActiveFilters}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'RECEIVED', label: 'Received' },
        { value: 'COMPLETED', label: 'Completed' },
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
      onRowClick={(order) => navigate(`/returns/list/${order.id}`)}
      emptyTitle="No returns found"
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

export default ReturnsListPage;
