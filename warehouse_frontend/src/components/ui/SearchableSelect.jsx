import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';
import { twMerge } from 'tailwind-merge';

const SearchableSelect = ({
  value,
  options = [],
  onChange,
  placeholder = 'Select',
  searchPlaceholder = 'Search...',
  emptyText = 'No matches',
  disabled = false,
  getOptionLabel,
  getOptionValue,
  className,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [pos, setPos] = useState({ top: 8, left: 0, width: 280, maxHeight: 280 });
  const triggerRef = useRef(null);
  const menuRef = useRef(null);
  const searchRef = useRef(null);

  const labelOf = (option) => (getOptionLabel ? getOptionLabel(option) : option?.label || option?.name || '');
  const valueOf = (option) => (getOptionValue ? getOptionValue(option) : option?.id);

  const sortedOptions = useMemo(() => {
    if (!Array.isArray(options)) return [];
    return [...options].sort((a, b) => {
      const la = String(labelOf(a) ?? '').trim();
      const lb = String(labelOf(b) ?? '').trim();
      return la.localeCompare(lb, undefined, { numeric: true, sensitivity: 'base' });
    });
  }, [options, getOptionLabel]);

  const selected = sortedOptions.find((option) => String(valueOf(option)) === String(value));
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sortedOptions;
    return sortedOptions.filter((option) => labelOf(option).toLowerCase().includes(q));
  }, [sortedOptions, query, getOptionLabel]);

  const placeMenu = () => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const gap = 4;
    const spaceBelow = window.innerHeight - rect.bottom - gap - 12;
    const maxHeight = Math.max(140, Math.min(280, spaceBelow));
    const width = Math.min(Math.max(rect.width, 220), window.innerWidth - 16);
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    setPos({
      top: rect.bottom + gap,
      left,
      width,
      maxHeight,
    });
  };

  useEffect(() => {
    if (!open) return;
    placeMenu();
    const handle = (event) => {
      if (triggerRef.current?.contains(event.target) || menuRef.current?.contains(event.target)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', handle);
    window.addEventListener('resize', placeMenu);
    window.addEventListener('scroll', placeMenu, true);
    const focusTimer = window.setTimeout(() => searchRef.current?.focus(), 0);
    return () => {
      document.removeEventListener('mousedown', handle);
      window.removeEventListener('resize', placeMenu);
      window.removeEventListener('scroll', placeMenu, true);
      window.clearTimeout(focusTimer);
    };
  }, [open]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => {
          if (disabled) return;
          setQuery('');
          setOpen((current) => !current);
        }}
        className={twMerge(
          'w-full max-w-[18rem] h-9 bg-white border border-gray-200 rounded-md px-2 text-sm flex items-center justify-between gap-1 text-left focus:ring-2 focus:ring-primary-500 outline-none disabled:bg-gray-50 disabled:text-gray-400',
          className
        )}
      >
        <span className={twMerge('truncate', selected ? 'text-gray-900' : 'text-gray-400')}>
          {selected ? labelOf(selected) : placeholder}
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-gray-400" />
      </button>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            className="rounded-md border border-gray-200 bg-white shadow-lg overflow-hidden"
            style={{
              position: 'fixed',
              top: pos.top,
              left: pos.left,
              width: pos.width,
              maxHeight: pos.maxHeight,
              zIndex: 80,
            }}
          >
            <div className="p-2 border-b border-gray-100">
              <input
                ref={searchRef}
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                className="w-full h-8 bg-gray-50 border border-gray-200 rounded px-2 text-sm outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div
              className="overflow-y-auto py-1"
              style={{ maxHeight: Math.max(112, pos.maxHeight - 48) }}
            >
              {filtered.length === 0 && (
                <p className="px-3 py-2 text-xs text-gray-500">{emptyText}</p>
              )}
              {filtered.map((option, index) => {
                const id = String(valueOf(option));
                const active = String(value) === id;
                return (
                  <button
                    key={`${id}-${index}`}
                    type="button"
                    onClick={() => {
                      onChange?.(id);
                      setOpen(false);
                    }}
                    className={twMerge(
                      'block w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50 whitespace-normal',
                      active && 'bg-primary-50 text-primary-800'
                    )}
                  >
                    {labelOf(option)}
                  </button>
                );
              })}
            </div>
          </div>,
          document.body
        )}
    </>
  );
};

export default SearchableSelect;
