import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../../hooks/use-list-state';
import { useCategories, useUpdateCategory } from '../hooks/use-categories';
import ListPage from '../../../../components/tables/ListPage';
import RowActions from '../../../../components/tables/RowActions';
import { isEntityActive } from '../../../../constants/status';

const CategoryListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Category Name', sortable: true },
    { key: 'description', label: 'Description' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'updated_at', label: 'Last Updated', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useCategories(list.params);
  const { mutateAsync: updateCategory } = useUpdateCategory();

  const handleToggleStatus = async (category) => {
    const isCurrentlyActive = isEntityActive(category);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateCategory({
        id: category.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} category:`, err);
    }
  };

  const renderRowActions = (category) => {
    const isActive = isEntityActive(category);
    return (
      <RowActions
        actions={[
          {
            type: 'view',
            label: 'View Products',
            onClick: () => navigate(`/masters/products?category_id=${category.id}`),
          },
          {
            type: 'edit',
            label: 'Edit Category',
            onClick: () => navigate(`/masters/products/categories/${category.id}/edit`),
          },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(category),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(category),
            hidden: isActive,
          },
          {
            type: 'delete',
            label: 'Delete',
            onClick: () => console.log('Delete', category.id),
            variant: 'danger',
          },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Product Categories"
      description="Manage product category hierarchy for warehouse items."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Masters' },
        { label: 'Products', to: '/masters/products' },
        { label: 'Categories' },
      ]}
      createTo="/masters/products/categories/new"
      createLabel="Add Category"
      canCreate={true}
      searchPlaceholder="Search by category code or name..."
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
      onRowClick={(category) => navigate(`/masters/products/categories/${category.id}/edit`)}
      emptyTitle="No categories found"
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

export default CategoryListPage;
