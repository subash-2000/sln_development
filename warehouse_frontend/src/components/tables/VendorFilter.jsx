import React, { useMemo } from 'react';
import { Truck, ChevronDown } from 'lucide-react';
import { useVendors } from '../../modules/vendors/hooks/use-vendors';
import { useAuthStore } from '../../store/auth.store';

const VendorFilter = ({ value, onChange, layout = 'default', className = '' }) => {
  const isToolbar = layout === 'toolbar';
  const { companyContext, vendorContext, setVendorContext } = useAuthStore();
  const isControlled = typeof onChange === 'function';
  const selectedValue = isControlled ? (value ?? '') : (vendorContext ?? '');
  const { data: vendorsData, isLoading } = useVendors({
    page_size: 200,
    company_id: companyContext,
    sort_by: 'name',
    sort_order: 'asc',
  });
  const vendors = useMemo(() => {
    const items = vendorsData?.items || [];
    return [...items].sort((a, b) => String(a.name).localeCompare(String(b.name)));
  }, [vendorsData]);

  if (isLoading && vendors.length === 0) {
    return (
      <div
        className={`h-9 bg-gray-100 animate-pulse rounded-lg ${isToolbar ? 'w-full' : 'w-48'} ${className}`}
      />
    );
  }

  return (
    <div
      className={`flex items-center gap-1.5 min-w-0 ${isToolbar ? 'w-full' : 'shrink-0'} ${className}`}
    >
      {!isToolbar && (
        <span className="text-xs font-semibold text-gray-600 whitespace-nowrap hidden md:inline">
          Supplier
        </span>
      )}
      <div className={`relative flex items-center min-w-0 ${isToolbar ? 'w-full' : 'w-[10.5rem] sm:w-48 md:w-52'}`}>
        <Truck size={16} className="absolute left-3 text-gray-400 pointer-events-none z-[1]" />
        <select
          value={selectedValue}
          onChange={(e) => {
            const next = e.target.value;
            if (isControlled) {
              onChange(next);
            } else {
              setVendorContext(next || null);
            }
          }}
          title={isToolbar ? 'Supplier' : undefined}
          className="h-9 w-full min-w-0 pl-9 pr-8 py-1.5 text-xs font-medium bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none appearance-none cursor-pointer hover:bg-white transition-all text-gray-800 truncate"
          aria-label="Filter by supplier"
          title="Filter stock by supplier"
        >
          <option value="">All suppliers</option>
          {vendors.map((vendor) => (
            <option key={vendor.id} value={vendor.id}>
              {vendor.name}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="absolute right-2.5 text-gray-400 pointer-events-none" />
      </div>
    </div>
  );
};

export default VendorFilter;
