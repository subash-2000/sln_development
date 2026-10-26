import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
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
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { clsx } from 'clsx';

const menuItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
  { 
    label: 'Masters', 
    items: [
      { 
        label: 'Entity Management', 
        items: [
          { icon: Building2, label: 'Companies', path: '/companies' },
          { icon: GitBranch, label: 'Branches', path: '/branches' },
        ]
      },
      { 
        label: 'Business Partners', 
        items: [
          { icon: Users, label: 'Suppliers', path: '/suppliers' },
          { icon: UserCircle, label: 'Customers', path: '/customers' },
          { icon: Store, label: 'Buyers', path: '/buyers' },
          { icon: Truck, label: 'Transport', path: '/transport' },
        ]
      },
      { 
        label: 'Inventory Items', 
        items: [
          { icon: Package, label: 'Products', path: '/products' },
          { icon: LayoutDashboard, label: 'Product Categories', path: '/products/categories' },
          { icon: Database, label: 'Units of Measure', path: '/products/uom' },
        ]
      },
    ]
  },
  { 
    label: 'Warehouse', 
    items: [
      { 
        label: 'Storage Structure', 
        items: [
          { icon: Warehouse, label: 'Warehouses', path: '/warehouses' },
          { icon: MapPin, label: 'Zones & Locations', path: '/locations' },
          { icon: Layers, label: 'Racks', path: '/racks' },
          { icon: Box, label: 'Bins', path: '/bins' },
        ]
      },
      {
        label: 'Return Mgmt',
        items: [
          { icon: RotateCcw, label: 'Returns & Rejections', path: '/rejection-returns' },
        ]
      }
    ]
  },
  { 
    label: 'Inventory', 
    items: [
      { 
        label: 'Stock Views', 
        items: [
          { icon: Boxes, label: 'Current Stock', path: '/inventory/stock' },
          { icon: Package, label: 'Supplier Stock', path: '/supplier-stock' },
        ]
      },
      { 
        label: 'Movement', 
        items: [
          { icon: History, label: 'Transactions', path: '/inventory/transactions' },
          { icon: BookOpen, label: 'Stock Ledger', path: '/inventory/ledger' },
        ]
      },
    ]
  },
  {
    label: 'Operations',
    items: [
      { 
        label: 'Job Work', 
        items: [
          { icon: ClipboardList, label: 'Register', path: '/job-work/register' },
          { icon: FileText, label: 'DCS / Challans', path: '/job-work/dcs' },
        ]
      },
      {
        label: 'Warehouse',
        items: [
          { icon: ArrowDownLeft, label: 'Inward', path: '/rings/inward' },
          { icon: ArrowUpRight, label: 'Outward', path: '/logistics/outward' },
          { icon: ClipboardList, label: 'Picking List', path: '/rings/picks' },
          { icon: FileText, label: 'Dispatch / Challan', path: '/rings/dispatch' },
          { icon: Truck, label: 'Dispatch Control', path: '/logistics/dispatch' },
          { icon: Boxes, label: 'Stock Closing', path: '/rings/stock' },
          { icon: BarChart3, label: 'Sales Report', path: '/rings/sales' },
        ]
      },
    ]
  },
  {
    label: 'Finance',
    items: [
      { 
        label: 'BILLING & TAX', 
        items: [
          { icon: Receipt, label: 'Billing Documents', path: '/finance/billing' },
          { icon: FileSpreadsheet, label: 'Invoicing & GST', path: '/finance/invoicing' },
          { icon: FileText, label: 'GST Reports', path: '/finance/invoicing/gst-reports' },
        ]
      },
    ]
  },
  {
    label: 'System',
    items: [
      { 
        label: 'Monitoring', 
        items: [
          { icon: BarChart3, label: 'Analytics Reports', path: '/reports' },
          { icon: History, label: 'Audit Trail', path: '/audit' },
          { icon: Database, label: 'Data Migration', path: '/migration' },
        ]
      },
      { 
        label: 'Administration', 
        items: [
          { icon: Users, label: 'User Management', path: '/users' },
          { icon: Shield, label: 'Role Definitions', path: '/roles' },
          { icon: ShieldCheck, label: 'Access Control', path: '/roles/permissions' },
          { icon: Settings, label: 'System Settings', path: '/settings' },
        ]
      },
    ]
  },
];

const TopMenu = () => {
  const [activeMenu, setActiveMenu] = useState(null);
  const location = useLocation();

  const handleMouseEnter = (label) => setActiveMenu(label);
  const handleMouseLeave = () => setActiveMenu(null);

  const isItemActive = (item) => {
    if (item.path === location.pathname) return true;
    if (item.items) {
      return item.items.some(sub => {
        if (sub.path === location.pathname) return true;
        if (sub.items) return sub.items.some(deepSub => location.pathname.startsWith(deepSub.path));
        return sub.path && location.pathname.startsWith(sub.path);
      });
    }
    return false;
  };

  return (
    <nav className="flex items-center gap-1 w-full h-full px-4 overflow-visible">
      {menuItems.map((item, index) => (
        <div 
          key={item.label}
          className="relative flex items-center h-full group"
          onMouseEnter={() => handleMouseEnter(item.label)}
          onMouseLeave={handleMouseLeave}
        >
          {item.items ? (
            <div className={clsx(
              "flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-default",
              isItemActive(item) 
                ? "text-primary-700 bg-primary-50/50" 
                : "text-gray-600 group-hover:text-gray-900 group-hover:bg-gray-50"
            )}>
              <span>{item.label}</span>
              <ChevronDown size={14} className={clsx("ml-1.5 transition-transform duration-200", activeMenu === item.label && "rotate-180")} />
            </div>
          ) : (
            <NavLink
              to={item.path}
              className={({ isActive }) => clsx(
                "flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                isActive 
                  ? "text-primary-700 bg-primary-50/50" 
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              )}
            >
              {item.icon && <item.icon size={16} className="mr-2" />}
              <span>{item.label}</span>
            </NavLink>
          )}

          {/* Mega Dropdown Structure */}
          {item.items && activeMenu === item.label && (
            <div className={clsx(
              "absolute top-full mt-0 pt-1 z-50 animate-in fade-in slide-in-from-top-1 duration-150",
              index > menuItems.length - 2 ? "right-0" : "left-0"
            )}>
              <div className="bg-white border border-gray-100 rounded-xl shadow-2xl py-3 px-2 flex gap-4 min-w-[320px] max-w-[800px]">
                {item.items.map((group) => (
                  <div key={group.label} className="flex-1 min-w-[180px] space-y-1.5">
                    <h5 className="px-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5 border-b border-gray-50 pb-1">
                      {group.label}
                    </h5>
                    <div className="space-y-0.5">
                      {group.items.map((subItem) => {
                        const Icon = subItem.icon;
                        const isSubActive = location.pathname === subItem.path;
                        return (
                          <NavLink
                            key={subItem.path}
                            to={subItem.path}
                            onClick={() => setActiveMenu(null)}
                            className={clsx(
                              "flex items-center px-3 py-1.5 text-sm rounded-lg transition-all",
                              isSubActive 
                                ? "bg-primary-50 text-primary-700 font-semibold" 
                                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                            )}
                          >
                            <Icon size={14} className={clsx("mr-2.5", isSubActive ? "text-primary-600" : "text-gray-400")} />
                            <span className="truncate">{subItem.label}</span>
                          </NavLink>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </nav>
  );
};

export default TopMenu;
