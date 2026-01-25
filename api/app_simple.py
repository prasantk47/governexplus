"""
GRC Zero Trust Platform - Simplified API Application
A working demo API that starts cleanly without complex dependencies.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

# Create FastAPI application
app = FastAPI(
    title="GRC Zero Trust Platform",
    description="Python-based GRC Access Control Platform - Demo API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Models
# ==============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class AccessRequest(BaseModel):
    user_id: str
    role_id: str
    justification: str
    duration_days: int = 30

class RiskAnalysisRequest(BaseModel):
    user_id: str
    transaction_codes: List[str] = []

class FirefighterRequest(BaseModel):
    firefighter_id: str
    reason: str
    duration_hours: int = 4


# ==============================================================================
# Mock Data
# ==============================================================================

DEMO_USERS = {
    "JSMITH": {"name": "John Smith", "department": "Finance", "email": "jsmith@company.com"},
    "MBROWN": {"name": "Mary Brown", "department": "Procurement", "email": "mbrown@company.com"},
    "TDAVIS": {"name": "Tom Davis", "department": "IT", "email": "tdavis@company.com"},
    "AWILSON": {"name": "Alice Wilson", "department": "HR", "email": "awilson@company.com"},
    "admin": {"name": "Admin User", "department": "IT", "email": "admin@company.com"},
}

DEMO_ROLES = {
    "SAP_FI_USER": {"name": "Finance User", "system": "SAP", "risk_level": "low"},
    "SAP_MM_BUYER": {"name": "Procurement Buyer", "system": "SAP", "risk_level": "medium"},
    "SAP_HR_ADMIN": {"name": "HR Administrator", "system": "SAP", "risk_level": "high"},
    "SAP_ALL": {"name": "Super User", "system": "SAP", "risk_level": "critical"},
}

SOD_RULES = [
    {"rule_id": "SOD-FI-001", "name": "Vendor Master vs AP Payment", "risk_level": "critical"},
    {"rule_id": "SOD-MM-002", "name": "PO Creation vs Goods Receipt", "risk_level": "high"},
    {"rule_id": "SOD-HR-001", "name": "Personnel Master vs Payroll", "risk_level": "critical"},
]


# ==============================================================================
# Root Endpoints
# ==============================================================================

@app.get("/", tags=["System"])
async def root():
    """API root"""
    return {
        "name": "GRC Zero Trust Platform",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "modules": [
            "/auth", "/users", "/roles", "/risk",
            "/access-requests", "/firefighter", "/dashboard",
            "/certification", "/sod-rules"
        ]
    }

@app.get("/health", tags=["System"])
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "healthy",
            "database": "healthy"
        }
    }


# ==============================================================================
# Auth Endpoints
# ==============================================================================

@app.post("/auth/login", tags=["Auth"])
async def login(request: LoginRequest):
    """Login endpoint"""
    if request.username in DEMO_USERS or request.username == "admin":
        return {
            "access_token": f"demo_token_{request.username}_{int(time.time())}",
            "token_type": "bearer",
            "user": {
                "user_id": request.username,
                **DEMO_USERS.get(request.username, {"name": "Demo User", "department": "Demo", "email": "demo@company.com"})
            }
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auth/profile", tags=["Auth"])
async def get_profile():
    """Get current user profile"""
    return {
        "user_id": "admin",
        "name": "Admin User",
        "department": "IT",
        "email": "admin@company.com",
        "roles": ["ADMIN", "GRC_MANAGER"]
    }


# ==============================================================================
# Users Endpoints
# ==============================================================================

@app.get("/users", tags=["Users"])
async def list_users(limit: int = 100, search: Optional[str] = None):
    """List all users"""
    users = [
        {"user_id": uid, **data}
        for uid, data in DEMO_USERS.items()
    ]
    if search:
        users = [u for u in users if search.lower() in u["name"].lower()]
    return {"users": users[:limit], "total": len(users)}

@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: str):
    """Get user details"""
    if user_id not in DEMO_USERS:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id, **DEMO_USERS[user_id]}

@app.get("/users/{user_id}/roles", tags=["Users"])
async def get_user_roles(user_id: str):
    """Get user's assigned roles"""
    return {
        "user_id": user_id,
        "roles": [
            {"role_id": "SAP_FI_USER", "assigned_date": "2024-01-15"},
            {"role_id": "SAP_MM_BUYER", "assigned_date": "2024-02-01"}
        ]
    }


# ==============================================================================
# Roles Endpoints
# ==============================================================================

