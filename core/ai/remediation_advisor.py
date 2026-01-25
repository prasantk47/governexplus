# AI Remediation Advisor
# Intelligent recommendations for fixing access risks

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime


class ActionType(Enum):
    """Types of remediation actions"""
    REMOVE_ROLE = "remove_role"
    SPLIT_ROLE = "split_role"
    ADD_MITIGATION = "add_mitigation"
    MODIFY_ROLE = "modify_role"
    REASSIGN_TASK = "reassign_task"
    ACCEPT_RISK = "accept_risk"
    CREATE_WORKFLOW = "create_workflow"
    SCHEDULE_REVIEW = "schedule_review"


class ActionComplexity(Enum):
    """Complexity/effort level"""
    TRIVIAL = "trivial"      # 1-click fix
    SIMPLE = "simple"        # Few minutes
    MODERATE = "moderate"    # Hours
    COMPLEX = "complex"      # Days/weeks
    STRATEGIC = "strategic"  # Major initiative


@dataclass
class ImpactAssessment:
    """Assessment of remediation impact"""
    risk_reduction: float  # How much risk is reduced (0-100)
    users_affected: int
    roles_affected: int
    business_impact: str  # Description of business impact
    reversibility: str    # Easy, moderate, difficult
    side_effects: List[str] = field(default_factory=list)


@dataclass
class RemediationAction:
    """Single remediation action"""
    id: str
    action_type: ActionType
    title: str
    description: str
    complexity: ActionComplexity
    priority: int  # 1-10, higher = more urgent

    # What needs to be done
    target_user: Optional[str] = None
    target_role: Optional[str] = None
    target_transaction: Optional[str] = None

    # Impact analysis
    impact: Optional[ImpactAssessment] = None

    # Implementation details
    steps: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Automation
    can_auto_execute: bool = False
    auto_execute_command: Optional[str] = None


@dataclass
class RemediationPlan:
    """Complete remediation plan for a risk"""
    id: str
    risk_id: str
    risk_description: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Recommended actions (prioritized)
    recommended_actions: List[RemediationAction] = field(default_factory=list)

    # Alternative approaches
    alternatives: List[RemediationAction] = field(default_factory=list)

    # Summary
    total_risk_reduction: float = 0.0
    estimated_effort: str = ""
    recommended_approach: str = ""

    # AI reasoning
    reasoning: str = ""
    confidence: float = 0.0


