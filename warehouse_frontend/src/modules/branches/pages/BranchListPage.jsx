import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useBranches, useUpdateBranch } from '../hooks/use-branches';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const BranchListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Branch Name', sortable: true },
    { key: 'company_name', label: 'Company' },
    { key: 'gstin', label: 'GSTIN', widthClass: 'w-40' },
    { key: 'branch_type', label: 'Type', widthClass: 'w-28' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'updated_at', label: 'Updated', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useBranches(list.params);
  const { mutateAsync: updateBranch } = useUpdateBranch();

  const handleToggleStatus = async (branch) => {
    const isCurrentlyActive = isEntityActive(branch);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateBranch({
        id: branch.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} branch:`, err);
    }
  };

  const renderRowActions = (branch) => {
    const isActive = isEntityActive(branch);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/branches/${branch.id}`) },
          { type: 'edit', label: 'Edit Branch', onClick: () => navigate(`/branches/${branch.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(branch),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(branch),
            hidden: isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', branch.id), variant: 'danger' },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Branches"
      description="Manage company branches and operational locations."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Masters' }, 
        { label: 'Branches' }
      ]}
      createTo="/branches/new"
      createLabel="Add Branch"
      canCreate={true}
      showSupplierFilter={false}
      searchPlaceholder="Search by branch code or name..."
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
      onRowClick={(branch) => navigate(`/branches/${branch.id}`)}
      emptyTitle="No branches found"
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

export default BranchListPage;
