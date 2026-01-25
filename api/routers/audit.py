"""
Audit API Router

Endpoints for querying audit logs and generating compliance reports.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from audit.logger import AuditLogger, AuditAction
from db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["Audit"])

# Initialize audit logger
audit_logger = AuditLogger()


# =============================================================================
# Request/Response Models
# =============================================================================

class AuditLogResponse(BaseModel):
    """Audit log entry response"""
    id: int
    timestamp: str
    action: str
    actor_user_id: Optional[str]
    actor_username: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    success: bool
    details: Optional[Dict]


class ComplianceReportRequest(BaseModel):
    """Request for compliance report generation"""
    start_date: datetime
    end_date: datetime
    compliance_tags: Optional[List[str]] = None


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@router.get("/logs")
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    actor: Optional[str] = Query(None, description="Filter by actor user ID"),
    target_id: Optional[str] = Query(None, description="Filter by target ID"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    success_only: bool = Query(False, description="Only return successful actions"),
    limit: int = Query(100, le=1000, description="Maximum results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """
    Query audit logs with filters.
    """
    # Map action string to enum if provided
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            # Try to match by name
            for a in AuditAction:
                if a.value == action or a.name.lower() == action.lower():
                    action_enum = a
                    break

    logs = audit_logger.query(
        action=action_enum,
        actor_user_id=actor,
        target_id=target_id,
        start_date=start_date,
        end_date=end_date,
        success_only=success_only,
        limit=limit,
        offset=offset
    )

    return {
        'total': len(logs),
        'offset': offset,
        'limit': limit,
        'logs': [log.to_dict() for log in logs]
    }


@router.get("/logs/actions")
async def list_audit_actions():
    """
    List all available audit action types.
    """
    actions = []
    for action in AuditAction:
        # Determine category from action name
        name = action.value
        if name.startswith('user_'):
            category = 'User Management'
        elif name.startswith('role_'):
            category = 'Role Management'
        elif name.startswith('risk_') or name.startswith('violation_'):
            category = 'Risk Management'
        elif name.startswith('ff_'):
            category = 'Firefighter'
        else:
            category = 'System'

        actions.append({
            'action': action.value,
            'name': action.name,
            'category': category
        })

    return {'actions': actions}


@router.get("/logs/user/{user_id}")
async def get_user_audit_trail(
    user_id: str,
    days: int = Query(30, description="Number of days to look back")
):
    """
    Get complete audit trail for a specific user.
    """
    activities = audit_logger.get_user_activity(user_id, days)

    return {
        'user_id': user_id,
        'period_days': days,
        'activity_count': len(activities),
        'activities': activities
    }


@router.get("/logs/target/{target_type}/{target_id}")
async def get_target_audit_trail(
    target_type: str,
    target_id: str,
    days: int = Query(90, description="Number of days to look back")
):
    """
    Get audit trail for a specific target object.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    logs = audit_logger.query(
        target_id=target_id,
        start_date=start_date,
        limit=1000
    )

    # Filter by target type
    filtered_logs = [
        log.to_dict() for log in logs
        if log.target_type == target_type
    ]

    return {
        'target_type': target_type,
        'target_id': target_id,
        'period_days': days,
        'entry_count': len(filtered_logs),
        'entries': filtered_logs
    }


# =============================================================================
# Compliance Report Endpoints
# =============================================================================

@router.post("/reports/compliance")
async def generate_compliance_report(request: ComplianceReportRequest):
    """
    Generate a compliance report for a date range.

    This report aggregates all compliance-relevant audit entries.
    """
    report = audit_logger.get_compliance_report(
        start_date=request.start_date,
        end_date=request.end_date,
        tags=request.compliance_tags
    )

    return report


@router.get("/reports/summary")
async def get_audit_summary(
    days: int = Query(30, description="Number of days to summarize")
):
    """
    Get a summary of audit activity for the specified period.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()

    logs = audit_logger.query(
        start_date=start_date,
        end_date=end_date,
        limit=10000
    )

    # Aggregate by action
    by_action = {}
    by_actor = {}
    by_day = {}
    failed_count = 0

    for log in logs:
        # By action
        action = log.action.value
        by_action[action] = by_action.get(action, 0) + 1

        # By actor
        if log.actor_user_id:
            by_actor[log.actor_user_id] = by_actor.get(log.actor_user_id, 0) + 1

        # By day
        day = log.timestamp.strftime('%Y-%m-%d')
        by_day[day] = by_day.get(day, 0) + 1

        # Failed count
        if not log.success:
            failed_count += 1

    # Sort by count
    top_actors = sorted(by_actor.items(), key=lambda x: x[1], reverse=True)[:10]
    top_actions = sorted(by_action.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'days': days
        },
        'total_entries': len(logs),
        'failed_actions': failed_count,
        'unique_actors': len(by_actor),
        'top_actors': [{'user_id': a[0], 'count': a[1]} for a in top_actors],
        'top_actions': [{'action': a[0], 'count': a[1]} for a in top_actions],
        'by_day': by_day
    }


@router.get("/reports/firefighter")
async def get_firefighter_audit_report(
    days: int = Query(30, description="Number of days to report"),
    session_id: Optional[str] = Query(None, description="Filter by specific session")
):
    """
    Generate a firefighter activity audit report.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get all firefighter-related logs
    all_logs = audit_logger.query(
        start_date=start_date,
        limit=10000
    )

    # Filter to firefighter actions
    ff_logs = [
        log for log in all_logs
        if log.action.value.startswith('ff_')
    ]

    if session_id:
        ff_logs = [
            log for log in ff_logs
            if log.target_id == session_id
        ]

    # Aggregate by action type
    by_action = {}
    sessions = set()

    for log in ff_logs:
        action = log.action.value
        by_action[action] = by_action.get(action, 0) + 1

        if log.target_id and log.target_type == 'firefighter_session':
            sessions.add(log.target_id)

    return {
        'period_days': days,
        'total_entries': len(ff_logs),
        'unique_sessions': len(sessions),
        'by_action': by_action,
        'entries': [log.to_dict() for log in ff_logs[:100]]  # Limit to first 100
    }


# =============================================================================
# Export Endpoints
# =============================================================================

@router.get("/export/csv")
async def export_audit_logs_csv(
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    action: Optional[str] = Query(None, description="Filter by action type")
):
    """
    Export audit logs as CSV (returns data in CSV-friendly format).
    """
    action_enum = None
    if action:
        for a in AuditAction:
            if a.value == action:
                action_enum = a
                break

    logs = audit_logger.query(
        action=action_enum,
        start_date=start_date,
        end_date=end_date,
        limit=10000
    )

    # Format for CSV
    rows = []
    for log in logs:
        rows.append({
            'timestamp': log.timestamp.isoformat(),
            'action': log.action.value,
            'actor_user_id': log.actor_user_id or '',
            'actor_username': log.actor_username or '',
            'target_type': log.target_type or '',
            'target_id': log.target_id or '',
            'success': 'Yes' if log.success else 'No',
            'error': log.error_message or ''
        })

    return {
        'format': 'csv',
        'row_count': len(rows),
        'columns': ['timestamp', 'action', 'actor_user_id', 'actor_username',
                   'target_type', 'target_id', 'success', 'error'],
        'data': rows
    }
