import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useCompanies, useUpdateCompany } from '../hooks/use-companies';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const CompanyListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Company Name', sortable: true },
    { key: 'gstin', label: 'GSTIN', widthClass: 'w-40' },
    { key: 'branch_count', label: 'Branches', type: 'number', widthClass: 'w-24' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'created_at', label: 'Created At', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useCompanies(list.params);
  const { mutateAsync: updateCompany } = useUpdateCompany();

  const handleToggleStatus = async (company) => {
    const isCurrentlyActive = isEntityActive(company);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateCompany({
        id: company.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} company:`, err);
    }
  };

  const renderRowActions = (company) => {
    const isActive = isEntityActive(company);
    return (
      <RowActions
        actions={[
          {
            type: 'view',
            label: 'View Details',
            onClick: () => navigate(`/companies/${company.id}`),
          },
          {
            type: 'edit',
            label: 'Edit Company',
            onClick: () => navigate(`/companies/${company.id}/edit`),
          },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(company),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(company),
            hidden: isActive,
          },
          {
            type: 'delete',
            label: 'Delete',
            onClick: () => console.log('Delete', company.id),
            variant: 'danger',
          },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Companies"
      description="Manage operating companies and tenant organizations."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Masters' }, 
        { label: 'Companies' }
      ]}
      createTo="/companies/new"
      createLabel="Add Company"
      canCreate={true}
      showSupplierFilter={false}
      searchPlaceholder="Search by company code or name..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'ACTIVE', label: 'Active' },
        { value: 'INACTIVE', label: 'Inactive' },
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
      onRowClick={(company) => navigate(`/companies/${company.id}`)}
      emptyTitle="No companies found"
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

export default CompanyListPage;
