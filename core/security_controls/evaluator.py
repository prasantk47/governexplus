"""
Control Evaluator

Evaluates SAP security controls against actual system values.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
import uuid

from db.models.sap_security_controls import (
    SAPSecurityControl,
    ControlValueMapping,
    ControlEvaluation,
    RiskRating,
    EvaluationStatus
)


class ControlEvaluator:
    """Evaluates security controls against actual values."""

    def __init__(self, manager):
        """
        Initialize evaluator with a SecurityControlManager.

        Args:
            manager: SecurityControlManager instance
        """
        self.manager = manager
        self.db = manager.db

    def evaluate_control(
        self,
        control_id: str,
        system_id: str,
        actual_value: Any,
        evaluated_by: Optional[str] = None,
        client: Optional[str] = None,
        additional_data: Optional[Dict] = None
    ) -> ControlEvaluation:
        """
        Evaluate a control against an actual value.

        Args:
            control_id: Control identifier
            system_id: SAP system ID
            actual_value: The actual value from the system
            evaluated_by: User performing the evaluation
            client: SAP client number
            additional_data: Additional context/data

        Returns:
            ControlEvaluation record
        """
        control = self.manager.get_control(control_id)
        if not control:
            raise ValueError(f"Control not found: {control_id}")

        # Determine risk rating based on value mappings
        risk_rating, finding = self._determine_risk_rating(control, actual_value)

        # Get recommendation from matching mapping or control default
        recommendation = self._get_recommendation(control, risk_rating)

        # Build affected users list if applicable
        affected_users = None
        affected_count = 0
        if additional_data and 'affected_users' in additional_data:
            affected_users = additional_data['affected_users']
            affected_count = len(affected_users) if isinstance(affected_users, list) else 0

        evaluation_data = {
            'control_id': control_id,
            'system_id': system_id,
            'client': client,
            'evaluation_id': f"EVAL-{uuid.uuid4().hex[:12].upper()}",
            'evaluation_date': datetime.utcnow(),
            'evaluated_by': evaluated_by or 'system',
            'actual_value': str(actual_value) if actual_value is not None else None,
            'actual_value_details': additional_data,
            'risk_rating': risk_rating.value,
            'status': 'completed',
            'finding_description': finding,
            'affected_users': affected_users,
            'affected_count': affected_count,
            'remediation_steps': [recommendation] if recommendation else None
        }

        return self.manager.record_evaluation(evaluation_data)

    def _determine_risk_rating(
        self,
        control: SAPSecurityControl,
        actual_value: Any
    ) -> Tuple[RiskRating, str]:
        """
        Determine risk rating based on value mappings.

        Returns:
            Tuple of (RiskRating, finding_description)
        """
        # Get value mappings ordered by evaluation order
        mappings = self.db.query(ControlValueMapping).filter(
            ControlValueMapping.control_id == control.id
        ).order_by(ControlValueMapping.evaluation_order).all()

        if not mappings:
            # No mappings, use default rating
            return control.default_risk_rating, f"No specific value mapping found. Using default rating."

        value_str = str(actual_value) if actual_value is not None else ""

        for mapping in mappings:
            if self._matches_condition(value_str, mapping):
                finding = f"Value '{value_str}' matches condition: {mapping.value_condition}"
                if mapping.comment:
                    finding += f". {mapping.comment}"
                return mapping.risk_rating, finding

        # No mapping matched
        return control.default_risk_rating, f"Value '{value_str}' did not match any specific condition."

    def _matches_condition(self, value: str, mapping: ControlValueMapping) -> bool:
        """
        Check if a value matches a mapping condition.

        Supports:
        - Regex patterns (value_pattern field)
        - Numeric ranges (e.g., "Value is between 1 and 3600")
        - Exact matches
        - Contains checks
        """
        condition = mapping.value_condition.lower()
        pattern = mapping.value_pattern

        # If explicit regex pattern is provided
        if pattern:
            try:
                return bool(re.match(pattern, value, re.IGNORECASE))
            except re.error:
                pass

        # Parse common condition patterns
        try:
            # Numeric value
            numeric_value = None
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                pass

            # "Value is between X and Y"
            between_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', condition)
            if between_match and numeric_value is not None:
                low, high = float(between_match.group(1)), float(between_match.group(2))
                return low <= numeric_value <= high

            # "Value is 0" or "Value is higher than X"
            if 'value is 0' in condition and numeric_value == 0:
                return True
            if 'higher than' in condition:
                higher_match = re.search(r'higher than\s+(\d+)', condition)
                if higher_match and numeric_value is not None:
                    threshold = float(higher_match.group(1))
                    return numeric_value > threshold

            # "Value is X" exact match
            is_match = re.search(r'value is\s+(\d+)', condition)
            if is_match and numeric_value is not None:
                expected = float(is_match.group(1))
                return numeric_value == expected

            # Contains specific values like "0 [multiple logons are allowed]"
            if '0 [' in condition and value.strip() == '0':
                return True
            if '1 [' in condition and value.strip() == '1':
                return True

            # "No users found" type conditions
            if 'no users found' in condition:
                if not value or value == '0' or value.lower() == 'none' or value == '[]':
                    return True

            # "Multiple users" conditions
            if 'multiple users' in condition:
                if value and value != '0' and value.lower() != 'none' and value != '[]':
                    return True

            # "Table does not contain" conditions
            if 'does not contain' in condition:
                if not value or value.lower() in ('none', 'empty', '[]', '{}'):
                    return True

            # "Contains" conditions
            if 'contains' in condition and 'does not' not in condition:
                if value and value.lower() not in ('none', 'empty', '[]', '{}'):
                    return True

        except Exception:
            pass

        # Fallback: case-insensitive substring match
        return value.lower() in condition

    def _get_recommendation(self, control: SAPSecurityControl, risk_rating: RiskRating) -> Optional[str]:
        """Get the recommendation for a given risk rating."""
        # First try to find matching value mapping
        mapping = self.db.query(ControlValueMapping).filter(
            ControlValueMapping.control_id == control.id,
            ControlValueMapping.risk_rating == risk_rating
        ).first()

        if mapping and mapping.recommendation:
            return mapping.recommendation

        return control.recommendation

    def batch_evaluate(
        self,
        system_id: str,
        evaluations: List[Dict[str, Any]],
        evaluated_by: Optional[str] = None,
        client: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate multiple controls in batch.

        Args:
            system_id: SAP system ID
            evaluations: List of {control_id, actual_value, additional_data}
            evaluated_by: User performing evaluations
            client: SAP client number

        Returns:
            Summary of evaluation results
        """
        results = {
            'system_id': system_id,
            'evaluation_date': datetime.utcnow().isoformat(),
            'total': len(evaluations),
            'successful': 0,
            'failed': 0,
            'summary': {
                'GREEN': 0,
                'YELLOW': 0,
                'RED': 0
            },
            'evaluations': [],
            'errors': []
        }

        for eval_data in evaluations:
            try:
                evaluation = self.evaluate_control(
                    control_id=eval_data['control_id'],
                    system_id=system_id,
                    actual_value=eval_data.get('actual_value'),
                    evaluated_by=evaluated_by,
                    client=client,
                    additional_data=eval_data.get('additional_data')
                )
                results['successful'] += 1
                results['summary'][evaluation.risk_rating.value] += 1
                results['evaluations'].append({
                    'control_id': eval_data['control_id'],
                    'evaluation_id': evaluation.evaluation_id,
                    'risk_rating': evaluation.risk_rating.value,
                    'finding': evaluation.finding_description
                })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'control_id': eval_data.get('control_id', 'unknown'),
                    'error': str(e)
                })

        return results

    def evaluate_parameter_controls(
        self,
        system_id: str,
        parameter_values: Dict[str, Any],
        evaluated_by: Optional[str] = None,
        client: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate all controls that have profile parameters against a dict of parameter values.

        Args:
            system_id: SAP system ID
            parameter_values: Dict mapping parameter names to values
            evaluated_by: User performing evaluations
            client: SAP client number

        Returns:
            Evaluation results summary
        """
        # Get all controls with profile parameters
        controls = self.db.query(SAPSecurityControl).filter(
            SAPSecurityControl.profile_parameter.isnot(None),
            SAPSecurityControl.profile_parameter != '',
            SAPSecurityControl.profile_parameter != 'N/A'
        ).all()

        evaluations = []
        for control in controls:
            param = control.profile_parameter
            if param in parameter_values:
                evaluations.append({
                    'control_id': control.control_id,
                    'actual_value': parameter_values[param]
                })

        return self.batch_evaluate(
            system_id=system_id,
            evaluations=evaluations,
            evaluated_by=evaluated_by,
            client=client
        )

    def get_evaluation_report(
        self,
        system_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate an evaluation report for a system.

        Args:
            system_id: SAP system ID
            start_date: Report start date
            end_date: Report end date

        Returns:
            Evaluation report data
        """
        from sqlalchemy import func, and_

        query_filters = [ControlEvaluation.system_id == system_id]
        if start_date:
            query_filters.append(ControlEvaluation.evaluation_date >= start_date)
        if end_date:
            query_filters.append(ControlEvaluation.evaluation_date <= end_date)

        # Get all evaluations in period
        evaluations = self.db.query(ControlEvaluation).filter(
            and_(*query_filters)
        ).all()

        # Group by category via control
        from collections import defaultdict
        by_category = defaultdict(lambda: {'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'controls': []})

        for eval in evaluations:
            control = self.manager.get_control_by_db_id(eval.control_id)
            if control:
                category = control.category
                rating = eval.risk_rating.value
                by_category[category][rating] += 1
                by_category[category]['controls'].append({
                    'control_id': control.control_id,
                    'control_name': control.control_name,
                    'rating': rating,
                    'finding': eval.finding_description
                })

        # Calculate overall stats
        total = len(evaluations)
        green = sum(1 for e in evaluations if e.risk_rating == RiskRating.GREEN)
        yellow = sum(1 for e in evaluations if e.risk_rating == RiskRating.YELLOW)
        red = sum(1 for e in evaluations if e.risk_rating == RiskRating.RED)

        compliance_score = (green * 100 + yellow * 50) / total if total > 0 else 0

        return {
            'system_id': system_id,
            'report_period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'summary': {
                'total_evaluations': total,
                'GREEN': green,
                'YELLOW': yellow,
                'RED': red,
                'compliance_score': round(compliance_score, 2)
            },
            'by_category': dict(by_category),
            'critical_findings': [
                {
                    'control_id': self.manager.get_control_by_db_id(e.control_id).control_id if self.manager.get_control_by_db_id(e.control_id) else e.control_id,
                    'finding': e.finding_description,
                    'affected_count': e.affected_count
                }
                for e in evaluations
                if e.risk_rating == RiskRating.RED
            ]
        }
