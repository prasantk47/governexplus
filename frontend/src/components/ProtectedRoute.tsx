import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface ProtectedRouteProps {
  children: React.ReactNode;
  permissions?: string[];
  requireAll?: boolean; // If true, requires ALL permissions. If false, requires ANY permission.
}

export function ProtectedRoute({
  children,
  permissions = [],
  requireAll = false,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, hasAnyPermission, hasAllPermissions } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If no specific permissions required, allow access
  if (permissions.length === 0) {
    return <>{children}</>;
  }

  // Check permissions
  const hasAccess = requireAll
    ? hasAllPermissions(permissions)
    : hasAnyPermission(permissions);

  if (!hasAccess) {
    return <AccessDenied />;
  }

  return <>{children}</>;
}

function AccessDenied() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <div className="mx-auto h-16 w-16 rounded-full bg-red-100 flex items-center justify-center">
          <ExclamationTriangleIcon className="h-8 w-8 text-red-600" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-gray-900">Access Denied</h2>
        <p className="mt-2 text-sm text-gray-500 max-w-md">
          You don't have permission to access this page. Please contact your administrator if you
          believe this is an error.
        </p>
        <div className="mt-6">
          <a
            href="/"
            className="btn-primary"
          >
            Return to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}

// Hook for conditional rendering based on permissions
export function usePermission(permission: string): boolean {
  const { hasPermission } = useAuth();
  return hasPermission(permission);
}

// Component for conditional rendering based on permissions
interface PermissionGateProps {
  children: React.ReactNode;
  permissions: string[];
  requireAll?: boolean;
  fallback?: React.ReactNode;
}

export function PermissionGate({
  children,
  permissions,
  requireAll = false,
  fallback = null,
}: PermissionGateProps) {
  const { hasAnyPermission, hasAllPermissions } = useAuth();

  const hasAccess = requireAll
    ? hasAllPermissions(permissions)
    : hasAnyPermission(permissions);

  return hasAccess ? <>{children}</> : <>{fallback}</>;
}
