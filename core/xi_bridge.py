"""
Cross-Module Integration Bridge (XI-02 through XI-06)

Provides the integration seams between Access Control (AC), Risk Management
(RM), Process Control (PC), and Audit Management (AM).

XI-02  SoD violations -> PC control deficiencies (auto-create on threshold breach)
XI-03  Risk <-> Control <-> Finding graph navigation
XI-04  Audit planning feed (composite risk score from RM + PC + AC)
XI-06  Unified notification dispatch for any GRC event
XI-02R Deficiency resolution -> AC violation status update (reverse sync)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

# GRC Foundation
from db.models.grc_foundation import OrgUnit

# Risk Management
from db.models.risk_management import EnterpriseRisk

# Process Control
from db.models.process_control import (
    ProcessControl,
    ControlDeficiency,
    DeficiencyStatus,
)

# Audit Management
from db.models.audit_management import AuditableEntity

# Access Control (violation tracking)
from db.models.risk import RiskViolation, ViolationStatus

logger = logging.getLogger(__name__)


class GRCIntegrationBridge:
    """
    Cross-module integration bridge (XI-01 through XI-08).

    Instantiated per request/job with a tenant-scoped DB session.  All writes
    are flushed but not committed — the caller controls the transaction
    boundary so that multiple bridge operations can be batched.
    """

    def __init__(self, tenant_id: str, db_session: Session) -> None:
        self.tenant_id = tenant_id
        self.db = db_session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _new_id(self, prefix: str = "") -> str:
        """Generate a short, collision-resistant string ID."""
        return f"{prefix}{uuid.uuid4().hex[:12]}"

    def _scoped(self, model):
        """Return a query pre-filtered to the current tenant."""
        return self.db.query(model).filter(model.tenant_id == self.tenant_id)

    # ------------------------------------------------------------------
    # XI-02: SoD Violations -> PC Deficiencies
    # ------------------------------------------------------------------

    def sync_sod_to_deficiencies(self, threshold: int = 10) -> dict:
        """
        XI-02: When OPEN SoD violation count for a rule_id exceeds *threshold*,
        auto-create a ControlDeficiency with source='sod_bridge' (if one does
        not already exist for that rule in OPEN or IN_REMEDIATION state).

        Returns a summary dict:
          {
            "rules_checked": int,
            "rules_above_threshold": int,
            "deficiencies_created": int,
            "deficiency_ids": [str, ...],
            "skipped_existing": int,
          }
        """
        # Count open violations per rule_id for this tenant
        rows = (
            self.db.query(
                RiskViolation.rule_id,
                func.count(RiskViolation.id).label("cnt"),
            )
            .filter(
                RiskViolation.tenant_id == self.tenant_id,
                RiskViolation.status == ViolationStatus.OPEN,
            )
            .group_by(RiskViolation.rule_id)
            .all()
        )

        rules_checked = len(rows)
        rules_above_threshold = 0
        deficiencies_created = 0
        skipped_existing = 0
        created_ids: list[str] = []

        for rule_id, count in rows:
            if count < threshold:
                continue

            rules_above_threshold += 1

            # Grab a sample violation to get the rule_name
            sample: RiskViolation | None = (
                self.db.query(RiskViolation)
                .filter(
                    RiskViolation.tenant_id == self.tenant_id,
                    RiskViolation.rule_id == rule_id,
                    RiskViolation.status == ViolationStatus.OPEN,
                )
                .first()
            )
            rule_name = sample.rule_name if sample else rule_id

            # Find the best-fit ProcessControl to attach this deficiency to.
            # Strategy: look for any active control whose name contains "SoD"
            # or "Segregation"; fall back to the first active control in the
            # tenant.  If none exists the deficiency is still created but
            # control_id is left pointing to a sentinel that the operator must
            # fix — we log a warning.
            control: ProcessControl | None = (
                self._scoped(ProcessControl)
                .filter(
                    ProcessControl.is_active == True,  # noqa: E712
                    ProcessControl.status != 'retired',
                )
                .filter(
                    ProcessControl.name.ilike('%SoD%')
                    | ProcessControl.name.ilike('%Segregation%')
                    | ProcessControl.name.ilike('%sod%')
                )
                .first()
            )
            if control is None:
                control = (
                    self._scoped(ProcessControl)
                    .filter(ProcessControl.is_active == True)  # noqa: E712
                    .first()
                )

            if control is None:
                logger.warning(
                    "XI-02 [tenant=%s] No ProcessControl found to attach SoD "
                    "deficiency for rule_id=%s — skipping.",
                    self.tenant_id, rule_id,
                )
                skipped_existing += 1
                continue

            # Check whether a sod_bridge deficiency already exists for this rule
            existing: ControlDeficiency | None = (
                self._scoped(ControlDeficiency)
                .filter(
                    ControlDeficiency.source == 'sod_bridge',
                    ControlDeficiency.control_id == control.id,
                    # The rule_id is embedded in the title
                    ControlDeficiency.title.ilike(f'%{rule_id}%'),
                    ControlDeficiency.status.in_([
                        DeficiencyStatus.OPEN.value,
                        DeficiencyStatus.IN_REMEDIATION.value,
                    ]),
                )
                .first()
            )
            if existing is not None:
                skipped_existing += 1
                continue

            # Create the deficiency
            deficiency_id = self._new_id("DEF-SOD-")
            deficiency = ControlDeficiency(
                tenant_id=self.tenant_id,
                deficiency_id=deficiency_id,
                control_id=control.id,
                source='sod_bridge',
                title=(
                    f"SoD Rule Breach: {rule_name} ({rule_id}) — "
                    f"{count} open violations (threshold: {threshold})"
                ),
                description=(
                    f"Automatically created by XI-02 bridge on {self._now().date()}. "
                    f"Rule '{rule_id}' has {count} OPEN violations which exceeds "
                    f"the configured threshold of {threshold}."
                ),
                severity='significant_deficiency',
                root_cause=(
                    "Multiple users hold conflicting access entitlements "
                    "that violate SoD rule constraints."
                ),
                status=DeficiencyStatus.OPEN,
                related_risk_ids=[],
                related_finding_ids=[],
                created_at=self._now(),
                updated_at=self._now(),
            )
            self.db.add(deficiency)
            self.db.flush()

            deficiencies_created += 1
            created_ids.append(deficiency_id)

            logger.info(
                "XI-02 [tenant=%s] Created deficiency %s for rule_id=%s "
                "(%d violations, threshold=%d).",
                self.tenant_id, deficiency_id, rule_id, count, threshold,
            )

        return {
            "rules_checked": rules_checked,
            "rules_above_threshold": rules_above_threshold,
            "deficiencies_created": deficiencies_created,
            "deficiency_ids": created_ids,
            "skipped_existing": skipped_existing,
        }

    # ------------------------------------------------------------------
    # XI-03: Risk <-> Control <-> Finding graph
    # ------------------------------------------------------------------

    def get_risk_control_finding_map(self) -> dict:
        """
        XI-03: Build a cross-module relationship graph for all active GRC objects
        in the current tenant.

        Returns:
          {
            "risks": {
              "<risk.id>": {
                "risk_id": str,
                "title": str,
                "residual_score": float | None,
                "linked_controls": [{"control_db_id": int, "control_id": str, "name": str}],
                "linked_findings": [{"finding_db_id": int, "finding_id": str, "title": str}]
              },
              ...
            },
            "controls": {
              "<control.id>": {
                "control_id": str,
                "name": str,
                "linked_risk_ids": [...],        # EnterpriseRisk.risk_id strings
                "linked_findings": [...]
              },
              ...
            },
            "summary": {
              "total_risks": int,
              "total_controls": int,
              "total_findings": int,
              "risks_with_controls": int,
              "risks_with_findings": int,
            }
          }
        """
        from db.models.audit_management import AuditFinding

        risks: list[EnterpriseRisk] = (
            self._scoped(EnterpriseRisk)
            .filter(EnterpriseRisk.is_active == True)  # noqa: E712
            .all()
        )
        controls: list[ProcessControl] = (
            self._scoped(ProcessControl)
            .filter(ProcessControl.is_active == True)  # noqa: E712
            .all()
        )
        findings: list[AuditFinding] = (
            self._scoped(AuditFinding)
            .all()
        )

        # Index controls by DB id for fast lookup
        control_by_id: dict[int, ProcessControl] = {c.id: c for c in controls}

        # Build a reverse map: enterprise_risk DB id -> list of controls
        # ProcessControl.risk_ids stores a JSON list of *EnterpriseRisk.id* integers
        risk_to_controls: dict[int, list[ProcessControl]] = {}
        for ctrl in controls:
            risk_ids_list: list | None = ctrl.risk_ids or []
            for risk_db_id in risk_ids_list:
                risk_to_controls.setdefault(int(risk_db_id), []).append(ctrl)

        # Build control -> findings map using AuditFinding.control_id
        control_to_findings: dict[int, list[AuditFinding]] = {}
        for finding in findings:
            if finding.control_id is not None:
                control_to_findings.setdefault(finding.control_id, []).append(finding)

        # Build risk -> findings map using AuditFinding.risk_id
        risk_to_findings: dict[int, list[AuditFinding]] = {}
        for finding in findings:
            if finding.risk_id is not None:
                risk_to_findings.setdefault(finding.risk_id, []).append(finding)

        # Assemble the risk section
        risk_map: dict[str, Any] = {}
        risks_with_controls = 0
        risks_with_findings = 0

        for risk in risks:
            linked_controls = [
                {
                    "control_db_id": c.id,
                    "control_id": c.control_id,
                    "name": c.name,
                }
                for c in risk_to_controls.get(risk.id, [])
            ]
            # Findings linked directly to the risk
            direct_findings = risk_to_findings.get(risk.id, [])
            # Findings linked via controls
            ctrl_findings: list[AuditFinding] = []
            for c in risk_to_controls.get(risk.id, []):
                ctrl_findings.extend(control_to_findings.get(c.id, []))

            # Deduplicate by finding id
            seen: set[int] = set()
            all_findings: list[AuditFinding] = []
            for f in direct_findings + ctrl_findings:
                if f.id not in seen:
                    seen.add(f.id)
                    all_findings.append(f)

            linked_findings = [
                {
                    "finding_db_id": f.id,
                    "finding_id": f.finding_id,
                    "title": f.title,
                    "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
                    "status": f.status.value if hasattr(f.status, 'value') else str(f.status),
                }
                for f in all_findings
            ]

            if linked_controls:
                risks_with_controls += 1
            if linked_findings:
                risks_with_findings += 1

            risk_map[str(risk.id)] = {
                "risk_id": risk.risk_id,
                "title": risk.title,
                "category": risk.category.value if hasattr(risk.category, 'value') else str(risk.category),
                "status": risk.status.value if hasattr(risk.status, 'value') else str(risk.status),
                "residual_score": risk.residual_score,
                "linked_controls": linked_controls,
                "linked_findings": linked_findings,
            }

        # Assemble the control section
        control_map: dict[str, Any] = {}
        for ctrl in controls:
            linked_risk_ids = []
            for risk_db_id in (ctrl.risk_ids or []):
                risk_obj = next((r for r in risks if r.id == int(risk_db_id)), None)
                if risk_obj:
                    linked_risk_ids.append(risk_obj.risk_id)

            ctrl_findings_list = [
                {
                    "finding_db_id": f.id,
                    "finding_id": f.finding_id,
                    "title": f.title,
                    "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
                    "status": f.status.value if hasattr(f.status, 'value') else str(f.status),
                }
                for f in control_to_findings.get(ctrl.id, [])
            ]

            control_map[str(ctrl.id)] = {
                "control_id": ctrl.control_id,
                "name": ctrl.name,
                "status": ctrl.status.value if hasattr(ctrl.status, 'value') else str(ctrl.status),
                "linked_risk_ids": linked_risk_ids,
                "linked_findings": ctrl_findings_list,
            }

        return {
            "risks": risk_map,
            "controls": control_map,
            "summary": {
                "total_risks": len(risks),
                "total_controls": len(controls),
                "total_findings": len(findings),
                "risks_with_controls": risks_with_controls,
                "risks_with_findings": risks_with_findings,
            },
        }

    # ------------------------------------------------------------------
    # XI-04: Audit planning data feed — composite risk score
    # ------------------------------------------------------------------

    def compute_audit_risk_scores(self, rm_weight: float = 0.40, pc_weight: float = 0.35, ac_weight: float = 0.25) -> list[dict]:
        """
        XI-04: Compute a composite risk score for each AuditableEntity and
        persist it back to entity.risk_score.

        Composite formula (equally weighted thirds):
          score = (
              rm_score * 0.40 +
              pc_score * 0.35 +
              ac_score * 0.25
          )

        where:
          rm_score  = max residual_score of EnterpriseRisks whose org_unit_id
                      matches entity.org_unit_id (normalised to 0-100 from 0-25)
          pc_score  = (open_deficiencies / max(total_controls_in_unit, 1)) * 100
          ac_score  = (open_violations_in_unit / max(total_users_possible, 1)) * 100
                      (capped at 100; when no org_unit_id available uses tenant-wide)

        Returns a list of dicts sorted by composite score descending:
          [
            {
              "entity_db_id": int,
              "entity_id": str,
              "name": str,
              "org_unit_id": int | None,
              "rm_score": float,
              "pc_score": float,
              "ac_score": float,
              "composite_score": float,
            },
            ...
          ]
        """
        entities: list[AuditableEntity] = (
            self._scoped(AuditableEntity)
            .filter(AuditableEntity.is_active == True)  # noqa: E712
            .all()
        )

        if not entities:
            return []

        # Pre-fetch all tenant-wide data once to avoid N+1 queries
        all_risks: list[EnterpriseRisk] = self._scoped(EnterpriseRisk).all()
        all_controls: list[ProcessControl] = self._scoped(ProcessControl).all()
        all_deficiencies: list[ControlDeficiency] = (
            self._scoped(ControlDeficiency)
            .filter(
                ControlDeficiency.status.in_([
                    DeficiencyStatus.OPEN.value,
                    DeficiencyStatus.IN_REMEDIATION.value,
                ])
            )
            .all()
        )
        all_violations: list[RiskViolation] = (
            self._scoped(RiskViolation)
            .filter(RiskViolation.status == ViolationStatus.OPEN)
            .all()
        )

        # Build lookup: org_unit_id -> objects
        risks_by_ou: dict[int | None, list[EnterpriseRisk]] = {}
        for r in all_risks:
            risks_by_ou.setdefault(r.org_unit_id, []).append(r)

        # controls by org_unit_id
        controls_by_ou: dict[int | None, list[ProcessControl]] = {}
        for c in all_controls:
            controls_by_ou.setdefault(c.org_unit_id, []).append(c)

        # deficiencies: map control_id -> deficiency, then look up via control.org_unit_id
        deficiencies_by_control: dict[int, list[ControlDeficiency]] = {}
        for d in all_deficiencies:
            deficiencies_by_control.setdefault(d.control_id, []).append(d)

        # AC violations: we use tenant-wide count as a proxy (no user->org_unit link
        # in the core violation model); if org_unit_id is set we use the same
        # tenant-wide metric proportionally.
        total_open_violations = len(all_violations)

        results: list[dict] = []

        for entity in entities:
            ou_id = entity.org_unit_id

            # --- RM score ---------------------------------------------------
            # Max residual score in the org unit (fall back to tenant-wide if no ou)
            risks_in_ou = risks_by_ou.get(ou_id, []) if ou_id else []
            if not risks_in_ou and ou_id is None:
                # Use all tenant risks
                risks_in_ou = all_risks
            rm_raw = max(
                (r.residual_score or 0.0 for r in risks_in_ou),
                default=0.0,
            )
            # Residual scores are 1-25 (5x5 matrix); normalise to 0-100
            rm_score = min((rm_raw / 25.0) * 100.0, 100.0)

            # --- PC score ---------------------------------------------------
            controls_in_ou = controls_by_ou.get(ou_id, []) if ou_id else []
            if not controls_in_ou and ou_id is None:
                controls_in_ou = all_controls

            open_deficiencies_in_ou = sum(
                len(deficiencies_by_control.get(c.id, []))
                for c in controls_in_ou
            )
            total_controls_in_ou = max(len(controls_in_ou), 1)
            pc_score = min((open_deficiencies_in_ou / total_controls_in_ou) * 100.0, 100.0)

            # --- AC score ---------------------------------------------------
            # Use tenant-wide open violations; when an org_unit_id is present
            # we apply a mild scaler (same violation pool but entity-specific
            # weighting can be refined once user->OU linkage is added).
            ac_score = min(total_open_violations * 2.0, 100.0)

            # --- Composite --------------------------------------------------
            composite = rm_score * rm_weight + pc_score * pc_weight + ac_score * ac_weight

            # Persist back to the entity
            entity.risk_score = round(composite, 2)
            entity.updated_at = self._now()

            results.append({
                "entity_db_id": entity.id,
                "entity_id": entity.entity_id,
                "name": entity.name,
                "org_unit_id": ou_id,
                "rm_score": round(rm_score, 2),
                "pc_score": round(pc_score, 2),
                "ac_score": round(ac_score, 2),
                "composite_score": round(composite, 2),
            })

        # Flush the updated risk_scores
        try:
            self.db.flush()
        except Exception as exc:
            logger.warning(
                "XI-04 [tenant=%s] Flush failed when persisting risk scores: %s",
                self.tenant_id, exc,
            )

        results.sort(key=lambda x: x["composite_score"], reverse=True)

        logger.info(
            "XI-04 [tenant=%s] Computed composite risk scores for %d auditable entities.",
            self.tenant_id, len(results),
        )

        return results

    # ------------------------------------------------------------------
    # XI-06: Unified notification dispatch
    # ------------------------------------------------------------------

    def notify_stakeholders(
        self,
        event_type: str,
        object_type: str,
        object_id: str,
        details: dict,
    ) -> dict:
        """
        XI-06: Unified notification dispatch for any GRC event.

        Persists a NotificationRecord if the model is available, then returns
        a routing summary.  If the notifications table is not yet provisioned,
        the method degrades gracefully and logs the event instead.

        Parameters
        ----------
        event_type   : str  e.g. 'violation_threshold_breach', 'deficiency_open',
                             'risk_score_updated', 'finding_raised'
        object_type  : str  e.g. 'risk_violation', 'control_deficiency',
                             'enterprise_risk', 'audit_finding'
        object_id    : str  Business-level ID of the affected object
        details      : dict Arbitrary event payload (merged into notification body)

        Returns
        -------
        dict with keys: notification_id, event_type, object_type, object_id,
                        recipients, channel, status
        """
        notification_id = self._new_id("NOTIF-")
        now = self._now()

        # Determine recipient routing by event type (XI-06 full event set)
        routing: dict[str, list[str]] = {
            # event_type -> [role labels / user IDs]
            'violation_threshold_breach': ['risk_manager', 'compliance_officer'],
            'deficiency_open': ['control_owner', 'risk_manager'],
            'deficiency_resolved': ['auditor', 'risk_manager'],
            'risk_score_updated': ['risk_owner', 'audit_committee'],
            'finding_raised': ['management_action_owner', 'lead_auditor'],
            'kri_breach': ['risk_owner', 'cro'],
            'audit_plan_approved': ['audit_director', 'all_auditors'],
            # XI-06 extended event types
            'risk_breach': ['risk_owner'],
            'control_failure': ['control_owner'],
            'finding_created': ['auditee', 'risk_owner'],
            'action_overdue': ['action_owner', 'manager'],
            'deficiency_created': ['control_owner'],
            'sod_violation': ['security_admin', 'compliance_officer'],
        }
        recipients = routing.get(event_type, ['grc_admin'])
        channel = 'in_app'  # default; extend to email/webhook in XI-06 full impl

        # Resolve actual recipient IDs from details payload when present
        # (e.g. details may contain risk_owner_id, control_owner_id, etc.)
        resolved_recipients = list(recipients)
        if event_type == 'risk_breach' and details.get('risk_owner_id'):
            resolved_recipients = [details['risk_owner_id']] + resolved_recipients
        elif event_type == 'control_failure' and details.get('control_owner_id'):
            resolved_recipients = [details['control_owner_id']] + resolved_recipients
        elif event_type == 'finding_created':
            if details.get('auditee_id'):
                resolved_recipients = [details['auditee_id']] + resolved_recipients
            if details.get('risk_owner_id'):
                resolved_recipients = [details['risk_owner_id']] + resolved_recipients
        elif event_type == 'action_overdue':
            if details.get('action_owner_id'):
                resolved_recipients = [details['action_owner_id']] + resolved_recipients
            if details.get('manager_id'):
                resolved_recipients = [details['manager_id']] + resolved_recipients
        elif event_type == 'kri_breach' and details.get('risk_owner_id'):
            resolved_recipients = [details['risk_owner_id']] + resolved_recipients
        elif event_type == 'deficiency_created' and details.get('control_owner_id'):
            resolved_recipients = [details['control_owner_id']] + resolved_recipients
        elif event_type == 'sod_violation' and details.get('security_admin_id'):
            resolved_recipients = [details['security_admin_id']] + resolved_recipients

        recipients = resolved_recipients

        notification_body = {
            "notification_id": notification_id,
            "tenant_id": self.tenant_id,
            "event_type": event_type,
            "object_type": object_type,
            "object_id": object_id,
            "recipients": recipients,
            "channel": channel,
            "created_at": now.isoformat(),
            "details": details,
        }

        # Attempt to persist via the notifications delivery layer if present
        persisted = False
        try:
            from core.notifications.delivery import NotificationDeliveryService  # type: ignore
            svc = NotificationDeliveryService(
                tenant_id=self.tenant_id,
                db_session=self.db,
            )
            svc.dispatch(
                event_type=event_type,
                object_type=object_type,
                object_id=object_id,
                recipients=recipients,
                payload=details,
            )
            persisted = True
        except (ImportError, AttributeError):
            # Delivery service not wired — try direct NotificationRecord insert
            try:
                from db.models.operations import NotificationRecord  # type: ignore
                record = NotificationRecord(
                    tenant_id=self.tenant_id,
                    notification_id=notification_id,
                    event_type=event_type,
                    object_type=object_type,
                    object_id=object_id,
                    recipients=recipients,
                    channel=channel,
                    payload=details,
                    created_at=now,
                )
                self.db.add(record)
                self.db.flush()
                persisted = True
            except Exception:
                logger.info(
                    "XI-06 [tenant=%s] Notification delivery service not available; "
                    "logging notification %s instead.",
                    self.tenant_id, notification_id,
                )
        except Exception as exc:
            logger.warning(
                "XI-06 [tenant=%s] Notification dispatch failed for %s: %s",
                self.tenant_id, notification_id, exc,
            )

        if not persisted:
            logger.info(
                "XI-06 NOTIFICATION | tenant=%s | id=%s | event=%s | "
                "object_type=%s | object_id=%s | recipients=%s | details=%s",
                self.tenant_id, notification_id, event_type,
                object_type, object_id, recipients, details,
            )

        return {
            "notification_id": notification_id,
            "event_type": event_type,
            "object_type": object_type,
            "object_id": object_id,
            "recipients": recipients,
            "channel": channel,
            "persisted": persisted,
            "status": "dispatched",
        }

    # ------------------------------------------------------------------
    # XI-02 Reverse: Deficiency resolution -> AC violation status update
    # ------------------------------------------------------------------

    def sync_deficiency_resolution_to_violations(self, deficiency_id: str) -> dict:
        """
        XI-02R: When a sod_bridge deficiency is closed (VERIFIED_CLOSED or
        REMEDIATED), find all OPEN RiskViolations whose rule_id is embedded
        in the deficiency title and mark them as REMEDIATED.

        Parameters
        ----------
        deficiency_id : str  The business-level deficiency_id string

        Returns
        -------
        dict:
          {
            "deficiency_id": str,
            "deficiency_status": str,
            "violations_updated": int,
            "violation_ids": [str, ...],
            "skipped_reason": str | None,
          }
        """
        deficiency: ControlDeficiency | None = (
            self._scoped(ControlDeficiency)
            .filter(ControlDeficiency.deficiency_id == deficiency_id)
            .first()
        )

        if deficiency is None:
            return {
                "deficiency_id": deficiency_id,
                "deficiency_status": None,
                "violations_updated": 0,
                "violation_ids": [],
                "skipped_reason": f"Deficiency '{deficiency_id}' not found.",
            }

        if deficiency.source != 'sod_bridge':
            return {
                "deficiency_id": deficiency_id,
                "deficiency_status": deficiency.status.value if hasattr(deficiency.status, 'value') else str(deficiency.status),
                "violations_updated": 0,
                "violation_ids": [],
                "skipped_reason": (
                    f"Deficiency source is '{deficiency.source}', not 'sod_bridge'. "
                    "Only sod_bridge deficiencies drive violation status updates."
                ),
            }

        current_status = (
            deficiency.status.value
            if hasattr(deficiency.status, 'value')
            else str(deficiency.status)
        )
        closable_statuses = {
            DeficiencyStatus.REMEDIATED.value,
            DeficiencyStatus.VERIFIED_CLOSED.value,
            DeficiencyStatus.ACCEPTED.value,
        }
        if current_status not in closable_statuses:
            return {
                "deficiency_id": deficiency_id,
                "deficiency_status": current_status,
                "violations_updated": 0,
                "violation_ids": [],
                "skipped_reason": (
                    f"Deficiency status is '{current_status}'. "
                    f"Must be one of {sorted(closable_statuses)} to trigger violation sync."
                ),
            }

        # Extract the rule_id from the deficiency title.
        # Title format: "SoD Rule Breach: <rule_name> (<rule_id>) — ..."
        rule_id: str | None = None
        title = deficiency.title or ""
        try:
            # Parse "(...)" between parens that follow the rule name
            import re
            match = re.search(r'\(([^)]+)\)', title)
            if match:
                rule_id = match.group(1).strip()
        except Exception:
            pass

        if not rule_id:
            return {
                "deficiency_id": deficiency_id,
                "deficiency_status": current_status,
                "violations_updated": 0,
                "violation_ids": [],
                "skipped_reason": (
                    f"Could not extract rule_id from deficiency title: '{title}'"
                ),
            }

        # Update all OPEN violations for this rule
        violations: list[RiskViolation] = (
            self._scoped(RiskViolation)
            .filter(
                RiskViolation.rule_id == rule_id,
                RiskViolation.status == ViolationStatus.OPEN,
            )
            .all()
        )

        now = self._now()
        updated_ids: list[str] = []
        for violation in violations:
            violation.status = ViolationStatus.REMEDIATED
            violation.resolved_at = now
            violation.resolved_by = 'xi_bridge'
            violation.resolution_notes = (
                f"Auto-resolved by XI-02R bridge: sod_bridge deficiency "
                f"'{deficiency_id}' was marked '{current_status}'."
            )
            violation.updated_at = now
            updated_ids.append(violation.violation_id)

        try:
            self.db.flush()
        except Exception as exc:
            logger.warning(
                "XI-02R [tenant=%s] Flush failed when updating violations: %s",
                self.tenant_id, exc,
            )

        logger.info(
            "XI-02R [tenant=%s] Deficiency '%s' resolved; updated %d violations "
            "for rule_id='%s'.",
            self.tenant_id, deficiency_id, len(updated_ids), rule_id,
        )

        return {
            "deficiency_id": deficiency_id,
            "deficiency_status": current_status,
            "rule_id": rule_id,
            "violations_updated": len(updated_ids),
            "violation_ids": updated_ids,
            "skipped_reason": None,
        }
