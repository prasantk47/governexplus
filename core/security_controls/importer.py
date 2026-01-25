"""
Control Importer

Imports SAP security controls from various formats (CSV, JSON).
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import csv
import json
import io
from collections import defaultdict

from db.models.sap_security_controls import RiskRating


class ControlImporter:
    """Imports security controls from external sources."""

    def __init__(self, manager):
        """
        Initialize importer with a SecurityControlManager.

        Args:
            manager: SecurityControlManager instance
        """
        self.manager = manager

    def import_from_csv(
        self,
        csv_content: str,
        delimiter: str = '\t',
        update_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Import controls from CSV/TSV content.

        Expected columns:
        - Control: Control ID (e.g., "Control 001")
        - Business Area: Business area name
        - Control Type: Type of control
        - Final categorization: Category
        - Control Description: Description text
        - Purpose: Purpose of the control
        - Procedure: How to check
        - Profile Parameter: SAP parameter name
        - Return value in system: Expected value description
        - Risk Rating: GREEN/YELLOW/RED
        - Recommendation: Remediation guidance
        - Comment: Additional comments

        Args:
            csv_content: CSV/TSV string content
            delimiter: Field delimiter
            update_existing: Whether to update existing controls

        Returns:
            Import summary
        """
        results = {
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'controls': []
        }

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)

        # Group rows by control ID (multiple rows per control for different value mappings)
        controls_data = defaultdict(list)
        for row in reader:
            control_id = row.get('Control', '').strip()
            if control_id:
                controls_data[control_id].append(row)

        # Process each control
        for control_id, rows in controls_data.items():
            try:
                result = self._process_control_rows(control_id, rows, update_existing)
                results['controls'].append(result)

                if result['status'] == 'imported':
                    results['imported'] += 1
                elif result['status'] == 'updated':
                    results['updated'] += 1
                else:
                    results['skipped'] += 1

            except Exception as e:
                results['errors'].append({
                    'control_id': control_id,
                    'error': str(e)
                })

        return results

    def _process_control_rows(
        self,
        control_id: str,
        rows: List[Dict],
        update_existing: bool
    ) -> Dict[str, Any]:
        """Process rows for a single control."""
        # Use first row for control definition
        first_row = rows[0]

        # Normalize control ID
        normalized_id = self._normalize_control_id(control_id)

        # Check if control exists
        existing = self.manager.get_control(normalized_id)

        if existing and not update_existing:
            return {
                'control_id': normalized_id,
                'status': 'skipped',
                'reason': 'Control already exists'
            }

        # Build control data
        control_data = {
            'control_id': normalized_id,
            'control_name': first_row.get('Control Description', '').strip(),
            'business_area': first_row.get('Business Area', '').strip(),
            'control_type': first_row.get('Control Type', '').strip(),
            'category': first_row.get('Final categorization', '').strip(),
            'description': first_row.get('Control Description', '').strip(),
            'purpose': first_row.get('Purpose', '').strip(),
            'procedure': first_row.get('Procedure', '').strip(),
            'profile_parameter': first_row.get('Profile Parameter', '').strip() or None,
            'expected_value': first_row.get('Return value in system', '').strip(),
            'recommendation': first_row.get('Recommendation', '').strip(),
            'comment': first_row.get('Comment', '').strip(),
            'default_risk_rating': 'YELLOW',  # Default
            'status': 'active',
            'is_automated': bool(first_row.get('Profile Parameter', '').strip() and
                                first_row.get('Profile Parameter', '').strip() != 'N/A'),
            'value_mappings': []
        }

        # Build value mappings from all rows
        for row in rows:
            risk_rating = row.get('Risk Rating', '').strip().upper()
            if risk_rating in ['GREEN', 'YELLOW', 'RED']:
                value_condition = row.get('Return value in system', '').strip()
                if value_condition:
                    mapping = {
                        'value_condition': value_condition,
                        'risk_rating': risk_rating,
                        'recommendation': row.get('Recommendation', '').strip(),
                        'comment': row.get('Comment', '').strip()
                    }
                    control_data['value_mappings'].append(mapping)

        # Set default risk rating based on most restrictive
        if control_data['value_mappings']:
            ratings = [m['risk_rating'] for m in control_data['value_mappings']]
            if 'RED' in ratings:
                control_data['default_risk_rating'] = 'RED'
            elif 'YELLOW' in ratings:
                control_data['default_risk_rating'] = 'YELLOW'
            else:
                control_data['default_risk_rating'] = 'GREEN'

        # Create or update
        if existing:
            self.manager.update_control(normalized_id, control_data)
            return {
                'control_id': normalized_id,
                'status': 'updated',
                'mappings': len(control_data['value_mappings'])
            }
        else:
            self.manager.create_control(control_data)
            return {
                'control_id': normalized_id,
                'status': 'imported',
                'mappings': len(control_data['value_mappings'])
            }

    def _normalize_control_id(self, control_id: str) -> str:
        """Normalize control ID to standard format."""
        # "Control 001" -> "CTRL-001"
        import re
        match = re.search(r'(\d+)', control_id)
        if match:
            num = match.group(1).zfill(3)
            return f"CTRL-{num}"
        return control_id.replace(' ', '-').upper()

    def import_from_json(
        self,
        json_content: str,
        update_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Import controls from JSON content.

        Expected format:
        [
            {
                "control_id": "CTRL-001",
                "control_name": "...",
                "business_area": "...",
                ...
                "value_mappings": [
                    {"value_condition": "...", "risk_rating": "GREEN", ...},
                    ...
                ]
            },
            ...
        ]

        Args:
            json_content: JSON string
            update_existing: Whether to update existing controls

        Returns:
            Import summary
        """
        results = {
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'controls': []
        }

        data = json.loads(json_content)
        if not isinstance(data, list):
            data = [data]

        for control_data in data:
            try:
                control_id = control_data.get('control_id', '')
                existing = self.manager.get_control(control_id)

                if existing and not update_existing:
                    results['skipped'] += 1
                    results['controls'].append({
                        'control_id': control_id,
                        'status': 'skipped',
                        'reason': 'Control already exists'
                    })
                    continue

                if existing:
                    self.manager.update_control(control_id, control_data)
                    results['updated'] += 1
                    results['controls'].append({
                        'control_id': control_id,
                        'status': 'updated'
                    })
                else:
                    self.manager.create_control(control_data)
                    results['imported'] += 1
                    results['controls'].append({
                        'control_id': control_id,
                        'status': 'imported'
                    })

            except Exception as e:
                results['errors'].append({
                    'control_id': control_data.get('control_id', 'unknown'),
                    'error': str(e)
                })

        return results

    def export_to_json(self, control_ids: Optional[List[str]] = None) -> str:
        """
        Export controls to JSON format.

        Args:
            control_ids: Optional list of control IDs to export.
                        If None, exports all controls.

        Returns:
            JSON string
        """
        if control_ids:
            controls = []
            for cid in control_ids:
                control = self.manager.get_control(cid)
                if control:
                    data = control.to_dict()
                    data['value_mappings'] = self.manager.get_value_mappings(cid)
                    controls.append(data)
        else:
            result = self.manager.list_controls(limit=10000)
            controls = result['items']
            for control in controls:
                control['value_mappings'] = self.manager.get_value_mappings(control['control_id'])

        return json.dumps(controls, indent=2, default=str)

    def export_to_csv(
        self,
        control_ids: Optional[List[str]] = None,
        delimiter: str = '\t'
    ) -> str:
        """
        Export controls to CSV format.

        Args:
            control_ids: Optional list of control IDs to export.
                        If None, exports all controls.
            delimiter: Field delimiter

        Returns:
            CSV string
        """
        if control_ids:
            controls = []
            for cid in control_ids:
                control = self.manager.get_control(cid)
                if control:
                    controls.append(control.to_dict())
        else:
            result = self.manager.list_controls(limit=10000)
            controls = result['items']

        output = io.StringIO()
        fieldnames = [
            'control_id', 'control_name', 'business_area', 'control_type',
            'category', 'description', 'purpose', 'procedure',
            'profile_parameter', 'expected_value', 'default_risk_rating',
            'recommendation', 'comment', 'status', 'is_automated'
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter, extrasaction='ignore')
        writer.writeheader()

        for control in controls:
            writer.writerow(control)

        return output.getvalue()

    def get_import_template(self, format: str = 'json') -> str:
        """
        Get a template for importing controls.

        Args:
            format: 'json' or 'csv'

        Returns:
            Template string
        """
        if format == 'json':
            template = [
                {
                    "control_id": "CTRL-001",
                    "control_name": "Example Control",
                    "business_area": "Security Check Authentication Checks",
                    "control_type": "General Authentication",
                    "category": "General Authentication",
                    "description": "Description of what this control checks",
                    "purpose": "Why this control is important",
                    "procedure": "How to perform this check",
                    "profile_parameter": "rdisp/gui_auto_logout",
                    "expected_value": "Value between 1 and 3600",
                    "default_risk_rating": "YELLOW",
                    "recommendation": "Set value to 1800 or 3600",
                    "comment": "Additional notes",
                    "status": "active",
                    "is_automated": True,
                    "compliance_frameworks": ["SOX", "ISO27001"],
                    "value_mappings": [
                        {
                            "value_condition": "Value is between 1 and 3600",
                            "risk_rating": "GREEN",
                            "recommendation": "Value is compliant"
                        },
                        {
                            "value_condition": "Value is 0 or higher than 3600",
                            "risk_rating": "YELLOW",
                            "recommendation": "Set value to 1800 or 3600"
                        }
                    ]
                }
            ]
            return json.dumps(template, indent=2)
        else:
            return "Control\tBusiness Area\tControl Type\tFinal categorization\tControl Description\tPurpose\tProcedure\tProfile Parameter\tReturn value in system\tRisk Rating\tRecommendation\tComment\n" \
                   "Control 001\tSecurity Check Authentication Checks\tGeneral Authentication\tGeneral Authentication\tExample Control\tPurpose text\tProcedure text\trdisp/gui_auto_logout\tValue is between 1 and 3600\tGREEN\tValue is compliant\tNotes\n"
