import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Truck, 
  ArrowDownLeft, 
  ArrowUpRight, 
  Boxes, 
  FileSpreadsheet, 
  BarChart3, 
  ArrowRight,
  Shield,
  FileText,
  ClipboardList
} from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';

const primaryReports = [
  {
    to: '/reports/vehicles',
    title: 'Vehicle Movement Reports',
    description: 'Track fleet vehicle trips, transporter assignments, driver contact details, and outward consignments.',
    icon: Truck,
    color: 'bg-blue-600 text-white',
    badge: 'Logistics',
  },
  {
    to: '/reports/inward',
    title: 'Inward Stock Reports',
    description: 'Detailed audit ledger of goods receipt notes (GRNs), supplier deliveries, quantities, and receipt status.',
    icon: ArrowDownLeft,
    color: 'bg-emerald-600 text-white',
    badge: 'Inventory Inward',
  },
  {
    to: '/reports/outward',
    title: 'Outward Dispatch Reports',
    description: 'Monitor outward dispatches, delivery challans, consignee destinations, and vehicle loadings.',
    icon: ArrowUpRight,
    color: 'bg-sky-600 text-white',
    badge: 'Distribution',
  },
  {
    to: '/reports/daily-stock',
    title: 'Daily Stock Reports',
    description: 'Real-time on-hand stock quantities, batch balances, reservations, and warehouse storage bin positions.',
    icon: Boxes,
    color: 'bg-amber-600 text-white',
    badge: 'Stock Levels',
  },
  {
    to: '/reports/supplier-wise',
    title: 'Supplier Wise Reports',
    description: 'Vendor-wise inventory holdings, consignment stocks, material availability, and valuation breakdown.',
    icon: Building2,
    color: 'bg-teal-600 text-white',
    badge: 'Supplier Audit',
  },
  {
    to: '/reports/invoices',
    title: 'Invoice & Sales Reports',
    description: 'GST tax invoices, customer billing summaries, CGST/SGST/IGST breakdown, and payment status.',
    icon: FileSpreadsheet,
    color: 'bg-purple-600 text-white',
    badge: 'Commercial & GST',
  },
];

const operationalReports = [
  { to: '/inventory/stock', title: 'Current Stock Master', description: 'On-hand, available and reserved warehouse quantities.' },
  { to: '/inventory/transactions', title: 'Stock Transactions', description: 'Complete history of receipts, deliveries and adjustments.' },
  { to: '/inventory/ledger', title: 'Stock Ledger', description: 'Double-entry posted inventory ledger with audit balances.' },
  { to: '/job-work/register', title: 'Job Work Register', description: 'Job work orders, issue/receipt tracking, and processing status.' },
  { to: '/finance/invoicing/gst-reports', title: 'GST Summary Breakup', description: 'Statutory GST tax components from confirmed invoices.' },
  { to: '/audit', title: 'Audit Logs', description: 'System mutations, access records, and administration audit trails.' },
];

const ReportListPage = () => {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Enterprise Reports Hub"
        description="Comprehensive analytics, vehicle movements, stock ledgers, and financial reports"
        breadcrumbs={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Reports' }]}
      />

      {/* Primary 5 Reports Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-base font-bold text-gray-900 tracking-tight">
            Core Enterprise Operational Reports
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Real-time interactive reports with advanced filtering, CSV exports, and line-item modal views
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {primaryReports.map((report) => {
            const Icon = report.icon;
            return (
              <Link key={report.to} to={report.to} className="group">
                <Card className="h-full border border-gray-100 hover:border-blue-200 hover:shadow-lg transition-all duration-200">
                  <Card.Body className="p-5 flex flex-col justify-between h-full space-y-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className={`w-11 h-11 rounded-xl ${report.color} flex items-center justify-center shadow-xs`}>
                          <Icon size={22} />
                        </div>
                        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-700">
                          {report.badge}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-900 text-base group-hover:text-blue-600 transition-colors">
                          {report.title}
                        </h3>
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2 leading-relaxed">
                          {report.description}
                        </p>
                      </div>
                    </div>
                    <div className="pt-3 border-t border-gray-100 flex items-center text-xs font-semibold text-blue-600 group-hover:translate-x-0.5 transition-transform">
                      Open Report <ArrowRight size={14} className="ml-1" />
                    </div>
                  </Card.Body>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Additional Statements Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider text-gray-500">
            System & Operational Registers
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {operationalReports.map((report) => (
            <Link key={report.to} to={report.to}>
              <Card className="h-full hover:shadow-md transition-shadow">
                <Card.Body className="p-4">
                  <h3 className="font-semibold text-gray-900 text-sm hover:text-blue-600">
                    {report.title}
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">{report.description}</p>
                </Card.Body>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ReportListPage;
