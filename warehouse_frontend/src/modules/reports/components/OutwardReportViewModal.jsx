import React from 'react';
import { X, ArrowUpRight, Calendar, User, Phone, Truck, Package, Building2 } from 'lucide-react';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';

const OutwardReportViewModal = ({ open, onClose, data }) => {
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
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-linear-to-r from-blue-50/70 to-sky-50/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
              <ArrowUpRight size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-gray-900 tracking-wide font-mono">
                  {data.dispatch_number || 'OUTWARD DISPATCH'}
                </h2>
                <StatusBadge status={data.status || 'CONFIRMED'} />
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Delivery Challan & Customer Outward Shipment
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
          {/* Customer & Transporter Info */}
          <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/70 space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Customer & Carrier Logistics
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Customer / Consignee</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Building2 size={14} className="text-gray-400" />
                  {data.customer_name || 'Standard Client'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Dispatch Date</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Calendar size={14} className="text-gray-400" />
                  {data.dispatch_date || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Transporter</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5">
                  {data.transporter_name || 'Direct Transport'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Vehicle Number</p>
                <p className="text-sm font-mono font-bold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Truck size={14} className="text-gray-400" />
                  {data.vehicle_number || 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Product & Quantity Dispatched */}
          <div className="p-4 rounded-xl border border-gray-100 bg-white space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Package size={14} /> Material Line Dispatched
            </h3>
            <div className="p-3 bg-gray-50 rounded-lg space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">Product Code:</span>
                <span className="text-sm font-mono font-bold text-gray-900">
                  {data.product_code || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">Product Name:</span>
                <span className="text-sm font-semibold text-gray-900">
                  {data.product_name || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-gray-200">
                <span className="text-xs font-medium text-gray-700">Dispatched Quantity:</span>
                <span className="text-base font-mono font-bold text-blue-600">
                  {Number(data.dispatched_qty || 0).toLocaleString()} {data.uom_code || 'PCS'}
                </span>
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

export default OutwardReportViewModal;

