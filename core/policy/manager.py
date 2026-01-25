"""
Policy Manager Module

Central management of policies with versioning, approvals, and audit trails.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import copy

from .models import (
    Policy, PolicyVersion, PolicyChange, PolicyTemplate,
    PolicyType, PolicyStatus, ChangeType, PolicyApproval
)


class PolicyManager:
    """
    Manages the complete policy lifecycle including versioning and approvals.

    Key features:
    - Full version history with rollback capability
    - Multi-level approval workflows
    - Audit trail of all changes
    - Policy templates for standardization
    - Scheduled effectiveness dates
    - Compliance framework mapping
    """

    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.templates: Dict[str, PolicyTemplate] = {}
        self.change_log: List[PolicyChange] = []

        # Index for efficient lookups
        self.index_by_type: Dict[PolicyType, List[str]] = defaultdict(list)
        self.index_by_owner: Dict[str, List[str]] = defaultdict(list)
        self.index_by_framework: Dict[str, List[str]] = defaultdict(list)

        # Load default templates
        self._create_default_templates()
        # Create sample policies
        self._create_sample_policies()

    def _create_default_templates(self):
        """Create standard policy templates"""

        # SoD Risk Rule Template
        sod_template = PolicyTemplate(
            template_id="sod-risk-rule",
            name="SoD Risk Rule",
            description="Template for Segregation of Duties risk rules",
            policy_type=PolicyType.RISK_RULE,
            content_schema={
                "rule_id": {"type": "string", "required": True},
                "rule_name": {"type": "string", "required": True},
                "description": {"type": "string", "required": True},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "function_1": {"type": "object", "required": True},
                "function_2": {"type": "object", "required": True},
                "business_process": {"type": "string"},
                "remediation": {"type": "string"}
            },
            default_content={
                "severity": "high",
                "is_active": True,
                "function_1": {"permissions": []},
                "function_2": {"permissions": []}
            },
            required_fields=["rule_id", "rule_name", "function_1", "function_2"],
            example_content={
                "rule_id": "SOD-P2P-001",
                "rule_name": "Vendor Creation vs Payment",
                "description": "Segregation between vendor master creation and payment processing",
                "severity": "critical",
                "business_process": "Procure to Pay",
                "function_1": {
                    "name": "Vendor Creation",
                    "permissions": [
                        {"auth_object": "S_TCODE", "field": "TCD", "values": ["XK01", "FK01"]}
                    ]
                },
                "function_2": {
                    "name": "Payment Processing",
                    "permissions": [
                        {"auth_object": "S_TCODE", "field": "TCD", "values": ["F110", "FB10"]}
                    ]
                },
                "remediation": "Separate vendor creation and payment roles"
            }
        )
        self.templates["sod-risk-rule"] = sod_template

        # Approval Policy Template
        approval_template = PolicyTemplate(
            template_id="approval-workflow",
            name="Approval Workflow Policy",
            description="Template for access request approval routing",
            policy_type=PolicyType.APPROVAL_POLICY,
            content_schema={
                "workflow_name": {"type": "string", "required": True},
                "trigger_conditions": {"type": "array"},
                "approval_levels": {"type": "array", "required": True},
                "sla_hours": {"type": "integer"},
                "escalation_rules": {"type": "array"}
            },
            default_content={
                "sla_hours": 48,
                "approval_levels": [
                    {"level": 1, "type": "manager", "required": True}
                ]
            },
            required_fields=["workflow_name", "approval_levels"]
        )
        self.templates["approval-workflow"] = approval_template

        # Firefighter Policy Template
        ff_template = PolicyTemplate(
            template_id="firefighter-policy",
            name="Firefighter/Emergency Access Policy",
            description="Template for emergency access policies",
            policy_type=PolicyType.FIREFIGHTER_POLICY,
            content_schema={
                "policy_name": {"type": "string", "required": True},
                "max_duration_hours": {"type": "integer"},
                "requires_dual_approval": {"type": "boolean"},
                "review_required": {"type": "boolean"},
                "allowed_systems": {"type": "array"},
                "allowed_firefighter_ids": {"type": "array"}
            },
            default_content={
                "max_duration_hours": 4,
                "requires_dual_approval": True,
                "review_required": True,
                "auto_revoke_on_timeout": True
            }
        )
        self.templates["firefighter-policy"] = ff_template

    def _create_sample_policies(self):
        """Create sample policies for demonstration"""

        # Sample SoD Risk Policy
        sod_policy = Policy(
            policy_id="POL-SOD-001",
            name="Procure to Pay SoD Rules",
            description="Segregation of Duties rules for the Procure to Pay business process",
            policy_type=PolicyType.RISK_RULE,
            category="Financial Controls",
            tags=["P2P", "procurement", "finance", "SOX"],
            scope={"business_process": "Procure to Pay", "systems": ["SAP"]},
            owner_id="security.admin@company.com",
            owner_name="Security Administrator",
            owner_department="IT Security",
            requires_approval=True,
            required_approver_count=2,
            allowed_approvers=["ciso@company.com", "cfo@company.com", "internal.audit@company.com"],
            compliance_frameworks=["SOX", "ISO27001"],
            control_ids=["CTRL-FIN-001", "CTRL-FIN-002"],
            next_review_date=datetime.now() + timedelta(days=90)
        )

        # Add initial version
        sod_version = PolicyVersion(
            policy_id=sod_policy.policy_id,
            version_number=1,
            version_label="1.0",
            content={
                "rules": [
                    {
                        "rule_id": "SOD-P2P-001",
                        "name": "Vendor Creation vs Payment",
                        "severity": "critical",
                        "function_1": {"name": "Vendor Creation", "tcodes": ["XK01", "FK01"]},
                        "function_2": {"name": "Payment Processing", "tcodes": ["F110", "FB10"]}
                    },
                    {
                        "rule_id": "SOD-P2P-002",
                        "name": "PO Creation vs Goods Receipt",
                        "severity": "high",
                        "function_1": {"name": "PO Creation", "tcodes": ["ME21N", "ME22N"]},
                        "function_2": {"name": "Goods Receipt", "tcodes": ["MIGO", "MB01"]}
                    }
                ],
                "enforcement_mode": "detect_and_block",
                "exception_process": "Requires VP approval"
            },
            status=PolicyStatus.ACTIVE,
            created_by="security.admin@company.com",
            change_type=ChangeType.CREATE,
            change_summary="Initial P2P SoD rule set",
            effective_from=datetime.now() - timedelta(days=30)
        )
        sod_version.approvals = [
            PolicyApproval(
                approver_id="ciso@company.com",
                approver_name="CISO",
                action="approve",
                comments="Approved for immediate deployment"
            ),
            PolicyApproval(
                approver_id="cfo@company.com",
                approver_name="CFO",
                action="approve",
                comments="Approved"
            )
        ]

        sod_policy.versions.append(sod_version)
        sod_policy.current_version_id = sod_version.version_id

        self.policies[sod_policy.policy_id] = sod_policy
        self._update_indexes(sod_policy)

        # Sample Emergency Access Policy
        ff_policy = Policy(
            policy_id="POL-FF-001",
            name="Emergency Access Policy",
            description="Controls for firefighter/emergency access usage",
            policy_type=PolicyType.FIREFIGHTER_POLICY,
            category="Emergency Access",
            tags=["firefighter", "emergency", "privileged_access"],
            owner_id="security.admin@company.com",
            owner_name="Security Administrator",
            compliance_frameworks=["SOX", "PCI-DSS"],
            next_review_date=datetime.now() + timedelta(days=180)
        )

        ff_version = PolicyVersion(
            policy_id=ff_policy.policy_id,
            version_number=1,
            version_label="1.0",
            content={
                "max_session_duration_hours": 4,
                "max_extensions": 2,
                "requires_dual_approval": True,
                "mandatory_post_review": True,
                "review_sla_hours": 48,
                "allowed_systems": ["SAP_PROD", "SAP_QA"],
                "restricted_tcodes": ["SE38", "SA38", "SM59"],
                "activity_logging": "comprehensive",
                "real_time_monitoring": True
            },
            status=PolicyStatus.ACTIVE,
            created_by="security.admin@company.com",
            change_type=ChangeType.CREATE,
            change_summary="Initial emergency access policy",
            effective_from=datetime.now() - timedelta(days=60)
        )

        ff_policy.versions.append(ff_version)
        ff_policy.current_version_id = ff_version.version_id

        self.policies[ff_policy.policy_id] = ff_policy
        self._update_indexes(ff_policy)

    def _update_indexes(self, policy: Policy):
        """Update lookup indexes for a policy"""
        # By type
        if policy.policy_id not in self.index_by_type[policy.policy_type]:
            self.index_by_type[policy.policy_type].append(policy.policy_id)

        # By owner
        if policy.owner_id:
            if policy.policy_id not in self.index_by_owner[policy.owner_id]:
                self.index_by_owner[policy.owner_id].append(policy.policy_id)

        # By compliance framework
        for framework in policy.compliance_frameworks:
            if policy.policy_id not in self.index_by_framework[framework]:
                self.index_by_framework[framework].append(policy.policy_id)

    def create_policy(
        self,
        name: str,
        description: str,
        policy_type: PolicyType,
        owner_id: str,
        owner_name: str,
        initial_content: Dict[str, Any],
        category: str = "",
        tags: List[str] = None,
        scope: Dict = None,
        requires_approval: bool = True,
        required_approver_count: int = 1,
        allowed_approvers: List[str] = None,
        compliance_frameworks: List[str] = None,
        effective_from: datetime = None
    ) -> Policy:
        """
        Create a new policy with initial version.
        """
        policy = Policy(
            name=name,
            description=description,
            policy_type=policy_type,
            category=category,
            tags=tags or [],
            scope=scope or {},
            owner_id=owner_id,
            owner_name=owner_name,
            requires_approval=requires_approval,
            required_approver_count=required_approver_count,
            allowed_approvers=allowed_approvers or [],
            compliance_frameworks=compliance_frameworks or [],
            next_review_date=datetime.now() + timedelta(days=365)  # Annual review default
        )

        # Create initial version
        version = PolicyVersion(
            policy_id=policy.policy_id,
            version_number=1,
            version_label="1.0-draft",
            content=initial_content,
            status=PolicyStatus.DRAFT if requires_approval else PolicyStatus.ACTIVE,
            created_by=owner_id,
            change_type=ChangeType.CREATE,
            change_summary="Initial policy creation",
            effective_from=effective_from,
            required_approvers=allowed_approvers[:required_approver_count] if allowed_approvers else []
        )

        policy.versions.append(version)
        policy.current_version_id = version.version_id

        self.policies[policy.policy_id] = policy
        self._update_indexes(policy)

        # Log the change
        self._log_change(
            policy_id=policy.policy_id,
            version_id=version.version_id,
            change_type=ChangeType.CREATE,
            changed_by=owner_id,
            new_content=initial_content,
            change_summary="Policy created"
        )

        return policy

    def create_new_version(
        self,
        policy_id: str,
        new_content: Dict[str, Any],
        created_by: str,
        change_summary: str,
        reason: str = "",
        effective_from: datetime = None
    ) -> PolicyVersion:
        """
        Create a new version of an existing policy.
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        current = policy.get_current_version()
        previous_content = current.content if current else None

        # Create new version
        new_version_num = policy.get_next_version_number()
        version = PolicyVersion(
            policy_id=policy_id,
            version_number=new_version_num,
            version_label=f"{new_version_num}.0-draft",
            content=new_content,
            status=PolicyStatus.DRAFT,
            created_by=created_by,
            change_type=ChangeType.UPDATE,
            change_summary=change_summary,
            effective_from=effective_from,
            required_approvers=policy.allowed_approvers[:policy.required_approver_count]
            if policy.allowed_approvers else []
        )

        policy.versions.append(version)
        policy.last_modified = datetime.now()

        # Log the change
        self._log_change(
            policy_id=policy_id,
            version_id=version.version_id,
            change_type=ChangeType.UPDATE,
            changed_by=created_by,
            previous_content=previous_content,
            new_content=new_content,
            change_summary=change_summary,
            reason=reason
        )

        return version

    def submit_for_approval(self, policy_id: str, version_id: str, submitter_id: str) -> PolicyVersion:
        """
        Submit a policy version for approval.
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        version = policy.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        if version.status != PolicyStatus.DRAFT:
            raise ValueError(f"Only draft versions can be submitted for approval")

        version.status = PolicyStatus.PENDING_APPROVAL

        self._log_change(
            policy_id=policy_id,
            version_id=version_id,
            change_type=ChangeType.UPDATE,
            changed_by=submitter_id,
            change_summary="Submitted for approval"
        )

        return version

    def approve_version(
        self,
        policy_id: str,
        version_id: str,
        approver_id: str,
        approver_name: str,
        comments: str = ""
    ) -> PolicyVersion:
        """
        Approve a policy version.
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        version = policy.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        if version.status not in [PolicyStatus.PENDING_APPROVAL, PolicyStatus.PENDING_REVIEW]:
            raise ValueError(f"Version is not pending approval")

        # Check if approver is authorized
        if policy.allowed_approvers and approver_id not in policy.allowed_approvers:
            raise PermissionError(f"User {approver_id} is not an authorized approver")

        # Record approval
        approval = PolicyApproval(
            approver_id=approver_id,
            approver_name=approver_name,
            action="approve",
            comments=comments
        )
        version.approvals.append(approval)

        # Check if fully approved
        if version.is_fully_approved():
            version.status = PolicyStatus.APPROVED
            version.version_label = version.version_label.replace("-draft", "")

        self._log_change(
            policy_id=policy_id,
            version_id=version_id,
            change_type=ChangeType.UPDATE,
            changed_by=approver_id,
            change_summary=f"Approved by {approver_name}"
        )

        return version

    def reject_version(
        self,
        policy_id: str,
        version_id: str,
        rejector_id: str,
        rejector_name: str,
        reason: str
    ) -> PolicyVersion:
        """
        Reject a policy version.
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        version = policy.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        # Record rejection
        rejection = PolicyApproval(
            approver_id=rejector_id,
            approver_name=rejector_name,
            action="reject",
            comments=reason
        )
        version.approvals.append(rejection)
        version.status = PolicyStatus.DRAFT  # Return to draft

        self._log_change(
            policy_id=policy_id,
            version_id=version_id,
            change_type=ChangeType.UPDATE,
            changed_by=rejector_id,
            change_summary=f"Rejected: {reason}"
        )

        return version

    def activate_version(
        self,
        policy_id: str,
        version_id: str,
        activated_by: str,
        effective_from: datetime = None
    ) -> PolicyVersion:
        """
        Activate an approved policy version.
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        version = policy.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        if version.status != PolicyStatus.APPROVED:
            raise ValueError(f"Only approved versions can be activated")

        # Deprecate current active version
        current = policy.get_current_version()
        if current and current.version_id != version_id and current.status == PolicyStatus.ACTIVE:
            current.status = PolicyStatus.DEPRECATED
            current.effective_to = datetime.now()

        # Activate new version
        version.status = PolicyStatus.ACTIVE
        version.effective_from = effective_from or datetime.now()
        policy.current_version_id = version_id
        policy.last_modified = datetime.now()

        self._log_change(
            policy_id=policy_id,
            version_id=version_id,
            change_type=ChangeType.ACTIVATE,
            changed_by=activated_by,
            change_summary=f"Policy version activated"
        )

        return version

    def rollback_to_version(
        self,
        policy_id: str,
        target_version_id: str,
        rolled_back_by: str,
        reason: str
    ) -> PolicyVersion:
        """
        Roll back to a previous policy version.

        Creates a new version with the content from the target version.
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        target_version = policy.get_version(target_version_id)
        if not target_version:
            raise ValueError(f"Version {target_version_id} not found")

        # Create new version with target's content
        new_version = self.create_new_version(
            policy_id=policy_id,
            new_content=copy.deepcopy(target_version.content),
            created_by=rolled_back_by,
            change_summary=f"Rollback to version {target_version.version_label}",
            reason=reason
        )
        new_version.change_type = ChangeType.ROLLBACK

        self._log_change(
            policy_id=policy_id,
            version_id=new_version.version_id,
            change_type=ChangeType.ROLLBACK,
            changed_by=rolled_back_by,
            change_summary=f"Rolled back to version {target_version.version_label}",
            reason=reason
        )

        return new_version

    def deprecate_policy(self, policy_id: str, deprecated_by: str, reason: str):
        """
        Deprecate a policy (soft delete, keeps history).
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        current = policy.get_current_version()
        if current:
            current.status = PolicyStatus.DEPRECATED
            current.effective_to = datetime.now()

        self._log_change(
            policy_id=policy_id,
            version_id=current.version_id if current else "",
            change_type=ChangeType.DEPRECATE,
            changed_by=deprecated_by,
            change_summary=f"Policy deprecated",
            reason=reason
        )

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID"""
        return self.policies.get(policy_id)

    def get_policies(
        self,
        policy_type: PolicyType = None,
        owner_id: str = None,
        framework: str = None,
        status: PolicyStatus = None,
        include_deprecated: bool = False
    ) -> List[Policy]:
        """
        Get policies with filters.
        """
        results = []

        # Start with type filter if specified
        if policy_type:
            policy_ids = self.index_by_type.get(policy_type, [])
        elif owner_id:
            policy_ids = self.index_by_owner.get(owner_id, [])
        elif framework:
            policy_ids = self.index_by_framework.get(framework, [])
        else:
            policy_ids = list(self.policies.keys())

        for pid in policy_ids:
            policy = self.policies.get(pid)
            if not policy:
                continue

            current = policy.get_current_version()

            # Apply status filter
            if status and current and current.status != status:
                continue

            # Filter deprecated unless requested
            if not include_deprecated:
                if current and current.status in [PolicyStatus.DEPRECATED, PolicyStatus.RETIRED]:
                    continue

            results.append(policy)

        return results

    def get_pending_approvals(self, approver_id: str = None) -> List[Dict]:
        """
        Get policy versions pending approval.
        """
        pending = []

        for policy in self.policies.values():
            for version in policy.versions:
                if version.status != PolicyStatus.PENDING_APPROVAL:
                    continue

                # Check if approver is authorized and hasn't already acted
                if approver_id:
                    if policy.allowed_approvers and approver_id not in policy.allowed_approvers:
                        continue
                    if any(a.approver_id == approver_id for a in version.approvals):
                        continue

                pending.append({
                    "policy_id": policy.policy_id,
                    "policy_name": policy.name,
                    "version_id": version.version_id,
                    "version_label": version.version_label,
                    "change_summary": version.change_summary,
                    "submitted_by": version.created_by,
                    "submitted_at": version.created_at.isoformat(),
                    "approvals_received": len([a for a in version.approvals if a.action == "approve"]),
                    "approvals_required": len(version.required_approvers)
                })

        return pending

    def get_change_history(
        self,
        policy_id: str = None,
        changed_by: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[PolicyChange]:
        """
        Get policy change history with filters.
        """
        results = []

        for change in self.change_log:
            if policy_id and change.policy_id != policy_id:
                continue
            if changed_by and change.changed_by != changed_by:
                continue
            if start_date and change.changed_at < start_date:
                continue
            if end_date and change.changed_at > end_date:
                continue

            results.append(change)

            if len(results) >= limit:
                break

        return results

    def compare_versions(self, policy_id: str, version_id_1: str, version_id_2: str) -> Dict:
        """
        Compare two versions of a policy.
        """
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        v1 = policy.get_version(version_id_1)
        v2 = policy.get_version(version_id_2)

        if not v1 or not v2:
            raise ValueError("One or both versions not found")

        # Find differences in content
        def find_diff(d1: Dict, d2: Dict, path: str = "") -> List[Dict]:
            diffs = []
            all_keys = set(d1.keys()) | set(d2.keys())

            for key in all_keys:
                current_path = f"{path}.{key}" if path else key
                val1 = d1.get(key)
                val2 = d2.get(key)

                if key not in d1:
                    diffs.append({"path": current_path, "type": "added", "new_value": val2})
                elif key not in d2:
                    diffs.append({"path": current_path, "type": "removed", "old_value": val1})
                elif val1 != val2:
                    if isinstance(val1, dict) and isinstance(val2, dict):
                        diffs.extend(find_diff(val1, val2, current_path))
                    else:
                        diffs.append({
                            "path": current_path,
                            "type": "modified",
                            "old_value": val1,
                            "new_value": val2
                        })

            return diffs

        differences = find_diff(v1.content, v2.content)

        return {
            "policy_id": policy_id,
            "version_1": {"id": v1.version_id, "label": v1.version_label},
            "version_2": {"id": v2.version_id, "label": v2.version_label},
            "differences": differences,
            "difference_count": len(differences)
        }

    def _log_change(
        self,
        policy_id: str,
        version_id: str,
        change_type: ChangeType,
        changed_by: str,
        previous_content: Dict = None,
        new_content: Dict = None,
        change_summary: str = "",
        reason: str = ""
    ):
        """Record a change in the audit log"""
        change = PolicyChange(
            policy_id=policy_id,
            version_id=version_id,
            change_type=change_type,
            changed_by=changed_by,
            previous_content=previous_content,
            new_content=new_content,
            change_summary=change_summary,
            reason=reason
        )
        self.change_log.append(change)

    def get_templates(self, policy_type: PolicyType = None) -> List[PolicyTemplate]:
        """Get available policy templates"""
        results = []
        for template in self.templates.values():
            if policy_type and template.policy_type != policy_type:
                continue
            results.append(template)
        return results

    def get_template(self, template_id: str) -> Optional[PolicyTemplate]:
        """Get a specific template"""
        return self.templates.get(template_id)

    def create_policy_from_template(
        self,
        template_id: str,
        name: str,
        owner_id: str,
        owner_name: str,
        content_overrides: Dict = None,
        **kwargs
    ) -> Policy:
        """
        Create a policy from a template with optional overrides.
        """
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Merge default content with overrides
        content = copy.deepcopy(template.default_content)
        if content_overrides:
            content.update(content_overrides)

        # Validate required fields
        for field in template.required_fields:
            if field not in content:
                raise ValueError(f"Required field '{field}' missing from content")

        return self.create_policy(
            name=name,
            description=kwargs.get("description", template.description),
            policy_type=template.policy_type,
            owner_id=owner_id,
            owner_name=owner_name,
            initial_content=content,
            **{k: v for k, v in kwargs.items() if k != "description"}
        )

    def get_statistics(self) -> Dict:
        """Get policy management statistics"""
        by_type = defaultdict(int)
        by_status = defaultdict(int)
        pending_review = 0
        overdue_review = 0

        for policy in self.policies.values():
            by_type[policy.policy_type.value] += 1

            current = policy.get_current_version()
            if current:
                by_status[current.status.value] += 1

            if policy.is_review_overdue():
                overdue_review += 1

        pending_approvals = len(self.get_pending_approvals())

        return {
            "total_policies": len(self.policies),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "pending_approvals": pending_approvals,
            "overdue_reviews": overdue_review,
            "total_versions": sum(len(p.versions) for p in self.policies.values()),
            "templates_available": len(self.templates)
        }
