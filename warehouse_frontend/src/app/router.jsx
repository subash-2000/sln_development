import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import {
  LegacyInventoryVendorStockRedirect,
  LegacyVendorStockRedirect,
  LegacyVendorsRedirect,
} from '../components/navigation/LegacyPathRedirect';
import { ProtectedRoute, PublicRoute } from '../components/navigation/ProtectedRoute';
import MainLayout from '../layouts/MainLayout';
import AuthLayout from '../layouts/AuthLayout';
import Loader from '../components/common/Loader';

// Module Routes
import { userRoutes } from '../modules/users/routes';
import { roleRoutes } from '../modules/roles/routes';
import { companyRoutes } from '../modules/companies/routes';
import { branchRoutes } from '../modules/branches/routes';
import { vendorRoutes } from '../modules/vendors/routes';
import { customerRoutes } from '../modules/customers/routes';
import { transportRoutes } from '../modules/transport/routes';
import { productRoutes } from '../modules/products/routes';
import { billingRoutes } from '../modules/billing/routes';
import { invoicingRoutes } from '../modules/invoicing/routes';
import { returnsRoutes } from '../modules/rejection-returns/routes';
import { reportRoutes } from '../modules/reports/routes';
import { auditRoutes } from '../modules/audit/routes';
import { migrationRoutes } from '../modules/migration/routes';
import { warehouseRoutes } from '../modules/warehouses/routes';
import { locationRoutes } from '../modules/locations/routes';
import { rackRoutes } from '../modules/racks/routes';
import { binRoutes } from '../modules/bins/routes';
import { inventoryRoutes } from '../modules/inventory/routes';
import { vendorStockRoutes } from '../modules/vendor-stock/routes';
import { jobWorkRoutes } from '../modules/job-work/routes';
import { logisticsRoutes } from '../modules/logistics/routes';
import { ringsRoutes } from '../modules/rings/routes';

// Lazy loaded pages
const LoginPage = lazy(() => import('../pages/auth/LoginPage'));
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPage'));
const NotFoundPage = lazy(() => import('../pages/errors/NotFoundPage'));
const ForbiddenPage = lazy(() => import('../pages/errors/ForbiddenPage'));
const ServerErrorPage = lazy(() => import('../pages/errors/ServerErrorPage'));
const SystemSettingsPage = lazy(() => import('../pages/settings/SystemSettingsPage'));

/**
 * Application Router
 */
export const AppRouter = () => {
  return (
    <Suspense fallback={<Loader fullPage />}>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<PublicRoute><AuthLayout /></PublicRoute>}>
          <Route index element={<Navigate to="/login" replace />} />
          <Route path="login" element={<LoginPage />} />
        </Route>

        {/* Protected Routes */}
        <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
          <Route path="vendors/*" element={<LegacyVendorsRedirect />} />
          <Route path="vendor-stock/*" element={<LegacyVendorStockRedirect />} />
          <Route path="inventory/vendor-stock/*" element={<LegacyInventoryVendorStockRedirect />} />
          <Route path="dashboard" element={<DashboardPage />} />
          
          {/* Users Module */}
          {userRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Roles Module */}
          {roleRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Companies Module */}
          {companyRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Branches Module */}
          {branchRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Suppliers Module */}
          {vendorRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Customers Module */}
          {customerRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Transport Master */}
          {transportRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Products Module */}
          {productRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Reports Module */}
          {reportRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Audit Module */}
          {auditRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Migration Module */}
          {migrationRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Billing Module */}
          {billingRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Invoicing Module */}
          {invoicingRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Rejection & Returns Module */}
          {returnsRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}
          
          {/* Warehouse Management */}
          {warehouseRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}
          {locationRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}
          {rackRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}
          {binRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Inventory Management */}
          {inventoryRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Supplier Stock Module */}
          {vendorStockRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Job Work Module */}
          {jobWorkRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Logistics Module */}
          {logisticsRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {ringsRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element}>
              {route.children?.map((child) => (
                <Route
                  key={child.path || 'index'}
                  index={child.index}
                  path={child.path}
                  element={child.element}
                />
              ))}
            </Route>
          ))}

          {/* Settings & Administration */}
          <Route path="settings" element={<SystemSettingsPage />} />
          <Route path="admin" element={<SystemSettingsPage />} />
        </Route>

        {/* Error Routes */}
        <Route path="/403" element={<ForbiddenPage />} />
        <Route path="/500" element={<ServerErrorPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
};