@app.get("/role-engineering/roles", tags=["Roles"])
async def list_roles():
    """List all roles"""
    return {
        "roles": [
            {"role_id": rid, **data}
            for rid, data in DEMO_ROLES.items()
        ],
        "total": len(DEMO_ROLES)
    }

@app.get("/role-engineering/catalog", tags=["Roles"])
async def get_role_catalog():
    """Get role catalog for request portal"""
    return {
        "categories": [
            {
                "name": "Finance",
                "roles": [{"role_id": "SAP_FI_USER", "name": "Finance User", "description": "Basic finance access"}]
            },
            {
                "name": "Procurement",
                "roles": [{"role_id": "SAP_MM_BUYER", "name": "Procurement Buyer", "description": "Purchase order creation"}]
            }
        ]
    }


# ==============================================================================
# Risk Analysis Endpoints
# ==============================================================================

@app.get("/risk/rules", tags=["Risk"])
async def list_risk_rules():
    """List all SoD rules"""
    return {"rules": SOD_RULES, "total": len(SOD_RULES)}

@app.post("/risk/analyze/user", tags=["Risk"])
async def analyze_user_risk(request: RiskAnalysisRequest):
    """Analyze user for SoD violations"""
    return {
        "user_id": request.user_id,
        "analysis_date": datetime.utcnow().isoformat(),
        "risk_score": 65,
        "risk_level": "medium",
        "violations": [
            {
                "rule_id": "SOD-FI-001",
                "rule_name": "Vendor Master vs AP Payment",
                "risk_level": "critical",
                "conflicting_functions": ["Vendor Maintenance", "Payment Processing"]
            }
        ],
        "sensitive_access": [],
        "recommendations": ["Review and remediate critical SoD violation"]
    }

@app.get("/risk/violations", tags=["Risk"])
async def list_violations():
    """List all active violations"""
    return {
        "violations": [
            {
                "violation_id": "VIO-001",
                "user_id": "JSMITH",
                "rule_id": "SOD-FI-001",
                "status": "open",
                "detected_at": "2024-01-15T10:30:00Z"
            }
        ],
        "total": 1
    }


# ==============================================================================
# Access Requests Endpoints
# ==============================================================================

@app.get("/access-requests", tags=["Access Requests"])
async def list_access_requests():
    """List access requests"""
    return {
        "requests": [
            {
                "request_id": "REQ-001",
                "user_id": "JSMITH",
                "role_id": "SAP_MM_BUYER",
                "status": "pending_approval",
                "created_at": "2024-01-20T09:00:00Z"
            }
        ],
        "total": 1
    }

@app.post("/access-requests", tags=["Access Requests"])
async def create_access_request(request: AccessRequest):
    """Create new access request"""
    return {
        "request_id": f"REQ-{int(time.time())}",
        "status": "submitted",
        "risk_preview": {
            "new_violations": 0,
            "risk_level": "low"
        }
    }

@app.get("/access-requests/approvals/pending", tags=["Access Requests"])
async def get_pending_approvals():
    """Get pending approvals for current user"""
    return {
        "approvals": [
            {
                "request_id": "REQ-001",
                "requester": "JSMITH",
                "role": "SAP_MM_BUYER",
                "step": "manager_approval"
            }
        ],
        "total": 1
    }


# ==============================================================================
# Firefighter Endpoints
# ==============================================================================

@app.get("/firefighter/firefighters", tags=["Firefighter"])
async def list_firefighters():
    """List firefighter IDs"""
    return {
        "firefighters": [
            {
                "firefighter_id": "FF_EMERGENCY_01",
                "description": "General Emergency Access",
                "status": "available"
            },
            {
                "firefighter_id": "FF_SECURITY_01",
                "description": "Security Emergency Access",
                "status": "in_use"
            }
        ]
    }

@app.post("/firefighter/requests", tags=["Firefighter"])
async def request_firefighter_access(request: FirefighterRequest):
    """Request firefighter access"""
    return {
        "request_id": f"FF-REQ-{int(time.time())}",
        "firefighter_id": request.firefighter_id,
        "status": "pending_approval",
        "expires_at": datetime.utcnow().isoformat()
    }

@app.get("/firefighter/sessions", tags=["Firefighter"])
async def list_firefighter_sessions():
    """List active firefighter sessions"""
    return {
        "sessions": [
            {
                "session_id": "FF-SES-001",
                "firefighter_id": "FF_SECURITY_01",
                "user_id": "TDAVIS",
                "status": "active",
                "started_at": "2024-01-20T14:00:00Z"
            }
        ],
        "total": 1
    }


