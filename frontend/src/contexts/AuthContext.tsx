import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { authApi } from '../services/api';
import { UserRole, hasPermission, getRolePermissions, ROLES } from '../config/roles';

// Environment flag for demo mode (only enabled in development)
const DEMO_MODE_ENABLED = import.meta.env.DEV && import.meta.env.VITE_DEMO_MODE === 'true';

interface User {
  user_id: string;
  name: string;
  email: string;
  department: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
  getUserPermissions: () => string[];
  getRoleName: () => string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem('accessToken');
    const storedRole = localStorage.getItem('userRole') as UserRole | null;
    if (token && storedRole) {
      // Restore user session with stored role
      const storedUser = localStorage.getItem('userData');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      } else {
        // Fallback for existing sessions
        setUser({
          user_id: 'admin',
          name: 'Admin User',
          email: 'admin@company.com',
          department: 'IT',
          role: storedRole,
        });
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await authApi.login({ username, password });
      const { access_token, refresh_token, user: userData } = response.data;

      // Store tokens securely
      localStorage.setItem('accessToken', access_token);
      if (refresh_token) {
        localStorage.setItem('refreshToken', refresh_token);
      }

      // Role comes from backend based on user's assigned role
      const role = (userData.role as UserRole) || 'end_user';
      const userWithRole: User = {
        user_id: userData.user_id || userData.id,
        name: userData.name || userData.display_name,
        email: userData.email,
        department: userData.department || 'General',
        role,
      };

      setUser(userWithRole);
      localStorage.setItem('userRole', role);
      localStorage.setItem('userData', JSON.stringify(userWithRole));
    } catch (error: unknown) {
      // In development with demo mode, allow fallback authentication
      if (DEMO_MODE_ENABLED) {
        const role = getRoleFromUsername(username);
        const demoUser: User = {
          user_id: username,
          name: getRoleDisplayName(role, username),
          email: `${username}@company.com`,
          department: getDepartmentForRole(role),
          role,
        };
        localStorage.setItem('accessToken', `demo-${Date.now()}`);
        localStorage.setItem('userRole', role);
        localStorage.setItem('userData', JSON.stringify(demoUser));
        setUser(demoUser);
        console.warn('Demo mode: Using fallback authentication');
        return;
      }

      // In production, propagate the error
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError?.response?.data?.detail || 'Authentication failed';
      throw new Error(message);
    }
  };

  const logout = useCallback(async () => {
    try {
      // Notify backend of logout (invalidates tokens)
      await authApi.logout();
    } catch (error) {
      // Continue with local logout even if API call fails
      console.warn('Logout API call failed, proceeding with local logout');
    } finally {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('userRole');
      localStorage.removeItem('userData');
      setUser(null);
      window.location.href = '/login';
    }
  }, []);

  const checkPermission = (permission: string): boolean => {
    if (!user) return false;
    return hasPermission(user.role, permission);
  };

  const checkAnyPermission = (permissions: string[]): boolean => {
    if (!user) return false;
    return permissions.some((p) => hasPermission(user.role, p));
  };

  const checkAllPermissions = (permissions: string[]): boolean => {
    if (!user) return false;
    return permissions.every((p) => hasPermission(user.role, p));
  };

  const getUserPermissions = (): string[] => {
    if (!user) return [];
    return getRolePermissions(user.role);
  };

  const getRoleName = (): string => {
    if (!user) return '';
    return ROLES[user.role]?.name ?? '';
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        hasPermission: checkPermission,
        hasAnyPermission: checkAnyPermission,
        hasAllPermissions: checkAllPermissions,
        getUserPermissions,
        getRoleName,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Helper functions

// Demo mode: determine role from username
// In production, role comes from backend authentication
function getRoleFromUsername(username: string): UserRole {
  const lowerUsername = username.toLowerCase();
  if (lowerUsername.includes('admin') && !lowerUsername.includes('security')) {
    return 'admin';
  }
  if (lowerUsername.includes('security') || lowerUsername.includes('sec_admin')) {
    return 'security_admin';
  }
  if (lowerUsername.includes('manager') || lowerUsername.includes('approver')) {
    return 'manager';
  }
  // Default to end_user for all other usernames
  return 'end_user';
}

function getRoleDisplayName(role: UserRole, username: string): string {
  const names: Record<UserRole, string> = {
    admin: 'System Administrator',
    security_admin: 'Security Admin',
    manager: 'Manager',
    end_user: 'End User',
  };
  return `${names[role]} (${username})`;
}

function getDepartmentForRole(role: UserRole): string {
  const departments: Record<UserRole, string> = {
    admin: 'IT Infrastructure',
    security_admin: 'IT Security',
    manager: 'Operations',
    end_user: 'General',
  };
  return departments[role];
}
