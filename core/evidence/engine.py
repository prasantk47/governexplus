"""
Evidence & Audit Provenance Engine

Append-only evidence store with hash-chain integrity.
Every significant action in the platform produces an evidence record.

This replaces ad-hoc AuditLog writes scattered across routers.
All modules call evidence_engine.record() to produce verifiable
audit evidence.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Any

from .models import (
    EvidenceIntegrity,
    EvidenceRecord,
    EvidenceType,
)

logger = logging.getLogger(__name__)


class EvidenceEngine:
    """Append-only evidence store with tamper detection."""

    def __init__(self):
        self._records: list[EvidenceRecord] = []
        self._index_by_id: dict[str, EvidenceRecord] = {}
        self._last_hash: str = "GENESIS"

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        evidence_type: EvidenceType,
        tenant_id: str,
        actor_user_id: str,
        action: str,
        *,
        actor_role: str = "",
        actor_ip: str = "",
        target_user_id: Optional[str] = None,
        target_object_type: str = "",
        target_object_id: str = "",
        justification: str = "",
        policy_id: Optional[str] = None,
        request_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        finding_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        session_id: Optional[str] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        system_response: Optional[str] = None,
        action_details: Optional[dict] = None,
    ) -> EvidenceRecord:
        """Create an immutable evidence record.

        Returns the created record with hash chain integrity.
        """
        eid = self._make_evidence_id(len(self._records))

        record = EvidenceRecord(
            evidence_id=eid,
            evidence_type=evidence_type,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            actor_ip=actor_ip,
            action=action,
            action_details=action_details or {},
            target_user_id=target_user_id,
            target_object_type=target_object_type,
            target_object_id=target_object_id,
            justification=justification,
            policy_id=policy_id,
            request_id=request_id,
            workflow_id=workflow_id,
            finding_id=finding_id,
            plan_id=plan_id,
            campaign_id=campaign_id,
            session_id=session_id,
            before_state=before_state,
            after_state=after_state,
            system_response=system_response,
            previous_hash=self._last_hash,
        )

        # Compute hash
        record.record_hash = self._compute_hash(record)
        self._last_hash = record.record_hash

        self._records.append(record)
        self._index_by_id[eid] = record

        # Write-through to DB
        self._persist_to_db(record)

        return record

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_by_id(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self._index_by_id.get(evidence_id)

    def get_for_user(self, user_id: str) -> list[EvidenceRecord]:
        """Get all evidence where user is actor or target."""
        return [
            r for r in self._records
            if r.actor_user_id == user_id or r.target_user_id == user_id
        ]

    def get_for_request(self, request_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.request_id == request_id]

    def get_for_finding(self, finding_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.finding_id == finding_id]

    def get_for_session(self, session_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.session_id == session_id]

    def get_for_campaign(self, campaign_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.campaign_id == campaign_id]

    def get_by_type(self, evidence_type: EvidenceType) -> list[EvidenceRecord]:
        return [r for r in self._records if r.evidence_type == evidence_type]

    def get_by_tenant(self, tenant_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.tenant_id == tenant_id]

    def get_timeline(
        self,
        tenant_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[EvidenceRecord]:
        """Get evidence records in chronological order."""
        filtered = [r for r in self._records if r.tenant_id == tenant_id]
        if start:
            filtered = [r for r in filtered if r.timestamp >= start]
        if end:
            filtered = [r for r in filtered if r.timestamp <= end]
        return filtered[-limit:]

    def get_all(self) -> list[EvidenceRecord]:
        return list(self._records)

    # ------------------------------------------------------------------
    # Integrity verification
    # ------------------------------------------------------------------

    def verify_chain(self) -> tuple[bool, list[str]]:
        """Verify the entire hash chain.

        Returns (is_valid, list_of_errors).
        """
        errors = []
        expected_prev = "GENESIS"

        for i, record in enumerate(self._records):
            # Check previous hash link
            if record.previous_hash != expected_prev:
                errors.append(
                    f"Record {i} ({record.evidence_id}): "
                    f"previous_hash mismatch — expected {expected_prev[:12]}, "
                    f"got {record.previous_hash[:12]}"
                )

            # Recompute and verify record hash
            computed = self._compute_hash(record)
            if computed != record.record_hash:
                errors.append(
                    f"Record {i} ({record.evidence_id}): "
                    f"hash mismatch — record tampered"
                )
                record.integrity = EvidenceIntegrity.TAMPERED

            expected_prev = record.record_hash

        return len(errors) == 0, errors

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_for_audit(
        self,
        tenant_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict]:
        """Export evidence records for external audit."""
        records = self.get_timeline(tenant_id, start, end, limit=10000)
        return [r.to_dict() for r in records]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_hash(self, record: EvidenceRecord) -> str:
        """Compute SHA-256 hash of record content + previous hash."""
        content = {
            "evidence_id": record.evidence_id,
            "type": record.evidence_type.value,
            "tenant_id": record.tenant_id,
            "actor": record.actor_user_id,
            "action": record.action,
            "target_type": record.target_object_type,
            "target_id": record.target_object_id,
            "timestamp": record.timestamp.isoformat(),
            "previous_hash": record.previous_hash,
        }
        raw = json.dumps(content, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _persist_to_db(self, record: EvidenceRecord) -> None:
        """Write-through: persist evidence record to database."""
        try:
            from db.database import db_manager
            from db.models.engines import EvidenceRecord as EvidenceRecordDB

            with db_manager.session_scope() as session:
                row = EvidenceRecordDB(
                    evidence_id=record.evidence_id,
                    tenant_id=record.tenant_id,
                    evidence_type=record.evidence_type.value,
                    actor_user_id=record.actor_user_id,
                    action=record.action,
                    timestamp=record.timestamp,
                    target_user_id=record.target_user_id,
                    target_object_type=record.target_object_type,
                    target_object_id=record.target_object_id,
                    request_id=record.request_id,
                    workflow_id=record.workflow_id,
                    finding_id=record.finding_id,
                    plan_id=record.plan_id,
                    campaign_id=record.campaign_id,
                    session_id=record.session_id,
                    before_state=record.before_state,
                    after_state=record.after_state,
                    action_details=record.action_details,
                    system_response={"value": record.system_response} if record.system_response else None,
                    previous_hash=record.previous_hash,
                    record_hash=record.record_hash,
                    integrity=record.integrity.value if hasattr(record.integrity, 'value') else str(record.integrity),
                )
                session.add(row)
        except Exception as exc:
            logger.warning(f"Evidence DB persist failed (in-memory intact): {exc}")

    @staticmethod
    def _make_evidence_id(sequence: int) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"EVD-{ts}-{sequence:06d}"
