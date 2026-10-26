import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../../hooks/use-list-state';
import ListPage from '../../../../components/tables/ListPage';
import RowActions from '../../../../components/tables/RowActions';
import { useUomMasterList } from '../hooks/use-uom-master';

const UomListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-24' },
    { key: 'name', label: 'Name', sortable: true },
    { key: 'category_name', label: 'Category', widthClass: 'w-32' },
    { key: 'uom_type', label: 'Type', widthClass: 'w-28' },
    { key: 'factor', label: 'Factor', widthClass: 'w-24' },
    { key: 'status', label: 'Status', type: 'status', widthClass: 'w-24' },
  ];

  const list = useListState({ defaultSortBy: 'code', initialColumns });
  const { data: allUoms = [], isLoading, isFetching, error, refetch } = useUomMasterList();

  const filtered = useMemo(() => {
    let rows = [...allUoms];
    const q = (list.params.search || '').trim().toLowerCase();
    if (q) {
      rows = rows.filter(
        (r) =>
          r.code?.toLowerCase().includes(q) ||
          r.name?.toLowerCase().includes(q) ||
          r.category_name?.toLowerCase().includes(q)
      );
    }
    const sortKey = list.sortBy || 'code';
    const dir = list.sortOrder === 'desc' ? -1 : 1;
    rows.sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
    return rows;
  }, [allUoms, list.params.search, list.sortBy, list.sortOrder]);

  const page = list.page;
  const pageSize = list.pageSize;
  const paged = filtered.slice((page - 1) * pageSize, page * pageSize);

  const renderRowActions = (row) => (
    <RowActions
      actions={[
        {
          type: 'edit',
          label: 'Edit',
          onClick: () => navigate(`/products/uom/${row.id}/edit`),
        },
      ]}
    />
  );

  return (
    <ListPage
      title="Units of Measure (UOM)"
      description="Master list of units used on products, stock, and transactions. Seeded defaults include Units (UNT), KG, etc."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Masters' },
        { label: 'UOM' },
      ]}
      createTo="/products/uom/new"
      createLabel="New UOM"
      showSupplierFilter={false}
      searchPlaceholder="Search by code, name or category..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      actions={renderRowActions}
      rows={paged}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      onRowClick={(row) => navigate(`/products/uom/${row.id}/edit`)}
      emptyTitle="No units of measure found"
      pagination={{
        currentPage: page,
        pageSize,
        totalRecords: filtered.length,
        onPageChange: list.setPage,
        onPageSizeChange: list.setPageSize,
      }}
    />
  );
};

export default UomListPage;
