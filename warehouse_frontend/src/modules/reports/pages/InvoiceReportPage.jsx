import React, { useState, useMemo } from 'react';
import { 
  FileSpreadsheet, 
  Search, 
  Download, 
  RotateCcw, 
  Eye, 
  Calendar,
  Building2,
  Receipt,
  DollarSign,
  CheckCircle2
} from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';
import Loader from '../../../components/common/Loader';
import { useInvoiceReports } from '../hooks/use-reports';
import { exportReportToCsv } from '../api/reports.api';
import InvoiceReportViewModal from '../components/InvoiceReportViewModal';

const InvoiceReportPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [viewItem, setViewItem] = useState(null);

  const queryParams = useMemo(() => {
    const params = { page_size: 200 };
    if (searchTerm) params.search = searchTerm;
    if (selectedStatus) params.status = selectedStatus;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [searchTerm, selectedStatus, dateFrom, dateTo]);

  const { data: reportsData, isLoading } = useInvoiceReports(queryParams);
  const items = reportsData?.items || [];

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (selectedStatus && item.status !== selectedStatus) return false;
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesInv = (item.invoice_number || '').toLowerCase().includes(term);
        const matchesCust = (item.customer_name || '').toLowerCase().includes(term);
        if (!matchesInv && !matchesCust) return false;
      }
      return true;
    });
  }, [items, selectedStatus, searchTerm]);

  // Aggregate KPIs
  const totalInvoices = filteredItems.length;
  const totalTaxable = filteredItems.reduce((sum, i) => sum + (Number(i.taxable_value) || 0), 0);
  const totalGst = filteredItems.reduce(
    (sum, i) =>
      sum +
      (Number(i.cgst_amount) || 0) +
      (Number(i.sgst_amount) || 0) +
      (Number(i.igst_amount) || 0),
    0
  );
  const grandTotal = filteredItems.reduce((sum, i) => sum + (Number(i.total_amount) || 0), 0);

  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedStatus('');
    setDateFrom('');
    setDateTo('');
  };

  const handleExportCsv = () => {
    const headers = [
      'Invoice Number',
      'Invoice Date',
      'Customer Name',
      'Taxable Value',
      'CGST',
      'SGST',
      'IGST',
      'Total Amount',
      'Status',
    ];

    const rows = filteredItems.map((item) => [
      item.invoice_number || '',
      item.invoice_date || '',
      item.customer_name || '',
      item.taxable_value || '',
      item.cgst_amount || '',
      item.sgst_amount || '',
      item.igst_amount || '',
      item.total_amount || '',
      item.status || '',
    ]);

    const dateStr = new Date().toISOString().split('T')[0];
    exportReportToCsv(headers, rows, `invoice_sales_report_${dateStr}.csv`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Invoice & Sales Reports"
        description="Comprehensive summary of sales invoices, GST component breakups, and accounts receivable"
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Reports', to: '/reports' },
          { label: 'Invoice Reports' },
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

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-purple-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Total Invoices</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{totalInvoices}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <FileSpreadsheet size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-blue-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Taxable Value</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">
                ₹{totalTaxable.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Receipt size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">GST Collected</p>
              <h3 className="text-2xl font-bold text-amber-600 mt-1">
                ₹{totalGst.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Receipt size={20} />
            </div>
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500">Gross Invoiced Revenue</p>
              <h3 className="text-2xl font-bold text-emerald-600 mt-1">
                ₹{grandTotal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 size={20} />
            </div>
          </div>
        </Card>
      </div>

      {/* Filters Toolbar */}
      <Card>
        <Card.Body className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-gray-400" size={16} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search invoice number, customer..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              />
            </div>

            <div>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:bg-white"
              >
                <option value="">All Invoice Statuses</option>
                <option value="PAID">Paid</option>
                <option value="PARTIALLY_PAID">Partially Paid</option>
                <option value="ISSUED">Issued</option>
                <option value="DRAFT">Draft</option>
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
            <FileSpreadsheet size={36} className="mx-auto text-gray-400" />
            <p className="text-base font-semibold text-gray-700">No invoices found</p>
            <p className="text-xs text-gray-400">
              Try adjusting your date range or status filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b border-gray-200 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="py-3 px-4">Invoice No</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4 text-right">Taxable Value</th>
                  <th className="py-3 px-4 text-right">CGST</th>
                  <th className="py-3 px-4 text-right">SGST</th>
                  <th className="py-3 px-4 text-right">IGST</th>
                  <th className="py-3 px-4 text-right">Total Amount</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filteredItems.map((item, idx) => (
                  <tr
                    key={`${item.invoice_number}-${idx}`}
                    onClick={() => setViewItem(item)}
                    className="hover:bg-purple-50/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-gray-900">
                      {item.invoice_number}
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 font-mono text-xs">
                      {item.invoice_date || '-'}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-gray-800">
                      {item.customer_name || 'Direct Customer'}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-gray-800">
                      ₹{Number(item.taxable_value).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-xs text-gray-600">
                      ₹{Number(item.cgst_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-xs text-gray-600">
                      ₹{Number(item.sgst_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-xs text-gray-600">
                      ₹{Number(item.igst_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-purple-700">
                      ₹{Number(item.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <StatusBadge status={item.status || 'ISSUED'} />
                    </td>
                    <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => setViewItem(item)}
                        className="p-1.5 rounded-lg text-purple-600 hover:text-purple-800 hover:bg-purple-50 transition-colors"
                        title="View Tax Invoice Breakdown"
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
      <InvoiceReportViewModal
        open={Boolean(viewItem)}
        onClose={() => setViewItem(null)}
        data={viewItem}
      />
    </div>
  );
};

export default InvoiceReportPage;

