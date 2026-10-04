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
import { CommandCenter } from './pages/CommandCenter';
import { Login } from './pages/auth/Login';
import { LandingPage } from './pages/LandingPage';

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
import { BusinessRoleManagement } from './pages/roles/BusinessRoleManagement';

// Reports Pages
import { ReportsDashboard } from './pages/reports/ReportsDashboard';
import { ReportViewer } from './pages/reports/ReportViewer';

// Settings Pages
import { Settings } from './pages/settings/Settings';
import { ApproverManagement } from './pages/settings/ApproverManagement';
import { SystemManagement } from './pages/settings/SystemManagement';
import { OrgRules } from './pages/settings/OrgRules';
import { MassAdmin } from './pages/settings/MassAdmin';
import { RepoSync } from './pages/settings/RepoSync';
import { TransportManagement } from './pages/settings/TransportManagement';
import { NotificationCenter } from './pages/settings/NotificationCenter';
import { SmtpSettings } from './pages/settings/SmtpSettings';
import { PolicyManagement } from './pages/settings/PolicyManagement';
import { DelegationManagement } from './pages/settings/DelegationManagement';

// Compliance Pages
import { ComplianceDashboard } from './pages/compliance/ComplianceDashboard';
import { ComplianceAssessment } from './pages/compliance/ComplianceAssessment';

// Audit Pages
import { AuditReport } from './pages/audit';

// GRC Suite — Risk Management
import { RiskRegister, RiskHeatmap, KRIDashboard, IncidentLog } from './pages/risk-management';

// GRC Suite — Process Control
import { ControlLibrary, ControlTesting, DeficiencyTracker, CCMDashboard } from './pages/process-control';

// GRC Suite — Audit Management
import { AuditDashboard as AuditMgmtDashboard, AuditPlanning, AuditEngagement, FindingsTracker } from './pages/audit-management';

// Integrations Page
import { Integrations } from './pages/integrations/Integrations';

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

// Risk - Mitigation Controls
import { MitigationControls } from './pages/risk/MitigationControls';
import { CustomTcode } from './pages/risk/CustomTcode';
import { MitigationMonitoring } from './pages/risk/MitigationMonitoring';

// Model User
import { ModelUser } from './pages/access-requests/ModelUser';

// Provisioning
import { ProvisioningDashboard } from './pages/provisioning/ProvisioningDashboard';

// Intelligence Pages (differentiator modules)
import {
  AccessTroubleshooter,
  RoleIntelligence,
  MigrationAnalyzer,
  RoleDriftDetection,
  AuditEvidenceCenter,
  FioriAnalyzer,
  AccessTimeline,
  UpgradeAnalyzer,
  IdentityCorrelation,
} from './pages/intelligence';

// Global Search
import { GlobalSearch } from './pages/intelligence/GlobalSearch';

// ARM Shopping Cart
import { ShoppingCart } from './pages/access-requests/ShoppingCart';

// Workflow Builder
import { WorkflowBuilder } from './pages/workflows';

// AI Assistant
import { AIAssistant } from './pages/ai';

// Admin Pages (Super Admin Portal)
import { AdminLogin, AdminDashboard, TenantOnboard } from './pages/admin';

// JML Pages
import { JmlPolicies, HrEventMonitor } from './pages/jml';

// TPRM Pages
import { VendorRegistry, AssessmentScoring, VendorIssues } from './pages/tprm';

// Fraud Detection Pages
import { DetectionRules, AlertInbox, CaseManagement } from './pages/fraud';

// BCM Pages
import { BiaSummary, BcmPlans, IncidentActivation } from './pages/bcm';

// Whistleblower Pages
import { WhistleblowerIntake, WhistleblowerInbox } from './pages/whistleblower';
import { ContentLibrary, ActivationWizard, ActiveContent, UpdateReview, PackBuilder } from './pages/library';

// Survey Pages
import { SurveyDesigner, SurveyDistribution, ResponseAnalytics } from './pages/survey';

// ML Dashboard
import { MLDashboard } from './pages/ml';

// Auth Context
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Form Config Context
import { FormConfigProvider } from './contexts/FormConfigContext';

