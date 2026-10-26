import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useQuery } from '@tanstack/react-query';
import { invoicingApi } from '../api/invoicing.api';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const InvoicingListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'invoice_number', label: 'Invoice No', sortable: true, widthClass: 'w-40' },
    { key: 'invoice_date', label: 'Date', type: 'date', sortable: true },
    { key: 'customer_name', label: 'Customer' },
    { key: 'subtotal_amount', label: 'Basic', type: 'currency' },
    { key: 'tax_amount', label: 'GST', type: 'currency' },
    { key: 'total_amount', label: 'Total', type: 'currency' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'invoice_date', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['invoices', list.params],
    queryFn: () => invoicingApi.list(list.params),
    placeholderData: (previous) => previous,
  });

  const renderRowActions = (invoice) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Invoice', onClick: () => navigate(`/finance/invoicing/${invoice.id}`) },
        { type: 'edit', label: 'Edit Invoice', onClick: () => navigate(`/finance/invoicing/${invoice.id}/edit`), hidden: invoice.status !== 'DRAFT' },
        { type: 'approve', label: 'Post Invoice', onClick: () => console.log('Post', invoice.id), hidden: invoice.status !== 'DRAFT' },
        { type: 'reject', label: 'Cancel', onClick: () => console.log('Cancel', invoice.id), hidden: ['PAID', 'CANCELLED'].includes(invoice.status), variant: 'danger' },
      ]}
    />
  );

  return (
    <ListPage
      title="Invoices"
      description="GST invoices, payments and outstanding balances."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Invoicing' }, 
        { label: 'Invoices' }
      ]}
      createTo="/finance/invoicing/new"
      createLabel="Create Invoice"
      canCreate={true}
      searchPlaceholder="Search by invoice number or customer..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'POSTED', label: 'Posted' },
        { value: 'PARTIALLY_PAID', label: 'Partially Paid' },
        { value: 'PAID', label: 'Paid' },
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
      onRowClick={(invoice) => navigate(`/finance/invoicing/${invoice.id}`)}
      emptyTitle="No invoices found"
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

export default InvoicingListPage;
