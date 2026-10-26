import React, { useState, useRef, useEffect } from 'react';
import { Filter, X } from 'lucide-react';
import Button from '../ui/Button';

const FilterPanel = ({ children, onApply, onClear, hasActiveFilters }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleApply = () => {
    onApply?.();
    setIsOpen(false);
  };

  const handleClear = () => {
    onClear?.();
  };

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      <Button 
        variant={hasActiveFilters ? 'primary' : 'secondary'} 
        leftIcon={<Filter size={16} />}
        className={hasActiveFilters ? 'bg-primary-50 text-primary-700 border-primary-200' : ''}
        onClick={() => setIsOpen((prev) => !prev)}
      >
        Filters
        {hasActiveFilters && (
          <span className="ml-2 flex h-2 w-2 rounded-full bg-primary-600" />
        )}
      </Button>

      {isOpen && (
        <div 
          className="absolute right-0 mt-2 w-80 rounded-lg shadow-xl bg-white ring-1 ring-black/5 z-50 p-4 space-y-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-gray-100 pb-2 mb-2">
            <h3 className="text-sm font-semibold text-gray-900">Filters</h3>
          </div>
          
          <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
            {children}
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-100 mt-4 gap-2">
            <Button variant="ghost" size="sm" onClick={handleClear} className="text-gray-500">
              Clear All
            </Button>
            <Button variant="primary" size="sm" onClick={handleApply}>
              Apply
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

const FilterGroup = ({ label, children }) => (
  <div className="space-y-1.5">
    <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</label>
    <div>{children}</div>
  </div>
);

FilterPanel.Group = FilterGroup;

export default FilterPanel;
