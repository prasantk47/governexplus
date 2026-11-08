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
import { FFIDRegistry } from './pages/firefighter/FFIDRegistry';
import { BreakGlass } from './pages/firefighter/BreakGlass';
import { FFIDCertification } from './pages/firefighter/FFIDCertification';
import { RegionalDashboard } from './pages/firefighter/RegionalDashboard';

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
import { RiskRegister, RiskHeatmap, KRIDashboard, IncidentLog, RiskWorkflowApproval } from './pages/risk-management';

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

// AI Assistant & AI Copilot Pages
import { AIAssistant, OneClickRemediation, AICertification, NaturalLanguageRules, AIFindings, PredictiveRisk, IdentityGraph, GRCCopilot } from './pages/ai';

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

// New GRC Modules
import { IssueTracker } from './pages/issue-tracker/IssueTracker';
import { RegulatoryIntelligence } from './pages/regulatory/RegulatoryIntelligence';
import { GRCAnalytics } from './pages/grc-analytics/GRCAnalytics';

// Risk Acceptance Register
import { RiskAcceptanceRegister } from './pages/risk-management/RiskAcceptanceRegister';

// Policy Hub
import { PolicyList } from './pages/policy-hub/PolicyList';
import { PolicyExceptionRegister } from './pages/policy-hub/PolicyExceptionRegister';

// Audit Workpapers
import { AuditWorkpapers } from './pages/audit-management/AuditWorkpapers';

// ML Dashboard & Analytics
import { MLDashboard } from './pages/ml';
import { ModelManagement } from './pages/ml/ModelManagement';
import { PredictiveAnalytics } from './pages/ml/PredictiveAnalytics';
import { UserBehaviorAnalytics } from './pages/ml/UserBehaviorAnalytics';

// Request Form Config
import { RequestFormConfig } from './pages/settings/RequestFormConfig';

// Wave 1 additions — audit & process-control
import { AuditUniverse } from './pages/audit-management/AuditUniverse';
import { AuditResources } from './pages/audit-management/AuditResources';
import { CSACampaigns } from './pages/process-control/CSACampaigns';
import { ControlObjectives } from './pages/process-control/ControlObjectives';
import { QuestionnaireLibrary } from './pages/process-control/QuestionnaireLibrary';

// Risk Management — scenarios / opportunities / objectives
import { RiskScenarios } from './pages/risk-management/RiskScenarios';
import { RiskOpportunities } from './pages/risk-management/RiskOpportunities';
import { BusinessObjectives } from './pages/risk-management/BusinessObjectives';

