import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useConfirmDispatch, useLogisticsDispatch } from '../hooks/use-logistics';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const LogisticsDispatchPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'dispatch_number', label: 'Dispatch No', sortable: true, widthClass: 'w-40' },
    { key: 'dispatch_date', label: 'Date', type: 'date', sortable: true },
    { key: 'customer_name', label: 'Customer' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'transporter_name', label: 'Transporter' },
    { key: 'lr_number', label: 'LR No', widthClass: 'w-32' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'dispatch_date', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useLogisticsDispatch(list.params);
  const { mutateAsync: confirmDispatch } = useConfirmDispatch();

  const handleConfirm = async (dispatch) => {
    if (!window.confirm(`Confirm dispatch ${dispatch.dispatch_number}?`)) return;
    await confirmDispatch(dispatch.id);
    refetch();
  };

  const renderRowActions = (dispatch) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View on Outward', onClick: () => navigate(`/logistics/outward`) },
        { type: 'approve', label: 'Confirm dispatch (stock)', onClick: () => handleConfirm(dispatch), hidden: dispatch.status !== 'DRAFT' && dispatch.status !== 'PACKED' },
      ]}
    />
  );

  return (
    <ListPage
      title="Dispatch Management"
      description="Track outbound dispatches, carrier assignments and final delivery confirmations."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Operations' },
        { label: 'Dispatch Control' },
      ]}
      canCreate={false}
      searchPlaceholder="Search by dispatch number, customer or LR number..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All Dispatches' },
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
      onRowClick={(dispatch) => navigate(`/logistics/dispatch/${dispatch.id}`)}
      emptyTitle="No dispatch orders found"
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

export default LogisticsDispatchPage;
