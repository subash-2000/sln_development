import React, { useState, useMemo } from 'react';
import { 
  Boxes, 
  Search, 
  Download, 
  FileSpreadsheet,
  RotateCcw, 
  Eye, 
  Warehouse, 
  Layers, 
  CheckCircle2, 
  AlertTriangle,
  Calendar
} from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import Loader from '../../../components/common/Loader';
import { useDailyStockReports } from '../hooks/use-reports';
import { exportReportToCsv } from '../api/reports.api';
import { exportDailyStockReportToExcel } from '../utils/excel-export';
import DailyStockReportViewModal from '../components/DailyStockReportViewModal';

const DailyStockReportPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedWarehouse, setSelectedWarehouse] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [stockFilter, setStockFilter] = useState('ALL'); // ALL, AVAILABLE_ONLY, LOW_STOCK
  const [period, setPeriod] = useState('DAILY'); // DAILY, WEEKLY, MONTHLY, YEARLY
  const [viewItem, setViewItem] = useState(null);

  const queryParams = useMemo(() => {
    const params = { page_size: 200 };
    if (searchTerm) params.search = searchTerm;
    return params;
  }, [searchTerm]);

  const { data: reportsData, isLoading } = useDailyStockReports(queryParams);
  const items = reportsData?.items || [];

  const warehouseOptions = useMemo(() => {
    return Array.from(new Set(items.map((i) => i.warehouse_name).filter(Boolean))).sort();
  }, [items]);

  const categoryOptions = useMemo(() => {
    return Array.from(new Set(items.map((i) => i.category_name).filter(Boolean))).sort();
  }, [items]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (selectedWarehouse && item.warehouse_name !== selectedWarehouse) return false;
      if (selectedCategory && item.category_name !== selectedCategory) return false;
      if (stockFilter === 'AVAILABLE_ONLY' && Number(item.quantity_available || 0) <= 0) return false;
      if (stockFilter === 'LOW_STOCK' && Number(item.quantity_available || 0) > 100) return false;

      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesSku = (item.product_code || '').toLowerCase().includes(term);
        const matchesName = (item.product_name || '').toLowerCase().includes(term);
        const matchesBatch = (item.batch_number || '').toLowerCase().includes(term);
        if (!matchesSku && !matchesName && !matchesBatch) return false;
      }
      return true;
    });
  }, [items, selectedWarehouse, selectedCategory, stockFilter, searchTerm]);

  // Aggregate KPIs
  const totalSkus = filteredItems.length;
  const totalOnHand = filteredItems.reduce((sum, i) => sum + (Number(i.quantity_on_hand) || 0), 0);
  const totalReserved = filteredItems.reduce((sum, i) => sum + (Number(i.quantity_reserved) || 0), 0);
  const totalAvailable = filteredItems.reduce((sum, i) => sum + (Number(i.quantity_available) || 0), 0);

  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedWarehouse('');
    setSelectedCategory('');
    setStockFilter('ALL');
  };

  const handleExportExcel = () => {
    exportDailyStockReportToExcel(filteredItems, {
      period,
      warehouse_name: selectedWarehouse,
      category_name: selectedCategory,
      stock_filter: stockFilter,
      search: searchTerm,
    });
  };

  const handleExportCsv = () => {
    const headers = [
      'Product SKU',
      'Product Name',
      'Category',
      'Warehouse',
      'Location / Bin',
      'Batch / Lot',
      'Quantity On Hand',
      'Quantity Reserved',
      'Quantity Available',
      'UOM',
    ];

    const rows = filteredItems.map((item) => [
      item.product_code || '',
      item.product_name || '',
      item.category_name || '',
      item.warehouse_name || '',
      item.location_code || '',
      item.batch_number || '',
      item.quantity_on_hand || '',
      item.quantity_reserved || '',
      item.quantity_available || '',
      item.uom_code || 'PCS',
    ]);

    const dateStr = new Date().toISOString().split('T')[0];
    exportReportToCsv(headers, rows, `daily_stock_report_${dateStr}.csv`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Daily Stock Reports"
        description="Comprehensive view of on-hand inventory balances, reservations, and storage bin positions"
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Reports', to: '/reports' },
          { label: 'Daily Stock Reports' },
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
              Export Excel (Summary Sheet)
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
        <Card className="p-4 border-l-4 border-l-blue-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Tracked SKUs</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalSkus}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Boxes size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total On Hand</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalOnHand.toLocaleString()}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Warehouse size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Reserved For Orders</p>
              <h3 className="text-2xl font-bold text-amber-600 mt-1">{totalReserved.toLocaleString()}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <AlertTriangle size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Available For Dispatch</p>
              <h3 className="text-2xl font-bold text-emerald-600 mt-1">{totalAvailable.toLocaleString()}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 size={20} />
            </div>
          </div>
        </Card>
      </div>

      {/* Period Selection Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-gray-200 shadow-xs">
        <div className="flex items-center gap-2">
          <Calendar size={18} className="text-gray-500" />
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Analysis Period:</span>
        </div>
        <div className="flex items-center gap-1.5 p-1 bg-gray-100 rounded-lg">
          {[
            { id: 'DAILY', label: 'Daily (Day-wise)' },
            { id: 'WEEKLY', label: 'Weekly Summary' },
            { id: 'MONTHLY', label: 'Monthly' },
            { id: 'YEARLY', label: 'Yearly' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setPeriod(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                period === tab.id
                  ? 'bg-white text-emerald-700 shadow-xs font-semibold'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Filters Toolbar */}
      <Card>
        <Card.Body className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-gray-400" size={16} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search SKU, product, batch..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              />
            </div>

            <div>
              <select
                value={selectedWarehouse}
                onChange={(e) => setSelectedWarehouse(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Warehouses</option>
                {warehouseOptions.map((w) => (
                  <option key={w} value={w}>
                    {w}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Categories</option>
                {categoryOptions.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <select
                value={stockFilter}
                onChange={(e) => setStockFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="ALL">All Stock Levels</option>
                <option value="AVAILABLE_ONLY">Available &gt; 0</option>
                <option value="LOW_STOCK">Low Stock (&le; 100)</option>
              </select>
            </div>

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
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-2">
            <Boxes size={36} className="mx-auto text-gray-400" />
            <p className="text-base font-semibold text-gray-700">No stock records found</p>
            <p className="text-xs text-gray-400">
              Try adjusting your warehouse or search filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="py-3 px-4">Product SKU</th>
                  <th className="py-3 px-4">Product Name</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Warehouse & Bin</th>
                  <th className="py-3 px-4">Batch / Lot</th>
                  <th className="py-3 px-4 text-right">On Hand</th>
                  <th className="py-3 px-4 text-right">Reserved</th>
                  <th className="py-3 px-4 text-right">Available</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filteredItems.map((item, idx) => (
                  <tr
                    key={`${item.product_code}-${item.batch_number}-${idx}`}
                    onClick={() => setViewItem(item)}
                    className="hover:bg-amber-50/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-gray-900">
                      {item.product_code}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-gray-800">
                      {item.product_name}
                    </td>
                    <td className="py-3.5 px-4 text-xs">
                      <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-medium">
                        {item.category_name || 'Standard'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-gray-900 text-xs font-medium">{item.warehouse_name}</div>
                      <div className="text-xs text-gray-400 font-mono">{item.location_code}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs text-gray-600">
                      {item.batch_number || '-'}
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
                        className="p-1.5 rounded-lg text-amber-600 hover:text-amber-800 hover:bg-amber-50 transition-colors"
                        title="View Stock Breakdown"
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
      <DailyStockReportViewModal
        open={Boolean(viewItem)}
        onClose={() => setViewItem(null)}
        data={viewItem}
      />
    </div>
  );
};

export default DailyStockReportPage;

