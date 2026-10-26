import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/auth.store';

/**
 * ProtectedRoute
 * Redirects to login if not authenticated
 */
export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    // Redirect to login but save the current location to redirect back
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

/**
 * PublicRoute
 * Redirects to dashboard if already authenticated (e.g. login page)
 */
export const PublicRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/dashboard';

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  return children;
};

/**
 * PermissionRoute
 * Checks if user has specific permission
 */
export const PermissionRoute = ({ permission, children }) => {
  const { hasPermission } = useAuthStore();

  if (!hasPermission(permission)) {
    return <Navigate to="/403" replace />;
  }

  return children;
};
