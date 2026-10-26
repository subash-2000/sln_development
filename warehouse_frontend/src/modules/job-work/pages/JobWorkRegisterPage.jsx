import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useIssueJobWorkMaterials, useJobWorkRegister } from '../hooks/use-job-work';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const JobWorkRegisterPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'job_work_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'product_name', label: 'Product' },
    { key: 'issue_date', label: 'Date', type: 'date', sortable: true },
    { key: 'received_qty', label: 'Received', type: 'quantity', widthClass: 'w-24' },
    { key: 'lifted_qty', label: 'Lifted', type: 'quantity', widthClass: 'w-24' },
    { key: 'balance_qty', label: 'Closing', type: 'quantity', widthClass: 'w-24' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'job_work_number',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useJobWorkRegister(list.params);
  const { mutateAsync: issueMaterials } = useIssueJobWorkMaterials();

  const handleIssue = async (order) => {
    const lines = order.lines || [];
    const items = lines
      .map((line) => ({
        product_id: line.product_id,
        quantity: Number(line.ordered_qty) - Number(line.issued_qty || 0) || Number(line.ordered_qty),
      }))
      .filter((item) => item.quantity > 0);
    if (!items.length) {
      window.alert('No pending quantity to issue on this order.');
      return;
    }
    await issueMaterials({ id: order.id, data: { items } });
    refetch();
  };

  const renderRowActions = (order) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Order', onClick: () => navigate(`/job-work/register/${order.id}`) },
        { type: 'edit', label: 'View / Issue', onClick: () => navigate(`/job-work/register/${order.id}/edit`), hidden: order.status === 'CANCELLED' },
        { type: 'approve', label: 'Issue Material', onClick: () => handleIssue(order), hidden: order.status !== 'DRAFT' },
      ]}
    />
  );

  return (
    <ListPage
      title="Job Work Register"
      description="Track processing work orders sent to suppliers and material reconciliation."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Job Work' }, 
        { label: 'Register' }
      ]}
      createTo="/job-work/register/new"
      createLabel="Create Job Work"
      canCreate={true}
      searchPlaceholder="Search by job work number or supplier..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'IN_PROCESS', label: 'In Process' },
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
      onRowClick={(order) => navigate(`/job-work/register/${order.id}`)}
      emptyTitle="No job work orders found"
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

export default JobWorkRegisterPage;
