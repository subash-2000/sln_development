import React from 'react';
import { useListState } from '../../../hooks/use-list-state';
import { useQuery } from '@tanstack/react-query';
import { invoicingApi } from '../api/invoicing.api';
import ListPage from '../../../components/tables/ListPage';

const GstReportPage = () => {
  const initialColumns = [
    { key: 'invoice_number', label: 'Invoice No', sortable: true, widthClass: 'w-40' },
    { key: 'invoice_date', label: 'Date', type: 'date', sortable: true },
    { key: 'customer_name', label: 'Customer' },
    { key: 'subtotal_amount', label: 'Taxable Val', type: 'currency', widthClass: 'w-32' },
    { key: 'cgst_amount', label: 'CGST', type: 'currency', widthClass: 'w-24' },
    { key: 'sgst_amount', label: 'SGST', type: 'currency', widthClass: 'w-24' },
    { key: 'igst_amount', label: 'IGST', type: 'currency', widthClass: 'w-24' },
    { key: 'tax_amount', label: 'Total GST', type: 'currency', widthClass: 'w-32' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'invoice_date', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['gst-invoices', list.params],
    queryFn: () => invoicingApi.list(list.params),
    placeholderData: (previous) => previous,
  });

  const handleExport = () => {
    console.log('Exporting GST report...');
  };

  return (
    <ListPage
      title="GST Reports"
      description="Detailed GST breakup for all posted invoices, including CGST, SGST and IGST components."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Invoicing' }, 
        { label: 'GST Reports' }
      ]}
      canCreate={false}
      searchPlaceholder="Search by invoice number or customer..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      onExport={handleExport}
      quickFilters={[
        { value: 'ALL', label: 'All Invoices' },
        { value: 'POSTED', label: 'Posted' },
        { value: 'PAID', label: 'Paid' },
      ]}
      quickFilterValue={list.status}
      onQuickFilterChange={list.setStatus}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      emptyTitle="No GST data found"
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

export default GstReportPage;
