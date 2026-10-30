import React from 'react';
import { X, Boxes, Warehouse, MapPin, Tag, Layers, CheckCircle2, ShieldAlert } from 'lucide-react';
import Button from '../../../components/ui/Button';

const DailyStockReportViewModal = ({ open, onClose, data }) => {
  if (!open || !data) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <button
        type="button"
        className="absolute inset-0 bg-gray-900/50 backdrop-blur-xs transition-opacity"
        aria-label="Close dialog"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-linear-to-r from-amber-50/70 to-orange-50/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-600 text-white flex items-center justify-center shadow-xs">
              <Boxes size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 tracking-wide font-mono">
                {data.product_code || 'STOCK RECORD'}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {data.product_name || 'Inventory Quant Details'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Warehouse & Location */}
          <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/70 space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Storage Location
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Warehouse</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Warehouse size={14} className="text-gray-400" />
                  {data.warehouse_name || 'Primary Warehouse'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Location / Bin</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <MapPin size={14} className="text-gray-400" />
                  {data.location_code || 'Main Storage'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Product Category</p>
                <p className="text-sm font-medium text-gray-800 mt-0.5 flex items-center gap-1.5">
                  <Layers size={14} className="text-gray-400" />
                  {data.category_name || 'Standard'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Batch / Lot Number</p>
                <p className="text-sm font-mono font-semibold text-gray-900 mt-0.5">
                  {data.batch_number || 'DEFAULT-LOT'}
                </p>
              </div>
            </div>
          </div>

          {/* Stock Metrics Card */}
          <div className="p-4 rounded-xl border border-gray-100 bg-white space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Stock Quantity Balance
            </h3>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 bg-gray-50 rounded-xl">
                <p className="text-xs text-gray-500 mb-1">On Hand</p>
                <p className="text-lg font-bold font-mono text-gray-900">
                  {Number(data.quantity_on_hand || 0).toLocaleString()}
                </p>
                <span className="text-xs text-gray-400">{data.uom_code || 'PCS'}</span>
              </div>
              <div className="p-3 bg-amber-50 rounded-xl">
                <p className="text-xs text-amber-700 mb-1">Reserved</p>
                <p className="text-lg font-bold font-mono text-amber-700">
                  {Number(data.quantity_reserved || 0).toLocaleString()}
                </p>
                <span className="text-xs text-amber-500">{data.uom_code || 'PCS'}</span>
              </div>
              <div className="p-3 bg-emerald-50 rounded-xl">
                <p className="text-xs text-emerald-700 mb-1">Available</p>
                <p className="text-lg font-bold font-mono text-emerald-700">
                  {Number(data.quantity_available || 0).toLocaleString()}
                </p>
                <span className="text-xs text-emerald-500">{data.uom_code || 'PCS'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-gray-100 bg-gray-50/50 flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

export default DailyStockReportViewModal;

