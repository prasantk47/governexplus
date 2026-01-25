# Access Risk Analysis Engine
# Core risk detection and scoring engine for GOVERNEX+

"""
Access Risk Analysis Engine.

Provides:
- SoD conflict detection
- Sensitive access analysis
- Critical action identification
- Real-time risk evaluation
- Context-aware scoring
- Usage-based risk analysis
"""

from typing import List, Optional, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from collections import defaultdict

from .models import (
    Risk,
    RiskSeverity,
    RiskCategory,
    RiskStatus,
    RiskType,
    SoDRule,
    SoDConflict,
    SoDRuleSet,
    ConflictType,
    RiskContext,
    UserContext,
    RiskAnalysisResult,
    SimulationResult,
    RemediationSuggestion,
)
from .rules import RuleEngine, RuleDefinition, RuleCondition, ConditionOperator

logger = logging.getLogger(__name__)


# =============================================================================
# SoD Analyzer
# =============================================================================

class SoDAnalyzer:
    """
    Segregation of Duties conflict analyzer.

    Detects conflicts at user, role, and cross-system levels.
    """

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine

    def analyze_user(
        self,
        user_id: str,
        user_access: Dict[str, Any],
        context: Optional[RiskContext] = None
    ) -> List[SoDConflict]:
        """
        Analyze user for SoD conflicts.

        Args:
            user_id: User identifier
            user_access: User's access (tcodes, roles, auth_objects)
            context: Optional risk context

        Returns:
            List of detected SoD conflicts
        """
        conflicts = []

        # Get applicable SoD rules
        sod_rules = self.rule_engine.list_rules(rule_type="sod")

        for rule in sod_rules:
            # Check if user has both functions
            if rule.evaluate(user_access):
                # Create conflict
                conflict = SoDConflict(
                    rule=rule.to_sod_rule(),
                    conflict_type=ConflictType.USER_LEVEL,
                    user_id=user_id,
                    function_1_access=self._extract_function_access(
                        user_access, rule.function_1_conditions
                    ),
                    function_2_access=self._extract_function_access(
                        user_access, rule.function_2_conditions
                    ),
                    severity=rule.severity,
                    risk_score=self._calculate_conflict_score(rule, context),
                )

                # Find source roles
                if "roles_by_tcode" in user_access:
                    conflict.function_1_roles = self._find_source_roles(
                        user_access, rule.function_1_conditions
                    )
                    conflict.function_2_roles = self._find_source_roles(
                        user_access, rule.function_2_conditions
                    )

                conflicts.append(conflict)
                logger.debug(f"SoD conflict detected: {rule.name} for user {user_id}")

        return conflicts

    def analyze_role(
        self,
        role_id: str,
        role_access: Dict[str, Any]
    ) -> List[SoDConflict]:
        """
        Analyze a single role for internal SoD conflicts.

        Args:
            role_id: Role identifier
            role_access: Role's access definition

        Returns:
            List of conflicts within the role
        """
        conflicts = []
        sod_rules = self.rule_engine.list_rules(rule_type="sod")

        for rule in sod_rules:
            if rule.evaluate(role_access):
                conflict = SoDConflict(
                    rule=rule.to_sod_rule(),
                    conflict_type=ConflictType.ROLE_LEVEL,
                    role_id=role_id,
                    function_1_access=self._extract_function_access(
                        role_access, rule.function_1_conditions
                    ),
                    function_2_access=self._extract_function_access(
                        role_access, rule.function_2_conditions
                    ),
                    severity=rule.severity,
                )
                conflicts.append(conflict)

        return conflicts

    def analyze_cross_role(
        self,
        user_id: str,
        roles: List[Dict[str, Any]]
    ) -> List[SoDConflict]:
        """
        Analyze conflicts across multiple roles.

        Detects when combination of roles creates a conflict.

        Args:
            user_id: User identifier
            roles: List of role access definitions

        Returns:
            List of cross-role conflicts
        """
        conflicts = []
        sod_rules = self.rule_engine.list_rules(rule_type="sod")

        # For each rule, check if different roles provide the two functions
        for rule in sod_rules:
            func1_roles = []
            func2_roles = []

            for role in roles:
                role_id = role.get("role_id", "unknown")
                role_access = role.get("access", role)

                # Check function 1
                func1_match = all(
                    cond.evaluate(role_access)
                    for cond in rule.function_1_conditions
                )
                if func1_match:
                    func1_roles.append(role_id)

                # Check function 2
                func2_match = all(
                    cond.evaluate(role_access)
                    for cond in rule.function_2_conditions
                )
                if func2_match:
                    func2_roles.append(role_id)

            # Cross-role conflict exists if functions come from different roles
            if func1_roles and func2_roles:
                # Check if truly cross-role (not same role having both)
                if set(func1_roles) != set(func2_roles):
                    conflict = SoDConflict(
                        rule=rule.to_sod_rule(),
                        conflict_type=ConflictType.CROSS_ROLE,
                        user_id=user_id,
                        function_1_roles=func1_roles,
                        function_2_roles=func2_roles,
                        severity=rule.severity,
                    )
                    conflicts.append(conflict)

        return conflicts

    def _extract_function_access(
        self,
        access: Dict[str, Any],
        conditions: List[RuleCondition]
    ) -> Dict[str, Any]:
        """Extract the specific access that satisfies function conditions."""
        result = {}

        for cond in conditions:
            field = cond.field
            if field in access:
                if isinstance(access[field], list):
                    # Filter to matching values
                    if cond.operator == ConditionOperator.ANY:
                        matching = [v for v in access[field] if v in cond.value]
                        result[field] = matching
                else:
                    result[field] = access[field]

        return result

    def _find_source_roles(
        self,
        access: Dict[str, Any],
        conditions: List[RuleCondition]
    ) -> List[str]:
        """Find which roles provide the function access."""
        roles = set()
        roles_by_tcode = access.get("roles_by_tcode", {})

        for cond in conditions:
            if cond.field == "tcodes" and isinstance(cond.value, list):
                for tcode in cond.value:
                    if tcode in roles_by_tcode:
                        roles.update(roles_by_tcode[tcode])

        return list(roles)

    def _calculate_conflict_score(
        self,
        rule: RuleDefinition,
        context: Optional[RiskContext]
    ) -> int:
        """Calculate risk score for a conflict."""
        base_score = int(rule.severity.score_weight * 100)

        if context:
            # Apply context modifiers
            if context.user_context:
                uc = context.user_context
                if uc.employment_type == "contractor":
                    base_score = min(100, base_score + 10)
                if uc.tenure_days < 90:
                    base_score = min(100, base_score + 5)
                if uc.is_privileged_user:
                    base_score = min(100, base_score + 15)

        return base_score


