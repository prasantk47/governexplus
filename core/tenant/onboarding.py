# Tenant Onboarding
# Self-service tenant provisioning and setup

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import uuid


class OnboardingStatus(Enum):
    """Onboarding workflow status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_VERIFICATION = "pending_verification"
    PROVISIONING = "provisioning"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OnboardingStep:
    """Individual onboarding step"""
    id: str
    name: str
    description: str
    order: int
    required: bool = True
    status: str = "pending"  # pending, in_progress, completed, skipped
    completed_at: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProvisioningResult:
    """Result of tenant provisioning"""
    success: bool
    tenant_id: str = ""
    tenant_slug: str = ""
    errors: List[str] = field(default_factory=list)

    # Provisioned resources
    database_provisioned: bool = False
    storage_provisioned: bool = False
    admin_user_created: bool = False
    default_config_applied: bool = False

    # Access details
    login_url: str = ""
    admin_email: str = ""
    temp_password: str = ""  # Would be sent via email, not returned

    # Next steps
    next_steps: List[str] = field(default_factory=list)


class TenantOnboarding:
    """
    Self-Service Tenant Onboarding

    Provides a streamlined onboarding experience:

    1. SIGNUP
       - Email verification
       - Company information
       - Plan selection

    2. PROVISIONING
       - Database creation
       - Storage allocation
       - Encryption key generation

    3. INITIAL SETUP
       - Admin user creation
       - Default configuration
       - First system connection

    4. ACTIVATION
       - Email confirmation
       - Welcome tour
       - First risk analysis
    """

    def __init__(self):
        # Onboarding sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Pending verifications
        self.verifications: Dict[str, Dict[str, Any]] = {}

        # Onboarding steps template
        self.steps_template = self._create_steps_template()

    def _create_steps_template(self) -> List[OnboardingStep]:
        """Create template of onboarding steps"""
        return [
            OnboardingStep(
                id="email_verification",
                name="Verify Email",
                description="Verify your email address",
                order=1,
                required=True
            ),
            OnboardingStep(
                id="company_info",
                name="Company Information",
                description="Tell us about your organization",
                order=2,
                required=True
            ),
            OnboardingStep(
                id="plan_selection",
                name="Select Plan",
                description="Choose your subscription plan",
                order=3,
                required=True
            ),
            OnboardingStep(
                id="payment_info",
                name="Payment Information",
                description="Add payment method (skip for free tier)",
                order=4,
                required=False
            ),
            OnboardingStep(
                id="admin_setup",
                name="Admin Account",
                description="Set up your administrator account",
                order=5,
                required=True
            ),
            OnboardingStep(
                id="team_invites",
                name="Invite Team",
                description="Invite your team members (optional)",
                order=6,
                required=False
            ),
            OnboardingStep(
                id="first_system",
                name="Connect System",
                description="Connect your first SAP system",
                order=7,
                required=False
            ),
            OnboardingStep(
                id="complete",
                name="Get Started",
                description="Complete setup and start using the platform",
                order=8,
                required=True
            )
        ]

    # ==================== Signup Flow ====================

    def start_signup(
        self,
        email: str,
        company_name: str = ""
    ) -> Dict[str, Any]:
        """Start the signup/onboarding process"""
        session_id = f"onboard_{uuid.uuid4().hex[:12]}"

        # Create verification token
        verification_token = uuid.uuid4().hex

        # Store verification
        self.verifications[verification_token] = {
            "email": email,
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "verified": False
        }

        # Create session
        self.sessions[session_id] = {
            "id": session_id,
            "email": email,
            "company_name": company_name,
            "status": OnboardingStatus.PENDING_VERIFICATION,
            "steps": [step.__dict__.copy() for step in self.steps_template],
            "created_at": datetime.utcnow(),
            "tenant_id": None,
            "data": {}
        }

        # Would send verification email here
        verification_link = f"https://app.grc-platform.com/verify?token={verification_token}"

        return {
            "success": True,
            "session_id": session_id,
            "message": f"Verification email sent to {email}",
            "verification_link": verification_link,  # For testing only
            "next_step": "Check your email to verify your address"
        }

    def verify_email(self, token: str) -> Dict[str, Any]:
        """Verify email address"""
        verification = self.verifications.get(token)
        if not verification:
            return {"success": False, "error": "Invalid verification token"}

        if verification["expires_at"] < datetime.utcnow():
            return {"success": False, "error": "Verification token expired"}

        if verification["verified"]:
            return {"success": False, "error": "Email already verified"}

        # Mark as verified
        verification["verified"] = True

        # Update session
        session_id = verification["session_id"]
        session = self.sessions.get(session_id)
        if session:
            session["status"] = OnboardingStatus.IN_PROGRESS
            self._update_step_status(session, "email_verification", "completed")

        return {
            "success": True,
            "session_id": session_id,
            "message": "Email verified successfully",
            "next_step": "company_info"
        }

    # ==================== Step Processing ====================

    def submit_step(
        self,
        session_id: str,
        step_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit data for an onboarding step"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        # Validate step
        step = self._get_step(session, step_id)
        if not step:
            return {"success": False, "error": "Step not found"}

        # Process step-specific logic
        if step_id == "company_info":
            result = self._process_company_info(session, data)
        elif step_id == "plan_selection":
            result = self._process_plan_selection(session, data)
        elif step_id == "payment_info":
            result = self._process_payment_info(session, data)
        elif step_id == "admin_setup":
            result = self._process_admin_setup(session, data)
        elif step_id == "team_invites":
            result = self._process_team_invites(session, data)
        elif step_id == "first_system":
            result = self._process_first_system(session, data)
        elif step_id == "complete":
            result = self._process_completion(session)
        else:
            result = {"success": True}

        if result.get("success"):
            self._update_step_status(session, step_id, "completed", data)

        # Determine next step
        next_step = self._get_next_step(session)

        return {
            "success": result.get("success", True),
            "error": result.get("error"),
            "session_id": session_id,
            "step_completed": step_id,
            "next_step": next_step["id"] if next_step else None,
            "data": result.get("data", {})
        }

    def skip_step(self, session_id: str, step_id: str) -> Dict[str, Any]:
        """Skip an optional step"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        step = self._get_step(session, step_id)
        if not step:
            return {"success": False, "error": "Step not found"}

        if step.get("required"):
            return {"success": False, "error": "Cannot skip required step"}

        self._update_step_status(session, step_id, "skipped")
        next_step = self._get_next_step(session)

        return {
            "success": True,
            "step_skipped": step_id,
            "next_step": next_step["id"] if next_step else None
        }

    def _process_company_info(
        self,
        session: Dict,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process company information step"""
        required_fields = ["company_name", "industry", "employee_count"]
        for field in required_fields:
            if not data.get(field):
                return {"success": False, "error": f"Missing required field: {field}"}

        session["company_name"] = data["company_name"]
        session["data"]["company_info"] = data

        return {"success": True}

    def _process_plan_selection(
        self,
        session: Dict,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process plan selection step"""
        plan_id = data.get("plan_id")
        if not plan_id:
            return {"success": False, "error": "Please select a plan"}

        session["data"]["plan"] = {
            "plan_id": plan_id,
            "billing_interval": data.get("billing_interval", "monthly")
        }

        # If free plan, skip payment
        if plan_id == "free":
            self._update_step_status(session, "payment_info", "skipped")

        return {"success": True}

    def _process_payment_info(
        self,
        session: Dict,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process payment information step"""
        # Would integrate with Stripe here
        payment_method_id = data.get("payment_method_id")
        if not payment_method_id:
            return {"success": False, "error": "Payment method required"}

        session["data"]["payment"] = {
            "payment_method_id": payment_method_id
        }

        return {"success": True}

    def _process_admin_setup(
        self,
        session: Dict,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process admin account setup"""
        required = ["full_name", "password"]
        for field in required:
            if not data.get(field):
                return {"success": False, "error": f"Missing: {field}"}

        # Validate password strength
        password = data.get("password", "")
        if len(password) < 8:
            return {"success": False, "error": "Password must be at least 8 characters"}

        session["data"]["admin"] = {
            "full_name": data["full_name"],
            "email": session["email"],
            # Password would be hashed, not stored plain
        }

        return {"success": True}

    def _process_team_invites(
        self,
        session: Dict,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process team invitations"""
        invites = data.get("invites", [])
        session["data"]["team_invites"] = invites

        # Would queue invitation emails

        return {
            "success": True,
            "data": {"invites_queued": len(invites)}
        }

    def _process_first_system(
        self,
        session: Dict,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process first system connection"""
        # Store connection details for later provisioning
        session["data"]["first_system"] = data

        return {"success": True}

    def _process_completion(self, session: Dict) -> Dict[str, Any]:
        """Complete the onboarding process"""
        # Provision the tenant
        result = self.provision_tenant(session["id"])

        if result.success:
            session["status"] = OnboardingStatus.COMPLETED
            session["tenant_id"] = result.tenant_id

        return {
            "success": result.success,
            "error": result.errors[0] if result.errors else None,
            "data": {
                "tenant_id": result.tenant_id,
                "login_url": result.login_url
            }
        }

    # ==================== Provisioning ====================

    def provision_tenant(self, session_id: str) -> ProvisioningResult:
        """Provision all resources for a new tenant"""
        session = self.sessions.get(session_id)
        if not session:
            return ProvisioningResult(
                success=False,
                errors=["Session not found"]
            )

        session["status"] = OnboardingStatus.PROVISIONING
        errors = []

        # Generate tenant ID and slug
        company_name = session.get("company_name", "Company")
        tenant_slug = self._generate_slug(company_name)
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"

        result = ProvisioningResult(
            success=True,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug
        )

        # 1. Create tenant record
        try:
            # Would call TenantManager.create_tenant()
            result.database_provisioned = True
        except Exception as e:
            errors.append(f"Database provisioning failed: {str(e)}")
            result.database_provisioned = False

        # 2. Provision storage
        try:
            # Would call TenantIsolation.provision_storage()
            result.storage_provisioned = True
        except Exception as e:
            errors.append(f"Storage provisioning failed: {str(e)}")
            result.storage_provisioned = False

        # 3. Create admin user
        try:
            admin_data = session["data"].get("admin", {})
            # Would create user in tenant
            result.admin_user_created = True
            result.admin_email = session["email"]
        except Exception as e:
            errors.append(f"Admin user creation failed: {str(e)}")
            result.admin_user_created = False

        # 4. Apply default configuration
        try:
            plan_data = session["data"].get("plan", {})
            # Would apply tier-based defaults
            result.default_config_applied = True
        except Exception as e:
            errors.append(f"Configuration failed: {str(e)}")
            result.default_config_applied = False

        # 5. Set up billing
        try:
            plan_id = session["data"].get("plan", {}).get("plan_id", "free")
            payment_id = session["data"].get("payment", {}).get("payment_method_id", "")
            # Would call BillingManager.create_subscription()
        except Exception as e:
            errors.append(f"Billing setup failed: {str(e)}")

        # 6. Send invitations
        invites = session["data"].get("team_invites", [])
        for invite in invites:
            # Would queue invitation email
            pass

        # Determine success
        result.success = (
            result.database_provisioned and
            result.admin_user_created
        )
        result.errors = errors

        # Set access details
        result.login_url = f"https://{tenant_slug}.grc-platform.com"
        result.next_steps = [
            "Log in with your admin credentials",
            "Complete the setup wizard",
            "Connect your first SAP system",
            "Run your first risk analysis"
        ]

        return result

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug"""
        slug = name.lower()
        slug = ''.join(c if c.isalnum() else '-' for c in slug)
        slug = '-'.join(filter(None, slug.split('-')))
        return slug[:50]

    # ==================== Helper Methods ====================

    def _get_step(self, session: Dict, step_id: str) -> Optional[Dict]:
        """Get step from session"""
        for step in session.get("steps", []):
            if step["id"] == step_id:
                return step
        return None

    def _update_step_status(
        self,
        session: Dict,
        step_id: str,
        status: str,
        data: Dict = None
    ):
        """Update step status in session"""
        for step in session.get("steps", []):
            if step["id"] == step_id:
                step["status"] = status
                if status == "completed":
                    step["completed_at"] = datetime.utcnow().isoformat()
                if data:
                    step["data"] = data
                break

    def _get_next_step(self, session: Dict) -> Optional[Dict]:
        """Get next incomplete step"""
        for step in sorted(session.get("steps", []), key=lambda s: s["order"]):
            if step["status"] == "pending":
                return step
        return None

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current onboarding session status"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        completed_steps = [
            s for s in session["steps"]
            if s["status"] == "completed"
        ]
        total_required = len([
            s for s in session["steps"]
            if s.get("required", True)
        ])

        return {
            "session_id": session_id,
            "status": session["status"].value if isinstance(session["status"], OnboardingStatus) else session["status"],
            "email": session["email"],
            "company_name": session.get("company_name", ""),
            "progress": {
                "completed": len(completed_steps),
                "total": len(session["steps"]),
                "required_remaining": total_required - len([
                    s for s in completed_steps
                    if s.get("required", True)
                ])
            },
            "steps": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "status": s["status"],
                    "required": s.get("required", True)
                }
                for s in session["steps"]
            ],
            "next_step": self._get_next_step(session),
            "tenant_id": session.get("tenant_id")
        }
