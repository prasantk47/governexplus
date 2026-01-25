"""
Security Control Manager

Handles CRUD operations and business logic for SAP security controls.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, distinct
import uuid
import re

from db.models.sap_security_controls import (
    SAPSecurityControl,
    ControlValueMapping,
    ControlEvaluation,
    ControlException,
    SystemSecurityProfile,
    RiskRating,
    ControlStatus,
    EvaluationStatus
)


class SecurityControlManager:
    """Manages SAP security controls and evaluations."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # Control CRUD Operations
    # =========================================================================

    def create_control(self, control_data: Dict[str, Any]) -> SAPSecurityControl:
        """Create a new security control."""
        control = SAPSecurityControl(
            control_id=control_data.get('control_id', f"CTRL-{uuid.uuid4().hex[:8].upper()}"),
            control_name=control_data['control_name'],
            business_area=control_data['business_area'],
            control_type=control_data['control_type'],
            category=control_data['category'],
            description=control_data['description'],
            purpose=control_data.get('purpose'),
            procedure=control_data.get('procedure'),
            profile_parameter=control_data.get('profile_parameter'),
            expected_value=control_data.get('expected_value'),
            default_risk_rating=RiskRating(control_data.get('default_risk_rating', 'YELLOW')),
            recommendation=control_data.get('recommendation'),
            comment=control_data.get('comment'),
            status=ControlStatus(control_data.get('status', 'active')),
            is_automated=control_data.get('is_automated', False),
            compliance_frameworks=control_data.get('compliance_frameworks', [])
        )

        self.db.add(control)
        self.db.flush()  # Get the ID

        # Add value mappings if provided
        if 'value_mappings' in control_data:
            for idx, mapping_data in enumerate(control_data['value_mappings']):
                mapping = ControlValueMapping(
                    control_id=control.id,
                    value_condition=mapping_data['value_condition'],
                    value_pattern=mapping_data.get('value_pattern'),
                    risk_rating=RiskRating(mapping_data['risk_rating']),
                    recommendation=mapping_data.get('recommendation'),
                    comment=mapping_data.get('comment'),
                    evaluation_order=mapping_data.get('evaluation_order', idx)
                )
                self.db.add(mapping)

        self.db.commit()
        return control

    def get_control(self, control_id: str) -> Optional[SAPSecurityControl]:
        """Get a control by ID."""
        return self.db.query(SAPSecurityControl).filter(
            or_(
                SAPSecurityControl.control_id == control_id,
                SAPSecurityControl.id == control_id if control_id.isdigit() else False
            )
        ).first()

    def get_control_by_db_id(self, db_id: int) -> Optional[SAPSecurityControl]:
        """Get a control by database ID."""
        return self.db.query(SAPSecurityControl).filter(
            SAPSecurityControl.id == db_id
        ).first()

    def list_controls(
        self,
        category: Optional[str] = None,
        business_area: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List controls with filtering and pagination."""
        query = self.db.query(SAPSecurityControl)

        if category:
            query = query.filter(SAPSecurityControl.category == category)
        if business_area:
            query = query.filter(SAPSecurityControl.business_area == business_area)
        if status:
            query = query.filter(SAPSecurityControl.status == ControlStatus(status))
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    SAPSecurityControl.control_name.ilike(search_filter),
                    SAPSecurityControl.description.ilike(search_filter),
                    SAPSecurityControl.control_id.ilike(search_filter)
                )
            )

        total = query.count()
        controls = query.order_by(SAPSecurityControl.control_id).offset(offset).limit(limit).all()

        return {
            'total': total,
            'offset': offset,
            'limit': limit,
            'items': [c.to_dict() for c in controls]
        }

    def update_control(self, control_id: str, update_data: Dict[str, Any]) -> Optional[SAPSecurityControl]:
        """Update an existing control."""
        control = self.get_control(control_id)
        if not control:
            return None

        updatable_fields = [
            'control_name', 'business_area', 'control_type', 'category',
            'description', 'purpose', 'procedure', 'profile_parameter',
            'expected_value', 'recommendation', 'comment', 'is_automated',
            'compliance_frameworks'
        ]

        for field in updatable_fields:
            if field in update_data:
                setattr(control, field, update_data[field])

        if 'default_risk_rating' in update_data:
            control.default_risk_rating = RiskRating(update_data['default_risk_rating'])
        if 'status' in update_data:
            control.status = ControlStatus(update_data['status'])

        self.db.commit()
        return control

    def delete_control(self, control_id: str) -> bool:
        """Delete a control."""
        control = self.get_control(control_id)
        if not control:
            return False

        self.db.delete(control)
        self.db.commit()
        return True

    # =========================================================================
    # Value Mappings
    # =========================================================================

    def add_value_mapping(self, control_id: str, mapping_data: Dict[str, Any]) -> ControlValueMapping:
        """Add a value mapping to a control."""
        control = self.get_control(control_id)
        if not control:
            raise ValueError(f"Control not found: {control_id}")

        mapping = ControlValueMapping(
            control_id=control.id,
            value_condition=mapping_data['value_condition'],
            value_pattern=mapping_data.get('value_pattern'),
            risk_rating=RiskRating(mapping_data['risk_rating']),
            recommendation=mapping_data.get('recommendation'),
            comment=mapping_data.get('comment'),
            evaluation_order=mapping_data.get('evaluation_order', 0)
        )

        self.db.add(mapping)
        self.db.commit()
        return mapping

    def get_value_mappings(self, control_id: str) -> List[Dict[str, Any]]:
        """Get all value mappings for a control."""
        control = self.get_control(control_id)
        if not control:
            return []

        mappings = self.db.query(ControlValueMapping).filter(
            ControlValueMapping.control_id == control.id
        ).order_by(ControlValueMapping.evaluation_order).all()

        return [m.to_dict() for m in mappings]

    # =========================================================================
    # Evaluations
    # =========================================================================

    def record_evaluation(self, evaluation_data: Dict[str, Any]) -> ControlEvaluation:
        """Record a control evaluation result."""
        control = self.get_control(evaluation_data['control_id'])
        if not control:
            raise ValueError(f"Control not found: {evaluation_data['control_id']}")

        evaluation = ControlEvaluation(
            control_id=control.id,
            system_id=evaluation_data['system_id'],
            client=evaluation_data.get('client'),
            evaluation_id=evaluation_data.get('evaluation_id', f"EVAL-{uuid.uuid4().hex[:12].upper()}"),
            evaluation_date=evaluation_data.get('evaluation_date', datetime.utcnow()),
            evaluated_by=evaluation_data.get('evaluated_by'),
            actual_value=evaluation_data.get('actual_value'),
            actual_value_details=evaluation_data.get('actual_value_details'),
            risk_rating=RiskRating(evaluation_data['risk_rating']),
            status=EvaluationStatus(evaluation_data.get('status', 'completed')),
            finding_description=evaluation_data.get('finding_description'),
            affected_users=evaluation_data.get('affected_users'),
            affected_count=evaluation_data.get('affected_count', 0),
            evidence=evaluation_data.get('evidence'),
            evidence_path=evaluation_data.get('evidence_path'),
            remediation_steps=evaluation_data.get('remediation_steps'),
            remediation_deadline=evaluation_data.get('remediation_deadline'),
            remediation_owner=evaluation_data.get('remediation_owner')
        )

        self.db.add(evaluation)
        self.db.commit()

        # Update system security profile
        self._update_system_profile(evaluation_data['system_id'])

        return evaluation

    def get_evaluations(
        self,
        control_id: Optional[str] = None,
        system_id: Optional[str] = None,
        risk_rating: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get evaluations with filtering."""
        query = self.db.query(ControlEvaluation)

        if control_id:
            control = self.get_control(control_id)
            if control:
                query = query.filter(ControlEvaluation.control_id == control.id)
        if system_id:
            query = query.filter(ControlEvaluation.system_id == system_id)
        if risk_rating:
            query = query.filter(ControlEvaluation.risk_rating == RiskRating(risk_rating))
        if start_date:
            query = query.filter(ControlEvaluation.evaluation_date >= start_date)
        if end_date:
            query = query.filter(ControlEvaluation.evaluation_date <= end_date)

        total = query.count()
        evaluations = query.order_by(ControlEvaluation.evaluation_date.desc()).offset(offset).limit(limit).all()

        return {
            'total': total,
            'offset': offset,
            'limit': limit,
            'items': [e.to_dict() for e in evaluations]
        }

    def get_latest_evaluation(self, control_id: str, system_id: str) -> Optional[ControlEvaluation]:
        """Get the latest evaluation for a control on a system."""
        control = self.get_control(control_id)
        if not control:
            return None

        return self.db.query(ControlEvaluation).filter(
            and_(
                ControlEvaluation.control_id == control.id,
                ControlEvaluation.system_id == system_id
            )
        ).order_by(ControlEvaluation.evaluation_date.desc()).first()

    # =========================================================================
    # Exceptions
    # =========================================================================

    def create_exception(self, exception_data: Dict[str, Any]) -> ControlException:
        """Create an exception request."""
        control = self.get_control(exception_data['control_id'])
        if not control:
            raise ValueError(f"Control not found: {exception_data['control_id']}")

        exception = ControlException(
            exception_id=exception_data.get('exception_id', f"EXC-{uuid.uuid4().hex[:12].upper()}"),
            control_id=control.id,
            system_id=exception_data.get('system_id'),
            requested_by=exception_data['requested_by'],
            business_justification=exception_data['business_justification'],
            risk_acceptance=exception_data.get('risk_acceptance'),
            compensating_controls=exception_data.get('compensating_controls'),
            valid_from=exception_data.get('valid_from'),
            valid_to=exception_data.get('valid_to'),
            is_permanent=exception_data.get('is_permanent', False),
            review_frequency_days=exception_data.get('review_frequency_days', 90)
        )

        self.db.add(exception)
        self.db.commit()
        return exception

    def approve_exception(
        self,
        exception_id: str,
        approved_by: str,
        approved: bool = True,
        rejection_reason: Optional[str] = None
    ) -> Optional[ControlException]:
        """Approve or reject an exception."""
        exception = self.db.query(ControlException).filter(
            ControlException.exception_id == exception_id
        ).first()

        if not exception:
            return None

        exception.approval_status = 'approved' if approved else 'rejected'
        exception.approved_by = approved_by
        exception.approved_date = datetime.utcnow()

        if not approved:
            exception.rejection_reason = rejection_reason
        else:
            # Set next review date
            from datetime import timedelta
            exception.next_review_date = datetime.utcnow() + timedelta(days=exception.review_frequency_days)

        self.db.commit()
        return exception

    def get_exceptions(
        self,
        control_id: Optional[str] = None,
        system_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get exceptions with filtering."""
        query = self.db.query(ControlException)

        if control_id:
            control = self.get_control(control_id)
            if control:
                query = query.filter(ControlException.control_id == control.id)
        if system_id:
            query = query.filter(ControlException.system_id == system_id)
        if status:
            query = query.filter(ControlException.approval_status == status)

        total = query.count()
        exceptions = query.order_by(ControlException.requested_date.desc()).offset(offset).limit(limit).all()

        return {
            'total': total,
            'offset': offset,
            'limit': limit,
            'items': [e.to_dict() for e in exceptions]
        }

    # =========================================================================
    # System Profiles
    # =========================================================================

    def _update_system_profile(self, system_id: str):
        """Update the security profile for a system based on latest evaluations."""
        profile = self.db.query(SystemSecurityProfile).filter(
            SystemSecurityProfile.system_id == system_id
        ).first()

        if not profile:
            profile = SystemSecurityProfile(system_id=system_id)
            self.db.add(profile)

        # Get latest evaluation for each control
        from sqlalchemy import distinct
        subquery = self.db.query(
            ControlEvaluation.control_id,
            func.max(ControlEvaluation.evaluation_date).label('max_date')
        ).filter(
            ControlEvaluation.system_id == system_id
        ).group_by(ControlEvaluation.control_id).subquery()

        latest_evaluations = self.db.query(ControlEvaluation).join(
            subquery,
            and_(
                ControlEvaluation.control_id == subquery.c.control_id,
                ControlEvaluation.evaluation_date == subquery.c.max_date
            )
        ).filter(ControlEvaluation.system_id == system_id).all()

        # Calculate counts
        green_count = sum(1 for e in latest_evaluations if e.risk_rating == RiskRating.GREEN)
        yellow_count = sum(1 for e in latest_evaluations if e.risk_rating == RiskRating.YELLOW)
        red_count = sum(1 for e in latest_evaluations if e.risk_rating == RiskRating.RED)

        total_controls = self.db.query(SAPSecurityControl).filter(
            SAPSecurityControl.status == ControlStatus.ACTIVE
        ).count()

        # Calculate score (GREEN=100, YELLOW=50, RED=0)
        evaluated_count = len(latest_evaluations)
        if evaluated_count > 0:
            score = (green_count * 100 + yellow_count * 50) / evaluated_count
        else:
            score = 0

        # Update profile
        profile.last_evaluation_date = datetime.utcnow()
        profile.total_controls = total_controls
        profile.controls_evaluated = evaluated_count
        profile.green_count = green_count
        profile.yellow_count = yellow_count
        profile.red_count = red_count
        profile.security_score = round(score, 2)

        self.db.commit()

    def get_system_profile(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get security profile for a system."""
        profile = self.db.query(SystemSecurityProfile).filter(
            SystemSecurityProfile.system_id == system_id
        ).first()

        return profile.to_dict() if profile else None

    def get_all_system_profiles(self) -> List[Dict[str, Any]]:
        """Get all system security profiles."""
        profiles = self.db.query(SystemSecurityProfile).all()
        return [p.to_dict() for p in profiles]

    # =========================================================================
    # Statistics and Dashboard
    # =========================================================================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for the dashboard."""
        total_controls = self.db.query(SAPSecurityControl).filter(
            SAPSecurityControl.status == ControlStatus.ACTIVE
        ).count()

        # Category breakdown
        category_stats = self.db.query(
            SAPSecurityControl.category,
            func.count(SAPSecurityControl.id).label('count')
        ).filter(
            SAPSecurityControl.status == ControlStatus.ACTIVE
        ).group_by(SAPSecurityControl.category).all()

        # Recent evaluations
        recent_evaluations = self.db.query(ControlEvaluation).order_by(
            ControlEvaluation.evaluation_date.desc()
        ).limit(10).all()

        # Evaluation summary
        eval_summary = self.db.query(
            ControlEvaluation.risk_rating,
            func.count(ControlEvaluation.id).label('count')
        ).group_by(ControlEvaluation.risk_rating).all()

        # Pending exceptions
        pending_exceptions = self.db.query(ControlException).filter(
            ControlException.approval_status == 'pending'
        ).count()

        return {
            'total_controls': total_controls,
            'category_breakdown': {str(c.category): c.count for c in category_stats},
            'recent_evaluations': [e.to_dict() for e in recent_evaluations],
            'evaluation_summary': {
                r.risk_rating.value if r.risk_rating else 'unknown': r.count
                for r in eval_summary
            },
            'pending_exceptions': pending_exceptions
        }

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        categories = self.db.query(distinct(SAPSecurityControl.category)).all()
        return [c[0] for c in categories if c[0]]

    def get_business_areas(self) -> List[str]:
        """Get all unique business areas."""
        areas = self.db.query(distinct(SAPSecurityControl.business_area)).all()
        return [a[0] for a in areas if a[0]]
