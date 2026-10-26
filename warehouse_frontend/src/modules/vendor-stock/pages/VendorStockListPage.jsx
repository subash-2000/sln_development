import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useVendorStock } from '../hooks/use-vendor-stock';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const VendorStockListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'agreement_number', label: 'Agreement', sortable: true, widthClass: 'w-40' },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'start_date', label: 'Start Date', type: 'date', sortable: true },
    { key: 'end_date', label: 'End Date', type: 'date' },
    { key: 'billing_cycle', label: 'Cycle', widthClass: 'w-32' },
    { key: 'free_storage_days', label: 'Free Days', type: 'number', widthClass: 'w-24' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'agreement_number',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useVendorStock(list.params);

  const renderRowActions = (agreement) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Agreement', onClick: () => navigate(`/inventory/supplier-stock/${agreement.id}`) },
        { type: 'edit', label: 'Edit Agreement', onClick: () => navigate(`/inventory/supplier-stock/${agreement.id}/edit`), hidden: agreement.status !== 'DRAFT' },
        { type: 'activate', label: 'Activate', onClick: () => console.log('Activate', agreement.id), hidden: agreement.status !== 'DRAFT' },
        { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', agreement.id), variant: 'danger', hidden: agreement.status !== 'DRAFT' },
      ]}
    />
  );

  return (
    <ListPage
      title="Supplier Stock Agreements"
      description="Manage consignment agreements and supplier-owned stock contracts."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Inventory' }, 
        { label: 'Supplier Stock' }
      ]}
      createTo="/inventory/supplier-stock/new"
      createLabel="New Agreement"
      canCreate={true}
      searchPlaceholder="Search by agreement number or supplier..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'ACTIVE', label: 'Active' },
        { value: 'EXPIRED', label: 'Expired' },
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
      onRowClick={(agreement) => navigate(`/inventory/supplier-stock/${agreement.id}`)}
      emptyTitle="No agreements found"
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

export default VendorStockListPage;
