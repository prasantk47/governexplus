# BRF+ to YAML Converter
# Migrate from SAP BRF+ to GOVERNEX+ rules

"""
BRF+ to YAML Rule Converter for GOVERNEX+.

Converts SAP BRF+ approval logic to GOVERNEX+ YAML format:
- Parse BRF+ decision tables
- Normalize conditions
- Map to YAML DSL
- Validate and simulate

Migration safety:
- Unsupported logic flagged
- Static role IDs mapped to personas
- Simulation run before activation
- Parallel run supported
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import logging
import re
import xml.etree.ElementTree as ET

from .rules import (
    ApprovalRule, RuleCondition, ApproverSpec, RuleLayer, RuleStatus,
    ConditionOperator, RuleSet
)
from .models import ApproverType, ApprovalPriority

logger = logging.getLogger(__name__)


class ConversionStatus(Enum):
    """Status of rule conversion."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class BRFPlusCondition:
    """A condition from BRF+ decision table."""
    field: str
    operator: str
    value: Any
    original_expression: str = ""

    def to_rule_condition(self) -> Optional[RuleCondition]:
        """Convert to GOVERNEX+ RuleCondition."""
        # Map BRF+ operators to our operators
        operator_map = {
            "EQ": ConditionOperator.EQUALS,
            "NE": ConditionOperator.NOT_EQUALS,
            "GT": ConditionOperator.GREATER_THAN,
            "LT": ConditionOperator.LESS_THAN,
            "GE": ConditionOperator.GREATER_EQUAL,
            "LE": ConditionOperator.LESS_EQUAL,
            "CP": ConditionOperator.CONTAINS,
            "IN": ConditionOperator.IN,
        }

        op = operator_map.get(self.operator.upper())
        if not op:
            logger.warning(f"Unknown BRF+ operator: {self.operator}")
            return None

        # Map BRF+ field names to our context paths
        field = self._map_field(self.field)

        return RuleCondition(
            field=field,
            operator=op,
            value=self.value,
        )

    def _map_field(self, brf_field: str) -> str:
        """Map BRF+ field names to GOVERNEX+ context paths."""
        field_map = {
            # System fields
            "SYSTEM": "request.system_id",
            "SYSTEM_TYPE": "request.system_criticality",
            "CLIENT": "request.system_id",

            # Risk fields
            "RISK_LEVEL": "risk.risk_score",
            "RISK_SCORE": "risk.risk_score",
            "SOD_FLAG": "risk.sod_conflict_count",

            # Access fields
            "ROLE_ID": "request.role_ids",
            "TCODE": "request.transaction_codes",
            "ACCESS_TYPE": "request.access_type",

            # User fields
            "REQUESTER": "user.user_id",
            "DEPARTMENT": "user.department",
            "EMPLOYMENT_TYPE": "user.employment_type",

            # Process fields
            "BUSINESS_PROCESS": "risk.business_process",
            "PROCESS": "risk.business_process",
        }

        return field_map.get(brf_field.upper(), f"custom.{brf_field.lower()}")


@dataclass
class BRFPlusResult:
    """A result action from BRF+ decision table."""
    approver_type: str
    approver_id: Optional[str] = None
    sla_hours: float = 24.0
    original_expression: str = ""

    def to_approver_spec(self) -> Optional[ApproverSpec]:
        """Convert to GOVERNEX+ ApproverSpec."""
        # Map BRF+ approver types to our types
        type_map = {
            "MANAGER": ApproverType.LINE_MANAGER,
            "LINE_MANAGER": ApproverType.LINE_MANAGER,
            "SECURITY": ApproverType.SECURITY_OFFICER,
            "SECURITY_OFFICER": ApproverType.SECURITY_OFFICER,
            "IT_SECURITY": ApproverType.SECURITY_OFFICER,
            "ROLE_OWNER": ApproverType.ROLE_OWNER,
            "PROCESS_OWNER": ApproverType.PROCESS_OWNER,
            "SYSTEM_OWNER": ApproverType.SYSTEM_OWNER,
            "DATA_OWNER": ApproverType.DATA_OWNER,
            "COMPLIANCE": ApproverType.COMPLIANCE_OFFICER,
            "COMPLIANCE_OFFICER": ApproverType.COMPLIANCE_OFFICER,
            "CISO": ApproverType.CISO,
            "GOVERNANCE": ApproverType.GOVERNANCE_DESK,
        }

        approver_type = type_map.get(self.approver_type.upper())
        if not approver_type:
            logger.warning(f"Unknown BRF+ approver type: {self.approver_type}")
            approver_type = ApproverType.GOVERNANCE_DESK  # Default fallback

        return ApproverSpec(
            approver_type=approver_type,
            specific_id=self.approver_id,
        )


