import React from 'react';
import { Columns, Check } from 'lucide-react';
import Dropdown from '../ui/Dropdown';
import Button from '../ui/Button';

const ColumnSelector = ({ columns, onToggleColumn }) => {
  return (
    <Dropdown
      closeOnClick={false}
      trigger={
        <Button variant="secondary" size="sm" className="h-9 shrink-0" leftIcon={<Columns size={16} />}>
          <span className="hidden sm:inline">Columns</span>
        </Button>
      }
    >
      <div className="p-2 w-56 bg-white" onClick={(e) => e.stopPropagation()}>
        <div className="px-3 py-2 border-b border-gray-100 mb-1">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Visible Columns</h3>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {columns.map((column) => (
            <div
              key={column.key}
              className="flex items-center px-3 py-2 hover:bg-gray-50 rounded-md cursor-pointer"
              onClick={() => onToggleColumn(column.key)}
            >
              <div className={`mr-3 flex h-4 w-4 items-center justify-center rounded border ${
                column.visible !== false ? 'bg-primary-600 border-primary-600' : 'bg-white border-gray-300'
              }`}>
                {column.visible !== false && <Check size={12} className="text-white" />}
              </div>
              <span className="text-sm text-gray-700">{column.label}</span>
            </div>
          ))}
        </div>
      </div>
    </Dropdown>
  );
};

export default ColumnSelector;
