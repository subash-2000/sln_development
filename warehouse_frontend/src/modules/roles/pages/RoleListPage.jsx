import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useRoles, useUpdateRole } from '../hooks/use-roles';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const RoleListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Role Name', sortable: true },
    { key: 'description', label: 'Description' },
    {
      key: 'permissions',
      label: 'Permissions Count',
      type: 'number',
      render: (val) => (Array.isArray(val) ? val.length : 0),
      widthClass: 'w-36'
    },
    { key: 'is_system_role', label: 'System', type: 'boolean', widthClass: 'w-24' },
    { key: 'is_active', label: 'Status', type: 'status', render: (val) => val ? 'ACTIVE' : 'INACTIVE' },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns
  });

  // Note: Roles API currently might not support full server-side params, 
  // but we follow the standard for UI consistency.
  const { data, isLoading, isFetching, error, refetch } = useRoles(list.params);
  const { mutateAsync: updateRole } = useUpdateRole();

  const handleToggleStatus = async (role) => {
    if (role.is_system_role) return;
    const isCurrentlyActive = isEntityActive(role);
    try {
      await updateRole({
        id: role.id,
        data: {
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} role:`, err);
    }
  };

  const renderRowActions = (role) => {
    const isActive = isEntityActive(role);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Permissions', onClick: () => navigate(`/roles/${role.id}`) },
          { type: 'edit', label: 'Edit Role', onClick: () => navigate(`/roles/${role.id}/edit`), hidden: role.is_system_role },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(role),
            hidden: role.is_system_role || !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(role),
            hidden: role.is_system_role || isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', role.id), variant: 'danger', hidden: role.is_system_role },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Roles"
      description="Define access levels and assign permissions to users."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Administration' }, 
        { label: 'Roles' }
      ]}
      createTo="/roles/new"
      createLabel="Add Role"
      canCreate={true}
      showSupplierFilter={false}
      searchPlaceholder="Search by role code or name..."
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
      onRowClick={(role) => navigate(`/roles/${role.id}`)}
      emptyTitle="No roles found"
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

export default RoleListPage;
