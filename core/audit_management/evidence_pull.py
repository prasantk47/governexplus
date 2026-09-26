"""Audit Evidence Pull — point-in-time immutable snapshots from AC/PC/RM (XL-D)"""
import hashlib
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from db.models.process_control import GRCEvidence, EvidenceStatus
from db.models.risk import RiskViolation
from db.models.firefighter import FirefighterSession, FirefighterActivity
from db.models.process_control import CCMExecution, CCMRule
from db.models.risk_management import EnterpriseRisk, RiskAssessment


class EvidencePullService:
    SOURCES = ("ccm_executions", "firefighter_sessions", "risk_baseline", "sod_violations")

    def __init__(self, tenant_id: str, db: Session):
        self.tenant_id = tenant_id
        self.db = db

    def pull_evidence(self, engagement_id: str, source: str, filters: dict,
                      title: str = None, pulled_by: str = "system",
                      procedure_id: str = None) -> dict:
        """Pull a point-in-time snapshot from a source module."""
        if source not in self.SOURCES:
            raise ValueError(f"Invalid source: {source}. Must be one of {self.SOURCES}")

        # Query source data
        rows = self._query_source(source, filters)

        # Serialize to canonical JSON
        payload = json.dumps(rows, default=str, sort_keys=True)
        content_hash = hashlib.sha256(payload.encode()).hexdigest()

        # Create evidence record
        evidence_id = f"EPL-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.utcnow()

        evidence = GRCEvidence(
            tenant_id=self.tenant_id,
            evidence_id=evidence_id,
            title=title or f"System Extract: {source} ({now:%Y-%m-%d %H:%M})",
            description=f"Automated evidence pull from {source} with {len(rows)} records",
            evidence_type="system_extract",
            source_module="am",
            linked_object_type="procedure" if procedure_id else "engagement",
            linked_object_id=procedure_id or engagement_id,
            uploaded_by=pulled_by,
            content_hash=content_hash,
            version=1,
            status=EvidenceStatus.ACTIVE,
            extract_metadata={
                "source": source,
                "filters": filters,
                "row_count": len(rows),
                "generated_at": now.isoformat(),
                "generated_by": pulled_by,
                "engagement_id": engagement_id,
                "procedure_id": procedure_id,
                "data": rows,  # The actual snapshot
            },
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)

        return {
            "evidence_id": evidence_id,
            "source": source,
            "row_count": len(rows),
            "sha256": content_hash,
            "generated_at": now.isoformat(),
            "linked_to": procedure_id or engagement_id,
        }

    def _query_source(self, source: str, filters: dict) -> list:
        date_from = filters.get("from")
        date_to = filters.get("to")

        if source == "ccm_executions":
            return self._pull_ccm(filters, date_from, date_to)
        elif source == "firefighter_sessions":
            return self._pull_firefighter(filters, date_from, date_to)
        elif source == "risk_baseline":
            return self._pull_risk_baseline(filters)
        elif source == "sod_violations":
            return self._pull_sod_violations(filters, date_from, date_to)
        return []

    def _pull_ccm(self, filters, date_from, date_to) -> list:
        q = self.db.query(CCMExecution).filter(CCMExecution.tenant_id == self.tenant_id)
        if date_from:
            q = q.filter(CCMExecution.executed_at >= date_from)
        if date_to:
            q = q.filter(CCMExecution.executed_at <= date_to)
        control_ids = filters.get("control_ids")
        if control_ids:
            rule_ids = [
                r.id for r in self.db.query(CCMRule).filter(
                    CCMRule.tenant_id == self.tenant_id,
                    CCMRule.control_id.in_(control_ids),
                ).all()
            ]
            if rule_ids:
                q = q.filter(CCMExecution.rule_id.in_(rule_ids))
        return [row.to_dict() for row in q.order_by(CCMExecution.executed_at.desc()).limit(1000).all()]

    def _pull_firefighter(self, filters, date_from, date_to) -> list:
        q = self.db.query(FirefighterSession).filter(FirefighterSession.tenant_id == self.tenant_id)
        if date_from:
            q = q.filter(FirefighterSession.started_at >= date_from)
        if date_to:
            q = q.filter(FirefighterSession.started_at <= date_to)
        ff_ids = filters.get("firefighter_ids")
        if ff_ids:
            q = q.filter(FirefighterSession.firefighter_id.in_(ff_ids))
        sessions = q.order_by(FirefighterSession.started_at.desc()).limit(500).all()
        result = []
        for s in sessions:
            row = s.to_dict() if hasattr(s, 'to_dict') else {
                "session_id": s.session_id,
                "firefighter_id": s.firefighter_id,
                "started_at": str(s.started_at),
            }
            # Include activities
            activities = self.db.query(FirefighterActivity).filter(
                FirefighterActivity.session_id == s.session_id
            ).all()
            row["activities"] = [
                {
                    "transaction_code": a.transaction_code,
                    "timestamp": str(a.timestamp),
                    "action_type": a.action_type,
                    "is_sensitive": a.is_sensitive,
                    "action_details": a.action_details,
                }
                for a in activities
            ]
            result.append(row)
        return result

    def _pull_risk_baseline(self, filters) -> list:
        q = self.db.query(EnterpriseRisk).filter(
            EnterpriseRisk.tenant_id == self.tenant_id,
            EnterpriseRisk.is_active == True,  # noqa: E712
        )
        risk_ids = filters.get("risk_ids")
        if risk_ids:
            q = q.filter(EnterpriseRisk.risk_id.in_(risk_ids))
        risks = q.all()
        result = []
        for r in risks:
            row = r.to_dict()
            # Include latest assessment
            latest = self.db.query(RiskAssessment).filter(
                RiskAssessment.risk_id == r.id,
                RiskAssessment.tenant_id == self.tenant_id,
            ).order_by(RiskAssessment.created_at.desc()).first()
            if latest:
                row["latest_assessment"] = latest.to_dict()
            result.append(row)
        return result

    def _pull_sod_violations(self, filters, date_from, date_to) -> list:
        q = self.db.query(RiskViolation).filter(RiskViolation.tenant_id == self.tenant_id)
        if date_from:
            q = q.filter(RiskViolation.detected_at >= date_from)
        if date_to:
            q = q.filter(RiskViolation.detected_at <= date_to)
        rule_ids = filters.get("rule_ids")
        if rule_ids:
            q = q.filter(RiskViolation.rule_id.in_(rule_ids))
        user_ids = filters.get("user_ids")
        if user_ids:
            q = q.filter(RiskViolation.user_external_id.in_(user_ids))
        return [row.to_dict() for row in q.order_by(RiskViolation.detected_at.desc()).limit(2000).all()]
