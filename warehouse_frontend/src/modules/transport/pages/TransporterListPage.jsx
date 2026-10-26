import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useTransporters, useUpdateTransporter } from '../hooks/use-transporters';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const TransporterListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-28' },
    { key: 'name', label: 'Transporter Name', sortable: true },
    { key: 'gstin', label: 'GSTIN', widthClass: 'w-40' },
    { key: 'contact_person', label: 'Contact' },
    { key: 'phone', label: 'Phone', widthClass: 'w-32' },
    { key: 'vehicle_number', label: 'Vehicle No.', widthClass: 'w-32' },
    { key: 'driver_name', label: 'Driver' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ defaultSortBy: 'name', initialColumns });
  const { data, isLoading, isFetching, error, refetch } = useTransporters(list.params);
  const { mutateAsync: updateTransporter } = useUpdateTransporter();

  const handleToggleStatus = async (row) => {
    const active = isEntityActive(row);
    await updateTransporter({
      id: row.id,
      data: { status: active ? 'INACTIVE' : 'ACTIVE' },
    });
    refetch();
  };

  const renderRowActions = (row) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View / Edit', onClick: () => navigate(`/transport/${row.id}`) },
        {
          type: 'toggle',
          label: isEntityActive(row) ? 'Deactivate' : 'Activate',
          onClick: () => handleToggleStatus(row),
        },
      ]}
    />
  );

  return (
    <ListPage
      title="Transport Master"
      description="Manage transporters and optional default vehicle/driver details for dispatch."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Masters' },
        { label: 'Transport' },
      ]}
      createTo="/transport/new"
      createLabel="New Transporter"
      searchPlaceholder="Search by code, name, GSTIN or phone..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
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
      onRowClick={(row) => navigate(`/transport/${row.id}`)}
      emptyTitle="No transporters found"
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

export default TransporterListPage;