class RemediationAdvisor:
    """
    AI-Powered Remediation Advisor

    Key advantages over traditional SAP GRC:

    1. INTELLIGENT RECOMMENDATIONS: Doesn't just flag - suggests fixes
       - Multiple options with trade-offs explained
       - Considers business context, not just technical compliance

    2. IMPACT PREDICTION: Shows what happens if you implement fix
       - How many users affected
       - Business process implications
       - Side effects

    3. PRIORITIZATION: Ranks actions by ROI
       - High impact + low effort = do first
       - Considers organizational constraints

    4. AUTOMATION: Can execute simple fixes automatically
       - One-click remediation for low-risk changes
       - Scheduled batch processing

    5. LEARNING: Gets smarter over time
       - Tracks which remediations work
       - Learns organizational preferences
    """

    def __init__(self):
        # Knowledge base of remediation patterns
        self.remediation_patterns: Dict[str, List[Dict]] = {}

        # Historical remediation data
        self.remediation_history: List[Dict] = []

        # Organizational preferences
        self.org_preferences = {
            "prefer_mitigation_over_removal": True,
            "auto_execute_threshold": "simple",
            "require_approval_for": ["complex", "strategic"],
            "max_users_for_auto": 10
        }

        self._initialize_patterns()

    def _initialize_patterns(self):
        """Initialize remediation pattern knowledge base"""
        self.remediation_patterns = {
            # Vendor Master + AP Payment conflict
            "vendor_payment_sod": [
                {
                    "action_type": ActionType.SPLIT_ROLE,
                    "title": "Split Vendor and Payment Functions",
                    "description": "Separate vendor maintenance from payment processing into different roles",
                    "complexity": ActionComplexity.MODERATE,
                    "risk_reduction": 95,
                    "recommended": True
                },
                {
                    "action_type": ActionType.ADD_MITIGATION,
                    "title": "Add Dual Control for Payments",
                    "description": "Require second approver for payments to vendors created by same user",
                    "complexity": ActionComplexity.SIMPLE,
                    "risk_reduction": 70,
                    "recommended": False
                },
                {
                    "action_type": ActionType.REASSIGN_TASK,
                    "title": "Reassign Vendor Maintenance",
                    "description": "Move vendor maintenance responsibility to dedicated data team",
                    "complexity": ActionComplexity.COMPLEX,
                    "risk_reduction": 100,
                    "recommended": False
                }
            ],
            # PO Creation + Goods Receipt conflict
            "po_gr_sod": [
                {
                    "action_type": ActionType.REMOVE_ROLE,
                    "title": "Remove Goods Receipt Authorization",
                    "description": "Remove MIGO access from users who create purchase orders",
                    "complexity": ActionComplexity.SIMPLE,
                    "risk_reduction": 100,
                    "recommended": True
                },
                {
                    "action_type": ActionType.ADD_MITIGATION,
                    "title": "Value-Based Controls",
                    "description": "Allow combined access only for low-value items (<$1000)",
                    "complexity": ActionComplexity.MODERATE,
                    "risk_reduction": 60,
                    "recommended": False
                }
            ],
            # User Admin + Role Admin conflict
            "user_role_admin_sod": [
                {
                    "action_type": ActionType.SPLIT_ROLE,
                    "title": "Separate User and Role Administration",
                    "description": "Create dedicated role admin team separate from user admin",
                    "complexity": ActionComplexity.COMPLEX,
                    "risk_reduction": 100,
                    "recommended": True
                },
                {
                    "action_type": ActionType.ADD_MITIGATION,
                    "title": "Four-Eyes Principle",
                    "description": "Require second admin to approve role assignments",
                    "complexity": ActionComplexity.SIMPLE,
                    "risk_reduction": 80,
                    "recommended": False
                }
            ],
            # Generic high access
            "excessive_access": [
                {
                    "action_type": ActionType.SCHEDULE_REVIEW,
                    "title": "Schedule Access Review",
                    "description": "Initiate certification campaign to review and reduce access",
                    "complexity": ActionComplexity.SIMPLE,
                    "risk_reduction": 40,
                    "recommended": True
                },
                {
                    "action_type": ActionType.MODIFY_ROLE,
                    "title": "Right-Size Role",
                    "description": "Remove unused transactions from role based on usage analysis",
                    "complexity": ActionComplexity.MODERATE,
                    "risk_reduction": 50,
                    "recommended": False
                }
            ]
        }

    # ==================== Plan Generation ====================

    def generate_remediation_plan(
        self,
        risk_id: str,
        risk_type: str,
        risk_description: str,
        affected_users: List[str],
        affected_roles: List[str],
        context: Dict[str, Any] = None
    ) -> RemediationPlan:
        """
        Generate a comprehensive remediation plan for a risk

        Analyzes the risk and recommends prioritized actions
        with impact assessment and implementation steps.
        """
        context = context or {}

        # 1. Match risk to known patterns
        pattern_key = self._match_risk_pattern(risk_type, risk_description)
        patterns = self.remediation_patterns.get(pattern_key, [])

        # 2. Generate actions from patterns
        actions = []
        for i, pattern in enumerate(patterns):
            action = self._create_action_from_pattern(
                pattern, risk_id, affected_users, affected_roles, i
            )
            actions.append(action)

        # 3. If no patterns match, generate generic recommendations
        if not actions:
            actions = self._generate_generic_actions(
                risk_id, risk_type, affected_users, affected_roles
            )

        # 4. Prioritize actions
        actions = self._prioritize_actions(actions, context)

        # 5. Separate recommended vs alternatives
        recommended = [a for a in actions if a.priority >= 7]
        alternatives = [a for a in actions if a.priority < 7]

        # 6. Calculate totals
        total_reduction = max([a.impact.risk_reduction for a in actions]) if actions else 0

        # 7. Generate reasoning
        reasoning = self._generate_reasoning(
            risk_type, actions, affected_users, affected_roles
        )

        return RemediationPlan(
            id=f"plan_{risk_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            risk_id=risk_id,
            risk_description=risk_description,
            recommended_actions=recommended,
            alternatives=alternatives,
            total_risk_reduction=total_reduction,
            estimated_effort=self._estimate_total_effort(actions),
            recommended_approach=recommended[0].title if recommended else "Manual review required",
            reasoning=reasoning,
            confidence=0.85 if patterns else 0.60
        )

    def _match_risk_pattern(self, risk_type: str, description: str) -> str:
        """Match risk to known remediation patterns"""
        desc_lower = description.lower()

        if "vendor" in desc_lower and "payment" in desc_lower:
            return "vendor_payment_sod"
        elif "purchase order" in desc_lower and "goods receipt" in desc_lower:
            return "po_gr_sod"
        elif "user admin" in desc_lower and "role" in desc_lower:
            return "user_role_admin_sod"
        elif "excessive" in desc_lower or "too many" in desc_lower:
            return "excessive_access"

        return "generic"

    def _create_action_from_pattern(
        self,
        pattern: Dict,
        risk_id: str,
        users: List[str],
        roles: List[str],
        index: int
    ) -> RemediationAction:
        """Create an action from a pattern template"""
        action_type = pattern["action_type"]

        # Generate implementation steps based on action type
        steps = self._generate_steps(action_type, users, roles)

        # Assess impact
        impact = ImpactAssessment(
            risk_reduction=pattern["risk_reduction"],
            users_affected=len(users),
            roles_affected=len(roles),
            business_impact=self._assess_business_impact(action_type, len(users)),
            reversibility=self._assess_reversibility(action_type),
            side_effects=self._identify_side_effects(action_type, roles)
        )

        # Determine if can auto-execute
        can_auto = (
            pattern["complexity"] in [ActionComplexity.TRIVIAL, ActionComplexity.SIMPLE] and
            len(users) <= self.org_preferences.get("max_users_for_auto", 10)
        )

        return RemediationAction(
            id=f"action_{risk_id}_{index}",
            action_type=action_type,
            title=pattern["title"],
            description=pattern["description"],
            complexity=pattern["complexity"],
            priority=9 if pattern.get("recommended") else 5,
            target_user=users[0] if len(users) == 1 else None,
            target_role=roles[0] if len(roles) == 1 else None,
            impact=impact,
            steps=steps,
            prerequisites=self._identify_prerequisites(action_type),
            warnings=self._identify_warnings(action_type, users, roles),
            can_auto_execute=can_auto,
            auto_execute_command=self._get_auto_command(action_type) if can_auto else None
        )

    def _generate_generic_actions(
        self,
        risk_id: str,
        risk_type: str,
        users: List[str],
        roles: List[str]
    ) -> List[RemediationAction]:
        """Generate generic remediation actions when no pattern matches"""
        actions = []

        # Always suggest review
        actions.append(RemediationAction(
            id=f"action_{risk_id}_review",
            action_type=ActionType.SCHEDULE_REVIEW,
            title="Schedule Access Review",
            description="Initiate a targeted review of the flagged access",
            complexity=ActionComplexity.SIMPLE,
            priority=6,
            impact=ImpactAssessment(
                risk_reduction=30,
                users_affected=len(users),
                roles_affected=len(roles),
                business_impact="Minimal - review does not change access immediately",
                reversibility="Not applicable"
            ),
            steps=[
                "Create certification campaign for affected users",
                "Assign reviewers (managers or role owners)",
                "Set review deadline",
                "Track completion and remediation"
            ],
            can_auto_execute=True
        ))

        # Suggest mitigation
        actions.append(RemediationAction(
            id=f"action_{risk_id}_mitigate",
            action_type=ActionType.ADD_MITIGATION,
            title="Add Mitigating Control",
            description="Implement detective or preventive control to reduce risk",
            complexity=ActionComplexity.MODERATE,
            priority=5,
            impact=ImpactAssessment(
                risk_reduction=50,
                users_affected=len(users),
                roles_affected=0,
                business_impact="Low - users retain access with additional oversight",
                reversibility="Easy"
            ),
            steps=[
                "Identify appropriate control type",
                "Configure control in GRC system",
                "Assign control owner",
                "Document justification"
            ]
        ))

        # Suggest role modification
        if roles:
            actions.append(RemediationAction(
                id=f"action_{risk_id}_modify",
                action_type=ActionType.MODIFY_ROLE,
                title="Modify Role Design",
                description="Adjust role to remove conflicting authorizations",
                complexity=ActionComplexity.COMPLEX,
                priority=4,
                impact=ImpactAssessment(
                    risk_reduction=80,
                    users_affected=len(users),
                    roles_affected=len(roles),
                    business_impact="Medium - requires testing and change management",
                    reversibility="Moderate"
                ),
                steps=[
                    "Analyze role usage patterns",
                    "Identify transactions to remove",
                    "Test role changes in sandbox",
                    "Deploy through change management",
                    "Communicate changes to users"
                ]
            ))

        return actions

    def _generate_steps(
        self,
        action_type: ActionType,
        users: List[str],
        roles: List[str]
    ) -> List[str]:
        """Generate implementation steps for an action"""
        steps_by_type = {
            ActionType.REMOVE_ROLE: [
                f"Identify affected users ({len(users)} users)",
                "Verify business need for role",
                "Check for alternative roles that don't conflict",
                "Execute role removal in test first",
                "Deploy to production with rollback plan",
                "Notify affected users"
            ],
            ActionType.SPLIT_ROLE: [
                "Analyze current role composition",
                "Design new split role structure",
                "Create new roles in development",
                "Test with sample users",
                "Plan migration for all affected users",
                "Execute migration with rollback plan",
                "Decommission old role"
            ],
            ActionType.ADD_MITIGATION: [
                "Select appropriate mitigation control",
                "Configure control parameters",
                "Assign control owner and reviewers",
                "Document control purpose and procedures",
                "Set up monitoring/reporting",
                "Train control owner"
            ],
            ActionType.MODIFY_ROLE: [
                "Export current role definition",
                "Identify authorizations to modify",
                "Make changes in development",
                "Execute regression testing",
                "Deploy through transport",
                "Validate in production"
            ],
            ActionType.REASSIGN_TASK: [
                "Identify receiving user/team",
                "Verify capability and capacity",
                "Transfer role assignment",
                "Update process documentation",
                "Communicate to stakeholders"
            ],
            ActionType.SCHEDULE_REVIEW: [
                "Create certification campaign",
                "Define scope (users, roles)",
                "Assign reviewers",
                "Set timeline and reminders",
                "Launch campaign"
            ]
        }

        return steps_by_type.get(action_type, ["Review and take appropriate action"])

    def _assess_business_impact(self, action_type: ActionType, user_count: int) -> str:
        """Assess business impact of an action"""
        if action_type == ActionType.REMOVE_ROLE:
            if user_count > 50:
                return "High - large number of users will lose access"
            elif user_count > 10:
                return "Medium - multiple users affected"
            else:
                return "Low - limited user impact"

        elif action_type == ActionType.SPLIT_ROLE:
            return "Medium - requires process changes and retraining"

        elif action_type == ActionType.ADD_MITIGATION:
            return "Low - access unchanged, only monitoring added"

        elif action_type == ActionType.SCHEDULE_REVIEW:
            return "Minimal - no immediate access changes"

        return "Medium - case-by-case evaluation needed"

    def _assess_reversibility(self, action_type: ActionType) -> str:
        """Assess how easily an action can be reversed"""
        reversibility = {
            ActionType.REMOVE_ROLE: "Easy - role can be re-assigned",
            ActionType.SPLIT_ROLE: "Difficult - complex to merge back",
            ActionType.ADD_MITIGATION: "Easy - mitigation can be removed",
            ActionType.MODIFY_ROLE: "Moderate - requires role change transport",
            ActionType.REASSIGN_TASK: "Easy - can reassign back",
            ActionType.SCHEDULE_REVIEW: "Not applicable",
            ActionType.ACCEPT_RISK: "Easy - acceptance can be revoked"
        }
        return reversibility.get(action_type, "Unknown")

    def _identify_side_effects(self, action_type: ActionType, roles: List[str]) -> List[str]:
        """Identify potential side effects of an action"""
        effects = []

        if action_type == ActionType.REMOVE_ROLE:
            effects.append("Users may lose access to required transactions")
            effects.append("May require new role assignment")

        elif action_type == ActionType.SPLIT_ROLE:
            effects.append("Role count in system will increase")
            effects.append("May complicate future role assignments")

        elif action_type == ActionType.MODIFY_ROLE:
            effects.append("All users of role will be affected")
            effects.append("May break existing processes")

        return effects

    def _identify_prerequisites(self, action_type: ActionType) -> List[str]:
        """Identify prerequisites for an action"""
        prereqs = {
            ActionType.REMOVE_ROLE: [
                "Verify user doesn't need the access",
                "Identify alternative roles if needed"
            ],
            ActionType.SPLIT_ROLE: [
                "Role design approval",
                "Development system access",
                "Test plan"
            ],
            ActionType.MODIFY_ROLE: [
                "Development system access",
                "Change management approval"
            ]
        }
        return prereqs.get(action_type, [])

    def _identify_warnings(
        self,
        action_type: ActionType,
        users: List[str],
        roles: List[str]
    ) -> List[str]:
        """Identify warnings for an action"""
        warnings = []

        if len(users) > 100:
            warnings.append("Large number of users affected - consider phased approach")

        if action_type == ActionType.REMOVE_ROLE:
            warnings.append("Verify business need before removing access")

        if action_type == ActionType.MODIFY_ROLE:
            warnings.append("Changes affect all users of this role")

        return warnings

    def _get_auto_command(self, action_type: ActionType) -> Optional[str]:
        """Get auto-execute command if available"""
        commands = {
            ActionType.SCHEDULE_REVIEW: "create_certification_campaign",
            ActionType.ADD_MITIGATION: "assign_mitigation_control"
        }
        return commands.get(action_type)

    def _prioritize_actions(
        self,
        actions: List[RemediationAction],
        context: Dict
    ) -> List[RemediationAction]:
        """Prioritize actions based on impact and effort"""
        for action in actions:
            # Calculate priority score
            impact_score = action.impact.risk_reduction if action.impact else 50
            effort_penalty = {
                ActionComplexity.TRIVIAL: 0,
                ActionComplexity.SIMPLE: 10,
                ActionComplexity.MODERATE: 25,
                ActionComplexity.COMPLEX: 40,
                ActionComplexity.STRATEGIC: 50
            }.get(action.complexity, 20)

            # Auto-executable gets bonus
            auto_bonus = 10 if action.can_auto_execute else 0

            # Calculate final priority (1-10 scale)
            raw_priority = (impact_score - effort_penalty + auto_bonus) / 10
            action.priority = max(1, min(10, int(raw_priority)))

        # Sort by priority descending
        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions

    def _estimate_total_effort(self, actions: List[RemediationAction]) -> str:
        """Estimate total effort for recommended actions"""
        if not actions:
            return "Unknown"

        recommended = [a for a in actions if a.priority >= 7]
        if not recommended:
            return "Varies by approach selected"

        max_complexity = max(a.complexity for a in recommended)
        effort_map = {
            ActionComplexity.TRIVIAL: "Less than 1 hour",
            ActionComplexity.SIMPLE: "1-4 hours",
            ActionComplexity.MODERATE: "1-2 days",
            ActionComplexity.COMPLEX: "1-2 weeks",
            ActionComplexity.STRATEGIC: "Multi-week initiative"
        }
        return effort_map.get(max_complexity, "Unknown")

    def _generate_reasoning(
        self,
        risk_type: str,
        actions: List[RemediationAction],
        users: List[str],
        roles: List[str]
    ) -> str:
        """Generate human-readable reasoning for recommendations"""
        if not actions:
            return "No automated recommendations available. Manual review required."

        top_action = actions[0]
        reasoning = f"Recommended approach: {top_action.title}\n\n"
        reasoning += f"Reasoning:\n"
        reasoning += f"- This approach provides {top_action.impact.risk_reduction}% risk reduction\n"
        reasoning += f"- Complexity level: {top_action.complexity.value}\n"
        reasoning += f"- Affects {len(users)} user(s) and {len(roles)} role(s)\n"

        if top_action.can_auto_execute:
            reasoning += f"- Can be executed automatically with one click\n"

        if len(actions) > 1:
            reasoning += f"\n{len(actions) - 1} alternative approach(es) also available."

        return reasoning

    # ==================== Execution ====================

    def execute_action(
        self,
        action_id: str,
        executed_by: str,
        plan: RemediationPlan
    ) -> Dict[str, Any]:
        """Execute a remediation action"""
        # Find the action
        action = None
        for a in plan.recommended_actions + plan.alternatives:
            if a.id == action_id:
                action = a
                break

        if not action:
            return {"success": False, "error": "Action not found"}

        if not action.can_auto_execute:
            return {
                "success": False,
                "error": "This action requires manual execution",
                "steps": action.steps
            }

        # Record execution
        self.remediation_history.append({
            "action_id": action_id,
            "plan_id": plan.id,
            "risk_id": plan.risk_id,
            "action_type": action.action_type.value,
            "executed_by": executed_by,
            "executed_at": datetime.utcnow(),
            "status": "completed"
        })

        return {
            "success": True,
            "message": f"Action '{action.title}' executed successfully",
            "action_type": action.action_type.value,
            "risk_reduction": action.impact.risk_reduction,
            "next_steps": ["Verify remediation effectiveness", "Update documentation"]
        }

    # ==================== Quick Recommendations ====================

    def get_quick_recommendations(
        self,
        risk_type: str,
        user_count: int = 1
    ) -> List[Dict[str, Any]]:
        """Get quick recommendations without full plan generation"""
        pattern_key = self._match_risk_pattern(risk_type, risk_type)
        patterns = self.remediation_patterns.get(pattern_key, [])

        recommendations = []
        for pattern in patterns[:3]:  # Top 3
            recommendations.append({
                "action": pattern["title"],
                "description": pattern["description"],
                "complexity": pattern["complexity"].value,
                "risk_reduction": f"{pattern['risk_reduction']}%",
                "recommended": pattern.get("recommended", False)
            })

        if not recommendations:
            recommendations.append({
                "action": "Schedule Access Review",
                "description": "Initiate review of affected access",
                "complexity": "simple",
                "risk_reduction": "30%",
                "recommended": True
            })

        return recommendations
