"""
Audit Logger

Centralized audit logging service for all GRC platform activities.
Provides structured logging to database with support for compliance requirements.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import json
import uuid

from db.models.audit import AuditLog, AuditAction
from db.database import db_manager

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Centralized audit logging service.

    Features:
    - Structured audit entries
    - Database persistence
    - Compliance tagging
    - Query and reporting capabilities
    """

    def __init__(self, db_session=None):
        """
        Initialize audit logger.

        Args:
            db_session: SQLAlchemy session (optional, uses global if None)
        """
        self._db_session = db_session

    def _get_session(self):
        """Get database session"""
        if self._db_session:
            return self._db_session
        return db_manager.get_session()

    def log(self,
            action: AuditAction,
            actor_user_id: Optional[str] = None,
            actor_username: Optional[str] = None,
            actor_type: str = 'user',
            target_type: Optional[str] = None,
            target_id: Optional[str] = None,
            target_name: Optional[str] = None,
            source_system: Optional[str] = None,
            source_ip: Optional[str] = None,
            user_agent: Optional[str] = None,
            session_id: Optional[str] = None,
            details: Optional[Dict] = None,
            old_values: Optional[Dict] = None,
            new_values: Optional[Dict] = None,
            success: bool = True,
            error_message: Optional[str] = None,
            compliance_relevant: bool = False,
            compliance_tags: Optional[List[str]] = None) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: The type of action being logged
            actor_user_id: ID of user performing the action
            actor_username: Username of actor
            actor_type: Type of actor (user, system, api)
            target_type: Type of target object
            target_id: ID of target object
            target_name: Name of target object
            source_system: System where action originated
            source_ip: IP address of actor
            user_agent: Browser/client user agent
            session_id: Session identifier
            details: Additional details as dict
            old_values: Previous values (for changes)
            new_values: New values (for changes)
            success: Whether action succeeded
            error_message: Error message if failed
            compliance_relevant: Flag for compliance-critical entries
            compliance_tags: List of compliance frameworks (SOX, GDPR, etc.)

        Returns:
            AuditLog object
        """

        # Determine action category
        action_category = self._get_action_category(action)

        # Create audit entry
        audit_entry = AuditLog(
            timestamp=datetime.utcnow(),
            action=action,
            action_category=action_category,
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            actor_type=actor_type,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            source_system=source_system,
            source_ip=source_ip,
            user_agent=user_agent,
            session_id=session_id,
            details=details,
            old_values=old_values,
            new_values=new_values,
            success=success,
            error_message=error_message,
            compliance_relevant=compliance_relevant,
            compliance_tags=compliance_tags
        )

        # Persist to database
        session = self._get_session()
        try:
            session.add(audit_entry)
            session.commit()
            session.refresh(audit_entry)

            # Also log to standard logger for real-time monitoring
            log_level = logging.INFO if success else logging.WARNING
            logger.log(
                log_level,
                f"AUDIT: {action.value} | Actor: {actor_user_id} | "
                f"Target: {target_type}:{target_id} | Success: {success}"
            )

            return audit_entry

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to write audit log: {e}")
            raise
        finally:
            if not self._db_session:  # Only close if we created it
                session.close()

    def _get_action_category(self, action: AuditAction) -> str:
        """Determine category from action type"""
        action_name = action.value

        if action_name.startswith('user_'):
            return 'user'
        elif action_name.startswith('role_'):
            return 'role'
        elif action_name.startswith('risk_') or action_name.startswith('violation_'):
            return 'risk'
        elif action_name.startswith('ff_'):
            return 'firefighter'
        else:
            return 'system'

    # ==========================================================================
    # Convenience Methods for Common Actions
    # ==========================================================================

    def log_user_login(self, user_id: str, username: str,
                      source_ip: str, user_agent: str,
                      success: bool = True, error: str = None):
        """Log user login attempt"""
        return self.log(
            action=AuditAction.USER_LOGIN,
            actor_user_id=user_id,
            actor_username=username,
            source_ip=source_ip,
            user_agent=user_agent,
            success=success,
            error_message=error,
            compliance_relevant=True,
            compliance_tags=['SOX', 'ISO27001']
        )

    def log_role_assignment(self, target_user_id: str, target_username: str,
                           role_id: str, role_name: str,
                           assigned_by: str, request_id: str = None):
        """Log role assignment to user"""
        return self.log(
            action=AuditAction.ROLE_ASSIGNED,
            actor_user_id=assigned_by,
            target_type='user',
            target_id=target_user_id,
            target_name=target_username,
            details={
                'role_id': role_id,
                'role_name': role_name,
                'request_id': request_id
            },
            compliance_relevant=True,
            compliance_tags=['SOX']
        )

    def log_violation_detected(self, user_id: str, username: str,
                              rule_id: str, rule_name: str,
                              severity: str, details: Dict):
        """Log risk violation detection"""
        return self.log(
            action=AuditAction.VIOLATION_DETECTED,
            actor_type='system',
            target_type='user',
            target_id=user_id,
            target_name=username,
            details={
                'rule_id': rule_id,
                'rule_name': rule_name,
                'severity': severity,
                **details
            },
            compliance_relevant=True,
            compliance_tags=['SOX', 'GRC']
        )

    def log_firefighter_request(self, request_id: str, requester_id: str,
                               firefighter_id: str, reason: str):
        """Log firefighter access request"""
        return self.log(
            action=AuditAction.FF_REQUEST_SUBMITTED,
            actor_user_id=requester_id,
            target_type='firefighter',
            target_id=firefighter_id,
            details={
                'request_id': request_id,
                'reason': reason
            },
            compliance_relevant=True,
            compliance_tags=['SOX', 'GRC']
        )

    def log_firefighter_session_start(self, session_id: str, user_id: str,
                                     firefighter_id: str, approver: str):
        """Log firefighter session start"""
        return self.log(
            action=AuditAction.FF_SESSION_STARTED,
            actor_user_id=user_id,
            target_type='firefighter_session',
            target_id=session_id,
            details={
                'firefighter_id': firefighter_id,
                'approved_by': approver
            },
            compliance_relevant=True,
            compliance_tags=['SOX', 'GRC']
        )

    def log_firefighter_activity(self, session_id: str, user_id: str,
                                action_type: str, action_details: Dict,
                                is_sensitive: bool = False):
        """Log activity during firefighter session"""
        return self.log(
            action=AuditAction.FF_ACTIVITY_LOGGED,
            actor_user_id=user_id,
            target_type='firefighter_session',
            target_id=session_id,
            details={
                'action_type': action_type,
                **action_details
            },
            compliance_relevant=is_sensitive,
            compliance_tags=['SOX', 'GRC'] if is_sensitive else None
        )

    # ==========================================================================
    # Query Methods
    # ==========================================================================

    def query(self,
              action: Optional[AuditAction] = None,
              actor_user_id: Optional[str] = None,
              target_id: Optional[str] = None,
              start_date: Optional[datetime] = None,
              end_date: Optional[datetime] = None,
              compliance_tags: Optional[List[str]] = None,
              success_only: bool = False,
              limit: int = 100,
              offset: int = 0) -> List[AuditLog]:
        """
        Query audit logs with filters.

        Returns list of matching AuditLog objects.
        """
        session = self._get_session()
        try:
            query = session.query(AuditLog)

            if action:
                query = query.filter(AuditLog.action == action)
            if actor_user_id:
                query = query.filter(AuditLog.actor_user_id == actor_user_id)
            if target_id:
                query = query.filter(AuditLog.target_id == target_id)
            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)
            if success_only:
                query = query.filter(AuditLog.success == True)
            if compliance_tags:
                # Note: This requires JSON containment, which varies by database
                # For PostgreSQL: AuditLog.compliance_tags.contains(compliance_tags)
                pass

            query = query.order_by(AuditLog.timestamp.desc())
            query = query.offset(offset).limit(limit)

            return query.all()

        finally:
            if not self._db_session:
                session.close()

    def get_user_activity(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get all activity for a user in the last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        logs = self.query(
            actor_user_id=user_id,
            start_date=start_date,
            limit=1000
        )
        return [log.to_dict() for log in logs]

    def get_compliance_report(self,
                             start_date: datetime,
                             end_date: datetime,
                             tags: Optional[List[str]] = None) -> Dict:
        """Generate compliance report for a date range"""
        session = self._get_session()
        try:
            query = session.query(AuditLog).filter(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.compliance_relevant == True
            )

            logs = query.all()

            # Aggregate by action type
            by_action = {}
            for log in logs:
                action_name = log.action.value
                if action_name not in by_action:
                    by_action[action_name] = {'count': 0, 'failed': 0}
                by_action[action_name]['count'] += 1
                if not log.success:
                    by_action[action_name]['failed'] += 1

            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'total_entries': len(logs),
                'by_action': by_action,
                'failed_actions': sum(1 for l in logs if not l.success)
            }

        finally:
            if not self._db_session:
                session.close()


# Global audit logger instance
audit_logger = AuditLogger()


def audit_log(action: AuditAction,
              target_type: Optional[str] = None,
              compliance_tags: Optional[List[str]] = None):
    """
    Decorator for automatically auditing function calls.

    Usage:
        @audit_log(AuditAction.USER_CREATED, target_type='user')
        def create_user(user_data: dict, created_by: str):
            # Function implementation
            return new_user

    The decorated function should return the created/modified object,
    or raise an exception on failure.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract common parameters if available
            actor_id = kwargs.get('actor_user_id') or kwargs.get('created_by') or kwargs.get('user_id')

            try:
                result = func(*args, **kwargs)

                # Try to get target_id from result
                target_id = None
                target_name = None
                if hasattr(result, 'id'):
                    target_id = str(result.id)
                if hasattr(result, 'user_id'):
                    target_id = result.user_id
                if hasattr(result, 'name'):
                    target_name = result.name

                audit_logger.log(
                    action=action,
                    actor_user_id=actor_id,
                    target_type=target_type,
                    target_id=target_id,
                    target_name=target_name,
                    details={'function': func.__name__, 'args': str(kwargs)},
                    success=True,
                    compliance_tags=compliance_tags
                )

                return result

            except Exception as e:
                audit_logger.log(
                    action=action,
                    actor_user_id=actor_id,
                    target_type=target_type,
                    details={'function': func.__name__, 'args': str(kwargs)},
                    success=False,
                    error_message=str(e),
                    compliance_tags=compliance_tags
                )
                raise

        return wrapper
    return decorator
