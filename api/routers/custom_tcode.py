"""
Custom Transaction Analysis Router
Endpoints for analyzing custom SAP transactions (Z*/Y* prefix).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.custom_tcode.analyzer import get_analyzer

router = APIRouter(tags=["Custom Transaction Analysis"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    tcode: str = Field(..., description="Custom transaction code to analyze (Z* or Y*)")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", summary="Dashboard summary for custom transaction analysis")
async def get_summary() -> Dict[str, Any]:
    """
    Return aggregated statistics across all known custom transactions:
    risk distribution, module breakdown, behavior breakdown, and
    the list of critical transactions requiring immediate review.
    """
    analyzer = get_analyzer()
    return analyzer.get_analysis_summary()


@router.get("/transactions", summary="List all known custom transactions")
async def list_transactions(
    module: Optional[str] = Query(None, description="Filter by SAP module, e.g. FI, MM, HR"),
    risk_level: Optional[str] = Query(
        None,
        description="Filter by risk level: low | medium | high | critical"
    ),
    behavior: Optional[str] = Query(
        None,
        description="Filter by behavior: creates | modifies | deletes | reads | executes | admin"
    ),
) -> List[Dict[str, Any]]:
    """
    List all custom transactions in the catalog with optional filters.

    Transactions are Z*/Y* custom programs discovered via system analysis.
    """
    analyzer = get_analyzer()
    return analyzer.get_all_custom_tcodes(
        module=module,
        risk_level=risk_level,
        behavior=behavior,
    )


@router.get("/risks", summary="All custom transactions with identified SoD risks")
async def get_risks() -> List[Dict[str, Any]]:
    """
    Return risk assessments for all custom transactions that have identified
    SoD risks or are classified as high/critical risk.
    """
    analyzer = get_analyzer()
    all_tcodes = analyzer.get_all_custom_tcodes()
    results = []
    for t in all_tcodes:
        if t["risk_level"] in ("high", "critical"):
            risk_detail = analyzer.detect_risk(t["tcode"])
            results.append(risk_detail)
    return results


@router.get(
    "/transactions/{tcode}",
    summary="Get analysis for a specific custom transaction"
)
async def get_transaction(tcode: str) -> Dict[str, Any]:
    """
    Return the full analysis for a specific custom transaction including:
    - Detected behaviors (creates, modifies, deletes, etc.)
    - Authorization objects used
    - Tables accessed
    - Function modules called
    - Standard SAP equivalent
    - Risk classification
    """
    analyzer = get_analyzer()
    result = analyzer.analyze_transaction(tcode)
    if "error" in result and "Not a custom transaction" in result.get("error", ""):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/analyze", summary="Analyze a custom transaction on demand")
async def analyze_transaction(body: AnalyzeRequest) -> Dict[str, Any]:
    """
    Perform on-demand analysis of a custom transaction code.

    Returns behavior detection, risk profile, business function mapping,
    and SoD rule suggestions in a single response.
    """
    tcode = body.tcode.strip().upper()
    if not (tcode.startswith("Z") or tcode.startswith("Y")):
        raise HTTPException(
            status_code=400,
            detail="Transaction code must start with Z or Y to be a custom transaction"
        )

    analyzer = get_analyzer()

    analysis = analyzer.analyze_transaction(tcode)
    risk = analyzer.detect_risk(tcode)
    functions = analyzer.map_to_functions(tcode)
    sod_suggestions = analyzer.suggest_sod_rules(tcode)

    return {
        "tcode": tcode,
        "analysis": analysis,
        "risk": risk,
        "business_functions": functions,
        "sod_suggestions": sod_suggestions,
    }


@router.get(
    "/sod-suggestions/{tcode}",
    summary="SoD rule suggestions for a custom transaction"
)
async def get_sod_suggestions(tcode: str) -> Dict[str, Any]:
    """
    Return suggested SoD rules for a custom transaction based on the business
    functions it performs and known conflict patterns.

    Use these suggestions to configure GRC rules that will flag users who
    have access to conflicting combinations of functions.
    """
    tcode_upper = tcode.strip().upper()
    if not (tcode_upper.startswith("Z") or tcode_upper.startswith("Y")):
        raise HTTPException(
            status_code=400,
            detail="Transaction code must start with Z or Y"
        )

    analyzer = get_analyzer()
    return analyzer.suggest_sod_rules(tcode_upper)
