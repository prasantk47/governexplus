"""
Access Certification API Router

Endpoints for access certification/review campaigns.
All data is DB-backed via dependency-injected CertificationManager.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.certification import (
    CertificationManager, CertificationCampaign,
    CampaignStatus, CampaignType, CertificationAction
)
from core.rules import RuleEngine
from db.database import get_db

router = APIRouter(tags=["Certification"])

# Shared rule engine
rule_engine = RuleEngine()

DEFAULT_TENANT = "tenant_default"


def _get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    return x_tenant_id or DEFAULT_TENANT


def _get_manager(db: Session = Depends(get_db)) -> CertificationManager:
    return CertificationManager(db=db, rule_engine=rule_engine)


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateCampaignModel(BaseModel):
    name: str = Field(..., example="Q1 2024 User Access Review")
    description: str = Field(..., example="Quarterly access certification for all users")
    campaign_type: str = Field(default="user_access", example="user_access")
    owner_id: str = Field(..., example="security.admin@company.com")
    owner_name: str = Field(..., example="Security Admin")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    included_systems: Optional[List[str]] = Field(default=["SAP"])
    included_departments: Optional[List[str]] = None
    risk_threshold: Optional[float] = Field(None, description="Only include items above this risk score")
    include_sod_only: bool = Field(default=False)


class CertifyDecisionModel(BaseModel):
    reviewer_id: str = Field(..., example="manager@company.com")
    action: str = Field(..., example="certify")
    comments: Optional[str] = Field(None, example="Verified access is still required")
    delegate_to: Optional[str] = None


class BulkCertifyModel(BaseModel):
    reviewer_id: str
    item_ids: List[str]
    comments: str = "Bulk certified"


# =============================================================================
# Campaign Management Endpoints
# =============================================================================

@router.post("/campaigns", status_code=201)
async def create_campaign(
    campaign: CreateCampaignModel,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        type_map = {
            "user_access": CampaignType.USER_ACCESS,
            "role_membership": CampaignType.ROLE_MEMBERSHIP,
            "sensitive_access": CampaignType.SENSITIVE_ACCESS,
            "sod_violations": CampaignType.SOD_VIOLATIONS,
            "manager": CampaignType.MANAGER_CERTIFICATION
        }
        camp_type = type_map.get(campaign.campaign_type, CampaignType.USER_ACCESS)

        cert_campaign = await mgr.create_campaign(
            name=campaign.name,
            description=campaign.description,
            campaign_type=camp_type,
            owner_id=campaign.owner_id,
            owner_name=campaign.owner_name,
            tenant_id=tenant_id,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            included_systems=campaign.included_systems,
            included_departments=campaign.included_departments,
            risk_threshold=campaign.risk_threshold,
            include_sod_only=campaign.include_sod_only
        )

        return {
            "campaign_id": cert_campaign.campaign_id,
            "status": cert_campaign.status.value,
            "message": "Campaign created. Use /generate-items to populate items."
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/generate-items")
async def generate_campaign_items(
    campaign_id: str,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        campaign = await mgr.generate_campaign_items(campaign_id, tenant_id)

        return {
            "campaign_id": campaign_id,
            "items_generated": len(campaign.items),
            "status": campaign.status.value,
            "message": "Items generated. Use /start to activate the campaign."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        campaign = await mgr.start_campaign(campaign_id, tenant_id)

        return {
            "campaign_id": campaign_id,
            "status": campaign.status.value,
            "total_items": len(campaign.items),
            "end_date": campaign.end_date.isoformat(),
            "message": "Campaign started. Reviewers have been notified."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns")
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status"),
    owner: Optional[str] = Query(None, description="Filter by owner"),
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    status_enum = None
    if status:
        try:
            status_enum = CampaignStatus(status)
        except ValueError:
            pass

    campaigns = mgr.get_campaigns(status=status_enum, owner_id=owner, tenant_id=tenant_id)

    return {
        "total": len(campaigns),
        "campaigns": [c.to_summary() for c in campaigns]
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    campaign = mgr.get_campaign(campaign_id, tenant_id)

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    return {
        **campaign.to_dict(),
        "reviewer_summary": campaign.get_reviewer_summary()
    }


@router.get("/campaigns/{campaign_id}/items")
async def get_campaign_items(
    campaign_id: str,
    reviewer: Optional[str] = Query(None, description="Filter by reviewer"),
    pending_only: bool = Query(False, description="Only pending items"),
    limit: int = Query(100, le=500),
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    campaign = mgr.get_campaign(campaign_id, tenant_id)

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    items = campaign.items

    if reviewer:
        items = [i for i in items if i.reviewer_id == reviewer or i.delegated_to == reviewer]

    if pending_only:
        items = [i for i in items if not i.is_completed]

    return {
        "campaign_id": campaign_id,
        "total": len(items),
        "items": [i.to_dict() for i in items[:limit]]
    }


# =============================================================================
# Certification Decision Endpoints
# =============================================================================

@router.post("/campaigns/{campaign_id}/items/{item_id}/decision")
async def submit_decision(
    campaign_id: str,
    item_id: str,
    decision: CertifyDecisionModel,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        action_map = {
            "certify": CertificationAction.CERTIFY,
            "revoke": CertificationAction.REVOKE,
            "modify": CertificationAction.MODIFY,
            "delegate": CertificationAction.DELEGATE,
            "skip": CertificationAction.SKIP
        }
        action = action_map.get(decision.action.lower())

        if not action:
            raise ValueError(f"Invalid action: {decision.action}")

        item = await mgr.process_decision(
            campaign_id=campaign_id,
            item_id=item_id,
            action=action,
            reviewer_id=decision.reviewer_id,
            comments=decision.comments or "",
            delegate_to=decision.delegate_to,
            tenant_id=tenant_id,
        )

        return {
            "item_id": item_id,
            "action": decision.action,
            "is_completed": item.is_completed,
            "message": f"Decision '{decision.action}' recorded"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/campaigns/{campaign_id}/bulk-certify")
async def bulk_certify(
    campaign_id: str,
    request: BulkCertifyModel,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    result = await mgr.bulk_certify(
        campaign_id=campaign_id,
        item_ids=request.item_ids,
        reviewer_id=request.reviewer_id,
        comments=request.comments,
        tenant_id=tenant_id,
    )

    return {
        "campaign_id": campaign_id,
        **result,
        "message": f"Processed {result['processed']} items"
    }


# =============================================================================
# Reviewer Endpoints
# =============================================================================

@router.get("/my-reviews")
async def get_my_reviews(
    reviewer_id: str = Query(..., description="Reviewer user ID"),
    pending_only: bool = Query(True),
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    items = mgr.get_reviewer_items(reviewer_id, pending_only=pending_only, tenant_id=tenant_id)

    return {
        "reviewer_id": reviewer_id,
        "total_pending": len([i for i in items if not i.is_completed]),
        "items": [i.to_dict() for i in items],
    }


@router.get("/reviewer-workload")
async def get_reviewer_workload(
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    return mgr.get_reviewer_workload(tenant_id)


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics")
async def get_certification_statistics(
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    return mgr.get_statistics(tenant_id)


@router.get("/campaigns/{campaign_id}/statistics")
async def get_campaign_statistics(
    campaign_id: str,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    campaign = mgr.get_campaign(campaign_id, tenant_id)

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    progress = campaign.calculate_progress()
    reviewer_summary = campaign.get_reviewer_summary()

    risk_distribution = {
        "low": sum(1 for i in campaign.items if i.risk_score < 30),
        "medium": sum(1 for i in campaign.items if 30 <= i.risk_score < 60),
        "high": sum(1 for i in campaign.items if 60 <= i.risk_score < 80),
        "critical": sum(1 for i in campaign.items if i.risk_score >= 80)
    }

    return {
        "campaign_id": campaign_id,
        **progress,
        "reviewer_summary": reviewer_summary,
        "risk_distribution": risk_distribution,
        "sod_violations": sum(1 for i in campaign.items if i.has_sod_violation),
        "days_remaining": campaign.days_remaining()
    }


# =============================================================================
# Review Type Endpoints (Role Owner, App Owner, Compliance)
# =============================================================================

class GenerateRoleOwnerModel(BaseModel):
    role_id: str
    role_owner_id: str
    role_owner_name: str = ""


class GenerateAppOwnerModel(BaseModel):
    system_id: str
    app_owner_id: str
    app_owner_name: str = ""


class GenerateComplianceModel(BaseModel):
    reviewer_id: str
    reviewer_name: str = ""
    min_risk_score: float = 70


@router.post("/campaigns/{campaign_id}/generate-role-owner-items")
async def generate_role_owner_items(
    campaign_id: str,
    request: GenerateRoleOwnerModel,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        items = await mgr.generate_role_owner_items(
            campaign_id, request.role_id, request.role_owner_id, request.role_owner_name, tenant_id
        )
        return {"campaign_id": campaign_id, "items_generated": len(items), "review_type": "role_owner"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/generate-app-owner-items")
async def generate_app_owner_items(
    campaign_id: str,
    request: GenerateAppOwnerModel,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        items = await mgr.generate_app_owner_items(
            campaign_id, request.system_id, request.app_owner_id, request.app_owner_name, tenant_id
        )
        return {"campaign_id": campaign_id, "items_generated": len(items), "review_type": "app_owner"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/generate-compliance-items")
async def generate_compliance_items(
    campaign_id: str,
    request: GenerateComplianceModel,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        items = await mgr.generate_compliance_items(
            campaign_id, request.reviewer_id, request.reviewer_name, request.min_risk_score, tenant_id
        )
        return {"campaign_id": campaign_id, "items_generated": len(items), "review_type": "compliance"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Escalation Endpoints
# =============================================================================

@router.post("/campaigns/{campaign_id}/check-escalation")
async def check_escalation(
    campaign_id: str,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    result = await mgr.check_escalation(campaign_id, tenant_id)
    return result


# =============================================================================
# Evidence Endpoints
# =============================================================================

class AddEvidenceModel(BaseModel):
    evidence_type: str = "justification"
    description: str
    uploaded_by: str
    content: Optional[str] = None


@router.post("/campaigns/{campaign_id}/items/{item_id}/evidence")
async def add_evidence(
    campaign_id: str,
    item_id: str,
    request: AddEvidenceModel,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        evidence = await mgr.add_evidence(
            campaign_id, item_id, request.evidence_type,
            request.description, request.uploaded_by, request.content,
            tenant_id=tenant_id,
        )
        return {"evidence_id": evidence.evidence_id, "message": "Evidence added"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns/{campaign_id}/items/{item_id}/evidence")
async def get_evidence(
    campaign_id: str,
    item_id: str,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    evidence = mgr.get_evidence(campaign_id, item_id, tenant_id)
    return {"item_id": item_id, "evidence": evidence}


# =============================================================================
# De-provisioning Endpoint
# =============================================================================

@router.post("/campaigns/{campaign_id}/execute-revocations")
async def execute_revocations(
    campaign_id: str,
    mgr: CertificationManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        result = await mgr.execute_revocations(campaign_id, tenant_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
