import React from 'react';
import { 
  X, 
  Truck, 
  Calendar, 
  MapPin, 
  User, 
  Phone, 
  Building2, 
  Package, 
  ArrowDownLeft, 
  ArrowUpRight 
} from 'lucide-react';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';

const VehicleReportViewModal = ({ open, onClose, data }) => {
  if (!open || !data) return null;

  const isInward = data.movement_type === 'INWARD';

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
        className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div
          className={`flex items-center justify-between px-6 py-4 border-b border-gray-100 ${
            isInward
              ? 'bg-linear-to-r from-emerald-50/70 to-teal-50/40'
              : 'bg-linear-to-r from-blue-50/70 to-indigo-50/40'
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-xl text-white flex items-center justify-center shadow-xs ${
                isInward ? 'bg-emerald-600' : 'bg-blue-600'
              }`}
            >
              {isInward ? <ArrowDownLeft size={22} /> : <Truck size={20} />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-gray-900 tracking-wide font-mono">
                  {data.vehicle_number || 'VEHICLE RECORD'}
                </h2>
                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                    isInward
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      : 'bg-blue-100 text-blue-800 border border-blue-200'
                  }`}
                >
                  {isInward ? <ArrowDownLeft size={12} /> : <ArrowUpRight size={12} />}
                  {data.movement_type || 'MOVEMENT'}
                </span>
                <StatusBadge status={data.status || 'CONFIRMED'} />
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                {isInward
                  ? 'Inward Supplier Goods Receipt & Vehicle Trip Manifest'
                  : 'Outward Customer Delivery Challan & Vehicle Trip Manifest'}
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
          {/* Party (Supplier / Customer) Information Card */}
          <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/70 space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              {isInward ? 'Consignor / Supplier Details' : 'Consignee / Customer Details'}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">
                  {isInward ? 'Supplier / Vendor Name' : 'Customer / Destination'}
                </p>
                <p className="text-sm font-bold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Building2 size={15} className={isInward ? 'text-emerald-600' : 'text-blue-600'} />
                  {data.party_name || data.vendor_name || data.destination || 'Direct Consignee'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Movement Date</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Calendar size={14} className="text-gray-400" />
                  {data.movement_date || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">
                  {isInward ? 'GRN / Inward Ref Number' : 'Dispatch / Delivery Challan Ref'}
                </p>
                <p className="text-sm font-mono font-bold text-blue-600 mt-0.5">
                  {data.reference_number || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Warehouse Receiving / Dispatch Bin</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <MapPin size={14} className="text-gray-400" />
                  {data.destination || 'Central Warehouse'}
                </p>
              </div>
            </div>
          </div>

          {/* Transporter & Driver Card */}
          <div className="p-4 rounded-xl border border-gray-100 bg-white space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Carrier & Driver Information
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Transporter / Carrier</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5">
                  {data.transporter_name || 'Own Fleet'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Vehicle Type</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5">
                  {data.vehicle_type || 'Truck'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Driver Name</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <User size={14} className="text-gray-400" />
                  {data.driver_name || 'Carrier Driver'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Driver Contact</p>
                <p className="text-sm font-semibold text-gray-900 mt-0.5 flex items-center gap-1.5">
                  <Phone size={14} className="text-gray-400" />
                  {data.driver_phone || '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">LR / Bilty Number</p>
                <p className="text-sm font-mono text-gray-800 mt-0.5">
                  {data.lr_number || 'Pending'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">E-Way Bill Number</p>
                <p className="text-sm font-mono text-gray-800 mt-0.5">
                  {data.eway_bill_number || 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Material & Quantity Manifest */}
          <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 space-y-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Package size={14} /> Material Manifest
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-200 text-gray-500">
                    <th className="py-2 font-medium">Material Description</th>
                    <th className="py-2 text-right font-medium">Quantity</th>
                    <th className="py-2 text-right font-medium">UOM</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  <tr>
                    <td className="py-2.5 font-medium text-gray-900">
                      {data.material_summary || 'Standard Warehousing Material Batch'}
                    </td>
                    <td className="py-2.5 text-right font-mono font-bold text-gray-900">
                      {data.dispatched_qty != null
                        ? Number(data.dispatched_qty).toLocaleString()
                        : '1'}
                    </td>
                    <td className="py-2.5 text-right text-gray-600 font-mono">
                      {data.uom_code || 'PCS'}
                    </td>
                  </tr>
                </tbody>
              </table>
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

export default VehicleReportViewModal;
