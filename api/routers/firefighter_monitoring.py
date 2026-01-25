"""
Firefighter Monitoring API Router

Endpoints for real-time firefighter session monitoring and alerting.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from core.firefighter import FirefighterMonitor, AlertSeverity

router = APIRouter(tags=["Firefighter Monitoring"])

# Initialize monitor
ff_monitor = FirefighterMonitor()


# Seed some sample data for demonstration
def _seed_sample_session():
    """Create a sample session for demo"""
    from datetime import timedelta

    # Register a sample session
    ff_monitor.register_session(
        session_id="SESS-DEMO-001",
        user_id="JSMITH",
        firefighter_id="FF_EMERGENCY_01",
        target_system="SAP_PROD",
        started_at=datetime.now() - timedelta(hours=1),
        expires_at=datetime.now() + timedelta(hours=2)
    )

    # Log some sample activities
    sample_activities = [
        ("tcode", "SE16", "Data Browser", "BSEG"),
        ("tcode", "FB03", "Display Document", ""),
        ("tcode", "XK03", "Display Vendor", ""),
        ("tcode", "ME23N", "Display Purchase Order", ""),
        ("tcode", "SM21", "System Log", ""),  # Restricted
    ]

    for action_type, action_code, desc, target in sample_activities:
        ff_monitor.log_activity(
            session_id="SESS-DEMO-001",
            action_type=action_type,
            action_code=action_code,
            action_description=desc,
            target_object=target,
            ip_address="10.0.0.100",
            client="100"
        )

_seed_sample_session()


# =============================================================================
# Request/Response Models
# =============================================================================

class LogActivityRequest(BaseModel):
    """Request to log an activity"""
    action_type: str = Field(..., example="tcode")
    action_code: str = Field(..., example="SE16")
    action_description: str = Field(default="", example="Data Browser")
    target_object: str = Field(default="", example="BSEG")
    client: str = Field(default="", example="100")
    ip_address: str = Field(default="", example="10.0.0.100")
    terminal: str = Field(default="")
    program: str = Field(default="")


class AcknowledgeAlertRequest(BaseModel):
    """Request to acknowledge an alert"""
    acknowledged_by: str = Field(..., example="security.admin@company.com")


class RegisterSessionRequest(BaseModel):
    """Request to register a session for monitoring"""
    session_id: str = Field(...)
    user_id: str = Field(...)
    firefighter_id: str = Field(...)
    target_system: str = Field(...)
    started_at: datetime
    expires_at: datetime


# =============================================================================
# Dashboard Endpoints
# =============================================================================

@router.get("/dashboard")
async def get_monitoring_dashboard():
    """
    Get real-time monitoring dashboard data.

    Returns active sessions with their current status, activity counts,
    and risk scores.
    """
    return ff_monitor.get_active_sessions_dashboard()


@router.get("/statistics")
async def get_monitoring_statistics():
    """Get overall monitoring statistics"""
    return ff_monitor.get_monitoring_statistics()


# =============================================================================
# Session Monitoring Endpoints
# =============================================================================

@router.post("/sessions/register")
async def register_session_for_monitoring(request: RegisterSessionRequest):
    """
    Register a firefighter session for real-time monitoring.

    This should be called when a session is started.
    """
    ff_monitor.register_session(
        session_id=request.session_id,
        user_id=request.user_id,
        firefighter_id=request.firefighter_id,
        target_system=request.target_system,
        started_at=request.started_at,
        expires_at=request.expires_at
    )

    return {
        "message": "Session registered for monitoring",
        "session_id": request.session_id
    }


@router.post("/sessions/{session_id}/unregister")
async def unregister_session(session_id: str, reason: str = Query(default="normal")):
    """
    Unregister a session from monitoring.

    This should be called when a session ends.
    """
    ff_monitor.unregister_session(session_id, reason)

    return {
        "message": "Session unregistered",
        "session_id": session_id
    }


@router.post("/sessions/{session_id}/activity")
async def log_session_activity(session_id: str, request: LogActivityRequest):
    """
    Log an activity within a firefighter session.

    Activities are automatically assessed for risk and alerts
    are generated as needed.
    """
    activity = ff_monitor.log_activity(
        session_id=session_id,
        action_type=request.action_type,
        action_code=request.action_code,
        action_description=request.action_description,
        target_object=request.target_object,
        client=request.client,
        ip_address=request.ip_address,
        terminal=request.terminal,
        program=request.program
    )

    return {
        "activity_id": activity.activity_id,
        "is_sensitive": activity.is_sensitive,
        "is_restricted": activity.is_restricted,
        "risk_level": activity.risk_level,
        "risk_reason": activity.risk_reason
    }


@router.get("/sessions/{session_id}/activities")
async def get_session_activities(
    session_id: str,
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(100, le=500)
):
    """
    Get activities for a specific session.
    """
    activities = ff_monitor.get_session_activities(
        session_id=session_id,
        risk_level=risk_level,
        limit=limit
    )

    return {
        "session_id": session_id,
        "total": len(activities),
        "activities": [a.to_dict() for a in activities]
    }


@router.get("/sessions/{session_id}/timeline")
async def get_session_timeline(session_id: str):
    """
    Get chronological timeline of all session events.

    Includes activities, alerts, and snapshots.
    """
    timeline = ff_monitor.get_session_timeline(session_id)

    return {
        "session_id": session_id,
        "event_count": len(timeline),
        "timeline": [
            {
                "type": item["type"],
                "timestamp": item["timestamp"].isoformat(),
                "data": item["data"]
            }
            for item in timeline
        ]
    }


@router.post("/sessions/{session_id}/snapshot")
async def capture_session_snapshot(session_id: str):
    """
    Capture a point-in-time snapshot of session state.
    """
    try:
        snapshot = ff_monitor.capture_snapshot(session_id)
        return snapshot.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/{session_id}/risk")
async def get_session_risk(session_id: str):
    """
    Get current risk assessment for a session.
    """
    if session_id not in ff_monitor.active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    risk_score = ff_monitor._calculate_session_risk(session_id)
    activities = ff_monitor.activities.get(session_id, [])

    return {
        "session_id": session_id,
        "risk_score": risk_score,
        "risk_level": "critical" if risk_score >= 75 else (
            "high" if risk_score >= 50 else (
                "medium" if risk_score >= 25 else "low"
            )
        ),
        "factors": {
            "restricted_actions": len([a for a in activities if a.is_restricted]),
            "sensitive_actions": len([a for a in activities if a.is_sensitive]),
            "total_actions": len(activities),
            "unacknowledged_alerts": len([
                a for a in ff_monitor.alerts.values()
                if a.session_id == session_id and not a.acknowledged
            ])
        }
    }


# =============================================================================
# Alert Endpoints
# =============================================================================

@router.get("/alerts")
async def get_alerts(
    session_id: Optional[str] = Query(None, description="Filter by session"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(100, le=500)
):
    """
    Get monitoring alerts with filters.
    """
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            pass

    alerts = ff_monitor.get_alerts(
        session_id=session_id,
        severity=severity_enum,
        acknowledged=acknowledged,
        limit=limit
    )

    return {
        "total": len(alerts),
        "alerts": [a.to_dict() for a in alerts]
    }


@router.get("/alerts/unacknowledged")
async def get_unacknowledged_alerts():
    """
    Get all unacknowledged alerts.
    """
    alerts = ff_monitor.get_alerts(acknowledged=False)

    by_severity = {
        "critical": [],
        "high": [],
        "warning": [],
        "info": []
    }

    for alert in alerts:
        by_severity[alert.severity.value].append(alert.to_dict())

    return {
        "total": len(alerts),
        "by_severity": by_severity
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, request: AcknowledgeAlertRequest):
    """
    Acknowledge a monitoring alert.
    """
    try:
        alert = ff_monitor.acknowledge_alert(alert_id, request.acknowledged_by)
        return {
            "message": "Alert acknowledged",
            "alert_id": alert_id,
            "acknowledged_by": request.acknowledged_by
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/alerts/bulk-acknowledge")
async def bulk_acknowledge_alerts(
    alert_ids: List[str],
    acknowledged_by: str = Query(...)
):
    """
    Acknowledge multiple alerts at once.
    """
    results = []

    for alert_id in alert_ids:
        try:
            ff_monitor.acknowledge_alert(alert_id, acknowledged_by)
            results.append({"alert_id": alert_id, "success": True})
        except ValueError:
            results.append({"alert_id": alert_id, "success": False, "error": "Not found"})

    return {
        "processed": len(results),
        "results": results
    }


# =============================================================================
# System Monitoring Endpoints
# =============================================================================

@router.post("/check-expiring-sessions")
async def check_expiring_sessions():
    """
    Check for expiring sessions and generate alerts.

    This endpoint should be called periodically by a scheduler.
    """
    alerts = ff_monitor.check_expiring_sessions()

    return {
        "alerts_generated": len(alerts),
        "alerts": [a.to_dict() for a in alerts]
    }


@router.get("/restricted-codes")
async def get_restricted_codes():
    """
    Get list of restricted transaction codes being monitored.
    """
    return {
        "restricted_tcodes": [
            {"code": code, "description": desc}
            for code, desc in ff_monitor.RESTRICTED_TCODES.items()
        ],
        "sensitive_tables": [
            {"table": table, "description": desc}
            for table, desc in ff_monitor.SENSITIVE_TABLES.items()
        ]
    }


@router.get("/policy-config")
async def get_monitoring_policy():
    """
    Get current monitoring policy configuration.
    """
    return ff_monitor.policy_config


# =============================================================================
# WebSocket for Real-Time Updates
# =============================================================================

# Store active WebSocket connections
active_connections: List[WebSocket] = []


@router.websocket("/ws/live")
async def websocket_live_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time monitoring updates.

    Clients receive:
    - New alerts as they occur
    - Session status changes
    - Activity notifications for high-risk actions
    """
    await websocket.accept()
    active_connections.append(websocket)

    # Register alert callback
    async def send_alert(alert):
        for connection in active_connections:
            try:
                await connection.send_json({
                    "type": "alert",
                    "data": alert.to_dict()
                })
            except Exception:
                pass

    # Note: In production, use proper async handling
    # ff_monitor.subscribe_to_alerts(send_alert)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")
            elif data == "dashboard":
                dashboard = ff_monitor.get_active_sessions_dashboard()
                await websocket.send_json({
                    "type": "dashboard",
                    "data": dashboard
                })

    except WebSocketDisconnect:
        active_connections.remove(websocket)