# ==============================================================================
# Dashboard Endpoints
# ==============================================================================

@app.get("/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats():
    """Get dashboard statistics"""
    return {
        "totalUsers": 1250,
        "activeViolations": 45,
        "pendingApprovals": 12,
        "certificationProgress": 78,
        "activeFirefighterSessions": 2,
        "riskScore": 42,
        "riskTrend": "down"
    }

@app.get("/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary():
    """Get dashboard summary"""
    return {
        "risk_summary": {
            "critical": 5,
            "high": 15,
            "medium": 25,
            "low": 100
        },
        "recent_activity": [
            {"type": "access_granted", "user": "JSMITH", "timestamp": "2024-01-20T10:00:00Z"},
            {"type": "violation_detected", "user": "MBROWN", "timestamp": "2024-01-20T09:30:00Z"}
        ]
    }


# ==============================================================================
# Certification Endpoints
# ==============================================================================

@app.get("/certification/campaigns", tags=["Certification"])
async def list_certification_campaigns():
    """List certification campaigns"""
    return {
        "campaigns": [
            {
                "campaign_id": "CAMP-Q1-2024",
                "name": "Q1 2024 Access Review",
                "status": "active",
                "progress": 65
            }
        ],
        "total": 1
    }

@app.get("/certification/my-reviews", tags=["Certification"])
async def get_my_reviews():
    """Get certification items for current reviewer"""
    return {
        "items": [
            {
                "item_id": "CERT-001",
                "user_id": "JSMITH",
                "role_id": "SAP_FI_USER",
                "status": "pending"
            }
        ],
        "total": 1
    }


# ==============================================================================
# SoD Rules Endpoints
# ==============================================================================

@app.get("/sod-rules/rules", tags=["SoD Rules"])
async def list_sod_rules():
    """List SoD rules"""
    return {
        "rules": SOD_RULES,
        "total": len(SOD_RULES)
    }

@app.get("/sod-rules/stats", tags=["SoD Rules"])
async def get_sod_stats():
    """Get SoD statistics"""
    return {
        "total_rules": 35,
        "active_rules": 32,
        "by_risk_level": {
            "critical": 8,
            "high": 12,
            "medium": 10,
            "low": 5
        },
        "sox_relevant": 25
    }


# ==============================================================================
# AI Endpoints
# ==============================================================================

@app.post("/ai/chat", tags=["AI"])
async def ai_chat(message: str, conversation_id: Optional[str] = None):
    """Chat with AI assistant"""
    return {
        "response": f"I understand you're asking about: {message}. How can I help with your GRC needs?",
        "conversation_id": conversation_id or f"conv-{int(time.time())}"
    }

@app.post("/ai/query", tags=["AI"])
async def ai_query(query: str):
    """Natural language query"""
    return {
        "query": query,
        "answer": "Based on the platform data, here's what I found...",
        "confidence": 0.85
    }


# ==============================================================================
# Reports Endpoints
# ==============================================================================

@app.get("/reporting/reports", tags=["Reports"])
async def list_reports():
    """List available reports"""
    return {
        "reports": [
            {"report_id": "RPT-SOD", "name": "SoD Violations Report", "category": "Risk"},
            {"report_id": "RPT-ACCESS", "name": "User Access Report", "category": "Access"},
            {"report_id": "RPT-FF", "name": "Firefighter Usage Report", "category": "Emergency"}
        ]
    }


# ==============================================================================
# GovernEx+ Advanced Capabilities (The 5 Differentiators)
# ==============================================================================

@app.get("/governex-plus/dashboard", tags=["GovernEx+ Advanced"])
async def governex_plus_dashboard():
    """
    GovernEx+ Dashboard - The 5 features that beat SAP GRC

    These capabilities are BEYOND what SAP GRC offers.
    """
    return {
        "platform": "GovernEx+",
        "tagline": "Beyond SAP GRC - Unbeatable Features",
        "capabilities": {
            "1_business_intent_governance": {
                "status": "active",
                "description": "Captures the 'WHY' behind access - auditor gold",
                "what_it_does": "Every access request links to a governed business purpose",
                "why_sap_cant": "SAP GRC has no concept of intent governance",
                "sample_data": {
                    "active_intents": 156,
                    "reused_intents": 42,
                    "audit_ready": True
                }
            },
            "2_control_effectiveness": {
                "status": "active",
                "description": "PROVES controls work, not just exist",
                "what_it_does": "Measures if controls actually prevent risk",
                "why_sap_cant": "SAP GRC only documents controls exist",
                "sample_data": {
                    "overall_score": 87.5,
                    "rating": "STRONG",
                    "controls_tested": 45,
                    "assurance_statement": "Control environment demonstrates strong effectiveness"
                }
            },
            "3_approval_behavior_analytics": {
                "status": "active",
                "description": "Detects rubber-stamping and approval bias",
                "what_it_does": "Analyzes if approvals are meaningful or ceremonial",
                "why_sap_cant": "SAP GRC just logs approvals without quality analysis",
                "sample_data": {
                    "approvers_analyzed": 28,
                    "rubber_stampers_detected": 2,
                    "bias_alerts": 1,
                    "audit_opinion": "Approval governance is ADEQUATE with areas for improvement"
                }
            },
            "4_identity_risk_scoring": {
                "status": "active",
                "description": "Per-identity risk - because auditors audit identities",
                "what_it_does": "Calculates risk score for each identity, not just access",
                "why_sap_cant": "SAP GRC focuses on access, not identity lifecycle",
                "sample_data": {
                    "total_identities": 1250,
                    "ghost_identities": 3,
                    "dormant_identities": 47,
                    "high_risk_identities": 12,
                    "avg_risk_score": 34.5
                }
            },
            "5_explainable_risk": {
                "status": "active",
                "description": "Plain English explanations for ALL decisions",
                "what_it_does": "Generates narratives for executives, managers, auditors, and users",
                "why_sap_cant": "SAP GRC shows numbers, not explanations",
                "sample_data": {
                    "narratives_generated": 2847,
                    "audience_types": ["executive", "manager", "auditor", "end_user"],
                    "avg_confidence": 89.2
                }
            }
        },
        "competitive_edge": [
            "SAP GRC cannot answer 'Why was this access needed?'",
            "SAP GRC cannot prove controls actually work",
            "SAP GRC cannot detect rubber-stamp approvers",
            "SAP GRC cannot score identity-level risk",
            "SAP GRC cannot explain risk in plain English"
        ],
        "auditor_value": {
            "intent_documentation": "Complete trail of business purposes",
            "assurance_statements": "Effectiveness proof, not just existence",
            "governance_quality": "Evidence approvals are meaningful",
            "identity_hygiene": "No ghost or orphaned accounts",
            "explainability": "Every decision can be explained"
        }
    }


@app.post("/governex-plus/explain-risk", tags=["GovernEx+ Advanced"])
async def explain_risk_narrative(
    user_id: str,
    user_name: str = "John Smith",
    risk_score: float = 65,
    risk_level: str = "medium",
    audience: str = "manager"
):
    """
    Generate plain-English risk explanation.

    EXPLAINABILITY = TRUST, TRUST = ADOPTION
    """
    explanations = {
        "executive": f"{user_name} presents moderate business risk (score: {risk_score}). "
                     f"Primary concern: elevated access across multiple systems. "
                     f"This is 15% higher than peers in similar roles.",
        "manager": f"{user_name}'s risk score of {risk_score} places them at {risk_level.upper()} risk. "
                   f"This assessment is based on 3 contributing factors including "
                   f"cross-system admin access and high role count.",
        "auditor": f"Identity {user_id} ({user_name}) assessed at {risk_level.upper()} risk "
                   f"(score: {risk_score}/100). Assessment based on access footprint analysis, "
                   f"behavioral patterns, and peer group comparison. Above peer average.",
        "end_user": f"Your access risk score is {risk_score} out of 100. "
                    f"This doesn't mean you did anything wrong - it just reflects your current access levels. "
                    f"Your main factor: you have access to multiple systems with elevated privileges."
    }

    recommendations_by_audience = {
        "executive": ["Review quarterly with security team", "Consider role consolidation initiative"],
        "manager": ["Schedule access review within 30 days", "Verify business justification for admin access"],
        "auditor": ["Sample test 3 recent transactions", "Verify mitigation controls are operating"],
        "end_user": ["Consider if you still need all your access", "Contact IT if you have questions"]
    }

    return {
        "user_id": user_id,
        "user_name": user_name,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "audience": audience,
        "headline": f"Risk Assessment: {user_name} - {risk_level.upper()} Risk",
        "narrative": explanations.get(audience, explanations["manager"]),
        "key_points": [
            "Access across 5 connected systems",
            "Admin privileges in SAP and Oracle",
            "15% above peer group average",
            "No recent access review"
        ],
        "evidence": [
            "System access data from 5 platforms",
            "Role analysis: 12 active roles",
            "Peer comparison: Department average is 52"
        ],
        "recommendations": recommendations_by_audience.get(audience, []),
        "confidence_score": 87.5,
        "generated_for": audience
    }


@app.get("/governex-plus/identity-hygiene", tags=["GovernEx+ Advanced"])
async def identity_hygiene_dashboard():
    """
    Identity hygiene dashboard.

    Auditors audit IDENTITIES, not just access.
    """
    return {
        "summary": {
            "total_identities": 1250,
            "average_risk_score": 34.5,
            "ghost_identities": 3,
            "dormant_identities": 47,
            "orphaned_identities": 12,
            "high_risk_identities": 15
        },
        "risk_distribution": {
            "minimal": 450,
            "low": 520,
            "moderate": 200,
            "high": 65,
            "critical": 15
        },
        "ghost_identities": [
            {
                "identity_id": "GHOST001",
                "name": "Former Employee A",
                "termination_date": "2024-01-05",
                "active_systems": ["SAP", "Oracle"],
                "urgency": "CRITICAL"
            },
            {
                "identity_id": "GHOST002",
                "name": "Contractor B",
                "termination_date": "2024-01-10",
                "active_systems": ["SAP"],
                "urgency": "HIGH"
            }
        ],
        "dormant_identities_sample": [
            {"identity_id": "DORM001", "name": "User C", "days_inactive": 120},
            {"identity_id": "DORM002", "name": "User D", "days_inactive": 95}
        ],
        "audit_summary": "SIGNIFICANT IDENTITY GOVERNANCE ISSUES detected. 3 ghost identities "
                         "represent immediate security risks. Immediate remediation recommended."
    }


@app.get("/governex-plus/control-effectiveness", tags=["GovernEx+ Advanced"])
async def control_effectiveness_dashboard():
    """
    Control effectiveness assurance dashboard.

    PROVES controls work, not just that they exist.
    """
    return {
        "overall_assurance_score": 87.5,
        "overall_rating": "STRONG",
        "assurance_statement": "Based on comprehensive testing, the control environment demonstrates "
                               "STRONG effectiveness. All controls are operating as designed with "
                               "no significant exceptions noted.",
        "control_effectiveness": {
            "total_controls": 45,
            "average_effectiveness": 87.5,
            "controls_highly_effective": 32,
            "controls_needing_attention": 3,
            "controls_declining": 2
        },
        "approval_quality": {
            "total_approvers_analyzed": 28,
            "rubber_stamp_alerts": 2,
            "low_risk_awareness_alerts": 3,
            "bias_alerts": 1
        },
        "mitigation_effectiveness": {
            "total_mitigations": 18,
            "average_success_rate": 91.2,
            "ineffective_mitigations": 1,
            "mitigations_with_incidents": 0
        },
        "key_risks": [
            "2 approvers show rubber-stamping patterns",
            "3 controls have declining effectiveness trend"
        ],
        "recommendations": [
            "PRIORITY 1: Coach 2 approvers on approval responsibilities",
            "PRIORITY 2: Review 3 declining controls"
        ]
    }


@app.get("/governex-plus/approval-behavior", tags=["GovernEx+ Advanced"])
async def approval_behavior_analytics():
    """
    Approval behavior analytics report.

    Ensures approvals are MEANINGFUL, not ceremonial.
    """
    return {
        "summary": {
            "total_approvers_analyzed": 28,
            "total_approvals_analyzed": 1847,
            "rubber_stampers_identified": 2,
            "low_risk_awareness": 3,
            "bias_concerns": 1,
            "overwhelmed_approvers": 2
        },
        "pattern_distribution": {
            "normal": 20,
            "rubber_stamper": 2,
            "risk_averse": 3,
            "inconsistent": 1,
            "overwhelmed": 2
        },
        "average_scores": {
            "rubber_stamp_score": 28.5,
            "risk_awareness_score": 72.3,
            "consistency_score": 85.1,
            "engagement_score": 68.9
        },
        "rubber_stamp_concerns": [
            {
                "approver_id": "MGR001",
                "approver_name": "Manager A",
                "rubber_stamp_score": 78.5,
                "approval_rate": 99.2,
                "avg_decision_time": "0.3 hours",
                "recommendation": "Requires coaching on approval responsibilities"
            }
        ],
        "audit_conclusion": "Approval governance is ADEQUATE with areas for improvement. "
                            "3 of 28 approvers (10%) show concerning patterns that should "
                            "be addressed through training or process changes."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
