import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useLogisticsOutward } from '../hooks/use-logistics';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const LogisticsOutwardPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'dispatch_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'dispatch_date', label: 'Date', type: 'date', sortable: true },
    { key: 'order_type', label: 'Type', widthClass: 'w-28' },
    { key: 'customer_name', label: 'Customer' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'vehicle_number', label: 'Vehicle', widthClass: 'w-32' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'dispatch_date', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useLogisticsOutward(list.params);

  const renderRowActions = (outward) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Details', onClick: () => navigate(`/logistics/outward/${outward.id}`) },
        { type: 'edit', label: 'Edit Outward', onClick: () => navigate(`/logistics/outward/${outward.id}/edit`), hidden: outward.status !== 'DRAFT' },
        { type: 'delete', label: 'Cancel', onClick: () => console.log('Cancel', outward.id), variant: 'danger', hidden: ['DELIVERED', 'CANCELLED'].includes(outward.status) },
      ]}
    />
  );

  return (
    <ListPage
      title="Outward Transactions"
      description="Manage stock dispatches, vehicle assignments and outbound logistics."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Operations' },
        { label: 'Outward' },
      ]}
      createTo="/logistics/outward/new"
      createLabel="New Outward"
      canCreate={true}
      searchPlaceholder="Search by dispatch number, customer or vehicle..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'DISPATCHED', label: 'Dispatched' },
        { value: 'DELIVERED', label: 'Delivered' },
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
      onRowClick={(outward) => navigate(`/logistics/outward/${outward.id}`)}
      emptyTitle="No outward dispatch orders found"
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

export default LogisticsOutwardPage;
