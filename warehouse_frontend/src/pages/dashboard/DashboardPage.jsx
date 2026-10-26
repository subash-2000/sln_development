import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Card from '../../components/ui/Card';
import {
  Users,
  Package,
  Warehouse,
  AlertTriangle,
  ArrowRight,
  PieChart,
  Activity,
  RefreshCw,
  Truck,
  BarChart3,
} from 'lucide-react';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Loader from '../../components/common/Loader';
import { useAuthStore } from '../../store/auth.store';
import { useDashboardSummary } from '../../modules/dashboard/hooks/use-dashboard';
import { formatAgeStatusLabel } from '../../utils/stockAge';
import StatusBadge from '../../components/ui/StatusBadge';
import { auditApi } from '../../modules/audit/api/audit.api';

const SUPPLIER_BAR_COLORS = [
  'bg-primary-500',
  'bg-emerald-500',
  'bg-amber-500',
  'bg-violet-500',
  'bg-rose-500',
];

const formatCount = (n) => {
  if (n === null || n === undefined) return '—';
  const num = Number(n);
  if (Number.isNaN(num)) return '—';
  return num.toLocaleString('en-IN', { maximumFractionDigits: 0 });
};

const formatQty = (n) => {
  if (n === null || n === undefined) return '0';
  const num = Number(n);
  if (Number.isNaN(num)) return '0';
  return num.toLocaleString('en-IN', { maximumFractionDigits: 0 });
};

const formatPct = (n) => {
  const num = Number(n);
  if (Number.isNaN(num)) return '0%';
  return `${num.toFixed(1)}%`;
};

const StatCard = ({ title, value, icon: Icon, subtitle }) => (
  <Card className="hover:shadow-clay-md transition-shadow">
    <Card.Body>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">{title}</p>
          <h3 className="text-2xl font-bold text-gray-900 mt-1">{value}</h3>
          {subtitle && <p className="text-xs text-gray-400 mt-2">{subtitle}</p>}
        </div>
        <div className="h-12 w-12 bg-primary-50 text-primary-600 rounded-xl flex items-center justify-center">
          <Icon size={24} />
        </div>
      </div>
    </Card.Body>
  </Card>
);

const ManagementChart = ({ title, icon: Icon, children, action }) => (
  <Card>
    <Card.Header className="flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <Icon size={18} className="text-primary-600" />
        <Card.Title>{title}</Card.Title>
      </div>
      {action}
    </Card.Header>
    <Card.Body>{children}</Card.Body>
  </Card>
);

const HorizontalShareBar = ({ label, value, sharePct, colorClass, sublabel }) => (
  <div className="space-y-1.5">
    <div className="flex justify-between text-sm gap-2">
      <span className="font-medium text-gray-800 truncate" title={label}>{label}</span>
      <span className="text-gray-600 whitespace-nowrap">{formatQty(value)} · {formatPct(sharePct)}</span>
    </div>
    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
        style={{ width: `${Math.min(Math.max(sharePct, 0), 100)}%` }}
      />
    </div>
    {sublabel && <p className="text-xs text-gray-400">{sublabel}</p>}
  </div>
);

