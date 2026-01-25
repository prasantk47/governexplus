"""
Access Certification API Router

Endpoints for access certification/review campaigns.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from core.certification import (
    CertificationManager, CertificationCampaign,
    CampaignStatus, CampaignType, CertificationAction
)

router = APIRouter(tags=["Certification"])

# Initialize manager
certification_manager = CertificationManager()


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateCampaignModel(BaseModel):
    """Model for creating a certification campaign"""
    name: str = Field(..., example="Q1 2024 User Access Review")
    description: str = Field(..., example="Quarterly access certification for all users")
    campaign_type: str = Field(default="user_access",
        example="user_access")  # user_access, role_membership, sensitive_access, sod_violations
    owner_id: str = Field(..., example="security.admin@company.com")
    owner_name: str = Field(..., example="Security Admin")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    included_systems: Optional[List[str]] = Field(default=["SAP"])
    included_departments: Optional[List[str]] = None
    risk_threshold: Optional[float] = Field(None, description="Only include items above this risk score")
    include_sod_only: bool = Field(default=False)


class CertifyDecisionModel(BaseModel):
    """Model for certification decision"""
    reviewer_id: str = Field(..., example="manager@company.com")
    action: str = Field(..., example="certify")  # certify, revoke, modify, delegate
    comments: Optional[str] = Field(None, example="Verified access is still required")
    delegate_to: Optional[str] = None


class BulkCertifyModel(BaseModel):
    """Model for bulk certification"""
    reviewer_id: str
    item_ids: List[str]
    comments: str = "Bulk certified"


# =============================================================================
# Campaign Management Endpoints
# =============================================================================

@router.post("/campaigns", status_code=201)
async def create_campaign(campaign: CreateCampaignModel):
    """
    Create a new certification campaign.

    The campaign is created in DRAFT status. Use /generate-items and /start
    to activate it.
    """
    try:
        # Map campaign type
        type_map = {
            "user_access": CampaignType.USER_ACCESS,
            "role_membership": CampaignType.ROLE_MEMBERSHIP,
            "sensitive_access": CampaignType.SENSITIVE_ACCESS,
            "sod_violations": CampaignType.SOD_VIOLATIONS,
            "manager": CampaignType.MANAGER_CERTIFICATION
        }
        camp_type = type_map.get(campaign.campaign_type, CampaignType.USER_ACCESS)

        cert_campaign = await certification_manager.create_campaign(
            name=campaign.name,
            description=campaign.description,
            campaign_type=camp_type,
            owner_id=campaign.owner_id,
            owner_name=campaign.owner_name,
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
async def generate_campaign_items(campaign_id: str):
    """
    Generate certification items for a campaign.

    Pulls data from connected systems based on campaign scope.
    """
    try:
        campaign = await certification_manager.generate_campaign_items(campaign_id)

        return {
            "campaign_id": campaign_id,
            "items_generated": len(campaign.items),
            "status": campaign.status.value,
            "message": "Items generated. Use /start to activate the campaign."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    """
    Start a certification campaign.

    Notifies all reviewers of their assigned items.
    """
    try:
        campaign = await certification_manager.start_campaign(campaign_id)

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
    owner: Optional[str] = Query(None, description="Filter by owner")
):
    """List certification campaigns"""
    status_enum = None
    if status:
        try:
            status_enum = CampaignStatus(status)
        except ValueError:
            pass

    campaigns = certification_manager.get_campaigns(status=status_enum, owner_id=owner)

    return {
        "total": len(campaigns),
        "campaigns": [c.to_summary() for c in campaigns]
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get full campaign details"""
    campaign = certification_manager.get_campaign(campaign_id)

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
    limit: int = Query(100, le=500)
):
    """Get items for a campaign"""
    campaign = certification_manager.get_campaign(campaign_id)

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
    decision: CertifyDecisionModel
):
    """
    Submit a certification decision for an item.

    Actions: certify, revoke, modify, delegate
    """
    try:
        # Map action
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

        item = await certification_manager.process_decision(
            campaign_id=campaign_id,
            item_id=item_id,
            action=action,
            reviewer_id=decision.reviewer_id,
            comments=decision.comments or "",
            delegate_to=decision.delegate_to
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
async def bulk_certify(campaign_id: str, request: BulkCertifyModel):
    """
    Bulk certify multiple items at once.
    """
    result = await certification_manager.bulk_certify(
        campaign_id=campaign_id,
        item_ids=request.item_ids,
        reviewer_id=request.reviewer_id,
        comments=request.comments
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
    pending_only: bool = Query(True)
):
    """
    Get all certification items assigned to a reviewer.

    This is the reviewer's unified inbox.
    """
    items = certification_manager.get_reviewer_items(reviewer_id, pending_only=pending_only)

    # Group by campaign
    by_campaign = {}
    for item in items:
        campaign = certification_manager.get_campaign(item.item_id.split("-")[0]) if "-" in item.item_id else None
        campaign_id = "unknown"

        for c in certification_manager.campaigns.values():
            if any(i.item_id == item.item_id for i in c.items):
                campaign_id = c.campaign_id
                break

        if campaign_id not in by_campaign:
            by_campaign[campaign_id] = []
        by_campaign[campaign_id].append(item)

    return {
        "reviewer_id": reviewer_id,
        "total_pending": len([i for i in items if not i.is_completed]),
        "items": [i.to_dict() for i in items],
        "by_campaign": {k: len(v) for k, v in by_campaign.items()}
    }


@router.get("/reviewer-workload")
async def get_reviewer_workload():
    """Get workload distribution across reviewers"""
    return certification_manager.get_reviewer_workload()


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics")
async def get_certification_statistics():
    """Get overall certification statistics"""
    return certification_manager.get_statistics()


@router.get("/campaigns/{campaign_id}/statistics")
async def get_campaign_statistics(campaign_id: str):
    """Get detailed statistics for a specific campaign"""
    campaign = certification_manager.get_campaign(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    progress = campaign.calculate_progress()
    reviewer_summary = campaign.get_reviewer_summary()

    # Risk distribution of items
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
