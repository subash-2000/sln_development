import { twMerge } from 'tailwind-merge';
import { ChevronUp, ChevronDown } from 'lucide-react';
import TableSkeleton from './TableSkeleton';
import Pagination from './Pagination';
import EmptyState from '../feedback/EmptyState';
import ErrorState from '../feedback/ErrorState';
import StatusBadge from '../ui/StatusBadge';
import { formatCurrency, formatDate, formatDateTime, formatNumber, formatQuantity } from '../../utils/formatters';

const getValue = (row, key) => {
  if (!key) return undefined;
  return key.split('.').reduce((acc, part) => acc?.[part], row);
};

const numericTypes = new Set(['number', 'currency', 'quantity', 'percentage']);

const columnAlign = (column) => column.align || (numericTypes.has(column.type) ? 'right' : undefined);

const renderTypedValue = (column, value, row) => {
  if (column.render) return column.render(value, row);
  switch (column.type) {
    case 'status':
      return <StatusBadge status={value} />;
    case 'currency':
      return formatCurrency(value);
    case 'quantity':
      return formatQuantity(value, column.uomKey ? row[column.uomKey] : column.uom);
    case 'number':
      return formatNumber(value);
    case 'date':
      return formatDate(value);
    case 'datetime':
      return formatDateTime(value);
    case 'boolean':
      return value ? 'Yes' : 'No';
    default:
      return value ?? '-';
  }
};

const DataTable = ({
  columns,
  data = [],
  isLoading = false,
  isFetching = false,
  error,
  onRetry,
  pagination,
  sorting,
  onSort,
  onRowClick,
  actions, // New prop for row actions
  emptyTitle,
  emptyDescription,
  hasFilters = false,
  onClearFilters,
  emptyActionLabel,
  onEmptyAction,
  selectable = false,
  selectedIds = [],
  onToggleRow,
  onTogglePage,
  className,
}) => {
  const visibleColumns = columns.filter((column) => column.visible !== false);
  const allSelected = data.length > 0 && data.every((row) => selectedIds.includes(row.id));

  if (isLoading && data.length === 0) {
    return <TableSkeleton columns={visibleColumns.length} rows={8} />;
  }

  if (error && data.length === 0) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }

  return (
    <div className={twMerge('w-full flex-1 flex flex-col justify-between', className)}>
      <div className={twMerge('overflow-x-auto rounded-xl border border-gray-200 bg-white min-h-[260px]', isFetching && 'opacity-80')}>
        <table className="w-full text-sm text-left text-gray-700">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs font-semibold border-b border-gray-200 sticky top-0 z-10">
            <tr>
              {selectable && (
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={(event) => onTogglePage?.(event.target.checked)}
                    aria-label="Select all records on this page"
                  />
                </th>
              )}
              {visibleColumns.map((column) => {
                const align = columnAlign(column);
                const isActive = sorting?.key === column.key;
                return (
                <th
                  key={column.key}
                  className={twMerge(
                    'px-4 py-3 whitespace-nowrap',
                    column.sortable && 'hover:bg-gray-100',
                    align === 'right' && 'text-right',
                    align === 'center' && 'text-center',
                    column.widthClass
                  )}
                >
                  <div
                    className={twMerge(
                      'flex items-center gap-1',
                      align === 'right' && 'justify-end',
                      align === 'center' && 'justify-center'
                    )}
                  >
                    <span>{column.label}</span>
                    {column.sortable && (
                      <span className="inline-flex flex-col -space-y-1 ml-0.5">
                        <button
                          type="button"
                          title="Sort ascending"
                          aria-label={`Sort ${column.label} ascending`}
                          className="leading-none p-0"
                          onClick={(event) => {
                            event.stopPropagation();
                            onSort?.(column.key, 'asc');
                          }}
                        >
                          <ChevronUp
                            size={12}
                            className={isActive && sorting.order === 'asc' ? 'text-primary-600' : 'text-gray-300'}
                          />
                        </button>
                        <button
                          type="button"
                          title="Sort descending"
                          aria-label={`Sort ${column.label} descending`}
                          className="leading-none p-0"
                          onClick={(event) => {
                            event.stopPropagation();
                            onSort?.(column.key, 'desc');
                          }}
                        >
                          <ChevronDown
                            size={12}
                            className={isActive && sorting.order === 'desc' ? 'text-primary-600' : 'text-gray-300'}
                          />
                        </button>
                      </span>
                    )}
                  </div>
                </th>
                );
              })}
              {actions && (
                <th className="px-4 py-3 w-16 text-right font-semibold">Actions</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.length === 0 ? (
              <tr>
                <td colSpan={visibleColumns.length + (selectable ? 1 : 0)}>
                  <EmptyState
                    title={emptyTitle}
                    description={emptyDescription}
                    hasFilters={hasFilters}
                    onClearFilters={onClearFilters}
                    actionLabel={emptyActionLabel}
                    onAction={onEmptyAction}
                  />
                </td>
              </tr>
            ) : (
              data.map((row, rowIndex) => (
                <tr
                  key={row.id || rowIndex}
                  className={twMerge('hover:bg-blue-50/30 transition-colors', onRowClick && 'cursor-pointer')}
                  onClick={() => onRowClick?.(row)}
                >
                  {selectable && (
                    <td className="px-4 py-3" onClick={(event) => event.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(row.id)}
                        onChange={() => onToggleRow?.(row)}
                        aria-label="Select row"
                      />
                    </td>
                  )}
                  {visibleColumns.map((column) => {
                    const value = getValue(row, column.key);
                    const align = columnAlign(column);
                    return (
                      <td
                        key={column.key}
                        className={twMerge(
                          'px-4 py-3 max-w-[18rem] truncate',
                          align === 'right' && 'text-right font-medium tabular-nums',
                          align === 'center' && 'text-center'
                        )}
                        title={typeof value === 'string' ? value : undefined}
                      >
                        {renderTypedValue(column, value, row)}
                      </td>
                    );
                  })}
                  {actions && (
                    <td className="px-4 py-3 text-right" onClick={(event) => event.stopPropagation()}>
                      {actions(row)}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {pagination && data.length > 0 && (
        <div className="mt-auto pt-4">
          <Pagination {...pagination} />
        </div>
      )}
    </div>
  );
};

export default DataTable;
