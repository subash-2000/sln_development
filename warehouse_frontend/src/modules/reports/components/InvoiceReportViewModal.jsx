import React from 'react';
import { X, FileSpreadsheet, Calendar, User, Receipt, DollarSign, CheckCircle2 } from 'lucide-react';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';

const InvoiceReportViewModal = ({ open, onClose, data }) => {
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
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-linear-to-r from-violet-50/70 to-purple-50/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-600 text-white flex items-center justify-center shadow-xs">
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-gray-900 tracking-wide font-mono">
                  {data.invoice_number || 'TAX INVOICE'}
                </h2>
                <StatusBadge status={data.status || 'ISSUED'} />
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Statutory GST Invoice & Financial Billing Audit
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
          {/* Customer & Invoice Date */}
          <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/70 space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Billed Customer Details
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Customer / Buyer</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <User size={14} className="text-gray-400" />
                  {data.customer_name || 'Direct Customer'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Invoice Date</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Calendar size={14} className="text-gray-400" />
                  {data.invoice_date || 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Tax Breakdown Table */}
          <div className="p-4 rounded-xl border border-gray-100 bg-white space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Receipt size={14} /> GST & Tax Breakdown
            </h3>
            <div className="divide-y divide-gray-100 text-sm">
              <div className="flex justify-between py-2 text-gray-600">
                <span>Taxable Value (Subtotal):</span>
                <span className="font-mono font-medium text-gray-900">
                  ₹{Number(data.taxable_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between py-2 text-gray-600">
                <span>Central GST (CGST):</span>
                <span className="font-mono font-medium text-gray-900">
                  ₹{Number(data.cgst_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between py-2 text-gray-600">
                <span>State GST (SGST):</span>
                <span className="font-mono font-medium text-gray-900">
                  ₹{Number(data.sgst_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between py-2 text-gray-600">
                <span>Integrated GST (IGST):</span>
                <span className="font-mono font-medium text-gray-900">
                  ₹{Number(data.igst_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between py-2.5 font-bold text-base text-gray-900 bg-gray-50 px-3 rounded-lg mt-2">
                <span>Total Invoice Value:</span>
                <span className="font-mono text-violet-700">
                  ₹{Number(data.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
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

export default InvoiceReportViewModal;

