"""
Gate 2 — Golden E2E Flow Integration Test

Proves the complete lifecycle:
  Request → EffectiveAccess → RiskEngine → Findings → DecisionEngine
  → Approval → ExecutionEngine → Evidence → Close

Uses real DB (SQLite) and all 6 core engines wired through AccessRequestManager.
"""

import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from db.models.user import User, Role, UserRole, UserEntitlement
from core.access_request.manager import AccessRequestManager
from core.access_request.models import (
    AccessRequestStatus, RequestType, ApprovalAction
)
from core.rules import RuleEngine


@pytest.fixture
def db_session():
    """Create an in-memory SQLite DB with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db_session):
    """Seed the DB with test users and roles."""
    # Create users
    requester = User(
        username="JSMITH",
        user_id="JSMITH",
        full_name="John Smith",
        email="john.smith@company.com",
        department="Finance",
    )
    target = User(
        username="MJONES",
        user_id="MJONES",
        full_name="Mary Jones",
        email="mary.jones@company.com",
        department="Finance",
    )
    db_session.add_all([requester, target])
    db_session.flush()

    # Create roles
    role_ap = Role(
        role_id="Z_AP_CLERK",
        role_name="AP Clerk",
        description="Accounts Payable Clerk",
        source_system="SAP",
        risk_level="medium",
        is_active=True,
    )
    db_session.add(role_ap)
    db_session.commit()

    return db_session


@pytest.fixture
def manager(seeded_db):
    """Create an AccessRequestManager wired to the test DB."""
    return AccessRequestManager(db=seeded_db, rule_engine=RuleEngine())


# =========================================================================
# Test: Full E2E Golden Flow
# =========================================================================

@pytest.mark.asyncio
async def test_golden_flow_request_to_provisioned(manager, seeded_db):
    """
    Prove the full lifecycle from request creation through to provisioning
    with all 6 core engines participating.
    """

    # 1. Create a request
    request = await manager.create_request(
        tenant_id="tenant_test",
        requester_user_id="JSMITH",
        requester_name="John Smith",
        requester_email="john.smith@company.com",
        target_user_id="MJONES",
        target_user_name="Mary Jones",
        requested_roles=["Z_AP_CLERK"],
        business_justification="Mary needs AP Clerk access for invoice processing in Q3 close.",
    )

    assert request.status == AccessRequestStatus.DRAFT
    assert request.request_id is not None

    # 2. Submit the request (triggers EffectiveAccess → RiskEngine → Findings → Decision → Evidence)
    submitted = await manager.submit_request(request.request_id, tenant_id="tenant_test")

    assert submitted.status == AccessRequestStatus.PENDING_APPROVAL
    assert submitted.submitted_at is not None
    assert submitted.overall_risk_score >= 0
    assert len(submitted.approval_steps) > 0

    # 3. Verify evidence was recorded for submission
    evidence_records = manager.evidence_engine.get_for_request(request.request_id)
    assert len(evidence_records) >= 1
    submit_evidence = [e for e in evidence_records if e.action == "submit_request"]
    assert len(submit_evidence) == 1
    assert submit_evidence[0].target_user_id == "MJONES"

    # 4. Process approval — use the actual approver assigned to each step
    step = submitted.approval_steps[0]
    actor = step.approver_ids[0] if step.approver_ids else "default.manager@company.com"
    approved = await manager.process_approval(
        request_id=request.request_id,
        step_id=step.step_id,
        action=ApprovalAction.APPROVE,
        actor_id=actor,
        comments="Approved for Q3 close",
        tenant_id="tenant_test",
    )

    # If multi-step, approve remaining steps
    while approved.status == AccessRequestStatus.PENDING_APPROVAL:
        next_step = approved.approval_steps[approved.current_step]
        next_actor = next_step.approver_ids[0] if next_step.approver_ids else "security@company.com"
        approved = await manager.process_approval(
            request_id=request.request_id,
            step_id=next_step.step_id,
            action=ApprovalAction.APPROVE,
            actor_id=next_actor,
            comments="Approved",
            tenant_id="tenant_test",
        )

    # 5. After final approval → should be PROVISIONED
    assert approved.status == AccessRequestStatus.PROVISIONED
    assert approved.provisioned_at is not None
    assert approved.completed_at is not None

    # 6. Verify evidence was recorded for approval + provisioning
    all_evidence = manager.evidence_engine.get_for_request(request.request_id)
    evidence_actions = {e.action for e in all_evidence}
    assert "submit_request" in evidence_actions
    assert "provision_access" in evidence_actions

    # 7. Verify evidence chain integrity
    valid, errors = manager.evidence_engine.verify_chain()
    assert valid, f"Evidence chain broken: {errors}"

    # 8. Verify execution plan was created and closed
    plans = manager.execution_engine.get_plans_for_user("MJONES")
    assert len(plans) >= 1
    assert plans[0].phase.value in ("closed", "verified")

    # 9. Verify findings engine processed something (even if no violations)
    summary = manager.findings_engine.get_summary()
    assert "total" in summary or "by_severity" in summary


@pytest.mark.asyncio
async def test_request_rejection_flow(manager):
    """Test that rejecting a request records evidence and stops provisioning."""

    request = await manager.create_request(
        tenant_id="tenant_test",
        requester_user_id="JSMITH",
        requester_name="John Smith",
        requester_email="john.smith@company.com",
        target_user_id="MJONES",
        target_user_name="Mary Jones",
        requested_roles=["Z_AP_CLERK"],
        business_justification="Need AP access for month-end processing and reconciliation.",
    )

    submitted = await manager.submit_request(request.request_id, tenant_id="tenant_test")
    step = submitted.approval_steps[0]
    actor = step.approver_ids[0] if step.approver_ids else "default.manager@company.com"

    rejected = await manager.process_approval(
        request_id=request.request_id,
        step_id=step.step_id,
        action=ApprovalAction.REJECT,
        actor_id=actor,
        comments="Not justified",
        tenant_id="tenant_test",
    )

    assert rejected.status == AccessRequestStatus.REJECTED

    # No provisioning should have happened
    plans = manager.execution_engine.get_plans_for_user("MJONES")
    # Either no plans or plan not executed/closed
    assert all(p.phase.value != "closed" for p in plans)

    # Evidence should include the rejection
    all_evidence = manager.evidence_engine.get_for_request(request.request_id)
    rejection_evidence = [e for e in all_evidence if "reject" in e.action]
    assert len(rejection_evidence) >= 1


@pytest.mark.asyncio
async def test_evidence_chain_integrity(manager):
    """Verify the hash chain remains intact across multiple operations."""

    # Create and submit two requests
    for i in range(2):
        req = await manager.create_request(
            tenant_id="tenant_test",
            requester_user_id="JSMITH",
            requester_name="John Smith",
            requester_email="john.smith@company.com",
            target_user_id="MJONES",
            target_user_name="Mary Jones",
            requested_roles=["Z_AP_CLERK"],
            business_justification=f"Request #{i+1} for AP access needed for reconciliation.",
        )
        await manager.submit_request(req.request_id, tenant_id="tenant_test")

    # Verify chain
    valid, errors = manager.evidence_engine.verify_chain()
    assert valid, f"Evidence chain integrity failed: {errors}"
    assert len(manager.evidence_engine.get_all()) >= 2