# =============================================================================
# Reporting Endpoints
# =============================================================================

@router.get("/reports/session-summary/{session_id}")
async def get_session_summary_report(session_id: str):
    """
    Generate a comprehensive summary report for a session.
    """
    if session_id not in ff_monitor.active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = ff_monitor.active_sessions[session_id]
    activities = ff_monitor.activities.get(session_id, [])
    alerts = [a for a in ff_monitor.alerts.values() if a.session_id == session_id]
    snapshots = ff_monitor.session_snapshots.get(session_id, [])

    # Calculate statistics
    restricted_activities = [a for a in activities if a.is_restricted]
    sensitive_activities = [a for a in activities if a.is_sensitive]

    # Group activities by type
    by_action_type = {}
    for activity in activities:
        key = activity.action_code
        if key not in by_action_type:
            by_action_type[key] = 0
        by_action_type[key] += 1

    return {
        "report_type": "session_summary",
        "generated_at": datetime.now().isoformat(),
        "session": {
            "session_id": session_id,
            "user_id": session["user_id"],
            "firefighter_id": session["firefighter_id"],
            "target_system": session["target_system"],
            "started_at": session["started_at"].isoformat(),
            "expires_at": session["expires_at"].isoformat(),
            "status": session["status"]
        },
        "activity_summary": {
            "total_activities": len(activities),
            "restricted_activities": len(restricted_activities),
            "sensitive_activities": len(sensitive_activities),
            "by_action_code": by_action_type
        },
        "restricted_actions_detail": [
            {
                "timestamp": a.timestamp.isoformat(),
                "action_code": a.action_code,
                "reason": a.risk_reason
            }
            for a in restricted_activities
        ],
        "alert_summary": {
            "total_alerts": len(alerts),
            "by_severity": {
                s.value: len([a for a in alerts if a.severity == s])
                for s in AlertSeverity
            },
            "acknowledged": len([a for a in alerts if a.acknowledged]),
            "unacknowledged": len([a for a in alerts if not a.acknowledged])
        },
        "risk_assessment": {
            "final_risk_score": ff_monitor._calculate_session_risk(session_id),
            "snapshot_count": len(snapshots)
        }
    }
