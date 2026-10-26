import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Package, ChevronDown, Search } from 'lucide-react';
import { useProducts } from '../../modules/products/hooks/use-products';
import { useAuthStore } from '../../store/auth.store';
import { formatProductOptionLabel } from './productFilterLabels';

const triggerClass =
  'h-9 w-full min-w-0 pl-9 pr-8 py-1.5 text-xs font-medium text-left bg-gray-50 border border-gray-200 rounded-lg hover:bg-white focus:ring-2 focus:ring-primary-500 outline-none cursor-pointer text-gray-800 truncate';

const ProductFilter = ({ value = '', onChange, layout = 'default', className = '' }) => {
  const isToolbar = layout === 'toolbar';
  const { companyContext } = useAuthStore();
  const { data: productsData, isLoading } = useProducts({
    page_size: 200,
    company_id: companyContext,
    status: 'ACTIVE',
  });

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const rootRef = useRef(null);

  const products = useMemo(() => {
    const items = productsData?.items || [];
    return [...items].sort((a, b) => String(a.name).localeCompare(String(b.name)));
  }, [productsData]);

  const selected = useMemo(
    () => products.find((p) => p.id === value),
    [products, value]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) =>
        p.name?.toLowerCase().includes(q)
        || p.sku?.toLowerCase().includes(q)
    );
  }, [products, query]);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
        setQuery('');
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const pick = (id) => {
    onChange?.(id);
    setOpen(false);
    setQuery('');
  };

  if (isLoading && products.length === 0) {
    return (
      <div
        className={`h-9 bg-gray-100 animate-pulse rounded-lg ${isToolbar ? 'w-full' : 'w-48 shrink-0'} ${className}`}
      />
    );
  }

  const displayLabel = selected ? formatProductOptionLabel(selected) : 'All products';

  return (
    <div
      className={`flex items-center gap-1.5 min-w-0 ${isToolbar ? 'w-full' : 'shrink-0'} ${className}`}
    >
      {!isToolbar && (
        <span className="text-xs font-semibold text-gray-600 whitespace-nowrap hidden md:inline">
          Product
        </span>
      )}
      <div
        ref={rootRef}
        className={`relative min-w-0 ${isToolbar ? 'w-full' : 'w-[10.5rem] sm:w-44'}`}
      >
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className={triggerClass}
          aria-label="Filter by product"
          aria-expanded={open}
          aria-haspopup="listbox"
        >
          <Package size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          <span className="block truncate">{displayLabel}</span>
          <ChevronDown
            size={14}
            className={`absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none transition-transform ${open ? 'rotate-180' : ''}`}
          />
        </button>

        {open && (
          <div
            className="absolute left-0 right-0 top-full z-[200] mt-1 rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden"
            role="listbox"
          >
            <div className="p-2 border-b border-gray-100 bg-gray-50/80">
              <div className="relative">
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search product or SKU..."
                  className="w-full h-8 pl-8 pr-2 text-xs border border-gray-200 rounded-md outline-none focus:ring-1 focus:ring-primary-500 bg-white"
                  autoFocus
                />
              </div>
            </div>
            <ul className="max-h-56 overflow-y-auto py-1 text-xs">
              <li>
                <button
                  type="button"
                  role="option"
                  aria-selected={!value}
                  onClick={() => pick('')}
                  className={`w-full text-left px-3 py-2 hover:bg-primary-50 ${!value ? 'bg-primary-50 text-primary-800 font-semibold' : 'text-gray-700'}`}
                >
                  All products
                </button>
              </li>
              {filtered.length === 0 ? (
                <li className="px-3 py-3 text-gray-500 text-center">No matches</li>
              ) : (
                filtered.map((product) => {
                  const label = formatProductOptionLabel(product);
                  const isSelected = value === product.id;
                  return (
                    <li key={product.id}>
                      <button
                        type="button"
                        role="option"
                        aria-selected={isSelected}
                        title={label}
                        onClick={() => pick(product.id)}
                        className={`w-full text-left px-3 py-2 hover:bg-gray-50 truncate ${isSelected ? 'bg-primary-50 text-primary-800 font-medium' : 'text-gray-800'}`}
                      >
                        {label}
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProductFilter;