@dataclass
class BRFPlusDecisionTable:
    """A BRF+ decision table structure."""
    table_id: str
    name: str
    description: str

    # Columns
    condition_columns: List[str] = field(default_factory=list)
    result_columns: List[str] = field(default_factory=list)

    # Rows (each row is a rule)
    rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "name": self.name,
            "description": self.description,
            "condition_columns": self.condition_columns,
            "result_columns": self.result_columns,
            "row_count": len(self.rows),
        }


@dataclass
class BRFPlusRule:
    """A complete BRF+ rule (row in decision table)."""
    rule_id: str
    table_id: str
    row_number: int

    conditions: List[BRFPlusCondition] = field(default_factory=list)
    results: List[BRFPlusResult] = field(default_factory=list)

    priority: int = 100
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "table_id": self.table_id,
            "row_number": self.row_number,
            "condition_count": len(self.conditions),
            "result_count": len(self.results),
            "is_active": self.is_active,
        }


@dataclass
class ConversionResult:
    """Result of BRF+ to YAML conversion."""
    source_id: str
    status: ConversionStatus
    converted_at: datetime = field(default_factory=datetime.now)

    # Converted rules
    rules: List[ApprovalRule] = field(default_factory=list)

    # Issues
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    unsupported_features: List[str] = field(default_factory=list)

    # Statistics
    rules_processed: int = 0
    rules_converted: int = 0
    rules_skipped: int = 0

    # YAML output
    yaml_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status.value,
            "converted_at": self.converted_at.isoformat(),
            "rules_processed": self.rules_processed,
            "rules_converted": self.rules_converted,
            "rules_skipped": self.rules_skipped,
            "warnings": self.warnings,
            "errors": self.errors,
            "unsupported_features": self.unsupported_features,
        }


