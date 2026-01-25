# Guided Setup Wizard - Zero Training Experience
# Provides step-by-step configuration with smart defaults

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import uuid


class SetupStatus(Enum):
    """Setup wizard status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ConnectionType(Enum):
    """System connection types"""
    SAP_ERP = "sap_erp"
    SAP_S4HANA = "sap_s4hana"
    SAP_BW = "sap_bw"
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    SERVICENOW = "servicenow"
    SALESFORCE = "salesforce"
    WORKDAY = "workday"
    CUSTOM_API = "custom_api"


class TemplateType(Enum):
    """Quick-start template types"""
    BASIC = "basic"              # Small company, simple setup
    STANDARD = "standard"        # Medium company, typical setup
    ENTERPRISE = "enterprise"    # Large company, full features
    SOX_COMPLIANT = "sox"        # SOX compliance focused
    GDPR_COMPLIANT = "gdpr"      # GDPR compliance focused
    HEALTHCARE = "healthcare"    # HIPAA focused
    FINANCIAL = "financial"      # Financial services
    MANUFACTURING = "manufacturing"  # Manufacturing focused


@dataclass
class SystemConnection:
    """System connection configuration"""
    id: str = ""
    name: str = ""
    connection_type: ConnectionType = ConnectionType.SAP_ERP
    host: str = ""
    port: int = 0
    client: str = ""  # SAP client number
    username: str = ""
    # password stored securely, not in this object
    use_sso: bool = False
    enabled: bool = True
    test_status: str = "pending"  # pending, success, failed
    last_tested: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"conn_{uuid.uuid4().hex[:8]}"


@dataclass
class SetupStep:
    """Individual setup step"""
    id: str
    name: str
    description: str
    category: str
    order: int
    status: SetupStatus = SetupStatus.NOT_STARTED
    required: bool = True
    estimated_minutes: int = 5
    help_url: str = ""
    auto_complete: bool = False  # Can be auto-completed with defaults
    data: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class QuickStartTemplate:
    """Pre-configured template for quick setup"""
    id: str
    name: str
    description: str
    template_type: TemplateType
    features: List[str] = field(default_factory=list)
    default_settings: Dict[str, Any] = field(default_factory=dict)
    recommended_for: str = ""


class SetupWizard:
    """
    Guided Setup Wizard for Zero Training Experience

    Provides:
    - Step-by-step guided configuration
    - Smart defaults for quick setup
    - Pre-built templates for common scenarios
    - Validation at each step
    - Auto-configuration where possible
    """

    def __init__(self):
        self.steps: Dict[str, SetupStep] = {}
        self.templates: Dict[str, QuickStartTemplate] = {}
        self.connections: Dict[str, SystemConnection] = {}
        self.current_step_id: Optional[str] = None
        self.selected_template: Optional[str] = None
        self.setup_started: Optional[datetime] = None
        self.setup_completed: Optional[datetime] = None
        self._initialize_steps()
        self._initialize_templates()

    def _initialize_steps(self):
        """Initialize all setup steps"""
        steps = [
            # Welcome & Template Selection
            SetupStep(
                id="welcome",
                name="Welcome",
                description="Welcome to GRC Zero Trust Platform! Let's get you set up.",
                category="Getting Started",
                order=1,
                estimated_minutes=2,
                auto_complete=False,
                help_url="/docs/setup/welcome"
            ),
            SetupStep(
                id="template_selection",
                name="Choose Setup Template",
                description="Select a pre-configured template that matches your organization.",
                category="Getting Started",
                order=2,
                estimated_minutes=2,
                auto_complete=False,
                help_url="/docs/setup/templates"
            ),

            # Organization Setup
            SetupStep(
                id="org_info",
                name="Organization Information",
                description="Basic information about your organization.",
                category="Organization",
                order=10,
                estimated_minutes=3,
                auto_complete=False,
                help_url="/docs/setup/organization"
            ),
            SetupStep(
                id="org_structure",
                name="Organization Structure",
                description="Define company codes, plants, and business units.",
                category="Organization",
                order=11,
                estimated_minutes=5,
                auto_complete=True,  # Can import from SAP
                help_url="/docs/setup/org-structure"
            ),

            # System Connections
            SetupStep(
                id="primary_system",
                name="Primary SAP System",
                description="Connect your main SAP ERP or S/4HANA system.",
                category="Connections",
                order=20,
                estimated_minutes=5,
                auto_complete=False,
                help_url="/docs/setup/sap-connection"
            ),
            SetupStep(
                id="identity_provider",
                name="Identity Provider",
                description="Connect your identity provider (AD, Azure AD, Okta).",
                category="Connections",
                order=21,
                estimated_minutes=5,
                required=False,  # Can use local users
                auto_complete=False,
                help_url="/docs/setup/identity-provider"
            ),
            SetupStep(
                id="hr_system",
                name="HR System (Optional)",
                description="Connect your HR system for employee data sync.",
                category="Connections",
                order=22,
                estimated_minutes=5,
                required=False,
                auto_complete=False,
                help_url="/docs/setup/hr-system"
            ),

            # Risk Analysis Setup
            SetupStep(
                id="sod_rules",
                name="SoD Ruleset",
                description="Configure Separation of Duties rules.",
                category="Risk Analysis",
                order=30,
                estimated_minutes=10,
                auto_complete=True,  # Use pre-built ruleset
                help_url="/docs/setup/sod-rules"
            ),
            SetupStep(
                id="org_rules",
                name="Organizational Rules",
                description="Configure org-level rules to filter false positives.",
                category="Risk Analysis",
                order=31,
                estimated_minutes=5,
                required=False,
                auto_complete=True,
                help_url="/docs/setup/org-rules"
            ),
            SetupStep(
                id="risk_levels",
                name="Risk Level Thresholds",
                description="Define risk scoring and threshold levels.",
                category="Risk Analysis",
                order=32,
                estimated_minutes=3,
                auto_complete=True,
                help_url="/docs/setup/risk-levels"
            ),

            # Workflow Setup
            SetupStep(
                id="workflow_approvers",
                name="Approval Workflow",
                description="Configure who approves access requests.",
                category="Workflows",
                order=40,
                estimated_minutes=5,
                auto_complete=True,  # Use manager-based approval
                help_url="/docs/setup/workflows"
            ),
            SetupStep(
                id="notification_settings",
                name="Notifications",
                description="Configure email and in-app notifications.",
                category="Workflows",
                order=41,
                estimated_minutes=3,
                auto_complete=True,
                help_url="/docs/setup/notifications"
            ),

            # User Access Review
            SetupStep(
                id="certification_schedule",
                name="Access Review Schedule",
                description="Set up periodic access certification campaigns.",
                category="User Access Review",
                order=50,
                estimated_minutes=5,
                required=False,
                auto_complete=True,
                help_url="/docs/setup/certifications"
            ),

            # Emergency Access
            SetupStep(
                id="firefighter_ids",
                name="Emergency Access (Firefighter)",
                description="Configure emergency/firefighter access IDs.",
                category="Emergency Access",
                order=60,
                required=False,
                estimated_minutes=5,
                auto_complete=False,
                help_url="/docs/setup/firefighter"
            ),

            # Security & Compliance
            SetupStep(
                id="audit_settings",
                name="Audit & Logging",
                description="Configure audit trail and logging settings.",
                category="Security",
                order=70,
                estimated_minutes=3,
                auto_complete=True,
                help_url="/docs/setup/audit"
            ),
            SetupStep(
                id="compliance_frameworks",
                name="Compliance Frameworks",
                description="Select applicable compliance frameworks (SOX, GDPR, etc.).",
                category="Security",
                order=71,
                estimated_minutes=3,
                auto_complete=True,
                help_url="/docs/setup/compliance"
            ),

            # Final Steps
            SetupStep(
                id="initial_sync",
                name="Initial Data Sync",
                description="Sync users, roles, and authorizations from connected systems.",
                category="Finalize",
                order=80,
                estimated_minutes=15,
                auto_complete=True,
                help_url="/docs/setup/initial-sync"
            ),
            SetupStep(
                id="first_analysis",
                name="First Risk Analysis",
                description="Run your first access risk analysis.",
                category="Finalize",
                order=81,
                estimated_minutes=10,
                auto_complete=True,
                help_url="/docs/setup/first-analysis"
            ),
            SetupStep(
                id="review_complete",
                name="Review & Complete",
                description="Review your configuration and complete setup.",
                category="Finalize",
                order=90,
                estimated_minutes=5,
                auto_complete=False,
                help_url="/docs/setup/complete"
            ),
        ]

        for step in steps:
            self.steps[step.id] = step

    def _initialize_templates(self):
        """Initialize quick-start templates"""
        templates = [
            QuickStartTemplate(
                id="basic",
                name="Basic Setup",
                description="Simple setup for small organizations. "
                           "Includes essential SoD rules and manager-based approvals.",
                template_type=TemplateType.BASIC,
                features=[
                    "50 essential SoD rules",
                    "Manager-based approval workflow",
                    "Basic email notifications",
                    "Quarterly access reviews"
                ],
                default_settings={
                    "sod_rules": "basic",
                    "workflow": "manager_only",
                    "review_frequency": "quarterly",
                    "risk_scoring": "simple"
                },
                recommended_for="Small businesses with < 500 users"
            ),
            QuickStartTemplate(
                id="standard",
                name="Standard Setup",
                description="Recommended for most organizations. "
                           "Full SoD ruleset with multi-level approvals.",
                template_type=TemplateType.STANDARD,
                features=[
                    "150+ SoD rules across all modules",
                    "Multi-level approval workflows",
                    "Role owner and manager approvals",
                    "Monthly access reviews",
                    "Emergency access management"
                ],
                default_settings={
                    "sod_rules": "standard",
                    "workflow": "multi_level",
                    "review_frequency": "monthly",
                    "risk_scoring": "weighted",
                    "firefighter": True
                },
                recommended_for="Medium organizations with 500-5000 users"
            ),
            QuickStartTemplate(
                id="enterprise",
                name="Enterprise Setup",
                description="Full-featured setup for large enterprises. "
                           "Comprehensive rules, parallel workflows, advanced analytics.",
                template_type=TemplateType.ENTERPRISE,
                features=[
                    "300+ SoD rules with org-level filtering",
                    "MSMP parallel approval workflows",
                    "Dynamic agent determination",
                    "Weekly access reviews",
                    "Full emergency access with logging",
                    "Cross-system correlation",
                    "Advanced risk analytics"
                ],
                default_settings={
                    "sod_rules": "comprehensive",
                    "workflow": "msmp_parallel",
                    "review_frequency": "weekly",
                    "risk_scoring": "ml_enhanced",
                    "firefighter": True,
                    "cross_system": True,
                    "org_rules": True
                },
                recommended_for="Large enterprises with 5000+ users"
            ),
            QuickStartTemplate(
                id="sox_compliant",
                name="SOX Compliance",
                description="Optimized for Sarbanes-Oxley compliance. "
                           "Focus on financial controls and audit trails.",
                template_type=TemplateType.SOX_COMPLIANT,
                features=[
                    "SOX-specific SoD rules highlighted",
                    "Strict approval workflows with segregation",
                    "Complete audit trail",
                    "Quarterly certification campaigns",
                    "Financial module focus (FI, CO, MM)",
                    "Control effectiveness tracking"
                ],
                default_settings={
                    "sod_rules": "sox_focused",
                    "workflow": "sox_compliant",
                    "review_frequency": "quarterly",
                    "audit_level": "comprehensive",
                    "compliance_frameworks": ["SOX"]
                },
                recommended_for="Public companies, financial institutions"
            ),
            QuickStartTemplate(
                id="gdpr_compliant",
                name="GDPR Compliance",
                description="Designed for GDPR compliance. "
                           "Focus on data access controls and privacy.",
                template_type=TemplateType.GDPR_COMPLIANT,
                features=[
                    "Personal data access rules",
                    "Right to access reporting",
                    "Data processing logs",
                    "Consent management integration",
                    "HR data protection focus",
                    "Data retention policies"
                ],
                default_settings={
                    "sod_rules": "gdpr_focused",
                    "workflow": "privacy_aware",
                    "review_frequency": "monthly",
                    "data_protection": True,
                    "compliance_frameworks": ["GDPR"]
                },
                recommended_for="Organizations processing EU personal data"
            ),
            QuickStartTemplate(
                id="financial",
                name="Financial Services",
                description="For banks and financial institutions. "
                           "Regulatory compliance and strict controls.",
                template_type=TemplateType.FINANCIAL,
                features=[
                    "Banking-specific SoD rules",
                    "Multi-approver workflows",
                    "Real-time risk monitoring",
                    "Regulatory reporting (Basel, MiFID)",
                    "Privileged access management",
                    "Transaction monitoring integration"
                ],
                default_settings={
                    "sod_rules": "financial_services",
                    "workflow": "dual_control",
                    "review_frequency": "weekly",
                    "real_time_monitoring": True,
                    "compliance_frameworks": ["SOX", "BASEL", "MIFID"]
                },
                recommended_for="Banks, insurance, investment firms"
            ),
        ]

        for template in templates:
            self.templates[template.id] = template

    # ==================== Progress & Navigation ====================

    def get_progress(self) -> Dict[str, Any]:
        """Get overall setup progress"""
        total = len([s for s in self.steps.values() if s.required])
        completed = len([s for s in self.steps.values()
                        if s.required and s.status == SetupStatus.COMPLETED])

        return {
            "total_steps": len(self.steps),
            "required_steps": total,
            "completed_steps": completed,
            "progress_percent": round((completed / total) * 100) if total > 0 else 0,
            "current_step": self.current_step_id,
            "status": self._get_overall_status(),
            "estimated_remaining_minutes": self._estimate_remaining_time()
        }

    def _get_overall_status(self) -> str:
        """Get overall setup status"""
        if self.setup_completed:
            return "completed"
        if self.setup_started:
            return "in_progress"
        return "not_started"

    def _estimate_remaining_time(self) -> int:
        """Estimate remaining setup time in minutes"""
        remaining = 0
        for step in self.steps.values():
            if step.status not in [SetupStatus.COMPLETED, SetupStatus.SKIPPED]:
                remaining += step.estimated_minutes
        return remaining

    def get_steps_by_category(self) -> Dict[str, List[SetupStep]]:
        """Get steps organized by category"""
        categories: Dict[str, List[SetupStep]] = {}
        for step in sorted(self.steps.values(), key=lambda s: s.order):
            if step.category not in categories:
                categories[step.category] = []
            categories[step.category].append(step)
        return categories

    def get_next_step(self) -> Optional[SetupStep]:
        """Get the next incomplete step"""
        for step in sorted(self.steps.values(), key=lambda s: s.order):
            if step.status == SetupStatus.NOT_STARTED:
                return step
        return None

    def start_step(self, step_id: str) -> Dict[str, Any]:
        """Start working on a step"""
        if step_id not in self.steps:
            return {"success": False, "error": "Step not found"}

        step = self.steps[step_id]
        step.status = SetupStatus.IN_PROGRESS
        self.current_step_id = step_id

        if not self.setup_started:
            self.setup_started = datetime.utcnow()

        return {
            "success": True,
            "step": step,
            "guidance": self._get_step_guidance(step_id),
            "defaults": self._get_step_defaults(step_id)
        }

    def complete_step(self, step_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete a step with provided data"""
        if step_id not in self.steps:
            return {"success": False, "error": "Step not found"}

        step = self.steps[step_id]

        # Validate step data
        validation = self._validate_step(step_id, data)
        if not validation["valid"]:
            step.validation_errors = validation["errors"]
            return {"success": False, "errors": validation["errors"]}

        step.data = data
        step.status = SetupStatus.COMPLETED
        step.validation_errors = []

        # Apply step configuration
        self._apply_step_config(step_id, data)

        # Get next step
        next_step = self.get_next_step()

        return {
            "success": True,
            "step": step,
            "next_step": next_step,
            "progress": self.get_progress()
        }

    def skip_step(self, step_id: str) -> Dict[str, Any]:
        """Skip an optional step"""
        if step_id not in self.steps:
            return {"success": False, "error": "Step not found"}

        step = self.steps[step_id]
        if step.required:
            return {"success": False, "error": "Cannot skip required step"}

        step.status = SetupStatus.SKIPPED
        next_step = self.get_next_step()

        return {
            "success": True,
            "step": step,
            "next_step": next_step,
            "progress": self.get_progress()
        }

    def auto_complete_step(self, step_id: str) -> Dict[str, Any]:
        """Auto-complete a step using smart defaults"""
        if step_id not in self.steps:
            return {"success": False, "error": "Step not found"}

        step = self.steps[step_id]
        if not step.auto_complete:
            return {"success": False, "error": "Step cannot be auto-completed"}

        defaults = self._get_step_defaults(step_id)
        return self.complete_step(step_id, defaults)

    # ==================== Template Application ====================

    def apply_template(self, template_id: str) -> Dict[str, Any]:
        """Apply a quick-start template"""
        if template_id not in self.templates:
            return {"success": False, "error": "Template not found"}

        template = self.templates[template_id]
        self.selected_template = template_id

        # Pre-fill step data based on template
        for step_id, step in self.steps.items():
            if step.auto_complete:
                defaults = self._get_template_defaults(template_id, step_id)
                step.data = defaults

        return {
            "success": True,
            "template": template,
            "message": f"Template '{template.name}' applied. "
                      f"You can proceed through steps or auto-complete with defaults."
        }

    def _get_template_defaults(self, template_id: str, step_id: str) -> Dict[str, Any]:
        """Get default values for a step based on selected template"""
        template = self.templates.get(template_id)
        if not template:
            return self._get_step_defaults(step_id)

        defaults = self._get_step_defaults(step_id)

        # Override with template-specific settings
        if step_id == "sod_rules":
            sod_level = template.default_settings.get("sod_rules", "standard")
            defaults["ruleset_level"] = sod_level
            defaults["enable_all_rules"] = sod_level in ["comprehensive", "sox_focused"]

        elif step_id == "workflow_approvers":
            workflow_type = template.default_settings.get("workflow", "manager_only")
            defaults["workflow_type"] = workflow_type
            defaults["parallel_paths"] = workflow_type == "msmp_parallel"

        elif step_id == "certification_schedule":
            frequency = template.default_settings.get("review_frequency", "quarterly")
            defaults["frequency"] = frequency

        elif step_id == "compliance_frameworks":
            frameworks = template.default_settings.get("compliance_frameworks", [])
            defaults["selected_frameworks"] = frameworks

        return defaults

    # ==================== Step Guidance & Defaults ====================

    def _get_step_guidance(self, step_id: str) -> Dict[str, Any]:
        """Get guidance and help text for a step"""
        guidance = {
            "welcome": {
                "title": "Welcome to GRC Zero Trust Platform!",
                "description": "This wizard will guide you through the initial setup. "
                              "Most steps have smart defaults - you can accept them or customize.",
                "tips": [
                    "Choose a template to get started quickly",
                    "Optional steps can be skipped and configured later",
                    "You can always change settings after setup is complete"
                ]
            },
            "template_selection": {
                "title": "Choose Your Setup Template",
                "description": "Select a template that best matches your organization. "
                              "This will pre-configure many settings for you.",
                "tips": [
                    "Basic: Best for small companies getting started",
                    "Standard: Recommended for most organizations",
                    "Enterprise: Full features for large companies",
                    "SOX/GDPR: Compliance-focused configurations"
                ]
            },
            "primary_system": {
                "title": "Connect Your SAP System",
                "description": "Connect to your main SAP ERP or S/4HANA system. "
                              "This enables user sync, role analysis, and real-time checks.",
                "tips": [
                    "You'll need: hostname, client number, and RFC user credentials",
                    "Use a dedicated RFC user with read-only access",
                    "Test the connection before proceeding"
                ],
                "fields": [
                    {"name": "host", "label": "SAP Host", "required": True},
                    {"name": "client", "label": "Client Number", "required": True},
                    {"name": "username", "label": "RFC Username", "required": True},
                    {"name": "password", "label": "RFC Password", "required": True, "type": "password"}
                ]
            },
            "sod_rules": {
                "title": "Separation of Duties Rules",
                "description": "SoD rules detect conflicting access. "
                              "We provide 300+ pre-built rules you can use immediately.",
                "tips": [
                    "Start with recommended rules and adjust later",
                    "Rules are categorized by SAP module (FI, MM, SD, HR, etc.)",
                    "Critical rules are highlighted for priority review"
                ]
            },
            "workflow_approvers": {
                "title": "Approval Workflow Configuration",
                "description": "Define who approves access requests. "
                              "Smart defaults use manager-based approval.",
                "tips": [
                    "Manager approval is the most common starting point",
                    "Add role owners for role-specific approvals",
                    "High-risk requests can require additional approvers"
                ]
            },
            "firefighter_ids": {
                "title": "Emergency Access (Firefighter)",
                "description": "Firefighter IDs provide temporary elevated access "
                              "for emergencies with full logging.",
                "tips": [
                    "Create IDs for each system that needs emergency access",
                    "Assign controllers who approve firefighter sessions",
                    "All actions are logged for audit"
                ]
            },
        }

        return guidance.get(step_id, {
            "title": self.steps[step_id].name,
            "description": self.steps[step_id].description,
            "tips": []
        })

    def _get_step_defaults(self, step_id: str) -> Dict[str, Any]:
        """Get smart default values for a step"""
        defaults = {
            "org_info": {
                "company_name": "",
                "industry": "general",
                "employee_count": "500-5000",
                "primary_erp": "sap"
            },
            "org_structure": {
                "import_from_sap": True,
                "company_codes": [],
                "plants": [],
                "auto_sync": True
            },
            "primary_system": {
                "connection_type": "sap_erp",
                "port": 3300,
                "use_sso": False
            },
            "identity_provider": {
                "provider_type": "azure_ad",
                "sync_groups": True,
                "sync_frequency": "hourly"
            },
            "sod_rules": {
                "ruleset_level": "standard",
                "enable_critical": True,
                "enable_high": True,
                "enable_medium": True,
                "enable_low": False,
                "modules": ["FI", "MM", "SD", "HR", "BASIS"]
            },
            "org_rules": {
                "enable_company_code_separation": True,
                "enable_plant_separation": True,
                "enable_sales_org_separation": False
            },
            "risk_levels": {
                "critical_threshold": 90,
                "high_threshold": 70,
                "medium_threshold": 40,
                "scoring_method": "weighted"
            },
            "workflow_approvers": {
                "workflow_type": "manager_based",
                "require_manager": True,
                "require_role_owner": True,
                "high_risk_additional": True,
                "parallel_paths": False,
                "auto_approve_low_risk": False
            },
            "notification_settings": {
                "email_enabled": True,
                "in_app_enabled": True,
                "digest_frequency": "daily",
                "urgent_immediate": True
            },
            "certification_schedule": {
                "frequency": "quarterly",
                "auto_create": True,
                "include_all_users": True,
                "reviewer": "manager"
            },
            "audit_settings": {
                "log_all_access": True,
                "log_changes": True,
                "retention_days": 365,
                "export_enabled": True
            },
            "compliance_frameworks": {
                "selected_frameworks": ["SOX"],
                "auto_map_controls": True,
                "generate_reports": True
            },
            "initial_sync": {
                "sync_users": True,
                "sync_roles": True,
                "sync_authorizations": True,
                "batch_size": 1000
            },
            "first_analysis": {
                "analyze_all_users": True,
                "include_mitigation": True,
                "generate_report": True
            }
        }

        return defaults.get(step_id, {})

    # ==================== Validation ====================

    def _validate_step(self, step_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate step data"""
        errors = []

        if step_id == "org_info":
            if not data.get("company_name"):
                errors.append("Company name is required")

        elif step_id == "primary_system":
            if not data.get("host"):
                errors.append("SAP host is required")
            if not data.get("client"):
                errors.append("SAP client number is required")
            if not data.get("username"):
                errors.append("RFC username is required")

        elif step_id == "sod_rules":
            if not data.get("modules") or len(data.get("modules", [])) == 0:
                errors.append("Select at least one SAP module")

        elif step_id == "workflow_approvers":
            if not data.get("require_manager") and not data.get("require_role_owner"):
                errors.append("At least one approver type must be configured")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _apply_step_config(self, step_id: str, data: Dict[str, Any]):
        """Apply step configuration to the system"""
        # This would actually configure the system
        # For now, just store the configuration
        pass

    # ==================== Quick Setup ====================

    def quick_setup(self, template_id: str = "standard") -> Dict[str, Any]:
        """
        One-click setup with a template
        Auto-completes all steps with template defaults
        """
        # Apply template
        result = self.apply_template(template_id)
        if not result["success"]:
            return result

        self.setup_started = datetime.utcnow()
        completed_steps = []
        skipped_steps = []

        for step in sorted(self.steps.values(), key=lambda s: s.order):
            if step.auto_complete:
                defaults = self._get_template_defaults(template_id, step.id)
                validation = self._validate_step(step.id, defaults)
                if validation["valid"]:
                    step.data = defaults
                    step.status = SetupStatus.COMPLETED
                    completed_steps.append(step.id)
            elif not step.required:
                step.status = SetupStatus.SKIPPED
                skipped_steps.append(step.id)

        # Mark steps that need manual input
        manual_steps = [
            s for s in self.steps.values()
            if s.status == SetupStatus.NOT_STARTED
        ]

        return {
            "success": True,
            "template": template_id,
            "auto_completed": completed_steps,
            "skipped": skipped_steps,
            "manual_required": [s.id for s in manual_steps],
            "message": f"Quick setup complete! {len(manual_steps)} steps need manual input.",
            "next_step": manual_steps[0] if manual_steps else None
        }

    # ==================== Connection Testing ====================

    def add_connection(self, connection: SystemConnection) -> Dict[str, Any]:
        """Add a system connection"""
        self.connections[connection.id] = connection
        return {"success": True, "connection_id": connection.id}

    def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test a system connection"""
        if connection_id not in self.connections:
            return {"success": False, "error": "Connection not found"}

        conn = self.connections[connection_id]

        # Simulate connection test (would actually test in production)
        conn.last_tested = datetime.utcnow()
        conn.test_status = "success"  # Would be based on actual test

        return {
            "success": True,
            "connection_id": connection_id,
            "status": conn.test_status,
            "message": f"Successfully connected to {conn.name}"
        }

    # ==================== Finalization ====================

    def finalize_setup(self) -> Dict[str, Any]:
        """Finalize and complete the setup wizard"""
        # Check all required steps are complete
        incomplete = [
            s for s in self.steps.values()
            if s.required and s.status not in [SetupStatus.COMPLETED, SetupStatus.SKIPPED]
        ]

        if incomplete:
            return {
                "success": False,
                "error": "Not all required steps are complete",
                "incomplete_steps": [s.id for s in incomplete]
            }

        self.setup_completed = datetime.utcnow()

        # Generate summary
        summary = self._generate_setup_summary()

        return {
            "success": True,
            "message": "Setup complete! Your GRC Zero Trust Platform is ready to use.",
            "summary": summary,
            "next_steps": [
                "Run your first access risk analysis",
                "Create your first access request",
                "Set up your first certification campaign",
                "Explore the dashboard"
            ]
        }

    def _generate_setup_summary(self) -> Dict[str, Any]:
        """Generate a summary of the completed setup"""
        return {
            "template_used": self.selected_template,
            "systems_connected": len(self.connections),
            "steps_completed": len([s for s in self.steps.values()
                                   if s.status == SetupStatus.COMPLETED]),
            "steps_skipped": len([s for s in self.steps.values()
                                 if s.status == SetupStatus.SKIPPED]),
            "configuration": {
                step_id: step.data
                for step_id, step in self.steps.items()
                if step.data
            }
        }

    def export_config(self) -> Dict[str, Any]:
        """Export the current configuration for backup/restore"""
        return {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "template": self.selected_template,
            "steps": {
                step_id: {
                    "status": step.status.value,
                    "data": step.data
                }
                for step_id, step in self.steps.items()
            },
            "connections": {
                conn_id: {
                    "name": conn.name,
                    "type": conn.connection_type.value,
                    "host": conn.host,
                    "enabled": conn.enabled
                }
                for conn_id, conn in self.connections.items()
            }
        }

    def import_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Import a previously exported configuration"""
        try:
            self.selected_template = config.get("template")

            for step_id, step_config in config.get("steps", {}).items():
                if step_id in self.steps:
                    self.steps[step_id].status = SetupStatus(step_config["status"])
                    self.steps[step_id].data = step_config.get("data", {})

            return {"success": True, "message": "Configuration imported successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
