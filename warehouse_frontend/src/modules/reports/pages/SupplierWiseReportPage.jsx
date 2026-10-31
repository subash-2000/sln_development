import React, { useState, useMemo } from 'react';
import { 
  Building2, 
  Search, 
  Download, 
  FileSpreadsheet,
  RotateCcw, 
  Eye, 
  Boxes, 
  Package, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import Loader from '../../../components/common/Loader';
import { useSupplierStockReports } from '../hooks/use-reports';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { exportReportToCsv } from '../api/reports.api';
import { exportSupplierWiseReportToExcel } from '../utils/excel-export';
import SupplierWiseReportViewModal from '../components/SupplierWiseReportViewModal';

const SupplierWiseReportPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSupplier, setSelectedSupplier] = useState('');
  const [stockLevelFilter, setStockLevelFilter] = useState('ALL'); // ALL, AVAILABLE_ONLY, LOW_STOCK
  const [viewItem, setViewItem] = useState(null);

  // Fetch full list of registered vendors
  const { data: vendorsData } = useVendors({ page_size: 200 });

  const queryParams = useMemo(() => {
    const params = { page_size: 200 };
    if (searchTerm) params.search = searchTerm.trim();
    if (selectedSupplier) params.vendor_name = selectedSupplier.trim();
    return params;
  }, [searchTerm, selectedSupplier]);

  const { data: reportsData, isLoading, isFetching, error, refetch } = useSupplierStockReports(queryParams);
  const items = reportsData?.items || [];

  const supplierOptions = useMemo(() => {
    const set = new Set();
    (vendorsData?.items || []).forEach((v) => {
      if (v.name) set.add(v.name.trim());
    });
    items.forEach((i) => {
      if (i.vendor_name) set.add(i.vendor_name.trim());
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [vendorsData, items]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (selectedSupplier) {
        const itemV = (item.vendor_name || '').trim().toLowerCase();
        const selV = selectedSupplier.trim().toLowerCase();
        if (itemV !== selV && !itemV.includes(selV) && !selV.includes(itemV)) {
          return false;
        }
      }
      if (stockLevelFilter === 'AVAILABLE_ONLY' && Number(item.quantity_available || 0) <= 0) return false;
      if (stockLevelFilter === 'LOW_STOCK' && Number(item.quantity_available || 0) > 100) return false;

      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesSupplier = (item.vendor_name || '').toLowerCase().includes(term);
        const matchesSku = (item.product_code || '').toLowerCase().includes(term);
        const matchesName = (item.product_name || '').toLowerCase().includes(term);
        if (!matchesSupplier && !matchesSku && !matchesName) return false;
      }
      return true;
    });
  }, [items, selectedSupplier, stockLevelFilter, searchTerm]);

  // Aggregate KPIs
  const totalRecords = filteredItems.length;
  const uniqueSuppliers = new Set(filteredItems.map((i) => i.vendor_name).filter(Boolean)).size;
  const totalOnHand = filteredItems.reduce((sum, i) => sum + (Number(i.quantity_on_hand) || 0), 0);
  const totalAvailable = filteredItems.reduce((sum, i) => sum + (Number(i.quantity_available) || 0), 0);

  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedSupplier('');
    setStockLevelFilter('ALL');
  };

  const handleExportExcel = () => {
    exportSupplierWiseReportToExcel(filteredItems, {
      vendor_name: selectedSupplier,
      stock_level: stockLevelFilter,
      search: searchTerm,
    });
  };

  const handleExportCsv = () => {
    const headers = [
      'Supplier / Vendor',
      'Product SKU',
      'Product Name',
      'Quantity On Hand',
      'Quantity Reserved',
      'Quantity Available',
      'UOM',
    ];

    const rows = filteredItems.map((item) => [
      item.vendor_name || '',
      item.product_code || '',
      item.product_name || '',
      item.quantity_on_hand || '',
      item.quantity_reserved || '',
      item.quantity_available || '',
      item.uom_code || 'PCS',
    ]);

    const dateStr = new Date().toISOString().split('T')[0];
    exportReportToCsv(headers, rows, `supplier_wise_stock_report_${dateStr}.csv`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supplier Wise Stock Reports"
        description="Monitor vendor-owned inventory, consignment stocks, holding positions, and material availability"
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Reports', to: '/reports' },
          { label: 'Supplier Wise Reports' },
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
              Export Excel (Type Wise Stock)
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
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-emerald-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Active Suppliers</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{uniqueSuppliers}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Building2 size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-blue-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Supplier Product Lines</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalRecords}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Package size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-teal-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Stock On Hand</p>
              <h3 className="text-2xl font-bold text-teal-700 mt-1">{totalOnHand.toLocaleString()}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
              <Boxes size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Available For Orders</p>
              <h3 className="text-2xl font-bold text-indigo-700 mt-1">{totalAvailable.toLocaleString()}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <CheckCircle2 size={20} />
            </div>
          </div>
        </Card>
      </div>

      {/* Filter Toolbar */}
      <Card>
        <Card.Body className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-gray-400" size={16} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search supplier, SKU, product..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              />
            </div>

            {/* Supplier Select */}
            <div>
              <select
                value={selectedSupplier}
                onChange={(e) => setSelectedSupplier(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Suppliers</option>
                {supplierOptions.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Stock Level Select */}
            <div>
              <select
                value={stockLevelFilter}
                onChange={(e) => setStockLevelFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="ALL">All Stock Levels</option>
                <option value="AVAILABLE_ONLY">Available &gt; 0</option>
                <option value="LOW_STOCK">Low Stock (&le; 100)</option>
              </select>
            </div>

            {/* Reset & Export */}
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={handleResetFilters}
                className="flex items-center gap-1.5 shrink-0"
                title="Reset Filters"
              >
                <RotateCcw size={16} />
              </Button>
              <Button
                variant="primary"
                onClick={handleExportExcel}
                disabled={filteredItems.length === 0}
                className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 text-sm shadow-xs"
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
            <p className="text-base font-semibold text-red-700">Failed to load supplier reports</p>
            <p className="text-xs text-red-500">
              {error?.message || 'Server connection error. Please ensure the backend is running.'}
            </p>
            <Button variant="secondary" onClick={() => refetch()} className="mt-2 text-xs">
              Retry
            </Button>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-2">
            <Building2 size={36} className="mx-auto text-gray-400" />
            <p className="text-base font-semibold text-gray-700">No supplier stock records found</p>
            <p className="text-xs text-gray-400">
              Try selecting a different supplier or clearing search filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="py-3 px-4">Supplier / Vendor</th>
                  <th className="py-3 px-4">Product SKU</th>
                  <th className="py-3 px-4">Product Name</th>
                  <th className="py-3 px-4 text-right">On Hand</th>
                  <th className="py-3 px-4 text-right">Reserved</th>
                  <th className="py-3 px-4 text-right">Available</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filteredItems.map((item, idx) => (
                  <tr
                    key={`${item.vendor_name}-${item.product_code}-${idx}`}
                    onClick={() => setViewItem(item)}
                    className="hover:bg-emerald-50/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-bold text-gray-900 flex items-center gap-2">
                      <div className="p-1.5 rounded-md bg-emerald-50 text-emerald-600">
                        <Building2 size={16} />
                      </div>
                      {item.vendor_name}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-600">
                      {item.product_code}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-gray-800">
                      {item.product_name}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-gray-900">
                      {Number(item.quantity_on_hand).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-amber-600 font-medium">
                      {Number(item.quantity_reserved).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-emerald-700">
                      {Number(item.quantity_available).toLocaleString()}
                      <span className="text-xs text-gray-400 font-normal ml-1">
                        {item.uom_code || 'PCS'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => setViewItem(item)}
                        className="p-1.5 rounded-lg text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 transition-colors"
                        title="View Supplier Stock Details"
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
      <SupplierWiseReportViewModal
        open={Boolean(viewItem)}
        onClose={() => setViewItem(null)}
        data={viewItem}
      />
    </div>
  );
};

export default SupplierWiseReportPage;

