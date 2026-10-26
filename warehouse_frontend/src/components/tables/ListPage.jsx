import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import PageHeader from '../common/PageHeader';
import Button from '../ui/Button';
import Card from '../ui/Card';
import ListToolbar from './ListToolbar';
import QuickFilters from './QuickFilters';
import DataTable from './DataTable';
import FilterPanel from './FilterPanel';
import ColumnSelector from './ColumnSelector';
import VendorFilter from './VendorFilter';

const ListPage = ({
  title,
  description,
  breadcrumbs,
  createTo,
  createLabel,
  canCreate = true,
  searchPlaceholder,
  searchWidthClass,
  searchValue,
  onSearchChange,
  onRefresh,
  onExport,
  onImport,
  toolbarExtra,
  customToolbar,
  companyControl,
  supplierControl,
  showCompanyFilter = false,
  showSupplierFilter = true,
  quickFilters,
  quickFilterValue,
  onQuickFilterChange,
  filterContent, // For FilterPanel children
  onApplyFilters,
  onClearFilters,
  hasActiveFilters,
  columns,
  onToggleColumn,
  rows,
  actions, // Row actions (function returning RowActions component)
  isLoading,
  isFetching,
  error,
  onRetry,
  pagination,
  sorting,
  onSort,
  emptyTitle,
  onRowClick,
  selectable,
  selectedIds,
  onToggleRow,
  onTogglePage,
}) => {
  return (
    <div className="flex-1 flex flex-col space-y-6">
      <PageHeader
        title={title}
        actions={
          canCreate && createTo ? (
            <Link to={createTo}>
              <Button leftIcon={<Plus size={18} />}>{createLabel}</Button>
            </Link>
          ) : null
        }
      />

      <Card className="overflow-visible">
        <Card.Body className="p-4 space-y-4">
          {customToolbar || (
            <ListToolbar
              searchPlaceholder={searchPlaceholder}
              searchWidthClass={searchWidthClass}
              searchValue={searchValue}
              onSearchChange={onSearchChange}
              onRefresh={onRefresh}
              onExport={onExport}
              onImport={onImport}
              companyControl={
                supplierControl || companyControl || (showSupplierFilter ? <VendorFilter /> : null)
              }
              filterControl={
                filterContent && (
                  <FilterPanel
                    onApply={onApplyFilters}
                    onClear={onClearFilters}
                    hasActiveFilters={hasActiveFilters}
                  >
                    {filterContent}
                  </FilterPanel>
                )
              }
              columnControl={
                columns && onToggleColumn && (
                  <ColumnSelector columns={columns} onToggleColumn={onToggleColumn} />
                )
              }
              extraActions={toolbarExtra}
            />
          )}
          {quickFilters && (
            <div className="pt-3 border-t border-gray-100">
              <QuickFilters
                options={quickFilters}
                value={quickFilterValue}
                onChange={onQuickFilterChange}
              />
            </div>
          )}
        </Card.Body>
      </Card>

      <DataTable
        className="flex-1"
        columns={columns}
        data={rows}
        actions={actions}
        isLoading={isLoading}
        isFetching={isFetching}
        error={error}
        onRetry={onRetry}
        pagination={pagination}
        sorting={sorting}
        onSort={onSort}
        onRowClick={onRowClick}
        emptyTitle={emptyTitle}
        hasFilters={hasActiveFilters || Boolean(searchValue)}
        onClearFilters={onClearFilters}
        emptyActionLabel={createLabel}
        onEmptyAction={createTo ? () => window.location.assign(createTo) : undefined}
        selectable={selectable}
        selectedIds={selectedIds}
        onToggleRow={onToggleRow}
        onTogglePage={onTogglePage}
      />
    </div>
  );
};

export default ListPage;
