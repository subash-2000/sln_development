import { Navigate, useLocation } from 'react-router-dom';

/**
 * Redirects legacy URL prefixes to supplier terminology paths.
 */
const LegacyPathRedirect = ({ fromPrefix, toPrefix }) => {
  const location = useLocation();
  const nextPath = location.pathname.replace(new RegExp(`^${fromPrefix}`), toPrefix);
  return <Navigate to={`${nextPath}${location.search}${location.hash}`} replace />;
};

export const LegacyVendorsRedirect = () => (
  <LegacyPathRedirect fromPrefix="/vendors" toPrefix="/suppliers" />
);

export const LegacyVendorStockRedirect = () => (
  <LegacyPathRedirect fromPrefix="/vendor-stock" toPrefix="/supplier-stock" />
);

export const LegacyInventoryVendorStockRedirect = () => (
  <LegacyPathRedirect fromPrefix="/inventory/vendor-stock" toPrefix="/inventory/supplier-stock" />
);
