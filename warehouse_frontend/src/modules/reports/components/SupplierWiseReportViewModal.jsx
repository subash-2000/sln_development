import React from 'react';
import { X, Building2, Package, Boxes, Tag, ShieldCheck, CheckCircle2 } from 'lucide-react';
import Button from '../../../components/ui/Button';

const SupplierWiseReportViewModal = ({ open, onClose, data }) => {
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
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-linear-to-r from-emerald-50/70 to-teal-50/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
              <Building2 size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 tracking-wide font-mono">
                {data.vendor_name || 'SUPPLIER STOCK'}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Supplier Stock Allocation & Product Holding Position
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
          {/* Product & Supplier Details */}
          <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/70 space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Product Master Information
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Product SKU / Code</p>
                <p className="text-sm font-bold font-mono text-gray-900 mt-0.5">
                  {data.product_code || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Product Name</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5">
                  {data.product_name || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Supplier / Vendor Partner</p>
                <p className="text-sm font-semibold text-emerald-800 mt-0.5 flex items-center gap-1.5">
                  <Building2 size={14} className="text-emerald-600" />
                  {data.vendor_name}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Unit of Measure (UOM)</p>
                <p className="text-sm font-mono font-medium text-gray-900 mt-0.5">
                  {data.uom_code || 'PCS'}
                </p>
              </div>
            </div>
          </div>

          {/* Quantity Balances Card */}
          <div className="p-4 rounded-xl border border-gray-100 bg-white space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Supplier Inventory Holdings
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

export default SupplierWiseReportViewModal;

