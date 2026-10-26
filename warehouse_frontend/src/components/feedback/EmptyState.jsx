import { PackageOpen } from 'lucide-react';
import Button from '../ui/Button';

const EmptyState = ({
  title = 'No records found',
  description,
  hasFilters = false,
  onClearFilters,
  actionLabel,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="h-12 w-12 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center mb-4">
        <PackageOpen size={22} />
      </div>
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="text-sm text-gray-500 mt-1 max-w-md">
        {description ||
          (hasFilters
            ? 'No records match your current search or filter criteria.'
            : 'No records have been created yet.')}
      </p>
      <div className="flex items-center gap-2 mt-4">
        {hasFilters && onClearFilters && (
          <Button variant="secondary" onClick={onClearFilters}>
            Clear Filters
          </Button>
        )}
        {onAction && actionLabel && <Button onClick={onAction}>{actionLabel}</Button>}
      </div>
    </div>
  );
};

export default EmptyState;
