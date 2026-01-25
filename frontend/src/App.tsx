/**
 * Governex+ Platform - Main Application
 * Domain: governexplus.com
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

// Layouts
import { DashboardLayout } from './layouts/DashboardLayout';
import { AuthLayout } from './layouts/AuthLayout';

// Pages
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/auth/Login';

// Access Request Pages
import { AccessRequestList } from './pages/access-requests/AccessRequestList';
import { AccessRequestDetail } from './pages/access-requests/AccessRequestDetail';
import { NewAccessRequest } from './pages/access-requests/NewAccessRequest';
import { ApprovalInbox } from './pages/access-requests/ApprovalInbox';
import { BulkAccessRequest } from './pages/access-requests/BulkAccessRequest';

// Certification Pages
import { CertificationCampaigns } from './pages/certification/CertificationCampaigns';
import { CertificationReview } from './pages/certification/CertificationReview';

// Firefighter Pages
import { FirefighterDashboard } from './pages/firefighter/FirefighterDashboard';
import { FirefighterRequest } from './pages/firefighter/FirefighterRequest';
import { FirefighterSessions } from './pages/firefighter/FirefighterSessions';
import { LiveSessionMonitor } from './pages/firefighter/LiveSessionMonitor';

// Risk Pages
import { RiskDashboard } from './pages/risk/RiskDashboard';
import { RiskRules } from './pages/risk/RiskRules';
import { RiskViolations } from './pages/risk/RiskViolations';
import { RiskSimulation } from './pages/risk/RiskSimulation';
import { SodRuleLibrary } from './pages/risk/SodRuleLibrary';
import { EntitlementIntelligence } from './pages/risk/EntitlementIntelligence';
import { ContextualRisk } from './pages/risk/ContextualRisk';

// User Pages
import { UserList } from './pages/users/UserList';
import { UserDetail } from './pages/users/UserDetail';
import { InactiveUsers } from './pages/users/InactiveUsers';

// Role Pages
import { RoleList } from './pages/roles/RoleList';
import { RoleDesigner } from './pages/roles/RoleDesigner';

// Reports Pages
import { ReportsDashboard } from './pages/reports/ReportsDashboard';
import { ReportViewer } from './pages/reports/ReportViewer';

// Settings Pages
import { Settings } from './pages/settings/Settings';
import { PolicyManagement } from './pages/settings/PolicyManagement';

// Integrations Page
import { Integrations } from './pages/integrations/Integrations';

// Compliance Pages
import { ComplianceDashboard, ComplianceAssessment } from './pages/compliance';

// Password Self-Service Pages
import { ChangePassword } from './pages/password/ChangePassword';
import { ResetInSystems } from './pages/password/ResetInSystems';

// Security Controls Pages
import {
  SecurityControlsDashboard,
  SecurityControlsList,
  SecurityControlDetail,
  SecurityControlsImport,
  SecurityControlsEvaluate,
} from './pages/security-controls';

// AI Assistant
import { AIAssistant } from './pages/ai';

// ML Analytics
import { MLDashboard, UserBehaviorAnalytics, ModelManagement, PredictiveAnalytics } from './pages/ml';

// Admin Pages (Super Admin Portal)
import { AdminLogin, AdminDashboard, TenantOnboard } from './pages/admin';

// Auth Context
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Form Config Context
import { FormConfigProvider } from './contexts/FormConfigContext';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

// Protected Route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
      </Route>

      {/* Protected Dashboard Routes */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        {/* Dashboard */}
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Access Requests */}
        <Route path="/access-requests" element={<AccessRequestList />} />
        <Route path="/access-requests/new" element={<NewAccessRequest />} />
        <Route path="/access-requests/bulk" element={<BulkAccessRequest />} />
        <Route path="/access-requests/:id" element={<AccessRequestDetail />} />
        <Route path="/approvals" element={<ApprovalInbox />} />

        {/* Certification */}
        <Route path="/certification" element={<CertificationCampaigns />} />
        <Route path="/certification/review" element={<CertificationReview />} />
        <Route path="/certification/:campaignId" element={<CertificationReview />} />

        {/* Firefighter */}
        <Route path="/firefighter" element={<FirefighterDashboard />} />
        <Route path="/firefighter/request" element={<FirefighterRequest />} />
        <Route path="/firefighter/sessions" element={<FirefighterSessions />} />
        <Route path="/firefighter/monitor" element={<LiveSessionMonitor />} />

        {/* Risk */}
        <Route path="/risk" element={<RiskDashboard />} />
        <Route path="/risk/rules" element={<RiskRules />} />
        <Route path="/risk/violations" element={<RiskViolations />} />
        <Route path="/risk/simulation" element={<RiskSimulation />} />
        <Route path="/risk/sod-rules" element={<SodRuleLibrary />} />
        <Route path="/risk/entitlements" element={<EntitlementIntelligence />} />
        <Route path="/risk/contextual" element={<ContextualRisk />} />

        {/* Users */}
        <Route path="/users" element={<UserList />} />
        <Route path="/users/inactive" element={<InactiveUsers />} />
        <Route path="/users/:userId" element={<UserDetail />} />

        {/* Roles */}
        <Route path="/roles" element={<RoleList />} />
        <Route path="/roles/designer" element={<RoleDesigner />} />
        <Route path="/roles/designer/:roleId" element={<RoleDesigner />} />

        {/* Reports */}
        <Route path="/reports" element={<ReportsDashboard />} />
        <Route path="/reports/:reportId" element={<ReportViewer />} />

        {/* Settings */}
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/policies" element={<PolicyManagement />} />

        {/* Integrations */}
        <Route path="/integrations" element={<Integrations />} />

        {/* Compliance */}
        <Route path="/compliance" element={<ComplianceDashboard />} />
        <Route path="/compliance/assessment" element={<ComplianceAssessment />} />

        {/* Password Self-Service */}
        <Route path="/password" element={<Navigate to="/password/change" replace />} />
        <Route path="/password/change" element={<ChangePassword />} />
        <Route path="/password/reset" element={<ResetInSystems />} />

        {/* Security Controls */}
        <Route path="/security-controls" element={<SecurityControlsDashboard />} />
        <Route path="/security-controls/list" element={<SecurityControlsList />} />
        <Route path="/security-controls/controls/:controlId" element={<SecurityControlDetail />} />
        <Route path="/security-controls/import" element={<SecurityControlsImport />} />
        <Route path="/security-controls/evaluate" element={<SecurityControlsEvaluate />} />

        {/* AI Assistant */}
        <Route path="/ai" element={<AIAssistant />} />

        {/* ML Analytics */}
        <Route path="/ml" element={<MLDashboard />} />
        <Route path="/ml/dashboard" element={<MLDashboard />} />
        <Route path="/ml/ueba" element={<UserBehaviorAnalytics />} />
        <Route path="/ml/models" element={<ModelManagement />} />
        <Route path="/ml/analytics" element={<PredictiveAnalytics />} />
        <Route path="/ml/anomalies" element={<MLDashboard />} />
        <Route path="/ml/recommendations" element={<MLDashboard />} />
      </Route>

      {/* Super Admin Portal Routes (outside protected routes) */}
      <Route path="/admin" element={<AdminLogin />} />
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/admin/onboard" element={<TenantOnboard />} />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <FormConfigProvider>
          <BrowserRouter>
            <AppRoutes />
            <Toaster position="top-right" />
          </BrowserRouter>
        </FormConfigProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
