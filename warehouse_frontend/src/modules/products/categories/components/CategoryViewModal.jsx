import React from 'react';
import { X, Layers, Edit, Calendar, Info, Tag } from 'lucide-react';
import Button from '../../../../components/ui/Button';
import StatusBadge from '../../../../components/ui/StatusBadge';
import { formatDate } from '../../../../utils/formatters';

const CategoryViewModal = ({
  open,
  onClose,
  category,
  onEdit,
  allCategories = [],
}) => {
  if (!open || !category) return null;

  const parentCategory = category.parent_id
    ? allCategories.find((c) => String(c.id) === String(category.parent_id))
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <button
        type="button"
        className="absolute inset-0 bg-gray-900/40 transition-opacity"
        aria-label="Close modal"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-lg bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden transform transition-all"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary-50 text-primary-600 border border-primary-100">
              <Layers size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-gray-900">{category.name}</h2>
                <StatusBadge status={category.status || (category.is_active ? 'ACTIVE' : 'INACTIVE')} />
              </div>
              <p className="text-xs text-gray-500 font-mono">Code: {category.code}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
              <span className="text-xs font-medium text-gray-500 flex items-center gap-1.5 mb-1">
                <Tag size={13} className="text-gray-400" />
                Category Code
              </span>
              <span className="text-sm font-semibold font-mono text-gray-800">
                {category.code || '—'}
              </span>
            </div>

            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
              <span className="text-xs font-medium text-gray-500 flex items-center gap-1.5 mb-1">
                <Layers size={13} className="text-gray-400" />
                Hierarchy / Parent
              </span>
              <span className="text-sm font-medium text-gray-800">
                {parentCategory ? `${parentCategory.name} (${parentCategory.code})` : 'Top-level (None)'}
              </span>
            </div>
          </div>

          <div className="p-3.5 bg-gray-50 rounded-xl border border-gray-100">
            <span className="text-xs font-medium text-gray-500 flex items-center gap-1.5 mb-1">
              <Info size={13} className="text-gray-400" />
              Description
            </span>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">
              {category.description || 'No description provided for this category.'}
            </p>
          </div>

          {category.updated_at && (
            <div className="flex items-center gap-2 text-xs text-gray-400 pt-1">
              <Calendar size={13} />
              <span>Last updated: {formatDate(category.updated_at)}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-gray-100 bg-gray-50/50">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              onClose();
              onEdit?.(category);
            }}
          >
            <Edit size={14} className="mr-1.5" />
            Edit Category
          </Button>
        </div>
      </div>
    </div>
  );
};

export default CategoryViewModal;

