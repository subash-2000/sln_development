import React, { useState, useMemo } from 'react';
import { 
  Truck, 
  Search, 
  Download, 
  RotateCcw, 
  Eye, 
  Calendar,
  Building2,
  Package,
  ArrowDownLeft,
  ArrowUpRight,
  Boxes,
  CheckCircle2
} from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';
import Loader from '../../../components/common/Loader';
import { useVehicleReports } from '../hooks/use-reports';
import { useTransporters } from '../../transport/hooks/use-transporters';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { exportReportToCsv } from '../api/reports.api';
import VehicleReportViewModal from '../components/VehicleReportViewModal';

const VehicleReportPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [movementType, setMovementType] = useState('ALL'); // ALL, INWARD, OUTWARD
  const [selectedSupplier, setSelectedSupplier] = useState('');
  const [selectedTransporter, setSelectedTransporter] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [viewItem, setViewItem] = useState(null);

  // Fetch Transporters
  const { data: transportersData } = useTransporters({ page_size: 200 });
  const transporters = transportersData?.items || [];

  // Fetch Suppliers / Vendors
  const { data: vendorsData } = useVendors({ page_size: 200 });
  const vendors = vendorsData?.items || [];

  // Query parameters sent to backend
  const queryParams = useMemo(() => {
    const params = { page_size: 200 };
    if (searchTerm) params.search = searchTerm;
    if (movementType !== 'ALL') params.movement_type = movementType;
    if (selectedSupplier) params.vendor_name = selectedSupplier;
    if (selectedStatus) params.status = selectedStatus;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [searchTerm, movementType, selectedSupplier, selectedStatus, dateFrom, dateTo]);

  const { data: reportsData, isLoading } = useVehicleReports(queryParams);
  const items = reportsData?.items || [];

  // Client-side filtering if needed
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (movementType !== 'ALL' && item.movement_type !== movementType) {
        return false;
      }
      if (selectedTransporter && item.transporter_name !== selectedTransporter) {
        return false;
      }
      if (selectedSupplier) {
        const itemVendor = (item.vendor_name || item.party_name || '').toLowerCase();
        if (!itemVendor.includes(selectedSupplier.toLowerCase())) {
          return false;
        }
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesVeh = (item.vehicle_number || '').toLowerCase().includes(term);
        const matchesDriver = (item.driver_name || '').toLowerCase().includes(term);
        const matchesRef = (item.reference_number || '').toLowerCase().includes(term);
        const matchesParty = (item.party_name || item.destination || '').toLowerCase().includes(term);
        const matchesMat = (item.material_summary || '').toLowerCase().includes(term);
        if (!matchesVeh && !matchesDriver && !matchesRef && !matchesParty && !matchesMat) {
          return false;
        }
      }
      return true;
    });
  }, [items, movementType, selectedTransporter, selectedSupplier, searchTerm]);

  // Aggregate KPIs
  const totalMovements = filteredItems.length;
  const inwardCount = filteredItems.filter((i) => i.movement_type === 'INWARD').length;
  const outwardCount = filteredItems.filter((i) => i.movement_type === 'OUTWARD').length;
  const totalDispatchedQty = filteredItems.reduce(
    (sum, i) => sum + (Number(i.dispatched_qty) || 0),
    0
  );
  const uniqueVehicles = new Set(filteredItems.map((i) => i.vehicle_number).filter(Boolean)).size;

  const handleResetFilters = () => {
    setSearchTerm('');
    setMovementType('ALL');
    setSelectedSupplier('');
    setSelectedTransporter('');
    setSelectedStatus('');
    setDateFrom('');
    setDateTo('');
  };

  const handleExportCsv = () => {
    const headers = [
      'Vehicle Number',
      'Movement Type',
      'Transporter',
      'Party (Supplier / Customer)',
      'Driver Name',
      'Driver Phone',
      'Reference No',
      'Destination / Location',
      'Material Description',
      'Quantity',
      'UOM',
      'Date',
      'Status',
      'LR Number',
      'E-Way Bill',
    ];

    const rows = filteredItems.map((item) => [
      item.vehicle_number || '',
      item.movement_type || 'OUTWARD',
      item.transporter_name || '',
      item.party_name || item.vendor_name || item.customer_name || '',
      item.driver_name || '',
      item.driver_phone || '',
      item.reference_number || '',
      item.destination || '',
      item.material_summary || '',
      item.dispatched_qty || '',
      item.uom_code || 'PCS',
      item.movement_date || '',
      item.status || '',
      item.lr_number || '',
      item.eway_bill_number || '',
    ]);

    const dateStr = new Date().toISOString().split('T')[0];
    exportReportToCsv(headers, rows, `vehicle_movements_inward_outward_${dateStr}.csv`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vehicle Movement Reports"
        description="Comprehensive audit of vehicle movements covering both Inward Supplier Receipts and Outward Customer Dispatches"
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Reports', to: '/reports' },
          { label: 'Vehicle Reports' },
        ]}
      >
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={handleExportCsv}
            disabled={filteredItems.length === 0}
            className="flex items-center gap-2"
          >
            <Download size={16} />
            Export CSV
          </Button>
        </div>
      </PageHeader>

      {/* Movement Type Toggle Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setMovementType('ALL')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-xs ${
            movementType === 'ALL'
              ? 'bg-blue-600 text-white shadow-blue-200'
              : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
          }`}
        >
          <Truck size={15} />
          All Vehicle Trips ({items.length})
        </button>

        <button
          type="button"
          onClick={() => setMovementType('INWARD')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-xs ${
            movementType === 'INWARD'
              ? 'bg-emerald-600 text-white shadow-emerald-200'
              : 'bg-white text-emerald-700 border border-emerald-200 hover:bg-emerald-50/50'
          }`}
        >
          <ArrowDownLeft size={15} />
          Inward Movements (Supplier Receipts)
        </button>

        <button
          type="button"
          onClick={() => setMovementType('OUTWARD')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-xs ${
            movementType === 'OUTWARD'
              ? 'bg-indigo-600 text-white shadow-indigo-200'
              : 'bg-white text-indigo-700 border border-indigo-200 hover:bg-indigo-50/50'
          }`}
        >
          <ArrowUpRight size={15} />
          Outward Movements (Customer Dispatches)
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-blue-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Vehicle Trips</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalMovements}</h3>
              <p className="text-xs text-gray-400 mt-0.5">{uniqueVehicles} registered vehicles</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Truck size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Inward Movements</p>
              <h3 className="text-2xl font-bold text-emerald-600 mt-1">{inwardCount}</h3>
              <p className="text-xs text-emerald-500 mt-0.5">Supplier Goods Receipts</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ArrowDownLeft size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Outward Movements</p>
              <h3 className="text-2xl font-bold text-indigo-600 mt-1">{outwardCount}</h3>
              <p className="text-xs text-indigo-500 mt-0.5">Customer Delivery Challans</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <ArrowUpRight size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Units Handled</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">
                {totalDispatchedQty.toLocaleString()}
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Across Inward & Outward</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Boxes size={20} />
            </div>
          </div>
        </Card>
      </div>

      {/* Filter Toolbar */}
      <Card>
        <Card.Body className="p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
            {/* Search */}
            <div className="relative lg:col-span-2">
              <Search className="absolute left-3 top-2.5 text-gray-400" size={16} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search vehicle, driver, GRN, challan..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              />
            </div>

            {/* Supplier / Vendor Select */}
            <div>
              <select
                value={selectedSupplier}
                onChange={(e) => setSelectedSupplier(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Suppliers</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.name}>
                    {v.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Transporter Select */}
            <div>
              <select
                value={selectedTransporter}
                onChange={(e) => setSelectedTransporter(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Transporters</option>
                {transporters.map((t) => (
                  <option key={t.id} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Date From */}
            <div className="relative">
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
                title="Date From"
              />
            </div>

            {/* Date To & Reset */}
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
                title="Date To"
              />
              <button
                type="button"
                onClick={handleResetFilters}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors shrink-0"
                title="Reset Filters"
              >
                <RotateCcw size={16} />
              </button>
            </div>
          </div>
        </Card.Body>
      </Card>

      {/* Main Table */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-12 flex justify-center">
            <Loader />
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-2">
            <Truck size={36} className="mx-auto text-gray-400" />
            <p className="text-base font-semibold text-gray-700">No vehicle movement records found</p>
            <p className="text-xs text-gray-400">
              Try adjusting your movement type, supplier, or date range filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="py-3 px-4">Vehicle Number</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Transporter</th>
                  <th className="py-3 px-4">Party (Supplier / Customer)</th>
                  <th className="py-3 px-4">Reference No</th>
                  <th className="py-3 px-4 text-right">Quantity</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filteredItems.map((item, idx) => {
                  const isInward = item.movement_type === 'INWARD';
                  return (
                    <tr
                      key={`${item.id || ''}-${item.reference_number || ''}-${item.material_summary || ''}-${idx}`}
                      onClick={() => setViewItem(item)}
                      className="hover:bg-blue-50/40 cursor-pointer transition-colors"
                    >
                      {/* Vehicle No */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className={`p-1.5 rounded-md ${
                              isInward
                                ? 'bg-emerald-50 text-emerald-600'
                                : 'bg-blue-50 text-blue-600'
                            }`}
                          >
                            <Truck size={16} />
                          </div>
                          <div>
                            <span className="font-mono font-bold text-gray-900">
                              {item.vehicle_number}
                            </span>
                            <span className="block text-xs text-gray-400">
                              {item.vehicle_type || 'Truck'}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Movement Type Badge */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                            isInward
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : 'bg-blue-100 text-blue-800 border border-blue-200'
                          }`}
                        >
                          {isInward ? <ArrowDownLeft size={13} /> : <ArrowUpRight size={13} />}
                          {item.movement_type || 'OUTWARD'}
                        </span>
                      </td>

                      {/* Transporter */}
                      <td className="py-3.5 px-4 font-medium text-gray-900">
                        {item.transporter_name || 'Own Fleet'}
                      </td>

                      {/* Party (Supplier / Customer) */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-gray-900 flex items-center gap-1.5">
                          <Building2
                            size={14}
                            className={isInward ? 'text-emerald-600' : 'text-blue-600'}
                          />
                          {item.party_name || item.vendor_name || item.destination || '-'}
                        </div>
                        <div className="text-xs text-gray-400">
                          {isInward ? 'Supplier Consignor' : 'Customer Consignee'}
                        </div>
                      </td>

                      {/* Ref No */}
                      <td className="py-3.5 px-4 font-mono text-xs font-bold text-blue-600">
                        {item.reference_number || '-'}
                      </td>

                      {/* Quantity */}
                      <td className="py-3.5 px-4 text-right font-mono font-bold text-gray-900">
                        {item.dispatched_qty != null
                          ? Number(item.dispatched_qty).toLocaleString()
                          : '-'}
                        <span className="text-xs text-gray-400 font-normal ml-1">
                          {item.uom_code || 'PCS'}
                        </span>
                        <div className="text-xs text-gray-500 font-normal truncate max-w-[140px] text-right">
                          {item.material_summary || '-'}
                        </div>
                      </td>

                      {/* Date */}
                      <td className="py-3.5 px-4 text-gray-600 font-mono text-xs">
                        {item.movement_date || '-'}
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4 text-center">
                        <StatusBadge status={item.status || 'CONFIRMED'} />
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => setViewItem(item)}
                          className="p-1.5 rounded-lg text-blue-600 hover:text-blue-800 hover:bg-blue-50 transition-colors"
                          title="View Full Trip Details"
                        >
                          <Eye size={18} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* View Detail Modal */}
      <VehicleReportViewModal
        open={Boolean(viewItem)}
        onClose={() => setViewItem(null)}
        data={viewItem}
      />
    </div>
  );
};

export default VehicleReportPage;
