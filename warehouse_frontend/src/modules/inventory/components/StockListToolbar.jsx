import React from 'react';
import { Search, RotateCcw } from 'lucide-react';
import Button from '../../../components/ui/Button';
import ColumnSelector from '../../../components/tables/ColumnSelector';
import ProductFilter from '../../../components/tables/ProductFilter';
import VendorFilter from '../../../components/tables/VendorFilter';

const fieldClass =
  'h-9 w-full bg-gray-50 border border-gray-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-primary-500 focus:bg-white transition-all';

/**
 * Current Stock toolbar: one balanced row on desktop (no gap between filters and actions).
 */
const StockListToolbar = ({
  searchValue,
  onSearchChange,
  searchPlaceholder,
  productId,
  onProductChange,
  columns,
  onToggleColumn,
  onRefresh,
  inventoryMenu,
}) => {
  return (
    <div
      className="grid w-full grid-cols-1 gap-2 md:grid-cols-[minmax(10rem,12rem)_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-center md:gap-x-2 md:gap-y-2"
    >
      <div className="relative min-w-0">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
          size={16}
        />
        <input
          type="search"
          value={searchValue || ''}
          onChange={(e) => onSearchChange?.(e.target.value)}
          placeholder={searchPlaceholder}
          className={`${fieldClass} pl-9 pr-3 text-xs sm:text-sm`}
        />
      </div>

      <ProductFilter
        layout="toolbar"
        value={productId}
        onChange={onProductChange}
        className="min-w-0"
      />

      <VendorFilter layout="toolbar" className="min-w-0" />

      <div className="flex items-center justify-end gap-1.5 shrink-0 md:pl-1">
        {columns && onToggleColumn && (
          <ColumnSelector columns={columns} onToggleColumn={onToggleColumn} />
        )}
        {onRefresh && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onRefresh}
            aria-label="Refresh"
            className="h-9 w-9 shrink-0"
          >
            <RotateCcw size={18} />
          </Button>
        )}
        {inventoryMenu}
      </div>
    </div>
  );
};

export default StockListToolbar;
