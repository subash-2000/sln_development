import React, { useState, useMemo } from 'react';
import { 
  ArrowDownLeft, 
  Search, 
  Download, 
  FileSpreadsheet,
  RotateCcw, 
  Eye, 
  Calendar,
  Building2,
  Package,
  CheckCircle2,
  Boxes
} from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';
import Loader from '../../../components/common/Loader';
import { useInwardReports } from '../hooks/use-reports';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { exportReportToCsv } from '../api/reports.api';
import { exportInwardReportToExcel } from '../utils/excel-export';
import InwardReportViewModal from '../components/InwardReportViewModal';

const InwardReportPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedVendor, setSelectedVendor] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [viewItem, setViewItem] = useState(null);

  // Fetch full list of registered vendors
  const { data: vendorsData } = useVendors({ page_size: 200 });

  const queryParams = useMemo(() => {
    const params = { page_size: 200 };
    if (searchTerm) params.search = searchTerm.trim();
    if (selectedVendor) params.vendor_name = selectedVendor.trim();
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [searchTerm, selectedVendor, dateFrom, dateTo]);

  const { data: reportsData, isLoading, isFetching, error, refetch } = useInwardReports(queryParams);
  const items = reportsData?.items || [];

  // Filter vendor list for dropdown (combining registered suppliers and returned data)
  const vendorOptions = useMemo(() => {
    const set = new Set();
    (vendorsData?.items || []).forEach((v) => {
      if (v.name) set.add(v.name.trim());
    });
    items.forEach((i) => {
      if (i.vendor_name) set.add(i.vendor_name.trim());
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [vendorsData, items]);

  // Client-side filtering
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (selectedVendor) {
        const itemV = (item.vendor_name || '').trim().toLowerCase();
        const selV = selectedVendor.trim().toLowerCase();
        if (itemV !== selV && !itemV.includes(selV) && !selV.includes(itemV)) {
          return false;
        }
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesTx = (item.transaction_number || '').toLowerCase().includes(term);
        const matchesProd = (item.product_name || '').toLowerCase().includes(term) || (item.product_code || '').toLowerCase().includes(term);
        const matchesVendor = (item.vendor_name || '').toLowerCase().includes(term);
        if (!matchesTx && !matchesProd && !matchesVendor) return false;
      }
      return true;
    });
  }, [items, selectedVendor, searchTerm]);

  // KPIs
  const totalReceipts = filteredItems.length;
  const totalReceivedQty = filteredItems.reduce(
    (sum, i) => sum + (Number(i.quantity) || 0),
    0
  );
  const activeSuppliers = new Set(filteredItems.map((i) => i.vendor_name).filter(Boolean)).size;

  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedVendor('');
    setDateFrom('');
    setDateTo('');
  };

  const handleExportExcel = () => {
    exportInwardReportToExcel(filteredItems, {
      vendor_name: selectedVendor,
      date_from: dateFrom,
      date_to: dateTo,
      search: searchTerm,
    });
  };

  const handleExportCsv = () => {
    const headers = [
      'Transaction Number (GRN)',
      'Receipt Date',
      'Supplier / Vendor',
      'Product Code',
      'Product Name',
      'Quantity',
      'UOM',
      'Status',
    ];

    const rows = filteredItems.map((item) => [
      item.transaction_number || '',
      item.confirmed_at || '',
      item.vendor_name || '',
      item.product_code || '',
      item.product_name || '',
      item.quantity || '',
      item.uom_code || 'PCS',
      item.status || '',
    ]);

    const dateStr = new Date().toISOString().split('T')[0];
    exportReportToCsv(headers, rows, `inward_stock_report_${dateStr}.csv`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Inward Stock Reports"
        description="Comprehensive audit of goods receipts (GRNs), supplier deliveries, and stock increments"
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Reports', to: '/reports' },
          { label: 'Inward Reports' },
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
              Export Excel (Receipt Sheet)
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
        <Card className="p-4 border-l-4 border-l-emerald-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Inward Receipts</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalReceipts}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ArrowDownLeft size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-teal-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Units Received</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">
                {totalReceivedQty.toLocaleString()}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
              <Boxes size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-blue-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Active Suppliers</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{activeSuppliers}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
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
                placeholder="Search GRN, product, supplier..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              />
            </div>

            <div>
              <select
                value={selectedVendor}
                onChange={(e) => setSelectedVendor(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Suppliers</option>
                {vendorOptions.map((v) => (
                  <option key={v} value={v}>
                    {v}
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
        ) : error ? (
          <div className="p-12 text-center text-red-500 space-y-2">
            <p className="text-base font-semibold text-red-700">Failed to load inward reports</p>
            <p className="text-xs text-red-500">
              {error?.message || 'Server connection error. Please ensure the backend is running.'}
            </p>
            <Button variant="secondary" onClick={() => refetch()} className="mt-2 text-xs">
              Retry
            </Button>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-2">
            <ArrowDownLeft size={36} className="mx-auto text-gray-400" />
            <p className="text-base font-semibold text-gray-700">No inward receipts found</p>
            <p className="text-xs text-gray-400">
              Try adjusting your date range or supplier filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="py-3 px-4">Transaction / GRN</th>
                  <th className="py-3 px-4">Receipt Date</th>
                  <th className="py-3 px-4">Supplier / Vendor</th>
                  <th className="py-3 px-4">Product SKU</th>
                  <th className="py-3 px-4">Product Name</th>
                  <th className="py-3 px-4 text-right">Received Qty</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filteredItems.map((item, idx) => (
                  <tr
                    key={`${item.transaction_number}-${item.product_code || ''}-${idx}`}
                    onClick={() => setViewItem(item)}
                    className="hover:bg-emerald-50/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-gray-900">
                      {item.transaction_number}
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 font-mono text-xs">
                      {item.confirmed_at || '-'}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-gray-800">
                      {item.vendor_name || 'General Supplier'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs text-blue-600">
                      {item.product_code}
                    </td>
                    <td className="py-3.5 px-4 text-gray-800">
                      {item.product_name}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-emerald-700">
                      {Number(item.quantity).toLocaleString()}
                      <span className="text-xs text-gray-400 font-normal ml-1">
                        {item.uom_code || 'PCS'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <StatusBadge status={item.status || 'COMPLETED'} />
                    </td>
                    <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => setViewItem(item)}
                        className="p-1.5 rounded-lg text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 transition-colors"
                        title="View GRN Details"
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
      <InwardReportViewModal
        open={Boolean(viewItem)}
        onClose={() => setViewItem(null)}
        data={viewItem}
      />
    </div>
  );
};

export default InwardReportPage;