// Theme Context
import { ThemeProvider } from './contexts/ThemeContext';

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
      {/* Public Landing Page */}
      <Route path="/welcome" element={<LandingPage />} />

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
        {/* Command Center (default home) + legacy dashboard */}
        <Route path="/" element={<CommandCenter />} />
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Access Requests */}
        <Route path="/access-requests" element={<AccessRequestList />} />
        <Route path="/access-requests/new" element={<NewAccessRequest />} />
        <Route path="/access-requests/bulk" element={<BulkAccessRequest />} />
        <Route path="/access-requests/cart" element={<ShoppingCart />} />
        <Route path="/access-requests/model-user" element={<ModelUser />} />
        <Route path="/access-requests/:id" element={<AccessRequestDetail />} />
        <Route path="/approvals" element={<ApprovalInbox />} />

        {/* Certification */}
        <Route path="/certification" element={<CertificationCampaigns />} />
        <Route path="/certification/review" element={<CertificationReview />} />
        <Route path="/certification/:campaignId" element={<CertificationReview />} />

        {/* Firefighter */}
        <Route path="/privileged-access" element={<FirefighterDashboard />} />
        <Route path="/privileged-access/request" element={<FirefighterRequest />} />
        <Route path="/privileged-access/sessions" element={<FirefighterSessions />} />
        <Route path="/privileged-access/monitor" element={<LiveSessionMonitor />} />

        {/* Risk */}
        <Route path="/risk" element={<RiskDashboard />} />
        <Route path="/risk/rules" element={<RiskRules />} />
        <Route path="/risk/violations" element={<RiskViolations />} />
        <Route path="/risk/simulation" element={<RiskSimulation />} />
        <Route path="/risk/sod-rules" element={<SodRuleLibrary />} />
        <Route path="/risk/entitlements" element={<EntitlementIntelligence />} />
        <Route path="/risk/contextual" element={<ContextualRisk />} />
        <Route path="/risk/mitigation" element={<MitigationControls />} />
        <Route path="/risk/custom-tcode" element={<CustomTcode />} />
        <Route path="/risk/mitigation-monitoring" element={<MitigationMonitoring />} />

        {/* Users */}
        <Route path="/users" element={<UserList />} />
        <Route path="/users/inactive" element={<InactiveUsers />} />
        <Route path="/users/:userId" element={<UserDetail />} />

        {/* Roles */}
        <Route path="/roles" element={<RoleList />} />
        <Route path="/roles/brm" element={<BusinessRoleManagement />} />
        <Route path="/roles/designer" element={<RoleDesigner />} />
        <Route path="/roles/designer/:roleId" element={<RoleDesigner />} />

        {/* Reports */}
        <Route path="/reports" element={<ReportsDashboard />} />
        <Route path="/reports/:reportId" element={<ReportViewer />} />

        {/* Settings */}
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/approvers" element={<ApproverManagement />} />
        <Route path="/settings/systems" element={<SystemManagement />} />
        <Route path="/settings/org-rules" element={<OrgRules />} />
        <Route path="/settings/mass-admin" element={<MassAdmin />} />
        <Route path="/settings/repo-sync" element={<RepoSync />} />
        <Route path="/settings/transports" element={<TransportManagement />} />
        <Route path="/settings/notifications" element={<NotificationCenter />} />
        <Route path="/settings/email" element={<SmtpSettings />} />
        <Route path="/settings/policies" element={<PolicyManagement />} />
        <Route path="/settings/delegations" element={<DelegationManagement />} />

        {/* Compliance */}
        <Route path="/compliance" element={<ComplianceDashboard />} />
        <Route path="/compliance/assessment" element={<ComplianceAssessment />} />

        {/* Audit */}
        <Route path="/audit" element={<AuditReport />} />

        {/* Integrations */}
        <Route path="/integrations" element={<Integrations />} />

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

        {/* Provisioning */}
        <Route path="/provisioning" element={<ProvisioningDashboard />} />

        {/* Intelligence / Differentiator Modules */}
        <Route path="/intelligence/search" element={<GlobalSearch />} />
        <Route path="/intelligence/troubleshooter" element={<AccessTroubleshooter />} />
        <Route path="/intelligence/role-intelligence" element={<RoleIntelligence />} />
        <Route path="/intelligence/migration" element={<MigrationAnalyzer />} />
        <Route path="/intelligence/drift" element={<RoleDriftDetection />} />
        <Route path="/intelligence/audit-evidence" element={<AuditEvidenceCenter />} />
        <Route path="/intelligence/fiori" element={<FioriAnalyzer />} />
        <Route path="/intelligence/timeline" element={<AccessTimeline />} />
        <Route path="/intelligence/upgrade" element={<UpgradeAnalyzer />} />
        <Route path="/intelligence/identity" element={<IdentityCorrelation />} />

        {/* Workflow Builder */}
        <Route path="/workflows/builder" element={<WorkflowBuilder />} />

        {/* GRC Suite — Risk Management */}
        <Route path="/risk-management" element={<RiskRegister />} />
        <Route path="/risk-management/register" element={<RiskRegister />} />
        <Route path="/risk-management/heatmap" element={<RiskHeatmap />} />
        <Route path="/risk-management/kri" element={<KRIDashboard />} />
        <Route path="/risk-management/incidents" element={<IncidentLog />} />

        {/* GRC Suite — Process Control */}
        <Route path="/process-control" element={<ControlLibrary />} />
        <Route path="/process-control/controls" element={<ControlLibrary />} />
        <Route path="/process-control/testing" element={<ControlTesting />} />
        <Route path="/process-control/deficiencies" element={<DeficiencyTracker />} />
        <Route path="/process-control/ccm" element={<CCMDashboard />} />

        {/* GRC Suite — Audit Management */}
        <Route path="/audit-management" element={<AuditMgmtDashboard />} />
        <Route path="/audit-management/planning" element={<AuditPlanning />} />
        <Route path="/audit-management/engagements" element={<AuditEngagement />} />
        <Route path="/audit-management/findings" element={<FindingsTracker />} />

        {/* AI Assistant */}
        <Route path="/ai" element={<AIAssistant />} />

        {/* JML — Joiner Mover Leaver */}
        <Route path="/jml" element={<JmlPolicies />} />
        <Route path="/jml/policies" element={<JmlPolicies />} />
        <Route path="/jml/events" element={<HrEventMonitor />} />

        {/* TPRM — Third-Party Risk */}
        <Route path="/tprm" element={<VendorRegistry />} />
        <Route path="/tprm/vendors" element={<VendorRegistry />} />
        <Route path="/tprm/assessments" element={<AssessmentScoring />} />
        <Route path="/tprm/issues" element={<VendorIssues />} />

        {/* Fraud Detection */}
        <Route path="/fraud" element={<AlertInbox />} />
        <Route path="/fraud/rules" element={<DetectionRules />} />
        <Route path="/fraud/alerts" element={<AlertInbox />} />
        <Route path="/fraud/cases" element={<CaseManagement />} />

        {/* BCM — Business Continuity */}
        <Route path="/bcm" element={<BiaSummary />} />
        <Route path="/bcm/bia" element={<BiaSummary />} />
        <Route path="/bcm/plans" element={<BcmPlans />} />
        <Route path="/bcm/activations" element={<IncidentActivation />} />

        {/* Whistleblower */}
        <Route path="/whistleblower" element={<WhistleblowerInbox />} />
        <Route path="/whistleblower/inbox" element={<WhistleblowerInbox />} />
        <Route path="/whistleblower/intake" element={<WhistleblowerIntake />} />
        {/* Template Library */}
        <Route path="/library" element={<ContentLibrary />} />
        <Route path="/library/content" element={<ContentLibrary />} />
        <Route path="/library/wizard" element={<ActivationWizard />} />
        <Route path="/library/active" element={<ActiveContent />} />
        <Route path="/library/updates" element={<UpdateReview />} />
        <Route path="/library/pack-builder" element={<PackBuilder />} />

        {/* Survey Engine */}
        <Route path="/surveys" element={<SurveyDesigner />} />
        <Route path="/surveys/designer" element={<SurveyDesigner />} />
        <Route path="/surveys/distribution" element={<SurveyDistribution />} />
        <Route path="/surveys/analytics" element={<ResponseAnalytics />} />

        {/* ML Dashboard */}
        <Route path="/ml" element={<MLDashboard />} />

      </Route>

      {/* Super Admin Portal Routes */}
      <Route path="/admin" element={<AdminLogin />} />
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin/dashboard" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
      <Route path="/admin/onboard" element={<ProtectedRoute><TenantOnboard /></ProtectedRoute>} />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <FormConfigProvider>
            <BrowserRouter>
              <AppRoutes />
              <Toaster position="top-right" />
            </BrowserRouter>
          </FormConfigProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
