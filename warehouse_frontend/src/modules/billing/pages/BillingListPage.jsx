import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useQuery } from '@tanstack/react-query';
import { billingApi } from '../api/billing.api';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const BillingListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'billing_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'period_name', label: 'Period', widthClass: 'w-32' },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'customer_name', label: 'Customer' },
    { key: 'total_storage_charges', label: 'Storage', type: 'currency' },
    { key: 'total_handling_charges', label: 'Handling', type: 'currency' },
    { key: 'total_amount', label: 'Total', type: 'currency' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'billing_number',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['billing-documents', list.params],
    queryFn: () => billingApi.documents(list.params),
    placeholderData: (previous) => previous,
  });

  const renderRowActions = (doc) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Details', onClick: () => navigate(`/finance/billing/${doc.id}`) },
        { type: 'edit', label: 'Edit Document', onClick: () => navigate(`/finance/billing/${doc.id}/edit`), hidden: doc.status !== 'DRAFT' },
        { type: 'approve', label: 'Confirm Billing', onClick: () => console.log('Confirm', doc.id), hidden: doc.status !== 'DRAFT' },
        { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', doc.id), variant: 'danger', hidden: doc.status !== 'DRAFT' },
      ]}
    />
  );

  return (
    <ListPage
      title="Billing & Charges"
      description="Manage warehouse storage and handling charges for suppliers and customers."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Finance' }, 
        { label: 'Billing' }
      ]}
      createTo="/finance/billing/new"
      createLabel="Create Billing"
      canCreate={true}
      searchPlaceholder="Search by billing number, supplier or customer..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'CONFIRMED', label: 'Confirmed' },
        { value: 'INVOICED', label: 'Invoiced' },
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
      onRowClick={(doc) => navigate(`/finance/billing/${doc.id}`)}
      emptyTitle="No billing documents found"
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

export default BillingListPage;