const DashboardPage = ({ title = 'Dashboard' }) => {
  const user = useAuthStore((s) => s.user);
  const displayName = user?.full_name || user?.username || 'User';

  const {
    data: summary,
    isLoading,
    isFetching,
    error,
    refetch,
    dataUpdatedAt,
  } = useDashboardSummary();

  const { data: auditData } = useQuery({
    queryKey: ['audit-logs', 'dashboard-recent'],
    queryFn: () => auditApi.list({ page: 1, page_size: 5, sort_by: 'timestamp', sort_order: 'desc' }),
    refetchInterval: 30_000,
  });

  const suppliers = summary?.supplier_analytics || [];

  const trendBars = useMemo(() => {
    const points = summary?.inward_trend_7d || [];
    const max = Math.max(...points.map((p) => p.inward_receipts || 0), 1);
    return points.map((p) => ({
      ...p,
      barPx: Math.round(((p.inward_receipts || 0) / max) * 180),
    }));
  }, [summary]);

  const opsTotal = useMemo(() => {
    const inward = summary?.todays_inward_count ?? 0;
    const outward = summary?.todays_outward_count ?? 0;
    const pending = summary?.pending_dispatch_count ?? 0;
    const total = inward + outward + pending || 1;
    return {
      inward,
      outward,
      pending,
      total,
      inwardPct: Math.round((inward / total) * 100),
      outwardPct: Math.round((outward / total) * 100),
      pendingPct: Math.round((pending / total) * 100),
    };
  }, [summary]);

  const warehouseBars = useMemo(() => {
    const rows = summary?.warehouse_stock || [];
    const total = rows.reduce((s, r) => s + (Number(r.value) || 0), 0) || 1;
    return rows.map((r) => ({
      label: r.label,
      value: Number(r.value) || 0,
      sharePct: ((Number(r.value) || 0) / total) * 100,
    }));
  }, [summary]);

  const stockAgeBuckets = useMemo(() => {
    const rows = summary?.stock_age_buckets || [];
    const total = rows.reduce((s, r) => s + (Number(r.count) || 0), 0) || 1;
    const colors = {
      STOCK_OK: 'bg-emerald-500',
      AGING: 'bg-amber-500',
      OVERDUE: 'bg-rose-500',
      UNKNOWN: 'bg-gray-400',
    };
    return rows
      .filter((r) => Number(r.count) > 0)
      .map((r) => ({
        ...r,
        sharePct: ((Number(r.count) || 0) / total) * 100,
        colorClass: colors[r.status] || 'bg-primary-500',
      }));
  }, [summary]);

  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;

  if (isLoading && !summary) {
    return <Loader fullPage />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          <p className="text-gray-500">
            Welcome back, {displayName}. Supplier-wise stock and live operations (refreshes every 30s).
            {lastUpdated && <span className="text-gray-400"> Last update: {lastUpdated}</span>}
          </p>
        </div>
        <div className="flex space-x-3">
          <Button variant="secondary" onClick={() => refetch()} isLoading={isFetching} leftIcon={<RefreshCw size={16} />}>
            Refresh
          </Button>
          <Link to="/reports">
            <Button type="button">Reports</Button>
          </Link>
        </div>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <Card.Body className="text-sm text-red-700">
            Could not load dashboard metrics. Check API connection and company context.
          </Card.Body>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Suppliers"
          value={formatCount(summary?.supplier_count)}
          icon={Users}
          subtitle={`${formatCount(summary?.customer_count)} customers`}
        />
        <StatCard
          title="Active Products"
          value={formatCount(summary?.product_count)}
          icon={Package}
          subtitle="Across all supplier catalogues"
        />
        <StatCard
          title="Warehouses"
          value={formatCount(summary?.warehouse_count)}
          icon={Warehouse}
          subtitle={`${formatQty(summary?.total_items_on_hand)} units on hand`}
        />
        <StatCard
          title="Pending Dispatch"
          value={formatCount(summary?.pending_dispatch_count)}
          icon={AlertTriangle}
          subtitle={`${summary?.todays_inward_count ?? 0} inward receipts today`}
        />
      </div>

      {/* Supplier-wise dashboard */}
      <Card>
        <Card.Header className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <Truck size={18} className="text-primary-600" />
            <Card.Title>Supplier-wise overview</Card.Title>
          </div>
          <Link to="/suppliers">
            <Button variant="ghost" size="sm" type="button" rightIcon={<ArrowRight size={16} />}>
              All suppliers
            </Button>
          </Link>
        </Card.Header>
        <Card.Body className="space-y-6">
          {suppliers.length === 0 ? (
            <p className="text-sm text-gray-500 py-8 text-center">No supplier stock data yet.</p>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {suppliers.map((s, idx) => (
                  <Link
                    key={s.supplier_id}
                    to={`/suppliers/${s.supplier_id}`}
                    className="block rounded-xl border border-gray-100 p-4 hover:border-primary-200 hover:shadow-md transition-all bg-gradient-to-br from-white to-gray-50"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-xs font-semibold text-primary-600 uppercase tracking-wide">{s.supplier_code}</p>
                        <h3 className="font-bold text-gray-900 mt-1 leading-tight">{s.supplier_name}</h3>
                      </div>
                      <Badge variant="neutral">{formatPct(s.stock_share_percent)} stock</Badge>
                    </div>
                    <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <dt className="text-gray-400 text-xs">On hand</dt>
                        <dd className="font-semibold text-gray-900">{formatQty(s.quantity_on_hand)}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-400 text-xs">Available</dt>
                        <dd className="font-semibold text-gray-900">{formatQty(s.quantity_available)}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-400 text-xs">SKU lines</dt>
                        <dd className="font-semibold text-gray-900">{s.sku_line_count}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-400 text-xs">Pending dispatch</dt>
                        <dd className="font-semibold text-gray-900">{s.pending_dispatch_count}</dd>
                      </div>
                    </dl>
                    <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${SUPPLIER_BAR_COLORS[idx % SUPPLIER_BAR_COLORS.length]}`}
                        style={{ width: `${Math.min(s.stock_share_percent, 100)}%` }}
                      />
                    </div>
                  </Link>
                ))}
              </div>

              <div className="overflow-x-auto rounded-lg border border-gray-100">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Supplier</th>
                      <th className="px-4 py-3 font-semibold text-right">On hand</th>
                      <th className="px-4 py-3 font-semibold text-right">Available</th>
                      <th className="px-4 py-3 font-semibold text-right">SKU lines</th>
                      <th className="px-4 py-3 font-semibold text-right">Share</th>
                      <th className="px-4 py-3 font-semibold text-right">Pending dispatch</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {suppliers.map((s, idx) => (
                      <tr key={s.supplier_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <Link to={`/suppliers/${s.supplier_id}`} className="font-medium text-primary-700 hover:underline">
                            {s.supplier_name}
                          </Link>
                          <span className="text-gray-400 text-xs ml-2">{s.supplier_code}</span>
                        </td>
                        <td className="px-4 py-3 text-right font-mono">{formatQty(s.quantity_on_hand)}</td>
                        <td className="px-4 py-3 text-right font-mono">{formatQty(s.quantity_available)}</td>
                        <td className="px-4 py-3 text-right">{s.sku_line_count}</td>
                        <td className="px-4 py-3 text-right">
                          <span className="inline-flex items-center gap-2 justify-end w-full">
                            <span className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden hidden sm:inline-block">
                              <span
                                className={`block h-full ${SUPPLIER_BAR_COLORS[idx % SUPPLIER_BAR_COLORS.length]}`}
                                style={{ width: `${Math.min(s.stock_share_percent, 100)}%` }}
                              />
                            </span>
                            {formatPct(s.stock_share_percent)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">{s.pending_dispatch_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card.Body>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ManagementChart title="Stock share by supplier" icon={BarChart3}>
          {suppliers.length === 0 ? (
            <p className="text-sm text-gray-500 py-16 text-center">No supplier stock on hand.</p>
          ) : (
            <div className="space-y-5 py-2">
              {suppliers.map((s, idx) => (
                <HorizontalShareBar
                  key={s.supplier_id}
                  label={s.supplier_name}
                  value={s.quantity_on_hand}
                  sharePct={s.stock_share_percent}
                  colorClass={SUPPLIER_BAR_COLORS[idx % SUPPLIER_BAR_COLORS.length]}
                  sublabel={`${s.sku_line_count} SKU lines · ${s.pending_dispatch_count} pending dispatch`}
                />
              ))}
            </div>
          )}
        </ManagementChart>

        <ManagementChart
          title="Stock age (warehouse)"
          icon={PieChart}
          action={
            <Link to="/inventory/stock">
              <Button variant="ghost" size="sm" type="button" rightIcon={<ArrowRight size={16} />}>
                Current stock
              </Button>
            </Link>
          }
        >
          {stockAgeBuckets.length === 0 ? (
            <p className="text-sm text-gray-500 py-16 text-center">No stock lines to analyse.</p>
          ) : (
            <div className="space-y-4 py-2">
              {stockAgeBuckets.map((bucket) => (
                <div key={bucket.status} className="flex items-center justify-between gap-3 text-sm">
                  <div className="flex items-center gap-2 min-w-0">
                    <StatusBadge status={formatAgeStatusLabel(bucket.status)} />
                    <span className="text-gray-600 truncate">{bucket.label}</span>
                  </div>
                  <span className="font-semibold text-gray-900 tabular-nums">{formatCount(bucket.count)} lines</span>
                </div>
              ))}
              <div className="space-y-2 pt-2 border-t border-gray-100">
                {stockAgeBuckets.map((bucket) => (
                  <HorizontalShareBar
                    key={`bar-${bucket.status}`}
                    label={formatAgeStatusLabel(bucket.status)}
                    value={bucket.count}
                    sharePct={bucket.sharePct}
                    colorClass={bucket.colorClass}
                  />
                ))}
              </div>
            </div>
          )}
        </ManagementChart>

        <ManagementChart title="Inward receipts (last 7 days)" icon={Activity}>
          <div className="h-56 flex items-end justify-between gap-2 px-1 pt-4">
            {trendBars.map((bar) => (
              <div key={bar.date} className="flex-1 flex flex-col items-center justify-end h-full min-w-0">
                <span className="text-[10px] text-gray-500 mb-1 font-mono">{bar.inward_receipts}</span>
                <div
                  className="w-full max-w-[48px] bg-primary-500 rounded-t-md hover:bg-primary-600 transition-colors"
                  style={{ height: `${Math.max(bar.barPx, 4)}px` }}
                  title={`${bar.day_label}: ${bar.inward_receipts} receipts`}
                />
                <span className="text-[10px] text-gray-400 mt-2 uppercase">{bar.day_label}</span>
              </div>
            ))}
          </div>
        </ManagementChart>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ManagementChart title="Stock by warehouse" icon={Warehouse}>
          {warehouseBars.length === 0 ? (
            <p className="text-sm text-gray-500 py-12 text-center">No warehouse stock.</p>
          ) : (
            <div className="space-y-4 py-2">
              {warehouseBars.map((w) => (
                <HorizontalShareBar
                  key={w.label}
                  label={w.label}
                  value={w.value}
                  sharePct={w.sharePct}
                  colorClass="bg-slate-600"
                />
              ))}
            </div>
          )}
        </ManagementChart>

        <ManagementChart title="Operations today" icon={PieChart}>
          <div className="h-56 flex items-center justify-around flex-wrap gap-4">
            <div className="relative h-44 w-44 shrink-0">
              <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
                <circle cx="18" cy="18" r="16" fill="none" className="stroke-gray-100" strokeWidth="4" />
                <circle
                  cx="18"
                  cy="18"
                  r="16"
                  fill="none"
                  className="stroke-primary-500"
                  strokeWidth="4"
                  strokeDasharray={`${opsTotal.inwardPct}, 100`}
                />
                <circle
                  cx="18"
                  cy="18"
                  r="16"
                  fill="none"
                  className="stroke-emerald-500"
                  strokeWidth="4"
                  strokeDasharray={`${opsTotal.outwardPct}, 100`}
                  strokeDashoffset={`-${opsTotal.inwardPct}`}
                />
                <circle
                  cx="18"
                  cy="18"
                  r="16"
                  fill="none"
                  className="stroke-amber-500"
                  strokeWidth="4"
                  strokeDasharray={`${opsTotal.pendingPct}, 100`}
                  strokeDashoffset={`-${opsTotal.inwardPct + opsTotal.outwardPct}`}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-gray-900">{opsTotal.total}</span>
                <span className="text-[10px] text-gray-500 uppercase tracking-widest">Events</span>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-primary-500 rounded-sm mr-2" />
                <span className="text-gray-600">Inward receipts ({opsTotal.inward})</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-emerald-500 rounded-sm mr-2" />
                <span className="text-gray-600">Outward dispatched ({opsTotal.outward})</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-amber-500 rounded-sm mr-2" />
                <span className="text-gray-600">Open dispatch orders ({opsTotal.pending})</span>
              </div>
            </div>
          </div>
        </ManagementChart>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <Card.Header className="flex items-center justify-between">
            <Card.Title>Recent activity</Card.Title>
            <Link to="/audit">
              <Button variant="ghost" size="sm" type="button" rightIcon={<ArrowRight size={16} />}>
                View all
              </Button>
            </Link>
          </Card.Header>
          <Card.Body>
            <div className="space-y-4">
              {(auditData?.items || []).length === 0 ? (
                <p className="text-sm text-gray-500">No audit events yet.</p>
              ) : (
                auditData.items.map((row) => (
                  <div
                    key={row.id}
                    className="flex items-center space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors"
                  >
                    <div className="h-10 w-10 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <Activity size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {row.action} {row.entity_name}
                        {row.entity_id ? ` · ${String(row.entity_id).slice(0, 8)}…` : ''}
                      </p>
                      <p className="text-xs text-gray-500">
                        {row.module} · {row.user_name || 'System'}
                      </p>
                    </div>
                    <Badge variant="neutral">{row.action}</Badge>
                  </div>
                ))
              )}
            </div>
          </Card.Body>
        </Card>

        <div className="space-y-6">
          <Card>
            <Card.Header>
              <Card.Title>Quick actions</Card.Title>
            </Card.Header>
            <Card.Body className="space-y-2">
              <Link to="/suppliers" className="block">
                <Button variant="outline" type="button" className="w-full justify-start">
                  Supplier master
                </Button>
              </Link>
              <Link to="/inventory/stock" className="block">
                <Button variant="outline" type="button" className="w-full justify-start">
                  Stock by supplier
                </Button>
              </Link>
              <Link to="/logistics/dispatch" className="block">
                <Button variant="outline" type="button" className="w-full justify-start">
                  Dispatch board
                </Button>
              </Link>
            </Card.Body>
          </Card>

          <Card className="bg-primary-600 text-white border-none">
            <Card.Body>
              <h4 className="font-bold text-lg">Financial snapshot</h4>
              <p className="text-primary-100 text-sm mt-1">Month-to-date from posted invoices.</p>
              <div className="mt-4 p-3 bg-primary-700/50 rounded-lg border border-primary-500 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span>Revenue MTD</span>
                  <span className="font-mono">₹{formatQty(summary?.total_revenue_mtd)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Pending invoices</span>
                  <span className="font-mono">₹{formatQty(summary?.pending_invoice_amount)}</span>
                </div>
                <div className="flex justify-between border-t border-primary-500/50 pt-2 mt-2">
                  <span>Job work balance (qty)</span>
                  <span className="font-mono">{formatQty(summary?.job_work_balance_total)}</span>
                </div>
              </div>
            </Card.Body>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
