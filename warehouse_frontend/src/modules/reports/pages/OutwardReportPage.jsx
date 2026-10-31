import React, { useState, useMemo } from 'react';
import { 
  ArrowUpRight, 
  Search, 
  Download, 
  FileSpreadsheet,
  RotateCcw, 
  Eye, 
  Calendar, 
  Building2, 
  Package, 
  Truck, 
  Boxes 
} from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';
import Loader from '../../../components/common/Loader';
import { useOutwardReports } from '../hooks/use-reports';
import { useCustomers } from '../../customers/hooks/use-customers';
import { exportReportToCsv } from '../api/reports.api';
import { exportOutwardReportToExcel } from '../utils/excel-export';
import OutwardReportViewModal from '../components/OutwardReportViewModal';

const OutwardReportPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [viewItem, setViewItem] = useState(null);

  // Fetch full list of registered customers
  const { data: customersData } = useCustomers({ page_size: 200 });

  const queryParams = useMemo(() => {
    const params = { page_size: 200 };
    if (searchTerm) params.search = searchTerm;
    if (selectedCustomer) params.customer_name = selectedCustomer;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [searchTerm, selectedCustomer, dateFrom, dateTo]);

  const { data: reportsData, isLoading } = useOutwardReports(queryParams);
  const items = reportsData?.items || [];

  const customerOptions = useMemo(() => {
    const set = new Set();
    (customersData?.items || []).forEach((c) => {
      if (c.name) set.add(c.name);
    });
    items.forEach((i) => {
      if (i.customer_name) set.add(i.customer_name);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [customersData, items]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (selectedCustomer && (item.customer_name || '').toLowerCase() !== selectedCustomer.toLowerCase()) {
        return false;
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesDisp = (item.dispatch_number || '').toLowerCase().includes(term);
        const matchesCust = (item.customer_name || '').toLowerCase().includes(term);
        const matchesVeh = (item.vehicle_number || '').toLowerCase().includes(term);
        const matchesProd = (item.product_name || '').toLowerCase().includes(term) || (item.product_code || '').toLowerCase().includes(term);
        if (!matchesDisp && !matchesCust && !matchesVeh && !matchesProd) return false;
      }
      return true;
    });
  }, [items, selectedCustomer, searchTerm]);

  // KPIs
  const totalDispatches = filteredItems.length;
  const totalDispatchedQty = filteredItems.reduce(
    (sum, i) => sum + (Number(i.dispatched_qty) || 0),
    0
  );
  const activeCustomers = new Set(filteredItems.map((i) => i.customer_name).filter(Boolean)).size;

  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedCustomer('');
    setDateFrom('');
    setDateTo('');
  };

  const handleExportExcel = () => {
    exportOutwardReportToExcel(filteredItems, {
      customer_name: selectedCustomer,
      date_from: dateFrom,
      date_to: dateTo,
      search: searchTerm,
    });
  };

  const handleExportCsv = () => {
    const headers = [
      'Dispatch Number',
      'Dispatch Date',
      'Customer',
      'Transporter',
      'Vehicle Number',
      'Product Code',
      'Product Name',
      'Dispatched Qty',
      'UOM',
      'Status',
    ];

    const rows = filteredItems.map((item) => [
      item.dispatch_number || '',
      item.dispatch_date || '',
      item.customer_name || '',
      item.transporter_name || '',
      item.vehicle_number || '',
      item.product_code || '',
      item.product_name || '',
      item.dispatched_qty || '',
      item.uom_code || 'PCS',
      item.status || '',
    ]);

    const dateStr = new Date().toISOString().split('T')[0];
    exportReportToCsv(headers, rows, `outward_dispatch_report_${dateStr}.csv`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Outward Dispatch Reports"
        description="Delivery challans, customer consignments, transporter vehicle assignments, and outward movements"
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Reports', to: '/reports' },
          { label: 'Outward Reports' },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              onClick={handleExportExcel}
              disabled={filteredItems.length === 0}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs font-medium"
            >
              <FileSpreadsheet size={16} />
              Export Excel (Outward Dispatches)
            </Button>
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
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 border-l-4 border-l-blue-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Outward Orders</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalDispatches}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <ArrowUpRight size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-sky-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Units Dispatched</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">
                {totalDispatchedQty.toLocaleString()}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
              <Boxes size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Active Customers</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{activeCustomers}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Building2 size={20} />
            </div>
          </div>
        </Card>
      </div>

      {/* Filters Toolbar */}
      <Card>
        <Card.Body className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-center">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-gray-400" size={16} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search challan, customer, vehicle..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              />
            </div>

            <div>
              <select
                value={selectedCustomer}
                onChange={(e) => setSelectedCustomer(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Customers</option>
                {customerOptions.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="relative">
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
                title="Date From"
              />
            </div>

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

            <div>
              <Button
                variant="primary"
                onClick={handleExportExcel}
                disabled={filteredItems.length === 0}
                className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 text-sm shadow-xs"
              >
                <FileSpreadsheet size={16} />
                Export Excel
              </Button>
            </div>
          </div>
        </Card.Body>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-12 flex justify-center">
            <Loader />
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-2">
            <ArrowUpRight size={36} className="mx-auto text-gray-400" />
            <p className="text-base font-semibold text-gray-700">No outward dispatches found</p>
            <p className="text-xs text-gray-400">
              Try adjusting your date range or customer filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="py-3 px-4">Dispatch Order</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Carrier / Transporter</th>
                  <th className="py-3 px-4">Vehicle No</th>
                  <th className="py-3 px-4">Product</th>
                  <th className="py-3 px-4 text-right">Dispatched Qty</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filteredItems.map((item, idx) => (
                  <tr
                    key={`${item.dispatch_number}-${item.product_code || ''}-${idx}`}
                    onClick={() => setViewItem(item)}
                    className="hover:bg-blue-50/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-gray-900">
                      {item.dispatch_number}
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 font-mono text-xs">
                      {item.dispatch_date || '-'}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-gray-800">
                      {item.customer_name || 'Standard Client'}
                    </td>
                    <td className="py-3.5 px-4 text-gray-700">
                      {item.transporter_name || 'Own Fleet'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs font-semibold text-gray-900">
                      {item.vehicle_number || '-'}
                    </td>
                    <td className="py-3.5 px-4 text-gray-800">
                      <div className="font-medium">{item.product_name}</div>
                      <div className="text-xs text-gray-400 font-mono">{item.product_code}</div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-blue-700">
                      {Number(item.dispatched_qty).toLocaleString()}
                      <span className="text-xs text-gray-400 font-normal ml-1">
                        {item.uom_code || 'PCS'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <StatusBadge status={item.status || 'CONFIRMED'} />
                    </td>
                    <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => setViewItem(item)}
                        className="p-1.5 rounded-lg text-blue-600 hover:text-blue-800 hover:bg-blue-50 transition-colors"
                        title="View Dispatch Order Details"
                      >
                        <Eye size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* View Detail Modal */}
      <OutwardReportViewModal
        open={Boolean(viewItem)}
        onClose={() => setViewItem(null)}
        data={viewItem}
      />
    </div>
  );
};

export default OutwardReportPage;