# =============================================================================
# Sensitive Access Analyzer
# =============================================================================

class SensitiveAccessAnalyzer:
    """
    Analyzer for sensitive and critical access.

    Detects:
    - Sensitive transaction codes
    - Critical authorization objects
    - Privileged role assignments
    """

    # Predefined sensitive access categories
    SENSITIVE_TCODES = {
        "development": ["SE38", "SE80", "SE24", "SE37", "SE11"],
        "data_access": ["SE16", "SE16N", "SE17", "SM30", "SM31"],
        "user_admin": ["SU01", "SU10", "PFCG", "SU53"],
        "transport": ["STMS", "SE09", "SE10"],
        "system_admin": ["SM21", "SM37", "SM50", "SM51", "SM66"],
        "security": ["SM19", "SM20", "RSAU_CONFIG", "RSUSR003"],
        "basis": ["RZ10", "RZ11", "RZ20", "SPRO"],
    }

    CRITICAL_AUTH_OBJECTS = {
        "S_DEVELOP": "ABAP Development",
        "S_TABU_DIS": "Table Maintenance",
        "S_RFC": "RFC Access",
        "S_USER_GRP": "User Maintenance",
        "S_TRANSPRT": "Transport Management",
        "S_ADMI_FCD": "Administration Functions",
    }

    PRIVILEGED_ROLES = [
        "SAP_ALL",
        "SAP_NEW",
        "S_A.ADMIN",
        "S_A.SYSTEM",
        "S_A.DEVELOP",
    ]

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine

    def analyze(
        self,
        user_id: str,
        access: Dict[str, Any],
        context: Optional[RiskContext] = None
    ) -> List[Risk]:
        """
        Analyze access for sensitive items.

        Args:
            user_id: User identifier
            access: User's access definition
            context: Optional risk context

        Returns:
            List of sensitive access risks
        """
        risks = []

        # Check sensitive tcodes
        tcode_risks = self._check_sensitive_tcodes(user_id, access)
        risks.extend(tcode_risks)

        # Check critical auth objects
        auth_risks = self._check_critical_auth_objects(user_id, access)
        risks.extend(auth_risks)

        # Check privileged roles
        role_risks = self._check_privileged_roles(user_id, access)
        risks.extend(role_risks)

        # Check rule-based sensitive access
        rule_risks = self._check_rule_based_sensitive(user_id, access)
        risks.extend(rule_risks)

        return risks

    def _check_sensitive_tcodes(
        self,
        user_id: str,
        access: Dict[str, Any]
    ) -> List[Risk]:
        """Check for sensitive transaction codes."""
        risks = []
        user_tcodes = set(access.get("tcodes", []))

        for category, tcodes in self.SENSITIVE_TCODES.items():
            matching = user_tcodes & set(tcodes)
            if matching:
                risk = Risk(
                    risk_type=RiskType.SENSITIVE_ACCESS,
                    severity=RiskSeverity.HIGH,
                    category=RiskCategory.IT,
                    user_id=user_id,
                    title=f"Sensitive Access: {category.replace('_', ' ').title()}",
                    description=f"User has access to sensitive {category} transactions",
                    conflicting_tcodes=list(matching),
                    base_score=70,
                )
                risks.append(risk)

        return risks

    def _check_critical_auth_objects(
        self,
        user_id: str,
        access: Dict[str, Any]
    ) -> List[Risk]:
        """Check for critical authorization objects."""
        risks = []
        user_auth_objects = access.get("auth_objects", {})

        for auth_obj, description in self.CRITICAL_AUTH_OBJECTS.items():
            if auth_obj in user_auth_objects:
                # Check for full access (*)
                obj_values = user_auth_objects[auth_obj]
                has_full_access = "*" in str(obj_values)

                severity = RiskSeverity.CRITICAL if has_full_access else RiskSeverity.HIGH

                risk = Risk(
                    risk_type=RiskType.SENSITIVE_ACCESS,
                    severity=severity,
                    category=RiskCategory.IT,
                    user_id=user_id,
                    title=f"Critical Authorization: {description}",
                    description=f"User has {auth_obj} authorization",
                    conflicting_auth_objects=[auth_obj],
                    base_score=80 if has_full_access else 65,
                )
                risks.append(risk)

        return risks

    def _check_privileged_roles(
        self,
        user_id: str,
        access: Dict[str, Any]
    ) -> List[Risk]:
        """Check for privileged role assignments."""
        risks = []
        user_roles = set(access.get("roles", []))

        for priv_role in self.PRIVILEGED_ROLES:
            if priv_role in user_roles:
                risk = Risk(
                    risk_type=RiskType.PRIVILEGED_ACCESS,
                    severity=RiskSeverity.CRITICAL,
                    category=RiskCategory.IT,
                    user_id=user_id,
                    title=f"Privileged Role: {priv_role}",
                    description=f"User is assigned privileged role {priv_role}",
                    conflicting_roles=[priv_role],
                    base_score=90,
                )
                risks.append(risk)

        return risks

    def _check_rule_based_sensitive(
        self,
        user_id: str,
        access: Dict[str, Any]
    ) -> List[Risk]:
        """Check sensitive access rules from rule engine."""
        risks = []

        sensitive_rules = self.rule_engine.list_rules(rule_type="sensitive")
        for rule in sensitive_rules:
            if rule.evaluate(access):
                risk = Risk(
                    risk_type=RiskType.SENSITIVE_ACCESS,
                    severity=rule.severity,
                    category=rule.category,
                    user_id=user_id,
                    title=rule.name,
                    description=rule.description,
                    business_impact=rule.business_impact,
                    rule_id=rule.rule_id,
                    base_score=int(rule.severity.score_weight * 100),
                )
                risks.append(risk)

        return risks


