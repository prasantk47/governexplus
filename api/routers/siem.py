"""
SIEM Connector API Router for Governex+

Endpoints for SIEM integration, event management, and threat correlation.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.siem import (
    SIEMConnector, SIEMEvent, SIEMEventType, SIEMSeverity,
    EventCorrelator, ThreatPattern
)
from core.siem.connector import SIEMDestination, siem_connector
from core.siem.correlator import event_correlator, ThreatCategory

router = APIRouter(tags=["SIEM Connector"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateEventRequest(BaseModel):
    """Request to create a security event"""
    event_type: str = Field(..., example="auth.login.success")
    severity: str = Field(default="MEDIUM", example="HIGH")
    source_user: str = Field(..., example="jsmith")
    action: str = Field(..., example="User logged in from new device")
    source_ip: str = Field(default="", example="192.168.1.100")
    source_system: str = Field(default="Governex+")
    target_user: str = Field(default="")
    target_resource: str = Field(default="")
    target_system: str = Field(default="")
    outcome: str = Field(default="success")
    reason: str = Field(default="")
    risk_score: Optional[int] = None
    transaction_code: str = Field(default="")
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class AddDestinationRequest(BaseModel):
    """Request to add a SIEM destination"""
    name: str = Field(..., example="Splunk HEC")
    type: str = Field(..., example="splunk")  # splunk, qradar, sentinel, elastic, syslog, webhook
    host: str = Field(..., example="splunk.company.com")
    port: int = Field(default=8088)
    protocol: str = Field(default="https")
    api_key: str = Field(default="")
    format: str = Field(default="json")  # json, cef, syslog
    min_severity: str = Field(default="LOW")
    event_types: List[str] = Field(default_factory=list)
    enabled: bool = Field(default=True)


class AcknowledgePatternRequest(BaseModel):
    """Request to acknowledge a threat pattern"""
    acknowledged_by: str = Field(..., example="admin@company.com")
    notes: str = Field(default="")


# =============================================================================
# SIEM Event Endpoints
# =============================================================================

@router.post("/events")
async def create_event(request: CreateEventRequest):
    """
    Create and emit a security event.

    This endpoint is used to report security events that will be:
    - Forwarded to configured SIEM destinations
    - Analyzed for threat correlation
    - Stored in the event buffer
    """
    try:
        event_type = SIEMEventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type. Valid types: {[e.value for e in SIEMEventType]}"
        )

    try:
        severity = SIEMSeverity[request.severity.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Valid severities: {[s.name for s in SIEMSeverity]}"
        )

    event = siem_connector.create_event(
        event_type=event_type,
        severity=severity,
        source_user=request.source_user,
        action=request.action,
        source_ip=request.source_ip,
        source_system=request.source_system,
        target_user=request.target_user,
        target_resource=request.target_resource,
        target_system=request.target_system,
        outcome=request.outcome,
        reason=request.reason,
        risk_score=request.risk_score,
        transaction_code=request.transaction_code,
        custom_fields=request.custom_fields
    )

    # Also process for correlation
    patterns = event_correlator.process_event(event)

    return {
        "status": "success",
        "event_id": event.event_id,
        "patterns_detected": len(patterns),
        "patterns": [p.to_dict() for p in patterns] if patterns else []
    }


@router.get("/events")
async def get_events(
    limit: int = Query(100, le=1000),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    user: Optional[str] = Query(None)
):
    """Get recent security events from the buffer"""
    events = siem_connector.get_recent_events(limit)

    # Apply filters
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    if severity:
        events = [e for e in events if e["severity"] == severity.upper()]
    if user:
        events = [e for e in events if e["source_user"] == user]

    return {
        "total": len(events),
        "events": events
    }


@router.get("/events/types")
async def list_event_types():
    """List all available event types"""
    return {
        "event_types": [
            {
                "value": e.value,
                "name": e.name,
                "category": e.value.split(".")[0]
            }
            for e in SIEMEventType
        ]
    }


@router.get("/events/severities")
async def list_severities():
    """List all severity levels"""
    return {
        "severities": [
            {"name": s.name, "value": s.value}
            for s in SIEMSeverity
        ]
    }


# =============================================================================
# SIEM Destination Endpoints
# =============================================================================

@router.get("/destinations")
async def get_destinations():
    """Get all configured SIEM destinations"""
    return {
        "destinations": siem_connector.get_destinations()
    }


@router.post("/destinations")
async def add_destination(request: AddDestinationRequest):
    """Add a new SIEM destination"""
    try:
        min_sev = SIEMSeverity[request.min_severity.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid minimum severity")

    dest = SIEMDestination(
        name=request.name,
        type=request.type,
        host=request.host,
        port=request.port,
        protocol=request.protocol,
        api_key=request.api_key,
        format=request.format,
        min_severity=min_sev,
        event_types=request.event_types,
        enabled=request.enabled
    )

    dest_id = siem_connector.add_destination(dest)

    return {
        "status": "success",
        "destination_id": dest_id,
        "message": f"Destination '{request.name}' added successfully"
    }


@router.delete("/destinations/{dest_id}")
async def remove_destination(dest_id: str):
    """Remove a SIEM destination"""
    if not siem_connector.remove_destination(dest_id):
        raise HTTPException(status_code=404, detail="Destination not found")

    return {"status": "success", "message": "Destination removed"}


@router.put("/destinations/{dest_id}/toggle")
async def toggle_destination(dest_id: str, enabled: bool = Query(...)):
    """Enable or disable a SIEM destination"""
    if dest_id not in siem_connector.destinations:
        raise HTTPException(status_code=404, detail="Destination not found")

    siem_connector.destinations[dest_id].enabled = enabled

    return {
        "status": "success",
        "destination_id": dest_id,
        "enabled": enabled
    }


# =============================================================================
# Threat Correlation Endpoints
# =============================================================================

@router.get("/threats")
async def get_threats(
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, le=500)
):
    """Get detected threat patterns"""
    cat_enum = None
    if category:
        try:
            cat_enum = ThreatCategory(category)
        except ValueError:
            pass

    sev_enum = None
    if severity:
        try:
            sev_enum = SIEMSeverity[severity.upper()]
        except KeyError:
            pass

    patterns = event_correlator.get_patterns(
        category=cat_enum,
        severity=sev_enum,
        user=user,
        acknowledged=acknowledged,
        limit=limit
    )

    return {
        "total": len(patterns),
        "threats": [p.to_dict() for p in patterns]
    }


@router.get("/threats/categories")
async def list_threat_categories():
    """List all threat categories"""
    return {
        "categories": [
            {"value": c.value, "name": c.name}
            for c in ThreatCategory
        ]
    }


@router.post("/threats/{pattern_id}/acknowledge")
async def acknowledge_threat(pattern_id: str, request: AcknowledgePatternRequest):
    """Acknowledge a detected threat pattern"""
    if not event_correlator.acknowledge_pattern(
        pattern_id,
        request.acknowledged_by,
        request.notes
    ):
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {"status": "success", "message": "Pattern acknowledged"}


@router.post("/threats/{pattern_id}/false-positive")
async def mark_false_positive(pattern_id: str, notes: str = Query(default="")):
    """Mark a threat pattern as false positive"""
    if not event_correlator.mark_false_positive(pattern_id, notes):
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {"status": "success", "message": "Marked as false positive"}


# =============================================================================
# Correlation Rules Endpoints
# =============================================================================

@router.get("/rules")
async def get_correlation_rules():
    """Get all correlation rules"""
    return {
        "rules": event_correlator.get_rules()
    }


@router.put("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, enabled: bool = Query(...)):
    """Enable or disable a correlation rule"""
    if rule_id not in event_correlator.rules:
        raise HTTPException(status_code=404, detail="Rule not found")

    event_correlator.rules[rule_id].enabled = enabled

    return {
        "status": "success",
        "rule_id": rule_id,
        "enabled": enabled
    }


# =============================================================================
# Statistics & Dashboard
# =============================================================================

@router.get("/statistics")
async def get_siem_statistics():
    """Get SIEM connector and correlator statistics"""
    return {
        "connector": siem_connector.get_statistics(),
        "correlator": event_correlator.get_statistics(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/dashboard")
async def get_siem_dashboard():
    """Get SIEM dashboard summary"""
    connector_stats = siem_connector.get_statistics()
    correlator_stats = event_correlator.get_statistics()

    # Get recent threats
    recent_threats = event_correlator.get_patterns(limit=5)
    pending_threats = [t for t in recent_threats if not t.acknowledged]

    return {
        "summary": {
            "total_events": connector_stats["total_events"],
            "events_sent": connector_stats["events_sent"],
            "patterns_detected": correlator_stats["patterns_detected"],
            "pending_threats": len(pending_threats),
            "active_destinations": connector_stats["active_destinations"],
            "active_rules": correlator_stats["active_rules"]
        },
        "events_by_severity": connector_stats["by_severity"],
        "threats_by_category": correlator_stats["by_category"],
        "recent_threats": [t.to_dict() for t in pending_threats[:3]],
        "destinations": siem_connector.get_destinations()[:3],
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# Test/Demo Endpoints
# =============================================================================

@router.post("/demo/generate-events")
async def generate_demo_events(count: int = Query(10, le=100)):
    """Generate demo security events for testing"""
    import random
    import uuid

    demo_users = ["jsmith", "mbrown", "tdavis", "awilson", "kjohnson"]
    demo_ips = ["192.168.1.100", "192.168.1.101", "10.0.0.50", "172.16.0.25"]

    events_created = []
    patterns_detected = []

    for _ in range(count):
        event_type = random.choice(list(SIEMEventType))
        severity = random.choice(list(SIEMSeverity))

        event = siem_connector.create_event(
            event_type=event_type,
            severity=severity,
            source_user=random.choice(demo_users),
            action=f"Demo action for {event_type.name}",
            source_ip=random.choice(demo_ips),
            source_system="SAP ECC",
            risk_score=random.randint(10, 90)
        )

        events_created.append(event.event_id)

        # Process for correlation
        patterns = event_correlator.process_event(event)
        patterns_detected.extend([p.pattern_id for p in patterns])

    return {
        "status": "success",
        "events_created": len(events_created),
        "patterns_detected": len(patterns_detected),
        "event_ids": events_created[:5],
        "pattern_ids": patterns_detected[:3] if patterns_detected else []
    }
