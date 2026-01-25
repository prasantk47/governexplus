"""
Cross-System SoD Engine

Enterprise-wide Segregation of Duties analysis across multiple systems.
Provides SAP GRC-equivalent cross-system risk analysis with enhancements.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from datetime import datetime
import hashlib


class SystemType(Enum):
    """Supported system types"""
    SAP_ECC = "sap_ecc"
    SAP_S4HANA = "sap_s4hana"
    SAP_BW = "sap_bw"
    SAP_ARIBA = "sap_ariba"
    SAP_CONCUR = "sap_concur"
    SAP_SUCCESSFACTORS = "sap_successfactors"
    ORACLE_EBS = "oracle_ebs"
    ORACLE_CLOUD = "oracle_cloud"
    WORKDAY = "workday"
    SALESFORCE = "salesforce"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    SERVICENOW = "servicenow"
    CUSTOM = "custom"


class ConflictType(Enum):
    """Types of cross-system conflicts"""
    INTRA_SYSTEM = "intra_system"       # Within same system
    INTER_SYSTEM = "inter_system"       # Across two systems
    MULTI_SYSTEM = "multi_system"       # Across 3+ systems
    CROSS_PLATFORM = "cross_platform"   # SAP + non-SAP


@dataclass
class SystemFunction:
    """Business function in a specific system"""
    function_id: str
    system_id: str
    system_type: SystemType
    name: str
    description: str
    module: str  # FI, MM, SD, HR, etc.

    # Function definition
    transactions: List[str] = field(default_factory=list)
    auth_objects: List[Dict[str, Any]] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)  # For non-SAP

    # Metadata
    risk_level: str = "medium"
    is_sensitive: bool = False
    compliance_tags: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(f"{self.system_id}:{self.function_id}")


@dataclass
class CrossSystemRule:
    """SoD rule spanning multiple systems"""
    rule_id: str
    name: str
    description: str

    # Functions involved (can be from different systems)
    function_1: SystemFunction
    function_2: SystemFunction

    # Risk classification
    risk_level: str = "high"  # low, medium, high, critical
    conflict_type: ConflictType = ConflictType.INTER_SYSTEM

    # Compliance
    compliance_frameworks: List[str] = field(default_factory=list)  # SOX, GDPR
    control_objective: str = ""

    # Business context
    business_process: str = ""
    risk_description: str = ""

    # Status
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""

    def __hash__(self):
        return hash(self.rule_id)


@dataclass
class SystemMapping:
    """Maps equivalent functions across systems"""
    mapping_id: str
    name: str
    description: str

    # Equivalent functions across systems
    function_mappings: Dict[str, SystemFunction] = field(default_factory=dict)  # system_id -> function

    # Mapping type
    mapping_type: str = "equivalent"  # equivalent, subset, superset, related
    confidence: float = 1.0  # How confident we are in the mapping

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CrossSystemViolation:
    """Violation spanning multiple systems"""
    violation_id: str
    user_id: str
    user_name: str

    # Rule violated
    rule: CrossSystemRule

    # Access details per system
    system_access: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Classification
    risk_level: str = "high"
    conflict_type: ConflictType = ConflictType.INTER_SYSTEM

    # Impact
    systems_affected: List[str] = field(default_factory=list)
    compliance_impact: List[str] = field(default_factory=list)

    # Status
    status: str = "open"  # open, mitigated, remediated, accepted
    mitigation_id: Optional[str] = None

    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CrossSystemUser:
    """User identity across multiple systems"""
    global_user_id: str
    email: str
    name: str
    department: str

    # System-specific identities
    system_identities: Dict[str, str] = field(default_factory=dict)  # system_id -> local_user_id

    # Aggregated access
    total_roles: int = 0
    total_permissions: int = 0
    systems_count: int = 0

    # Risk profile
    aggregate_risk_score: float = 0.0
    cross_system_violations: int = 0


class CrossSystemSoDEngine:
    """
    Enterprise Cross-System SoD Engine

    Provides:
    1. Multi-system function mapping
    2. Cross-system rule management
    3. Enterprise-wide SoD analysis
    4. Unified violation tracking
    5. Cross-platform risk correlation
    """

    def __init__(self):
        # System registry
        self.systems: Dict[str, Dict[str, Any]] = {}

        # Function catalog per system
        self.functions: Dict[str, Dict[str, SystemFunction]] = {}  # system_id -> {func_id -> func}

        # Cross-system rules
        self.rules: Dict[str, CrossSystemRule] = {}

        # Function mappings
        self.mappings: Dict[str, SystemMapping] = {}

        # User identity mapping
        self.user_mappings: Dict[str, CrossSystemUser] = {}  # global_id -> user

        # Violations
        self.violations: Dict[str, CrossSystemViolation] = {}

        # Initialize with sample data
        self._initialize_sample_systems()
        self._initialize_cross_system_rules()

    # ==================== System Management ====================

    def register_system(
        self,
        system_id: str,
        system_type: SystemType,
        name: str,
        connection_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Register a new system for cross-system analysis"""
        self.systems[system_id] = {
            "system_id": system_id,
            "system_type": system_type,
            "name": name,
            "connection_config": connection_config,
            "registered_at": datetime.utcnow(),
            "status": "active",
            "last_sync": None,
            "function_count": 0,
            "user_count": 0
        }

        self.functions[system_id] = {}

        return self.systems[system_id]

    def register_function(
        self,
        system_id: str,
        function: SystemFunction
    ) -> SystemFunction:
        """Register a business function for a system"""
        if system_id not in self.functions:
            self.functions[system_id] = {}

        self.functions[system_id][function.function_id] = function

        if system_id in self.systems:
            self.systems[system_id]["function_count"] = len(self.functions[system_id])

        return function

    # ==================== Function Mapping ====================

    def create_function_mapping(
        self,
        mapping_id: str,
        name: str,
        description: str,
        functions: List[SystemFunction],
        mapping_type: str = "equivalent"
    ) -> SystemMapping:
        """Create mapping between equivalent functions across systems"""
        mapping = SystemMapping(
            mapping_id=mapping_id,
            name=name,
            description=description,
            mapping_type=mapping_type
        )

        for func in functions:
            mapping.function_mappings[func.system_id] = func

        self.mappings[mapping_id] = mapping
        return mapping

    def find_equivalent_functions(
        self,
        function: SystemFunction
    ) -> List[SystemFunction]:
        """Find equivalent functions in other systems"""
        equivalents = []

        for mapping in self.mappings.values():
            if function.system_id in mapping.function_mappings:
                if mapping.function_mappings[function.system_id].function_id == function.function_id:
                    for sys_id, equiv_func in mapping.function_mappings.items():
                        if sys_id != function.system_id:
                            equivalents.append(equiv_func)

        return equivalents

    def auto_map_functions(
        self,
        source_system: str,
        target_system: str
    ) -> List[SystemMapping]:
        """Automatically map functions between systems using ML/heuristics"""
        auto_mappings = []

        source_funcs = self.functions.get(source_system, {})
        target_funcs = self.functions.get(target_system, {})

        for src_id, src_func in source_funcs.items():
            best_match = None
            best_score = 0.0

            for tgt_id, tgt_func in target_funcs.items():
                score = self._calculate_mapping_similarity(src_func, tgt_func)
                if score > best_score and score > 0.7:  # 70% threshold
                    best_score = score
                    best_match = tgt_func

            if best_match:
                mapping = SystemMapping(
                    mapping_id=f"auto_{src_func.function_id}_{best_match.function_id}",
                    name=f"{src_func.name} <-> {best_match.name}",
                    description="Auto-generated mapping",
                    mapping_type="equivalent",
                    confidence=best_score
                )
                mapping.function_mappings[source_system] = src_func
                mapping.function_mappings[target_system] = best_match
                auto_mappings.append(mapping)

        return auto_mappings

    def _calculate_mapping_similarity(
        self,
        func1: SystemFunction,
        func2: SystemFunction
    ) -> float:
        """Calculate similarity score between two functions"""
        score = 0.0

        # Name similarity
        name1_words = set(func1.name.lower().split())
        name2_words = set(func2.name.lower().split())
        if name1_words & name2_words:
            score += 0.3 * len(name1_words & name2_words) / max(len(name1_words), len(name2_words))

        # Module match
        if func1.module.upper() == func2.module.upper():
            score += 0.3

        # Risk level match
        if func1.risk_level == func2.risk_level:
            score += 0.2

        # Compliance tags overlap
        tags1 = set(func1.compliance_tags)
        tags2 = set(func2.compliance_tags)
        if tags1 & tags2:
            score += 0.2 * len(tags1 & tags2) / max(len(tags1), len(tags2), 1)

        return min(score, 1.0)

    # ==================== Cross-System Rules ====================

    def create_cross_system_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        function_1: SystemFunction,
        function_2: SystemFunction,
        risk_level: str = "high",
        compliance_frameworks: List[str] = None,
        business_process: str = "",
        risk_description: str = ""
    ) -> CrossSystemRule:
        """Create a cross-system SoD rule"""
        # Determine conflict type
        if function_1.system_id == function_2.system_id:
            conflict_type = ConflictType.INTRA_SYSTEM
        elif function_1.system_type.value.startswith("sap") != function_2.system_type.value.startswith("sap"):
            conflict_type = ConflictType.CROSS_PLATFORM
        else:
            conflict_type = ConflictType.INTER_SYSTEM

        rule = CrossSystemRule(
            rule_id=rule_id,
            name=name,
            description=description,
            function_1=function_1,
            function_2=function_2,
            risk_level=risk_level,
            conflict_type=conflict_type,
            compliance_frameworks=compliance_frameworks or [],
            business_process=business_process,
            risk_description=risk_description
        )

        self.rules[rule_id] = rule
        return rule

    def get_rules_for_system(self, system_id: str) -> List[CrossSystemRule]:
        """Get all rules involving a specific system"""
        return [
            rule for rule in self.rules.values()
            if rule.function_1.system_id == system_id or rule.function_2.system_id == system_id
        ]

    def get_cross_system_rules(self) -> List[CrossSystemRule]:
        """Get rules that span multiple systems"""
        return [
            rule for rule in self.rules.values()
            if rule.conflict_type in [ConflictType.INTER_SYSTEM, ConflictType.MULTI_SYSTEM, ConflictType.CROSS_PLATFORM]
        ]

    # ==================== User Identity Mapping ====================

    def map_user_identity(
        self,
        global_user_id: str,
        email: str,
        name: str,
        department: str,
        system_identities: Dict[str, str]
    ) -> CrossSystemUser:
        """Map a user's identities across systems"""
        user = CrossSystemUser(
            global_user_id=global_user_id,
            email=email,
            name=name,
            department=department,
            system_identities=system_identities,
            systems_count=len(system_identities)
        )

        self.user_mappings[global_user_id] = user
        return user

    def find_user_by_system_id(
        self,
        system_id: str,
        local_user_id: str
    ) -> Optional[CrossSystemUser]:
        """Find global user by system-specific ID"""
        for user in self.user_mappings.values():
            if user.system_identities.get(system_id) == local_user_id:
                return user
        return None

    def auto_correlate_users(
        self,
        users_by_system: Dict[str, List[Dict[str, Any]]]
    ) -> List[CrossSystemUser]:
        """Automatically correlate users across systems by email"""
        email_to_user: Dict[str, CrossSystemUser] = {}

        for system_id, users in users_by_system.items():
            for user_data in users:
                email = user_data.get("email", "").lower()
                local_id = user_data.get("user_id", "")

                if email:
                    if email not in email_to_user:
                        global_id = hashlib.md5(email.encode()).hexdigest()[:12]
                        email_to_user[email] = CrossSystemUser(
                            global_user_id=global_id,
                            email=email,
                            name=user_data.get("name", ""),
                            department=user_data.get("department", "")
                        )

                    email_to_user[email].system_identities[system_id] = local_id
                    email_to_user[email].systems_count = len(email_to_user[email].system_identities)

        # Store and return
        for user in email_to_user.values():
            self.user_mappings[user.global_user_id] = user

        return list(email_to_user.values())

    # ==================== Cross-System Analysis ====================

    def analyze_user_cross_system(
        self,
        global_user_id: str,
        access_by_system: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a user's access across all systems for SoD violations

        Args:
            global_user_id: The user's global identifier
            access_by_system: Dict of system_id -> {roles, permissions, transactions}

        Returns:
            Comprehensive cross-system risk analysis
        """
        user = self.user_mappings.get(global_user_id)
        if not user:
            return {"error": "User not found in identity mapping"}

        violations = []
        risk_summary = {
            "intra_system": 0,
            "inter_system": 0,
            "cross_platform": 0
        }

        # Collect all user's functions across systems
        user_functions: List[Tuple[str, SystemFunction]] = []

        for system_id, access in access_by_system.items():
            system_funcs = self.functions.get(system_id, {})

            # Match access to functions
            for func_id, func in system_funcs.items():
                if self._user_has_function(access, func):
                    user_functions.append((system_id, func))

        # Check all cross-system rules
        for rule in self.rules.values():
            if not rule.is_active:
                continue

            has_func1 = False
            has_func2 = False
            func1_system = None
            func2_system = None

            for system_id, func in user_functions:
                if self._functions_match(func, rule.function_1):
                    has_func1 = True
                    func1_system = system_id
                if self._functions_match(func, rule.function_2):
                    has_func2 = True
                    func2_system = system_id

            if has_func1 and has_func2:
                violation = CrossSystemViolation(
                    violation_id=f"CSV_{global_user_id}_{rule.rule_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    user_id=global_user_id,
                    user_name=user.name,
                    rule=rule,
                    system_access={
                        func1_system: {"function": rule.function_1.name},
                        func2_system: {"function": rule.function_2.name}
                    },
                    risk_level=rule.risk_level,
                    conflict_type=rule.conflict_type,
                    systems_affected=[func1_system, func2_system] if func1_system != func2_system else [func1_system],
                    compliance_impact=rule.compliance_frameworks
                )

                violations.append(violation)
                self.violations[violation.violation_id] = violation

                # Update summary
                if rule.conflict_type == ConflictType.INTRA_SYSTEM:
                    risk_summary["intra_system"] += 1
                elif rule.conflict_type == ConflictType.CROSS_PLATFORM:
                    risk_summary["cross_platform"] += 1
                else:
                    risk_summary["inter_system"] += 1

        # Calculate aggregate risk
        total_violations = len(violations)
        critical_count = sum(1 for v in violations if v.risk_level == "critical")
        high_count = sum(1 for v in violations if v.risk_level == "high")

        risk_score = min(100, (critical_count * 25) + (high_count * 15) + (total_violations * 5))

        # Update user risk profile
        user.aggregate_risk_score = risk_score
        user.cross_system_violations = total_violations

        return {
            "user": {
                "global_user_id": global_user_id,
                "name": user.name,
                "email": user.email,
                "department": user.department,
                "systems_count": user.systems_count,
                "system_identities": user.system_identities
            },
            "analysis_summary": {
                "total_violations": total_violations,
                "by_type": risk_summary,
                "aggregate_risk_score": risk_score,
                "risk_level": self._score_to_level(risk_score)
            },
            "violations": [
                {
                    "violation_id": v.violation_id,
                    "rule_name": v.rule.name,
                    "rule_description": v.rule.description,
                    "risk_level": v.risk_level,
                    "conflict_type": v.conflict_type.value,
                    "systems_affected": v.systems_affected,
                    "function_1": {
                        "system": v.rule.function_1.system_id,
                        "name": v.rule.function_1.name
                    },
                    "function_2": {
                        "system": v.rule.function_2.system_id,
                        "name": v.rule.function_2.name
                    },
                    "compliance_impact": v.compliance_impact,
                    "business_process": v.rule.business_process
                }
                for v in violations
            ],
            "recommendations": self._generate_recommendations(violations),
            "analyzed_at": datetime.utcnow().isoformat()
        }

    def analyze_enterprise_risk(
        self,
        access_data: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Enterprise-wide cross-system risk analysis

        Args:
            access_data: Dict of global_user_id -> system_id -> access_data
        """
        all_violations = []
        user_summaries = []

        for global_user_id, access_by_system in access_data.items():
            result = self.analyze_user_cross_system(global_user_id, access_by_system)
            if "violations" in result:
                all_violations.extend(result["violations"])
                user_summaries.append({
                    "user_id": global_user_id,
                    "name": result["user"]["name"],
                    "violation_count": result["analysis_summary"]["total_violations"],
                    "risk_score": result["analysis_summary"]["aggregate_risk_score"]
                })

        # Aggregate statistics
        total_users = len(access_data)
        users_with_violations = len([u for u in user_summaries if u["violation_count"] > 0])

        # Group violations by type
        by_conflict_type = {}
        for v in all_violations:
            ct = v["conflict_type"]
            by_conflict_type[ct] = by_conflict_type.get(ct, 0) + 1

        # Group by compliance framework
        by_compliance = {}
        for v in all_violations:
            for framework in v["compliance_impact"]:
                by_compliance[framework] = by_compliance.get(framework, 0) + 1

        # Top risky users
        top_risky = sorted(user_summaries, key=lambda x: x["risk_score"], reverse=True)[:10]

        return {
            "enterprise_summary": {
                "total_users_analyzed": total_users,
                "users_with_violations": users_with_violations,
                "violation_rate": f"{(users_with_violations/total_users*100):.1f}%" if total_users > 0 else "0%",
                "total_violations": len(all_violations),
                "systems_analyzed": len(self.systems)
            },
            "violations_by_type": by_conflict_type,
            "violations_by_compliance": by_compliance,
            "top_risky_users": top_risky,
            "critical_violations": [v for v in all_violations if v["risk_level"] == "critical"],
            "cross_platform_violations": [v for v in all_violations if v["conflict_type"] == "cross_platform"],
            "analyzed_at": datetime.utcnow().isoformat()
        }

    def _user_has_function(
        self,
        access: Dict[str, Any],
        function: SystemFunction
    ) -> bool:
        """Check if user's access includes a function"""
        user_transactions = set(access.get("transactions", []))
        user_roles = set(access.get("roles", []))
        user_permissions = set(access.get("permissions", []))

        # Check transactions
        if function.transactions:
            if user_transactions & set(function.transactions):
                return True

        # Check permissions
        if function.permissions:
            if user_permissions & set(function.permissions):
                return True

        return False

    def _functions_match(
        self,
        user_func: SystemFunction,
        rule_func: SystemFunction
    ) -> bool:
        """Check if a user's function matches a rule function"""
        # Direct match
        if user_func.function_id == rule_func.function_id and user_func.system_id == rule_func.system_id:
            return True

        # Check equivalents via mapping
        equivalents = self.find_equivalent_functions(rule_func)
        for equiv in equivalents:
            if user_func.function_id == equiv.function_id and user_func.system_id == equiv.system_id:
                return True

        return False

    def _score_to_level(self, score: float) -> str:
        """Convert risk score to level"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        violations: List[CrossSystemViolation]
    ) -> List[Dict[str, Any]]:
        """Generate remediation recommendations"""
        recommendations = []

        # Group by systems
        cross_platform = [v for v in violations if v.conflict_type == ConflictType.CROSS_PLATFORM]
        inter_system = [v for v in violations if v.conflict_type == ConflictType.INTER_SYSTEM]

        if cross_platform:
            recommendations.append({
                "priority": "critical",
                "title": "Cross-Platform Access Review Required",
                "description": f"User has {len(cross_platform)} violations spanning SAP and non-SAP systems. These require immediate review as they may indicate excessive privilege accumulation.",
                "action": "Conduct comprehensive access review across all platforms"
            })

        if inter_system:
            recommendations.append({
                "priority": "high",
                "title": "Multi-System SoD Conflicts",
                "description": f"User has {len(inter_system)} conflicts between different systems. Consider role redesign or implementing compensating controls.",
                "action": "Implement cross-system monitoring controls"
            })

        # Critical violations
        critical = [v for v in violations if v.risk_level == "critical"]
        if critical:
            recommendations.append({
                "priority": "critical",
                "title": "Critical Risk Violations",
                "description": f"{len(critical)} critical violations require immediate remediation or documented exception approval.",
                "action": "Escalate to Risk Committee for immediate action"
            })

        return recommendations

    # ==================== Reporting ====================

    def get_cross_system_matrix(self) -> Dict[str, Any]:
        """Generate cross-system conflict matrix"""
        systems = list(self.systems.keys())
        matrix = {}

        for sys1 in systems:
            matrix[sys1] = {}
            for sys2 in systems:
                # Count rules between these systems
                rules = [
                    r for r in self.rules.values()
                    if (r.function_1.system_id == sys1 and r.function_2.system_id == sys2) or
                       (r.function_1.system_id == sys2 and r.function_2.system_id == sys1)
                ]
                matrix[sys1][sys2] = len(rules)

        return {
            "systems": systems,
            "matrix": matrix,
            "total_cross_system_rules": len(self.get_cross_system_rules())
        }

    def export_ruleset(self) -> Dict[str, Any]:
        """Export complete cross-system ruleset"""
        return {
            "export_version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "systems": [
                {
                    "system_id": s["system_id"],
                    "system_type": s["system_type"].value if isinstance(s["system_type"], SystemType) else s["system_type"],
                    "name": s["name"]
                }
                for s in self.systems.values()
            ],
            "functions": {
                sys_id: [
                    {
                        "function_id": f.function_id,
                        "name": f.name,
                        "module": f.module,
                        "transactions": f.transactions,
                        "risk_level": f.risk_level
                    }
                    for f in funcs.values()
                ]
                for sys_id, funcs in self.functions.items()
            },
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "function_1_system": r.function_1.system_id,
                    "function_1_id": r.function_1.function_id,
                    "function_2_system": r.function_2.system_id,
                    "function_2_id": r.function_2.function_id,
                    "risk_level": r.risk_level,
                    "conflict_type": r.conflict_type.value,
                    "compliance_frameworks": r.compliance_frameworks
                }
                for r in self.rules.values()
            ],
            "mappings": [
                {
                    "mapping_id": m.mapping_id,
                    "name": m.name,
                    "functions": {
                        sys_id: f.function_id
                        for sys_id, f in m.function_mappings.items()
                    }
                }
                for m in self.mappings.values()
            ]
        }

    def import_ruleset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Import cross-system ruleset"""
        imported = {"systems": 0, "functions": 0, "rules": 0, "mappings": 0}

        # Import systems
        for sys_data in data.get("systems", []):
            self.register_system(
                system_id=sys_data["system_id"],
                system_type=SystemType(sys_data["system_type"]),
                name=sys_data["name"],
                connection_config={}
            )
            imported["systems"] += 1

        # Import functions
        for sys_id, funcs in data.get("functions", {}).items():
            for func_data in funcs:
                func = SystemFunction(
                    function_id=func_data["function_id"],
                    system_id=sys_id,
                    system_type=SystemType(self.systems[sys_id]["system_type"]) if sys_id in self.systems else SystemType.CUSTOM,
                    name=func_data["name"],
                    description=func_data.get("description", ""),
                    module=func_data["module"],
                    transactions=func_data.get("transactions", []),
                    risk_level=func_data.get("risk_level", "medium")
                )
                self.register_function(sys_id, func)
                imported["functions"] += 1

        # Import rules
        for rule_data in data.get("rules", []):
            func1 = self.functions.get(rule_data["function_1_system"], {}).get(rule_data["function_1_id"])
            func2 = self.functions.get(rule_data["function_2_system"], {}).get(rule_data["function_2_id"])

            if func1 and func2:
                self.create_cross_system_rule(
                    rule_id=rule_data["rule_id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    function_1=func1,
                    function_2=func2,
                    risk_level=rule_data.get("risk_level", "high"),
                    compliance_frameworks=rule_data.get("compliance_frameworks", [])
                )
                imported["rules"] += 1

        return imported

    # ==================== Sample Data ====================

    def _initialize_sample_systems(self):
        """Initialize sample systems for demo"""
        # SAP ECC
        self.register_system("SAP_ECC_PRD", SystemType.SAP_ECC, "SAP ECC Production", {})
        self.register_system("SAP_S4_PRD", SystemType.SAP_S4HANA, "SAP S/4HANA Production", {})
        self.register_system("ARIBA_PRD", SystemType.SAP_ARIBA, "SAP Ariba Procurement", {})
        self.register_system("SFDC_PRD", SystemType.SALESFORCE, "Salesforce CRM", {})
        self.register_system("WORKDAY_PRD", SystemType.WORKDAY, "Workday HCM", {})

        # SAP ECC Functions
        ecc_functions = [
            SystemFunction("ECC_PO_CREATE", "SAP_ECC_PRD", SystemType.SAP_ECC, "Create Purchase Order",
                          "Create and maintain purchase orders", "MM", ["ME21N", "ME22N"], risk_level="medium"),
            SystemFunction("ECC_PO_APPROVE", "SAP_ECC_PRD", SystemType.SAP_ECC, "Approve Purchase Order",
                          "Approve purchase orders", "MM", ["ME28", "ME29N"], risk_level="high"),
            SystemFunction("ECC_VENDOR_CREATE", "SAP_ECC_PRD", SystemType.SAP_ECC, "Create Vendor Master",
                          "Create and maintain vendor master data", "MM", ["XK01", "XK02"], risk_level="high"),
            SystemFunction("ECC_PAY_VENDOR", "SAP_ECC_PRD", SystemType.SAP_ECC, "Process Vendor Payment",
                          "Execute vendor payments", "FI", ["F110", "F-53"], risk_level="critical"),
            SystemFunction("ECC_GR_POST", "SAP_ECC_PRD", SystemType.SAP_ECC, "Post Goods Receipt",
                          "Post goods receipt for purchase orders", "MM", ["MIGO"], risk_level="medium"),
            SystemFunction("ECC_INV_POST", "SAP_ECC_PRD", SystemType.SAP_ECC, "Post Vendor Invoice",
                          "Post and verify vendor invoices", "FI", ["MIRO", "MIR7"], risk_level="high"),
        ]

        for func in ecc_functions:
            self.register_function("SAP_ECC_PRD", func)

        # SAP Ariba Functions
        ariba_functions = [
            SystemFunction("ARIBA_REQ_CREATE", "ARIBA_PRD", SystemType.SAP_ARIBA, "Create Requisition",
                          "Create purchase requisitions", "PROC", permissions=["Requisition.Create"], risk_level="low"),
            SystemFunction("ARIBA_REQ_APPROVE", "ARIBA_PRD", SystemType.SAP_ARIBA, "Approve Requisition",
                          "Approve purchase requisitions", "PROC", permissions=["Requisition.Approve"], risk_level="medium"),
            SystemFunction("ARIBA_SUPPLIER_MANAGE", "ARIBA_PRD", SystemType.SAP_ARIBA, "Manage Suppliers",
                          "Create and manage supplier records", "PROC", permissions=["Supplier.Manage"], risk_level="high"),
            SystemFunction("ARIBA_CONTRACT_MANAGE", "ARIBA_PRD", SystemType.SAP_ARIBA, "Manage Contracts",
                          "Create and manage procurement contracts", "PROC", permissions=["Contract.Manage"], risk_level="high"),
        ]

        for func in ariba_functions:
            self.register_function("ARIBA_PRD", func)

        # Salesforce Functions
        sfdc_functions = [
            SystemFunction("SFDC_OPP_MANAGE", "SFDC_PRD", SystemType.SALESFORCE, "Manage Opportunities",
                          "Create and manage sales opportunities", "SALES", permissions=["Opportunity.Edit"], risk_level="medium"),
            SystemFunction("SFDC_QUOTE_CREATE", "SFDC_PRD", SystemType.SALESFORCE, "Create Quotes",
                          "Create sales quotes and proposals", "SALES", permissions=["Quote.Create"], risk_level="medium"),
            SystemFunction("SFDC_DISCOUNT_APPROVE", "SFDC_PRD", SystemType.SALESFORCE, "Approve Discounts",
                          "Approve sales discounts", "SALES", permissions=["Discount.Approve"], risk_level="high"),
            SystemFunction("SFDC_CONTRACT_EXECUTE", "SFDC_PRD", SystemType.SALESFORCE, "Execute Contracts",
                          "Execute sales contracts", "SALES", permissions=["Contract.Execute"], risk_level="critical"),
        ]

        for func in sfdc_functions:
            self.register_function("SFDC_PRD", func)

        # Workday Functions
        workday_functions = [
            SystemFunction("WD_HIRE", "WORKDAY_PRD", SystemType.WORKDAY, "Hire Employee",
                          "Process new hire transactions", "HR", permissions=["Hire.Process"], risk_level="high"),
            SystemFunction("WD_TERM", "WORKDAY_PRD", SystemType.WORKDAY, "Terminate Employee",
                          "Process terminations", "HR", permissions=["Termination.Process"], risk_level="critical"),
            SystemFunction("WD_COMP_CHANGE", "WORKDAY_PRD", SystemType.WORKDAY, "Change Compensation",
                          "Modify employee compensation", "HR", permissions=["Compensation.Edit"], risk_level="critical"),
            SystemFunction("WD_PAYROLL_RUN", "WORKDAY_PRD", SystemType.WORKDAY, "Run Payroll",
                          "Execute payroll processing", "HR", permissions=["Payroll.Run"], risk_level="critical"),
        ]

        for func in workday_functions:
            self.register_function("WORKDAY_PRD", func)

    def _initialize_cross_system_rules(self):
        """Initialize sample cross-system rules"""
        # P2P Cross-System Rules

        # SAP ECC + Ariba: Requisition to Payment
        if "ECC_PO_CREATE" in self.functions.get("SAP_ECC_PRD", {}) and "ARIBA_SUPPLIER_MANAGE" in self.functions.get("ARIBA_PRD", {}):
            self.create_cross_system_rule(
                rule_id="XSR_001",
                name="Cross-Platform P2P: Supplier + PO",
                description="User can manage suppliers in Ariba AND create POs in SAP - fraud risk",
                function_1=self.functions["SAP_ECC_PRD"]["ECC_PO_CREATE"],
                function_2=self.functions["ARIBA_PRD"]["ARIBA_SUPPLIER_MANAGE"],
                risk_level="critical",
                compliance_frameworks=["SOX", "FRAUD"],
                business_process="Procure-to-Pay",
                risk_description="User could create fictitious supplier and route payments"
            )

        # SAP ECC + Ariba: Contract + Payment
        if "ECC_PAY_VENDOR" in self.functions.get("SAP_ECC_PRD", {}) and "ARIBA_CONTRACT_MANAGE" in self.functions.get("ARIBA_PRD", {}):
            self.create_cross_system_rule(
                rule_id="XSR_002",
                name="Cross-Platform P2P: Contract + Payment",
                description="User can manage contracts in Ariba AND process payments in SAP",
                function_1=self.functions["SAP_ECC_PRD"]["ECC_PAY_VENDOR"],
                function_2=self.functions["ARIBA_PRD"]["ARIBA_CONTRACT_MANAGE"],
                risk_level="critical",
                compliance_frameworks=["SOX"],
                business_process="Procure-to-Pay"
            )

        # Sales + Finance Cross-Platform
        if "SFDC_DISCOUNT_APPROVE" in self.functions.get("SFDC_PRD", {}) and "ECC_INV_POST" in self.functions.get("SAP_ECC_PRD", {}):
            self.create_cross_system_rule(
                rule_id="XSR_003",
                name="Cross-Platform O2C: Discount + Invoice",
                description="User can approve discounts in Salesforce AND post invoices in SAP",
                function_1=self.functions["SFDC_PRD"]["SFDC_DISCOUNT_APPROVE"],
                function_2=self.functions["SAP_ECC_PRD"]["ECC_INV_POST"],
                risk_level="high",
                compliance_frameworks=["SOX", "REVENUE"],
                business_process="Order-to-Cash"
            )

        # HR + Finance Cross-Platform
        if "WD_COMP_CHANGE" in self.functions.get("WORKDAY_PRD", {}) and "ECC_PAY_VENDOR" in self.functions.get("SAP_ECC_PRD", {}):
            self.create_cross_system_rule(
                rule_id="XSR_004",
                name="Cross-Platform HR-FI: Compensation + Payment",
                description="User can change compensation in Workday AND process payments in SAP",
                function_1=self.functions["WORKDAY_PRD"]["WD_COMP_CHANGE"],
                function_2=self.functions["SAP_ECC_PRD"]["ECC_PAY_VENDOR"],
                risk_level="critical",
                compliance_frameworks=["SOX", "FRAUD"],
                business_process="HR-Finance"
            )

        # Payroll + Vendor Payment
        if "WD_PAYROLL_RUN" in self.functions.get("WORKDAY_PRD", {}) and "ECC_PAY_VENDOR" in self.functions.get("SAP_ECC_PRD", {}):
            self.create_cross_system_rule(
                rule_id="XSR_005",
                name="Cross-Platform: Payroll + Vendor Payment",
                description="User can run payroll in Workday AND process vendor payments in SAP",
                function_1=self.functions["WORKDAY_PRD"]["WD_PAYROLL_RUN"],
                function_2=self.functions["SAP_ECC_PRD"]["ECC_PAY_VENDOR"],
                risk_level="critical",
                compliance_frameworks=["SOX", "FRAUD"],
                business_process="Finance"
            )


# Singleton instance
cross_system_engine = CrossSystemSoDEngine()
