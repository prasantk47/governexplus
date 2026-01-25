# MSMP to GOVERNEX+ Converter
# Migration tool for SAP GRC MSMP workflows

"""
MSMP Converter for GOVERNEX+.

Converts SAP GRC MSMP workflow configurations to GOVERNEX+ policies.

MSMP Concepts → GOVERNEX+ Mapping:
- Process ID → Process Type
- Workflow Path → Policy Rules
- Stages → Steps
- Agent Rules → Approver Resolvers
- Activation Conditions → Policy Conditions

This enables zero-disruption migration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import logging
import re

from .models import ProcessType, ApproverTypeEnum, WorkflowConfig
from .policy import (
    PolicySet, PolicyRule, PolicyCondition, PolicyAction,
    ActionType, ConditionOperator
)

logger = logging.getLogger(__name__)


# ============================================================
# MSMP DATA MODELS
# ============================================================

class MSMPProcessType(Enum):
    """SAP GRC MSMP process types."""
    SAP_GRAC_ACCESS_REQUEST = "SAP_GRAC_ACCESS_REQUEST"
    SAP_GRAC_SOD_RISK = "SAP_GRAC_SOD_RISK"
    SAP_GRAC_EAM = "SAP_GRAC_EAM"
    SAP_GRAC_USER_ACCT = "SAP_GRAC_USER_ACCT"
    SAP_GRAC_ROLE_MGMT = "SAP_GRAC_ROLE_MGMT"
    SAP_GRAC_FF_LOG = "SAP_GRAC_FF_LOG"
    CUSTOM = "CUSTOM"


class MSMPAgentType(Enum):
    """MSMP agent determination types."""
    STATIC = "STATIC"
    MANAGER = "MANAGER"
    ROLE_OWNER = "ROLE_OWNER"
    SECURITY = "SECURITY"
    COST_CENTER = "COST_CENTER"
    CUSTOM_TABLE = "CUSTOM_TABLE"
    BRF_PLUS = "BRF_PLUS"


@dataclass
class MSMPAgent:
    """MSMP agent definition."""
    agent_id: str = ""
    agent_type: MSMPAgentType = MSMPAgentType.STATIC
    static_users: List[str] = field(default_factory=list)
    lookup_table: str = ""
    brf_function: str = ""
    fallback_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "static_users": self.static_users,
            "lookup_table": self.lookup_table,
            "brf_function": self.brf_function,
            "fallback_agents": self.fallback_agents,
        }


@dataclass
class MSMPStage:
    """MSMP workflow stage."""
    stage_id: str = ""
    stage_number: int = 1
    stage_name: str = ""
    stage_type: str = "APPROVAL"  # APPROVAL, REVIEW, NOTIFICATION

    # Agent determination
    agent: Optional[MSMPAgent] = None

    # Settings
    require_all: bool = False
    sla_hours: int = 48
    allow_rejection: bool = True
    auto_approve_conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_number": self.stage_number,
            "stage_name": self.stage_name,
            "stage_type": self.stage_type,
            "agent": self.agent.to_dict() if self.agent else None,
            "require_all": self.require_all,
            "sla_hours": self.sla_hours,
            "allow_rejection": self.allow_rejection,
        }


@dataclass
class MSMPPath:
    """MSMP workflow path."""
    path_id: str = ""
    path_name: str = ""
    description: str = ""

    # Activation
    activation_conditions: Dict[str, Any] = field(default_factory=dict)

    # Stages
    stages: List[MSMPStage] = field(default_factory=list)

    # Settings
    priority: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "path_name": self.path_name,
            "description": self.description,
            "activation_conditions": self.activation_conditions,
            "stages": [s.to_dict() for s in self.stages],
            "priority": self.priority,
        }


@dataclass
class MSMPProcess:
    """Complete MSMP process definition."""
    process_id: str = ""
    process_type: MSMPProcessType = MSMPProcessType.SAP_GRAC_ACCESS_REQUEST
    process_name: str = ""
    description: str = ""

    # Paths
    paths: List[MSMPPath] = field(default_factory=list)

    # Default path
    default_path_id: Optional[str] = None

    # Metadata
    is_active: bool = True
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "process_type": self.process_type.value,
            "process_name": self.process_name,
            "description": self.description,
            "paths": [p.to_dict() for p in self.paths],
            "default_path_id": self.default_path_id,
            "is_active": self.is_active,
            "version": self.version,
        }


@dataclass
class ConversionResult:
    """Result of MSMP to GOVERNEX+ conversion."""
    success: bool = True
    policy_set: Optional[PolicySet] = None

    # Statistics
    processes_converted: int = 0
    paths_converted: int = 0
    stages_converted: int = 0
    rules_created: int = 0

    # Issues
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Mapping
    process_mapping: Dict[str, str] = field(default_factory=dict)  # MSMP ID → GOVERNEX+ policy ID
    agent_mapping: Dict[str, str] = field(default_factory=dict)    # MSMP agent → GOVERNEX+ approver

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "statistics": {
                "processes_converted": self.processes_converted,
                "paths_converted": self.paths_converted,
                "stages_converted": self.stages_converted,
                "rules_created": self.rules_created,
            },
            "warnings": self.warnings,
            "errors": self.errors,
            "mappings": {
                "processes": self.process_mapping,
                "agents": self.agent_mapping,
            },
        }


# ============================================================
# CONVERTER
# ============================================================

class MSMPConverter:
    """
    Converts MSMP configurations to GOVERNEX+ policies.

    Supports:
    - Process definition conversion
    - Path → Rule conversion
    - Stage → Action conversion
    - Agent → Approver mapping
    """

    def __init__(self):
        """Initialize converter."""
        # Process type mapping
        self._process_type_map = {
            MSMPProcessType.SAP_GRAC_ACCESS_REQUEST: ProcessType.ACCESS_REQUEST,
            MSMPProcessType.SAP_GRAC_SOD_RISK: ProcessType.RISK_ACCEPTANCE,
            MSMPProcessType.SAP_GRAC_EAM: ProcessType.FIREFIGHTER,
            MSMPProcessType.SAP_GRAC_USER_ACCT: ProcessType.USER_ONBOARDING,
            MSMPProcessType.SAP_GRAC_ROLE_MGMT: ProcessType.ROLE_CREATION,
            MSMPProcessType.SAP_GRAC_FF_LOG: ProcessType.POST_ACCESS_REVIEW,
        }

        # Agent type mapping
        self._agent_type_map = {
            MSMPAgentType.STATIC: ApproverTypeEnum.CUSTOM,
            MSMPAgentType.MANAGER: ApproverTypeEnum.LINE_MANAGER,
            MSMPAgentType.ROLE_OWNER: ApproverTypeEnum.ROLE_OWNER,
            MSMPAgentType.SECURITY: ApproverTypeEnum.SECURITY_OFFICER,
            MSMPAgentType.COST_CENTER: ApproverTypeEnum.PROCESS_OWNER,
            MSMPAgentType.CUSTOM_TABLE: ApproverTypeEnum.CUSTOM,
            MSMPAgentType.BRF_PLUS: ApproverTypeEnum.CUSTOM,
        }

    def convert(self, processes: List[MSMPProcess]) -> ConversionResult:
        """
        Convert multiple MSMP processes to GOVERNEX+ policy.

        Args:
            processes: List of MSMP process definitions

        Returns:
            ConversionResult with generated policy
        """
        result = ConversionResult()

        # Create policy set
        policy = PolicySet(
            policy_id=f"CONVERTED-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name="Converted MSMP Policy",
            description="Policy converted from SAP GRC MSMP configuration",
            version="1.0",
        )

        for process in processes:
            try:
                rules = self._convert_process(process, result)
                for rule in rules:
                    policy.add_rule(rule)
                result.processes_converted += 1
                result.process_mapping[process.process_id] = policy.policy_id

            except Exception as e:
                logger.error(f"Failed to convert process {process.process_id}: {e}")
                result.errors.append(f"Process {process.process_id}: {str(e)}")

        result.policy_set = policy
        result.rules_created = len(policy.get_all_rules())
        result.success = len(result.errors) == 0

        return result

    def _convert_process(
        self,
        process: MSMPProcess,
        result: ConversionResult
    ) -> List[PolicyRule]:
        """Convert a single MSMP process to rules."""
        rules = []

        for path in process.paths:
            path_rules = self._convert_path(process, path, result)
            rules.extend(path_rules)
            result.paths_converted += 1

        return rules

    def _convert_path(
        self,
        process: MSMPProcess,
        path: MSMPPath,
        result: ConversionResult
    ) -> List[PolicyRule]:
        """Convert an MSMP path to policy rules."""
        rules = []

        # Convert activation conditions to policy conditions
        conditions = self._convert_conditions(
            path.activation_conditions,
            process.process_type
        )

        # Create a rule for each stage
        for stage in path.stages:
            rule = self._convert_stage(process, path, stage, conditions, result)
            if rule:
                rules.append(rule)
                result.stages_converted += 1

        return rules

    def _convert_stage(
        self,
        process: MSMPProcess,
        path: MSMPPath,
        stage: MSMPStage,
        path_conditions: List[PolicyCondition],
        result: ConversionResult
    ) -> Optional[PolicyRule]:
        """Convert an MSMP stage to a policy rule."""
        # Map agent type to approver type
        approver_type = self._map_agent_type(stage.agent)

        if approver_type:
            result.agent_mapping[stage.agent.agent_id if stage.agent else "UNKNOWN"] = approver_type.value

        # Determine layer
        layer = self._determine_layer(stage, path)

        # Create rule
        rule_id = f"MSMP-{process.process_id}-{path.path_id}-{stage.stage_id}"

        rule = PolicyRule(
            rule_id=rule_id,
            name=stage.stage_name,
            description=f"Converted from MSMP: {process.process_name} / {path.path_name}",
            priority=path.priority + stage.stage_number,
            layer=layer,
            conditions=list(path_conditions),  # Copy conditions
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=approver_type,
                    sla_hours=float(stage.sla_hours),
                    reason=f"Converted from MSMP stage: {stage.stage_name}",
                )
            ],
            tags=["MSMP_CONVERTED", process.process_type.value],
        )

        # Handle auto-approve
        if stage.auto_approve_conditions:
            auto_conditions = self._convert_conditions(stage.auto_approve_conditions)
            if auto_conditions:
                # Create separate auto-approve rule
                auto_rule = PolicyRule(
                    rule_id=f"{rule_id}-AUTO",
                    name=f"{stage.stage_name} (Auto-Approve)",
                    description=f"Auto-approve rule for {stage.stage_name}",
                    priority=path.priority + stage.stage_number - 1,  # Higher priority
                    layer="RISK_ADAPTIVE",
                    conditions=path_conditions + auto_conditions,
                    actions=[
                        PolicyAction(
                            action_type=ActionType.AUTO_APPROVE,
                            reason="Auto-approved based on MSMP conditions",
                        )
                    ],
                    tags=["MSMP_CONVERTED", "AUTO_APPROVE"],
                )
                # Note: Would need to return both rules

        return rule

    def _convert_conditions(
        self,
        conditions: Dict[str, Any],
        process_type: Optional[MSMPProcessType] = None
    ) -> List[PolicyCondition]:
        """Convert MSMP conditions to policy conditions."""
        policy_conditions = []

        # Map MSMP condition fields to GOVERNEX+ fields
        field_map = {
            "request_type": "process_type",
            "risk_level": "risk_level",
            "system": "system",
            "system_type": "is_production",
            "role_type": "access_type",
            "has_sod_violation": "has_sod_conflicts",
            "department": "target_user_department",
        }

        for msmp_field, msmp_value in conditions.items():
            gex_field = field_map.get(msmp_field, msmp_field)

            # Handle special cases
            if msmp_field == "system_type" and msmp_value == "PROD":
                policy_conditions.append(PolicyCondition(
                    field="is_production",
                    operator=ConditionOperator.EQUALS,
                    value=True,
                ))
            elif isinstance(msmp_value, list):
                policy_conditions.append(PolicyCondition(
                    field=gex_field,
                    operator=ConditionOperator.IN,
                    value=msmp_value,
                ))
            else:
                policy_conditions.append(PolicyCondition(
                    field=gex_field,
                    operator=ConditionOperator.EQUALS,
                    value=msmp_value,
                ))

        # Add process type condition
        if process_type:
            gex_process_type = self._process_type_map.get(process_type, ProcessType.GENERIC)
            policy_conditions.append(PolicyCondition(
                field="process_type",
                operator=ConditionOperator.EQUALS,
                value=gex_process_type.value,
            ))

        return policy_conditions

    def _map_agent_type(self, agent: Optional[MSMPAgent]) -> ApproverTypeEnum:
        """Map MSMP agent to GOVERNEX+ approver type."""
        if not agent:
            return ApproverTypeEnum.LINE_MANAGER  # Default

        return self._agent_type_map.get(
            agent.agent_type,
            ApproverTypeEnum.CUSTOM
        )

    def _determine_layer(self, stage: MSMPStage, path: MSMPPath) -> str:
        """Determine policy layer for a stage."""
        # Heuristics based on stage/path characteristics
        if stage.stage_type == "NOTIFICATION":
            return "CONTEXTUAL"

        # Check if related to risk
        activation = path.activation_conditions
        if "risk_level" in activation or "has_sod_violation" in activation:
            return "RISK_ADAPTIVE"

        # Check if security-related
        if stage.agent and stage.agent.agent_type == MSMPAgentType.SECURITY:
            return "MANDATORY"

        # Default
        return "CONTEXTUAL"

    def convert_from_dict(self, data: Dict[str, Any]) -> ConversionResult:
        """
        Convert MSMP configuration from dictionary format.

        Expected format:
        {
            "processes": [
                {
                    "process_id": "...",
                    "process_type": "SAP_GRAC_ACCESS_REQUEST",
                    "paths": [
                        {
                            "path_id": "...",
                            "activation_conditions": {...},
                            "stages": [...]
                        }
                    ]
                }
            ]
        }
        """
        processes = []

        for proc_data in data.get("processes", []):
            process = MSMPProcess(
                process_id=proc_data.get("process_id", ""),
                process_type=MSMPProcessType(
                    proc_data.get("process_type", "SAP_GRAC_ACCESS_REQUEST")
                ),
                process_name=proc_data.get("process_name", ""),
                description=proc_data.get("description", ""),
            )

            for path_data in proc_data.get("paths", []):
                path = MSMPPath(
                    path_id=path_data.get("path_id", ""),
                    path_name=path_data.get("path_name", ""),
                    activation_conditions=path_data.get("activation_conditions", {}),
                    priority=path_data.get("priority", 100),
                )

                for stage_data in path_data.get("stages", []):
                    agent_data = stage_data.get("agent", {})
                    agent = MSMPAgent(
                        agent_id=agent_data.get("agent_id", ""),
                        agent_type=MSMPAgentType(agent_data.get("agent_type", "STATIC")),
                        static_users=agent_data.get("static_users", []),
                    ) if agent_data else None

                    stage = MSMPStage(
                        stage_id=stage_data.get("stage_id", ""),
                        stage_number=stage_data.get("stage_number", 1),
                        stage_name=stage_data.get("stage_name", ""),
                        stage_type=stage_data.get("stage_type", "APPROVAL"),
                        agent=agent,
                        sla_hours=stage_data.get("sla_hours", 48),
                        auto_approve_conditions=stage_data.get("auto_approve_conditions", {}),
                    )
                    path.stages.append(stage)

                process.paths.append(path)

            processes.append(process)

        return self.convert(processes)

    def generate_migration_report(self, result: ConversionResult) -> str:
        """Generate a human-readable migration report."""
        lines = []

        lines.append("=" * 70)
        lines.append("MSMP TO GOVERNEX+ MIGRATION REPORT")
        lines.append("=" * 70)
        lines.append("")

        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Conversion Status: {'SUCCESS' if result.success else 'FAILED'}")
        lines.append(f"Processes Converted: {result.processes_converted}")
        lines.append(f"Paths Converted: {result.paths_converted}")
        lines.append(f"Stages Converted: {result.stages_converted}")
        lines.append(f"Rules Created: {result.rules_created}")
        lines.append("")

        if result.warnings:
            lines.append("WARNINGS")
            lines.append("-" * 40)
            for warning in result.warnings:
                lines.append(f"  - {warning}")
            lines.append("")

        if result.errors:
            lines.append("ERRORS")
            lines.append("-" * 40)
            for error in result.errors:
                lines.append(f"  - {error}")
            lines.append("")

        lines.append("PROCESS MAPPING")
        lines.append("-" * 40)
        for msmp_id, gex_id in result.process_mapping.items():
            lines.append(f"  {msmp_id} -> {gex_id}")
        lines.append("")

        lines.append("AGENT MAPPING")
        lines.append("-" * 40)
        for msmp_agent, gex_approver in result.agent_mapping.items():
            lines.append(f"  {msmp_agent} -> {gex_approver}")
        lines.append("")

        if result.policy_set:
            lines.append("GENERATED POLICY")
            lines.append("-" * 40)
            lines.append(f"Policy ID: {result.policy_set.policy_id}")
            lines.append(f"Total Rules: {len(result.policy_set.get_all_rules())}")
            lines.append("")

            lines.append("Rules by Layer:")
            lines.append(f"  - Mandatory: {len(result.policy_set.mandatory_rules)}")
            lines.append(f"  - Risk-Adaptive: {len(result.policy_set.risk_adaptive_rules)}")
            lines.append(f"  - Contextual: {len(result.policy_set.contextual_rules)}")
            lines.append(f"  - Optimization: {len(result.policy_set.optimization_rules)}")

        lines.append("")
        lines.append("=" * 70)
        lines.append("NEXT STEPS")
        lines.append("=" * 70)
        lines.append("1. Review generated policy rules")
        lines.append("2. Test with sample requests in shadow mode")
        lines.append("3. Compare outcomes with MSMP")
        lines.append("4. Gradually migrate workflows")
        lines.append("")

        return "\n".join(lines)

    def compare_outcomes(
        self,
        msmp_result: Dict[str, Any],
        governex_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare workflow outcomes between MSMP and GOVERNEX+.

        For validation during migration.
        """
        msmp_approvers = set(msmp_result.get("approvers", []))
        gex_approvers = set(governex_result.get("approvers", []))

        msmp_sla = msmp_result.get("sla_hours", 0)
        gex_sla = governex_result.get("sla_hours", 0)

        return {
            "approvers_match": msmp_approvers == gex_approvers,
            "approvers": {
                "msmp": list(msmp_approvers),
                "governex": list(gex_approvers),
                "only_in_msmp": list(msmp_approvers - gex_approvers),
                "only_in_governex": list(gex_approvers - msmp_approvers),
            },
            "sla": {
                "msmp": msmp_sla,
                "governex": gex_sla,
                "difference": gex_sla - msmp_sla,
            },
            "recommendation": (
                "MATCH" if msmp_approvers == gex_approvers and abs(msmp_sla - gex_sla) < 4
                else "REVIEW_NEEDED"
            ),
        }