# =============================================================================
# Risk Scorer
# =============================================================================

class RiskScorer:
    """
    Dynamic risk scoring engine.

    Calculates risk scores based on:
    - Base severity
    - Context factors
    - Usage patterns
    - Behavioral indicators
    """

    # Context weight factors
    CONTEXT_WEIGHTS = {
        "employment_type": {
            "contractor": 1.2,
            "vendor": 1.3,
            "employee": 1.0,
        },
        "tenure_days": {
            "range": [(0, 30, 1.3), (30, 90, 1.15), (90, 365, 1.0), (365, 9999, 0.9)],
        },
        "is_privileged_user": {True: 1.25, False: 1.0},
        "is_emergency_access": {True: 1.4, False: 1.0},
        "current_location": {
            "external": 1.2,
            "unknown": 1.15,
            "internal": 1.0,
        },
        "is_business_hours": {True: 1.0, False: 1.15},
        "device_trust_level": {
            "low": 1.2,
            "medium": 1.1,
            "high": 1.0,
        },
    }

    def calculate_score(
        self,
        risk: Risk,
        context: Optional[RiskContext] = None,
        usage_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Calculate comprehensive risk score.

        Args:
            risk: Risk to score
            context: Risk context
            usage_data: Optional usage/activity data

        Returns:
            Risk score (0-100)
        """
        # Start with base score
        base_score = risk.base_score

        # Calculate context modifier
        context_modifier = self._calculate_context_modifier(context)
        context_score = int(base_score * context_modifier)

        # Calculate usage modifier
        usage_modifier = self._calculate_usage_modifier(risk, usage_data)
        usage_score = int(base_score * usage_modifier)

        # Update risk scores
        risk.context_score = min(100, context_score)
        risk.usage_score = min(100, usage_score)

        # Calculate final score (weighted)
        final_score = int(
            base_score * 0.5 +
            context_score * 0.3 +
            usage_score * 0.2
        )

        risk.final_score = min(100, max(0, final_score))
        risk.severity = RiskSeverity.from_score(risk.final_score)

        # Record context factors
        if context:
            risk.context_factors = self._extract_context_factors(context)

        return risk.final_score

    def _calculate_context_modifier(self, context: Optional[RiskContext]) -> float:
        """Calculate risk modifier from context."""
        if not context or not context.user_context:
            return 1.0

        uc = context.user_context
        modifier = 1.0

        # Employment type
        emp_weights = self.CONTEXT_WEIGHTS["employment_type"]
        modifier *= emp_weights.get(uc.employment_type, 1.0)

        # Tenure
        for min_days, max_days, weight in self.CONTEXT_WEIGHTS["tenure_days"]["range"]:
            if min_days <= uc.tenure_days < max_days:
                modifier *= weight
                break

        # Privileged user
        modifier *= self.CONTEXT_WEIGHTS["is_privileged_user"].get(uc.is_privileged_user, 1.0)

        # Emergency access
        modifier *= self.CONTEXT_WEIGHTS["is_emergency_access"].get(uc.is_emergency_access, 1.0)

        # Location
        loc_weights = self.CONTEXT_WEIGHTS["current_location"]
        modifier *= loc_weights.get(uc.current_location, 1.0)

        # Business hours
        modifier *= self.CONTEXT_WEIGHTS["is_business_hours"].get(uc.is_business_hours, 1.0)

        # Device trust
        device_weights = self.CONTEXT_WEIGHTS["device_trust_level"]
        modifier *= device_weights.get(uc.device_trust_level, 1.0)

        return modifier

    def _calculate_usage_modifier(
        self,
        risk: Risk,
        usage_data: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate risk modifier from usage patterns."""
        if not usage_data:
            return 1.0

        modifier = 1.0

        # Unused access is higher risk
        if risk.risk_type == RiskType.SENSITIVE_ACCESS:
            usage_count = usage_data.get("usage_count_30d", 0)
            if usage_count == 0:
                modifier *= 1.3  # Unused sensitive access
            elif usage_count < 5:
                modifier *= 1.1

        # Frequent use of conflicting functions
        if risk.risk_type == RiskType.SOD_CONFLICT:
            conflict_usage = usage_data.get("conflict_usage_count", 0)
            if conflict_usage > 10:
                modifier *= 1.4  # Frequently exercising conflict
            elif conflict_usage > 0:
                modifier *= 1.2

        # Peer deviation
        if "peer_deviation" in usage_data:
            deviation = usage_data["peer_deviation"]
            if deviation > 2.0:  # More than 2 std dev from peers
                modifier *= 1.25

        return modifier

    def _extract_context_factors(self, context: RiskContext) -> Dict[str, Any]:
        """Extract relevant context factors for audit."""
        factors = {}

        if context.user_context:
            uc = context.user_context
            factors["employment_type"] = uc.employment_type
            factors["tenure_days"] = uc.tenure_days
            factors["is_privileged"] = uc.is_privileged_user
            factors["is_emergency"] = uc.is_emergency_access
            factors["location"] = uc.current_location
            factors["device_trust"] = uc.device_trust_level

        factors["evaluation_time"] = context.evaluation_time.isoformat()
        factors["is_business_hours"] = context.is_business_hours
        factors["environment"] = context.environment

        return factors


# =============================================================================
# Main Access Risk Engine
# =============================================================================

class AccessRiskEngine:
    """
    Main Access Risk Analysis engine.

    Coordinates all risk analysis components.
    """

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.sod_analyzer = SoDAnalyzer(self.rule_engine)
        self.sensitive_analyzer = SensitiveAccessAnalyzer(self.rule_engine)
        self.risk_scorer = RiskScorer()

        # Risk storage (in production, use database)
        self.risks: Dict[str, Risk] = {}
        self.analysis_cache: Dict[str, RiskAnalysisResult] = {}

    def analyze_user(
        self,
        user_id: str,
        access: Dict[str, Any],
        context: Optional[RiskContext] = None,
        usage_data: Optional[Dict[str, Any]] = None
    ) -> RiskAnalysisResult:
        """
        Perform full risk analysis for a user.

        Args:
            user_id: User identifier
            access: User's access definition
            context: Risk context
            usage_data: Optional usage data

        Returns:
            Complete risk analysis result
        """
        start_time = datetime.now()

        result = RiskAnalysisResult(
            analysis_type="full",
            user_id=user_id,
            system_id=access.get("system_id", "SAP"),
            context=context,
        )

        # 1. SoD Analysis
        sod_conflicts = self.sod_analyzer.analyze_user(user_id, access, context)
        result.sod_conflicts = sod_conflicts

        # Convert conflicts to risks
        for conflict in sod_conflicts:
            risk = self._conflict_to_risk(conflict)
            self.risk_scorer.calculate_score(risk, context, usage_data)
            result.risks.append(risk)

        # 2. Sensitive Access Analysis
        sensitive_risks = self.sensitive_analyzer.analyze(user_id, access, context)
        for risk in sensitive_risks:
            self.risk_scorer.calculate_score(risk, context, usage_data)
            result.risks.append(risk)

        # 3. Calculate summary
        result.calculate_summary()
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Store in cache
        self.analysis_cache[user_id] = result

        logger.info(
            f"Analysis complete for {user_id}: "
            f"{result.total_risks} risks, score={result.aggregate_risk_score}"
        )

        return result

    def analyze_role(
        self,
        role_id: str,
        role_access: Dict[str, Any]
    ) -> RiskAnalysisResult:
        """Analyze a role for internal risks."""
        start_time = datetime.now()

        result = RiskAnalysisResult(
            analysis_type="role",
            role_id=role_id,
        )

        # SoD within role
        conflicts = self.sod_analyzer.analyze_role(role_id, role_access)
        result.sod_conflicts = conflicts

        for conflict in conflicts:
            risk = self._conflict_to_risk(conflict)
            result.risks.append(risk)

        result.calculate_summary()
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    def simulate_access(
        self,
        user_id: str,
        current_access: Dict[str, Any],
        requested_access: Dict[str, Any],
        context: Optional[RiskContext] = None
    ) -> SimulationResult:
        """
        Simulate impact of granting additional access.

        Args:
            user_id: User identifier
            current_access: Current access
            requested_access: Access to be granted
            context: Risk context

        Returns:
            Simulation result with risk delta
        """
        if context:
            context.is_simulation = True

        # Analyze current state
        current_result = self.analyze_user(user_id, current_access, context)

        # Merge access
        combined_access = self._merge_access(current_access, requested_access)

        # Analyze combined state
        combined_result = self.analyze_user(user_id, combined_access, context)

        # Find new risks
        current_risk_ids = {r.risk_id for r in current_result.risks}
        new_risks = [r for r in combined_result.risks if r.risk_id not in current_risk_ids]

        # Build simulation result
        simulation = SimulationResult(
            user_id=user_id,
            requested_roles=requested_access.get("roles", []),
            requested_tcodes=requested_access.get("tcodes", []),
            current_risks=current_result.risks,
            current_risk_score=current_result.aggregate_risk_score,
            new_risks=new_risks,
            simulated_risk_score=combined_result.aggregate_risk_score,
            risk_delta=combined_result.aggregate_risk_score - current_result.aggregate_risk_score,
            new_sod_conflicts=[
                c for c in combined_result.sod_conflicts
                if c.conflict_id not in {x.conflict_id for x in current_result.sod_conflicts}
            ],
        )

        # Generate recommendation
        simulation.recommendation, simulation.recommendation_reason = self._generate_recommendation(
            simulation
        )

        return simulation

    def get_remediation_suggestions(
        self,
        risks: List[Risk]
    ) -> List[RemediationSuggestion]:
        """
        Generate smart remediation suggestions for risks.

        Args:
            risks: Risks to remediate (single Risk or list)

        Returns:
            List of remediation suggestions
        """
        # Handle single risk for backwards compatibility
        if isinstance(risks, Risk):
            risks = [risks]

        suggestions = []
        for risk in risks:
            suggestions.extend(self._get_suggestions_for_risk(risk))

        return suggestions

    def _get_suggestions_for_risk(self, risk: Risk) -> List[RemediationSuggestion]:
        """Generate remediation suggestions for a single risk."""
        suggestions = []

        if risk.risk_type == RiskType.SOD_CONFLICT:
            # Suggest role removal
            for role in risk.conflicting_roles:
                suggestions.append(RemediationSuggestion(
                    risk_id=risk.risk_id,
                    action="remove_role",
                    target_type="role",
                    target_id=role,
                    target_name=role,
                    risk_reduction=30,
                    implementation_effort="medium",
                    rationale=f"Removing role {role} would eliminate one side of the SoD conflict",
                ))

            # Suggest role split
            if len(risk.conflicting_roles) == 1:
                suggestions.append(RemediationSuggestion(
                    risk_id=risk.risk_id,
                    action="split_role",
                    target_type="role",
                    target_id=risk.conflicting_roles[0],
                    target_name=risk.conflicting_roles[0],
                    risk_reduction=50,
                    implementation_effort="high",
                    requires_approval=True,
                    rationale="Splitting the role into separate functions would resolve internal conflict",
                ))

        elif risk.risk_type == RiskType.SENSITIVE_ACCESS:
            # Suggest tcode removal
            for tcode in risk.conflicting_tcodes:
                suggestions.append(RemediationSuggestion(
                    risk_id=risk.risk_id,
                    action="remove_tcode",
                    target_type="tcode",
                    target_id=tcode,
                    target_name=tcode,
                    risk_reduction=25,
                    implementation_effort="low",
                    rationale=f"Removing access to {tcode} would reduce sensitive access exposure",
                ))

        # Always suggest mitigation as an option
        suggestions.append(RemediationSuggestion(
            risk_id=risk.risk_id,
            action="add_mitigation",
            target_type="control",
            target_id="",
            target_name="Mitigating Control",
            risk_reduction=20,
            implementation_effort="low",
            rationale="Adding a compensating control would reduce the effective risk",
        ))

        return suggestions

    def _conflict_to_risk(self, conflict: SoDConflict) -> Risk:
        """Convert SoD conflict to Risk object."""
        return Risk(
            risk_type=RiskType.SOD_CONFLICT,
            severity=conflict.severity,
            category=conflict.rule.category if conflict.rule else RiskCategory.COMPLIANCE,
            status=RiskStatus.OPEN,
            title=conflict.rule.name if conflict.rule else "SoD Conflict",
            description=conflict.rule.description if conflict.rule else "",
            business_impact=conflict.rule.business_impact if conflict.rule else "",
            user_id=conflict.user_id,
            role_id=conflict.role_id,
            conflicting_roles=conflict.function_1_roles + conflict.function_2_roles,
            conflicting_tcodes=(
                list(conflict.function_1_access.get("tcodes", [])) +
                list(conflict.function_2_access.get("tcodes", []))
            ),
            base_score=conflict.risk_score,
            rule_id=conflict.rule.rule_id if conflict.rule else None,
        )

    def _merge_access(
        self,
        current: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two access definitions."""
        merged = {}

        for key in set(list(current.keys()) + list(new.keys())):
            curr_val = current.get(key, [])
            new_val = new.get(key, [])

            if isinstance(curr_val, list) and isinstance(new_val, list):
                merged[key] = list(set(curr_val + new_val))
            elif isinstance(curr_val, dict) and isinstance(new_val, dict):
                merged[key] = {**curr_val, **new_val}
            else:
                merged[key] = new_val if new_val else curr_val

        return merged

    def _generate_recommendation(
        self,
        simulation: SimulationResult
    ) -> Tuple[str, str]:
        """Generate access request recommendation."""
        new_critical = len([r for r in simulation.new_risks if r.severity == RiskSeverity.CRITICAL])
        new_high = len([r for r in simulation.new_risks if r.severity == RiskSeverity.HIGH])
        new_sod = len(simulation.new_sod_conflicts)

        if new_critical > 0 or new_sod >= 3:
            return "deny", f"Creates {new_critical} critical risks and {new_sod} SoD conflicts"
        elif new_high > 2 or new_sod >= 2:
            return "review", f"Creates {new_high} high-severity risks requiring review"
        elif simulation.risk_delta > 30:
            return "review", f"Significant risk increase of {simulation.risk_delta} points"
        else:
            return "approve", "Risk increase is within acceptable limits"

    # =========================================================================
    # SoD Rule Management
    # =========================================================================

    def get_sod_rules(self) -> List[SoDRule]:
        """Get all SoD rules."""
        rules = self.rule_engine.list_rules(rule_type="sod")
        return [r.to_sod_rule() for r in rules]

    def get_sod_rule(self, rule_id: str) -> Optional[SoDRule]:
        """Get a specific SoD rule by ID."""
        rule = self.rule_engine.get_rule(rule_id)
        if rule and rule.rule_type == "sod":
            return rule.to_sod_rule()
        return None

    def add_sod_rule(self, rule: SoDRule):
        """
        Add a new SoD rule.

        Args:
            rule: SoD rule to add
        """
        # Convert SoDRule to RuleDefinition
        rule_def = RuleDefinition(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            rule_type="sod",
            severity=rule.severity,
            category=rule.category,
            business_impact=rule.business_impact,
            enabled=rule.enabled,
            function_1_conditions=[
                RuleCondition(
                    field="tcodes",
                    operator=ConditionOperator.CONTAINS_ANY,
                    value=rule.function_1_tcodes,
                )
            ] if rule.function_1_tcodes else [],
            function_2_conditions=[
                RuleCondition(
                    field="tcodes",
                    operator=ConditionOperator.CONTAINS_ANY,
                    value=rule.function_2_tcodes,
                )
            ] if rule.function_2_tcodes else [],
        )

        self.rule_engine.add_rule(rule_def)
        logger.info(f"Added SoD rule: {rule.rule_id}")

    def remove_sod_rule(self, rule_id: str) -> bool:
        """
        Remove a SoD rule.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if removed, False if not found
        """
        return self.rule_engine.remove_rule(rule_id)