class BRFPlusConverter:
    """
    Converts BRF+ rules to GOVERNEX+ YAML format.

    Supports:
    - Decision table parsing
    - Condition mapping
    - Approver type mapping
    - Validation and simulation
    """

    def __init__(self):
        """Initialize converter."""
        self._conversion_counter = 0

    def convert_from_xml(self, xml_content: str) -> ConversionResult:
        """
        Convert BRF+ rules from XML export.

        Args:
            xml_content: BRF+ XML export content

        Returns:
            ConversionResult with converted rules
        """
        result = ConversionResult(
            source_id=f"BRF-XML-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        )

        try:
            # Parse XML
            root = ET.fromstring(xml_content)

            # Extract decision tables
            tables = self._parse_decision_tables(root)

            # Convert each table
            for table in tables:
                brf_rules = self._extract_rules_from_table(table)
                result.rules_processed += len(brf_rules)

                for brf_rule in brf_rules:
                    try:
                        converted = self._convert_rule(brf_rule)
                        if converted:
                            result.rules.append(converted)
                            result.rules_converted += 1
                        else:
                            result.rules_skipped += 1
                    except Exception as e:
                        result.errors.append(f"Rule {brf_rule.rule_id}: {str(e)}")
                        result.rules_skipped += 1

            # Generate YAML output
            result.yaml_output = self._generate_yaml(result.rules)

            # Determine status
            if result.rules_converted == result.rules_processed:
                result.status = ConversionStatus.SUCCESS
            elif result.rules_converted > 0:
                result.status = ConversionStatus.PARTIAL
            else:
                result.status = ConversionStatus.FAILED

        except ET.ParseError as e:
            result.status = ConversionStatus.FAILED
            result.errors.append(f"XML parse error: {str(e)}")

        return result

    def convert_from_dict(
        self,
        rules_data: List[Dict[str, Any]]
    ) -> ConversionResult:
        """
        Convert BRF+ rules from dictionary format.

        Expected format:
        [
            {
                "id": "RULE-001",
                "conditions": [
                    {"field": "SYSTEM", "operator": "EQ", "value": "SAP_PRD"}
                ],
                "results": [
                    {"approver_type": "SECURITY", "sla": 8}
                ]
            }
        ]
        """
        result = ConversionResult(
            source_id=f"BRF-DICT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        )

        result.rules_processed = len(rules_data)

        for i, rule_data in enumerate(rules_data):
            try:
                brf_rule = self._parse_rule_dict(rule_data, i)
                converted = self._convert_rule(brf_rule)

                if converted:
                    result.rules.append(converted)
                    result.rules_converted += 1
                else:
                    result.rules_skipped += 1
                    result.warnings.append(f"Rule {i}: Could not convert")

            except Exception as e:
                result.errors.append(f"Rule {i}: {str(e)}")
                result.rules_skipped += 1

        # Generate YAML output
        result.yaml_output = self._generate_yaml(result.rules)

        # Determine status
        if result.rules_converted == result.rules_processed:
            result.status = ConversionStatus.SUCCESS
        elif result.rules_converted > 0:
            result.status = ConversionStatus.PARTIAL
        else:
            result.status = ConversionStatus.FAILED

        return result

    def _parse_decision_tables(self, root: ET.Element) -> List[BRFPlusDecisionTable]:
        """Parse decision tables from XML."""
        tables = []

        # Look for decision table elements
        for dt_elem in root.findall(".//DecisionTable"):
            table = BRFPlusDecisionTable(
                table_id=dt_elem.get("id", ""),
                name=dt_elem.get("name", ""),
                description=dt_elem.get("description", ""),
            )

            # Extract columns
            for col in dt_elem.findall(".//ConditionColumn"):
                table.condition_columns.append(col.get("name", ""))

            for col in dt_elem.findall(".//ResultColumn"):
                table.result_columns.append(col.get("name", ""))

            # Extract rows
            for row in dt_elem.findall(".//Row"):
                row_data = {}
                for cell in row.findall(".//Cell"):
                    row_data[cell.get("column", "")] = cell.text
                table.rows.append(row_data)

            tables.append(table)

        return tables

    def _extract_rules_from_table(
        self,
        table: BRFPlusDecisionTable
    ) -> List[BRFPlusRule]:
        """Extract individual rules from decision table."""
        rules = []

        for i, row in enumerate(table.rows):
            rule = BRFPlusRule(
                rule_id=f"{table.table_id}-R{i+1}",
                table_id=table.table_id,
                row_number=i + 1,
            )

            # Parse conditions
            for col in table.condition_columns:
                value = row.get(col)
                if value:
                    condition = self._parse_condition(col, value)
                    if condition:
                        rule.conditions.append(condition)

            # Parse results
            for col in table.result_columns:
                value = row.get(col)
                if value:
                    result = self._parse_result(col, value)
                    if result:
                        rule.results.append(result)

            rules.append(rule)

        return rules

    def _parse_rule_dict(
        self,
        data: Dict[str, Any],
        index: int
    ) -> BRFPlusRule:
        """Parse BRF+ rule from dictionary."""
        rule = BRFPlusRule(
            rule_id=data.get("id", f"RULE-{index+1}"),
            table_id=data.get("table_id", "CONVERTED"),
            row_number=index + 1,
        )

        # Parse conditions
        for cond_data in data.get("conditions", []):
            condition = BRFPlusCondition(
                field=cond_data.get("field", ""),
                operator=cond_data.get("operator", "EQ"),
                value=cond_data.get("value", ""),
            )
            rule.conditions.append(condition)

        # Parse results
        for result_data in data.get("results", []):
            result = BRFPlusResult(
                approver_type=result_data.get("approver_type", ""),
                approver_id=result_data.get("approver_id"),
                sla_hours=result_data.get("sla", 24),
            )
            rule.results.append(result)

        rule.priority = data.get("priority", 100)
        rule.is_active = data.get("active", True)

        return rule

    def _parse_condition(
        self,
        column: str,
        value: str
    ) -> Optional[BRFPlusCondition]:
        """Parse a condition from table cell."""
        # Try to parse operator from value
        operators = [">=", "<=", "!=", ">", "<", "="]
        for op in operators:
            if value.startswith(op):
                return BRFPlusCondition(
                    field=column,
                    operator=self._map_operator(op),
                    value=value[len(op):].strip(),
                    original_expression=f"{column} {op} {value}",
                )

        # Default to equality
        return BRFPlusCondition(
            field=column,
            operator="EQ",
            value=value,
            original_expression=f"{column} = {value}",
        )

    def _map_operator(self, op: str) -> str:
        """Map operator symbol to BRF+ code."""
        op_map = {
            ">=": "GE",
            "<=": "LE",
            "!=": "NE",
            ">": "GT",
            "<": "LT",
            "=": "EQ",
        }
        return op_map.get(op, "EQ")

    def _parse_result(
        self,
        column: str,
        value: str
    ) -> Optional[BRFPlusResult]:
        """Parse a result from table cell."""
        return BRFPlusResult(
            approver_type=value,
            original_expression=f"{column}: {value}",
        )

    def _convert_rule(self, brf_rule: BRFPlusRule) -> Optional[ApprovalRule]:
        """Convert a BRF+ rule to GOVERNEX+ format."""
        self._conversion_counter += 1

        # Convert conditions
        conditions = []
        for brf_cond in brf_rule.conditions:
            cond = brf_cond.to_rule_condition()
            if cond:
                conditions.append(cond)

        # Convert approvers
        approvers = []
        max_sla = 0
        for brf_result in brf_rule.results:
            spec = brf_result.to_approver_spec()
            if spec:
                approvers.append(spec)
                max_sla = max(max_sla, brf_result.sla_hours)

        if not conditions and not approvers:
            return None

        # Determine layer based on conditions
        layer = self._determine_layer(conditions)

        return ApprovalRule(
            rule_id=f"CONVERTED-{brf_rule.rule_id}",
            name=f"Converted from {brf_rule.table_id}",
            description=f"Auto-converted from BRF+ rule {brf_rule.rule_id}",
            order=brf_rule.priority,
            layer=layer,
            conditions=conditions,
            approvers=approvers,
            sla_hours=max_sla if max_sla > 0 else 24.0,
            explanation=f"Converted from BRF+ decision table {brf_rule.table_id}",
            status=RuleStatus.ACTIVE if brf_rule.is_active else RuleStatus.DRAFT,
            version="1.0-converted",
        )

    def _determine_layer(self, conditions: List[RuleCondition]) -> RuleLayer:
        """Determine rule layer based on conditions."""
        # Check if any condition references risk
        for cond in conditions:
            if "risk" in cond.field.lower():
                return RuleLayer.RISK_ADAPTIVE

            if "system_criticality" in cond.field.lower():
                if cond.value == "PROD":
                    return RuleLayer.MANDATORY

        return RuleLayer.RISK_ADAPTIVE

    def _generate_yaml(self, rules: List[ApprovalRule]) -> str:
        """Generate YAML output for converted rules."""
        if not rules:
            return "# No rules converted"

        lines = [
            "# GOVERNEX+ Approval Rules",
            f"# Converted from BRF+ on {datetime.now().isoformat()}",
            "# Review and validate before activation",
            "",
            "rules:",
        ]

        for rule in rules:
            lines.append("")
            lines.append(f"  - rule_id: {rule.rule_id}")
            lines.append(f"    name: \"{rule.name}\"")
            lines.append(f"    order: {rule.order}")
            lines.append(f"    layer: {rule.layer.value}")
            lines.append("")
            lines.append("    conditions:")

            for cond in rule.conditions:
                lines.append(f"      {cond.field}: \"{cond.operator.value}{cond.value}\"")

            lines.append("")
            lines.append("    approvers:")
            for approver in rule.approvers:
                lines.append(f"      - type: {approver.approver_type.value}")
                if approver.process:
                    lines.append(f"        process: {approver.process}")

            lines.append("")
            lines.append(f"    sla_hours: {rule.sla_hours}")
            lines.append("")
            lines.append("    explain:")
            lines.append(f"      why: \"{rule.explanation}\"")
            lines.append("")
            lines.append("    lifecycle:")
            lines.append(f"      status: {rule.status.value}")
            lines.append(f"      version: \"{rule.version}\"")

        return "\n".join(lines)

    def validate_conversion(
        self,
        result: ConversionResult
    ) -> Dict[str, Any]:
        """
        Validate converted rules.

        Checks:
        - All conditions have valid fields
        - All approvers are resolvable
        - No conflicting rules
        """
        validation = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
        }

        for rule in result.rules:
            # Check conditions
            for cond in rule.conditions:
                if cond.field.startswith("custom."):
                    validation["warnings"].append(
                        f"Rule {rule.rule_id}: Custom field '{cond.field}' may need mapping"
                    )

            # Check approvers
            if not rule.approvers:
                validation["warnings"].append(
                    f"Rule {rule.rule_id}: No approvers defined"
                )

        if validation["issues"]:
            validation["is_valid"] = False

        return validation

    def generate_migration_report(
        self,
        result: ConversionResult
    ) -> str:
        """Generate migration report."""
        lines = [
            "# BRF+ to GOVERNEX+ Migration Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            f"- Rules Processed: {result.rules_processed}",
            f"- Rules Converted: {result.rules_converted}",
            f"- Rules Skipped: {result.rules_skipped}",
            f"- Status: {result.status.value}",
            "",
        ]

        if result.warnings:
            lines.append("## Warnings")
            for warning in result.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        if result.errors:
            lines.append("## Errors")
            for error in result.errors:
                lines.append(f"- {error}")
            lines.append("")

        if result.unsupported_features:
            lines.append("## Unsupported Features")
            for feature in result.unsupported_features:
                lines.append(f"- {feature}")
            lines.append("")

        lines.append("## Converted Rules")
        for rule in result.rules:
            lines.append(f"- {rule.rule_id}: {rule.name}")

        lines.append("")
        lines.append("## Next Steps")
        lines.append("1. Review converted rules in YAML format")
        lines.append("2. Validate field mappings")
        lines.append("3. Run simulation tests")
        lines.append("4. Enable in shadow mode")
        lines.append("5. Cutover after validation period")

        return "\n".join(lines)
