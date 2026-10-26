import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  Building2, 
  GitBranch, 
  Truck, 
  Package, 
  Warehouse, 
  MapPin,
  Layers,
  Box,
  BarChart3, 
  Settings,
  ChevronLeft,
  ChevronRight,
  Boxes,
  Shield,
  ShieldCheck,
  UserCircle,
  Store,
  History,
  BookOpen,
  Database,
  Receipt,
  FileSpreadsheet,
  RotateCcw,
  ClipboardList,
  FileText,
  ArrowDownLeft,
  ArrowUpRight,
  ClipboardCheck
} from 'lucide-react';
import { clsx } from 'clsx';

const menuItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
  { 
    label: 'Masters', 
    items: [
      { icon: Building2, label: 'Companies', path: '/companies' },
      { icon: GitBranch, label: 'Branches', path: '/branches' },
      { icon: Users, label: 'Suppliers', path: '/suppliers' },
      { icon: UserCircle, label: 'Customers', path: '/customers' },
      { icon: Store, label: 'Buyers', path: '/buyers' },
      { icon: Truck, label: 'Transport', path: '/transport' },
      { icon: Package, label: 'Products', path: '/products' },
      { icon: LayoutDashboard, label: 'Product Categories', path: '/products/categories' },
      { icon: Database, label: 'Units of Measure', path: '/products/uom' },
    ]
  },
  { 
    label: 'Warehouse Management', 
    items: [
      { icon: Warehouse, label: 'Warehouses', path: '/warehouses' },
      { icon: MapPin, label: 'Locations', path: '/locations' },
      { icon: Layers, label: 'Racks', path: '/racks' },
      { icon: Box, label: 'Bins', path: '/bins' },
      { icon: RotateCcw, label: 'Returns & Rejections', path: '/rejection-returns' },
    ]
  },
  { 
    label: 'Inventory Management', 
    items: [
      { icon: Boxes, label: 'Current Stock', path: '/inventory/stock' },
      { icon: Package, label: 'Supplier Stock', path: '/supplier-stock' },
      { icon: History, label: 'Transactions', path: '/inventory/transactions' },
      { icon: BookOpen, label: 'Ledger', path: '/inventory/ledger' },
    ]
  },
  {
    label: 'Operations',
    items: [
      { icon: ClipboardList, label: 'Job Work Register', path: '/job-work/register' },
      { icon: FileText, label: 'Job Work DCS', path: '/job-work/dcs' },
      { icon: ArrowDownLeft, label: 'Inward', path: '/rings/inward' },
      { icon: ArrowUpRight, label: 'Outward', path: '/logistics/outward' },
      { icon: ClipboardList, label: 'Picking List', path: '/rings/picks' },
      { icon: FileText, label: 'Dispatch / Challan', path: '/rings/dispatch' },
      { icon: Truck, label: 'Dispatch Control', path: '/logistics/dispatch' },
      { icon: Boxes, label: 'Stock Closing', path: '/rings/stock' },
      { icon: BarChart3, label: 'Sales Report', path: '/rings/sales' },
    ]
  },
  {
    label: 'Finance',
    items: [
      { icon: Receipt, label: 'Billing', path: '/billing' },
      { icon: FileSpreadsheet, label: 'Invoicing & GST', path: '/invoicing' },
    ]
  },
  { icon: BarChart3, label: 'Reports', path: '/reports' },
  { icon: History, label: 'Audit Logs', path: '/audit' },
  { icon: Database, label: 'Data Migration', path: '/migration' },
  { 
    label: 'Administration', 
    items: [
      { icon: Users, label: 'Users', path: '/users' },
      { icon: Shield, label: 'Roles', path: '/roles' },
      { icon: ShieldCheck, label: 'Permissions', path: '/roles/permissions' },
      { icon: Settings, label: 'Settings', path: '/settings' },
    ]
  },
];

const Sidebar = ({ isCollapsed, onToggle }) => {
  return (
    <aside 
      className={clsx(
        'bg-white border-r border-gray-200 flex flex-col transition-all duration-300 z-30',
        isCollapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Sidebar Header */}
      <div className="h-16 flex items-center justify-between px-6 border-b border-gray-100">
        {!isCollapsed && <span className="font-bold text-xl text-primary-600">SLN WMS</span>}
        <button 
          onClick={onToggle}
          className="p-1 rounded-lg hover:bg-gray-100 text-gray-400"
        >
          {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-6">
        {menuItems.map((item, index) => (
          <div key={index}>
            {item.items ? (
              <div className="space-y-1">
                {!isCollapsed && (
                  <h4 className="px-2 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                    {item.label}
                  </h4>
                )}
                {item.items.map((subItem) => (
                  <SidebarItem key={subItem.path} item={subItem} isCollapsed={isCollapsed} />
                ))}
              </div>
            ) : (
              <SidebarItem item={item} isCollapsed={isCollapsed} />
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
};

const SidebarItem = ({ item, isCollapsed }) => {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.path}
      className={({ isActive }) => clsx(
        'flex items-center px-3 py-2 rounded-lg transition-colors group',
        isActive 
          ? 'bg-primary-50 text-primary-700' 
          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
      )}
    >
      <Icon className={clsx('flex-shrink-0', isCollapsed ? 'mx-auto' : 'mr-3')} size={20} />
      {!isCollapsed && <span className="text-sm font-medium">{item.label}</span>}
      
      {isCollapsed && (
        <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 whitespace-nowrap">
          {item.label}
        </div>
      )}
    </NavLink>
  );
};

export default Sidebar;
