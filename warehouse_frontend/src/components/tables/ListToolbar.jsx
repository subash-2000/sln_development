import { Search, RotateCcw, Download, Upload } from 'lucide-react';
import Button from '../ui/Button';
import { twMerge } from 'tailwind-merge';

const ListToolbar = ({
  searchPlaceholder,
  searchValue,
  onSearchChange,
  filterControl,
  columnControl,
  companyControl,
  onRefresh,
  onExport,
  onImport,
  extraActions,
  searchWidthClass,
  className,
}) => {
  return (
    <div
      className={twMerge(
        'flex flex-col gap-2 xl:flex-row xl:items-center xl:gap-3',
        className
      )}
    >
      <div className={twMerge('relative shrink-0', searchWidthClass ?? 'w-full xl:flex-1 xl:min-w-[12rem] xl:max-w-md')}>
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
        <input
          type="search"
          value={searchValue || ''}
          onChange={(event) => onSearchChange?.(event.target.value)}
          placeholder={searchPlaceholder}
          className="w-full h-9 bg-gray-50 border border-gray-200 rounded-lg pl-10 pr-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 transition-all focus:bg-white"
        />
      </div>

      <div className="flex flex-1 flex-wrap items-center gap-2 min-w-0 xl:justify-start">
        {companyControl}
        {filterControl}
      </div>

      <div className="flex items-center gap-2 shrink-0 flex-wrap sm:flex-nowrap xl:ml-auto">
        {columnControl}

        {onImport && (
          <Button variant="secondary" size="sm" leftIcon={<Upload size={16} />} onClick={onImport}>
            Import
          </Button>
        )}

        {onExport && (
          <Button variant="secondary" size="sm" leftIcon={<Download size={16} />} onClick={onExport}>
            Export
          </Button>
        )}

        {onRefresh && (
          <Button variant="ghost" size="icon" onClick={onRefresh} aria-label="Refresh" className="h-9 w-9 shrink-0">
            <RotateCcw size={18} />
          </Button>
        )}

        {extraActions}
      </div>
    </div>
  );
};

export default ListToolbar;