// Wave 2 New GRC Modules
import { SOXICFRModule } from './pages/sox-icfr/SOXICFRModule';
import { PrivacyDashboard } from './pages/privacy/PrivacyDashboard';
import { RegulatoryChanges } from './pages/regulatory/RegulatoryChanges';
import { BoardDashboard } from './pages/board/BoardDashboard';
import { OperationalRiskEvents } from './pages/operational-risk/OperationalRiskEvents';
import { SoDRemediation } from './pages/sod-remediation/SoDRemediation';
import { ITChangeRisk } from './pages/it-change-risk/ITChangeRisk';
import { InsurancePolicies } from './pages/insurance/InsurancePolicies';
import { SanctionsScreening } from './pages/sanctions/SanctionsScreening';

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
    return <Navigate to="/welcome" replace />;
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

        {/* Firefighter / Privileged Access */}
        <Route path="/privileged-access" element={<FirefighterDashboard />} />
        <Route path="/privileged-access/request" element={<FirefighterRequest />} />
        <Route path="/privileged-access/sessions" element={<FirefighterSessions />} />
        <Route path="/privileged-access/monitor" element={<LiveSessionMonitor />} />
        <Route path="/privileged-access/registry" element={<FFIDRegistry />} />
        <Route path="/privileged-access/break-glass" element={<BreakGlass />} />
        <Route path="/privileged-access/certification" element={<FFIDCertification />} />
        <Route path="/privileged-access/regional" element={<RegionalDashboard />} />

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
        <Route path="/settings/request-form" element={<RequestFormConfig />} />
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
        <Route path="/risk-management/workflows" element={<RiskWorkflowApproval />} />

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

        {/* AI Assistant & AI Copilot */}
        <Route path="/ai" element={<AIAssistant />} />
        <Route path="/ai/copilot" element={<GRCCopilot />} />
        <Route path="/ai/remediation" element={<OneClickRemediation />} />
        <Route path="/ai/certification" element={<AICertification />} />
        <Route path="/ai/rules" element={<NaturalLanguageRules />} />
        <Route path="/ai/findings" element={<AIFindings />} />
        <Route path="/ai/forecast" element={<PredictiveRisk />} />
        <Route path="/ai/identity-graph" element={<IdentityGraph />} />

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

        {/* Whistleblower (inbox is protected; intake/submit are public — see below) */}
        <Route path="/whistleblower" element={<WhistleblowerInbox />} />
        <Route path="/whistleblower/inbox" element={<WhistleblowerInbox />} />
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

        {/* ML Dashboard & Analytics */}
        <Route path="/ml" element={<MLDashboard />} />
        <Route path="/ml/models" element={<ModelManagement />} />
        <Route path="/ml/predictive" element={<PredictiveAnalytics />} />
        <Route path="/ml/uba" element={<UserBehaviorAnalytics />} />

        {/* Issue Tracker */}
        <Route path="/issue-tracker" element={<IssueTracker />} />

        {/* Regulatory Intelligence */}
        <Route path="/regulatory" element={<RegulatoryIntelligence />} />

        {/* GRC Analytics */}
        <Route path="/grc-analytics" element={<GRCAnalytics />} />

        {/* Risk Acceptance Register */}
        <Route path="/risk-management/acceptances" element={<RiskAcceptanceRegister />} />

        {/* Policy Hub */}
        <Route path="/policy-hub" element={<PolicyList />} />
        <Route path="/policy-hub/exceptions" element={<PolicyExceptionRegister />} />

        {/* Audit Workpapers */}
        <Route path="/audit-management/workpapers" element={<AuditWorkpapers />} />

        {/* Audit Management — additions */}
        <Route path="/audit-management/universe" element={<AuditUniverse />} />
        <Route path="/audit-management/resources" element={<AuditResources />} />

        {/* Process Control — additions */}
        <Route path="/process-control/csa" element={<CSACampaigns />} />
        <Route path="/process-control/objectives" element={<ControlObjectives />} />
        <Route path="/process-control/questionnaires" element={<QuestionnaireLibrary />} />

        {/* Risk Management — scenarios / opportunities / objectives */}
        <Route path="/risk-management/scenarios" element={<RiskScenarios />} />
        <Route path="/risk-management/opportunities" element={<RiskOpportunities />} />
        <Route path="/risk-management/objectives" element={<BusinessObjectives />} />

        {/* SOX / ICFR */}
        <Route path="/sox-icfr" element={<SOXICFRModule />} />

        {/* Privacy & Data Protection */}
        <Route path="/privacy" element={<PrivacyDashboard />} />

        {/* Regulatory Change Management */}
        <Route path="/regulatory-changes" element={<RegulatoryChanges />} />

        {/* Board & Executive Reporting */}
        <Route path="/board-reporting" element={<BoardDashboard />} />

        {/* Operational Risk */}
        <Route path="/operational-risk" element={<OperationalRiskEvents />} />

        {/* SoD Remediation */}
        <Route path="/sod-remediation" element={<SoDRemediation />} />

        {/* IT Change Risk */}
        <Route path="/it-change-risk" element={<ITChangeRisk />} />

        {/* Insurance / Risk Transfer */}
        <Route path="/insurance" element={<InsurancePolicies />} />

        {/* Sanctions Screening */}
        <Route path="/sanctions-screening" element={<SanctionsScreening />} />

      </Route>

      {/* Public Whistleblower Routes (no auth required) */}
      <Route path="/whistleblower/submit" element={<WhistleblowerIntake />} />
      <Route path="/whistleblower/intake" element={<WhistleblowerIntake />} />

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
