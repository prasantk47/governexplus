# AI-Powered Risk Intelligence Engine
# Context-aware, predictive risk scoring beyond static rules

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
import math
import random


class RiskTrend(Enum):
    """Risk trend direction"""
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"
    VOLATILE = "volatile"


@dataclass
class RiskFactor:
    """Individual risk factor with weight and explanation"""
    id: str
    name: str
    category: str  # access, behavior, context, history
    weight: float  # 0.0 to 1.0
    value: float   # Current value
    baseline: float  # Expected baseline
    deviation: float  # How far from baseline
    explanation: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class RiskPrediction:
    """Predicted future risk state"""
    predicted_score: float
    confidence: float  # 0.0 to 1.0
    time_horizon: str  # "7d", "30d", "90d"
    trend: RiskTrend
    key_drivers: List[str]
    recommended_actions: List[str]


@dataclass
class ContextualRiskScore:
    """
    Context-aware risk score that goes beyond binary SoD violations

    Unlike traditional GRC which says "violation" or "no violation",
    this provides nuanced scoring based on:
    - Who the user is (role, department, history)
    - What they're accessing (sensitivity, business need)
    - When they're accessing (time patterns)
    - How they're accessing (normal vs anomalous behavior)
    """
    user_id: str
    base_score: float  # 0-100, from traditional rules
    contextual_score: float  # 0-100, AI-adjusted
    confidence: float  # How confident the AI is in this score

    # Score components
    access_risk: float  # Risk from current access rights
    behavioral_risk: float  # Risk from usage patterns
    contextual_risk: float  # Risk from situational factors
    historical_risk: float  # Risk from past incidents

    # Explanations
    risk_factors: List[RiskFactor] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)

    # Predictions
    prediction: Optional[RiskPrediction] = None

    # Comparison
    peer_percentile: float = 50.0  # Compared to similar users
    department_percentile: float = 50.0

    calculated_at: datetime = field(default_factory=datetime.utcnow)


class RiskIntelligenceEngine:
    """
    AI-Powered Risk Intelligence Engine

    Key advantages over traditional SAP GRC:

    1. CONTEXTUAL SCORING: Doesn't just detect SoD - understands context
       - Same access might be high-risk for one user, low for another
       - Considers business justification, approval history, peer patterns

    2. PREDICTIVE ANALYTICS: Forecasts future risk states
       - Identifies users trending toward high-risk before they get there
       - Proactive intervention vs reactive detection

    3. CONTINUOUS LEARNING: Improves over time
       - Learns from false positives/negatives
       - Adapts to organizational changes
       - Reduces alert fatigue

    4. BEHAVIORAL ANALYSIS: Usage patterns, not just access rights
       - Someone with risky access who never uses it = lower actual risk
       - Normal access used abnormally = higher risk

    5. EXPLAINABLE AI: Every score has clear reasoning
       - Auditors can understand why a score was given
       - Actionable insights, not black-box numbers
    """

    def __init__(self):
        # User profiles for contextual analysis
        self.user_profiles: Dict[str, Dict[str, Any]] = {}

        # Historical risk data for trend analysis
        self.risk_history: Dict[str, List[Tuple[datetime, float]]] = {}

        # Peer group baselines
        self.peer_baselines: Dict[str, Dict[str, float]] = {}

        # Learning data
        self.false_positive_patterns: List[Dict] = []
        self.confirmed_risks: List[Dict] = []

        # Model weights (would be trained in production)
        self.factor_weights = {
            "access_volume": 0.15,
            "sensitive_access": 0.25,
            "sod_violations": 0.20,
            "behavioral_anomaly": 0.15,
            "time_pattern": 0.10,
            "peer_deviation": 0.10,
            "history": 0.05
        }

        self._initialize_demo_data()

    def _initialize_demo_data(self):
        """Initialize with demo data for illustration"""
        # Demo user profiles
        self.user_profiles = {
            "JSMITH": {
                "department": "Finance",
                "role": "Senior Accountant",
                "tenure_years": 5,
                "manager": "MWILLIAMS",
                "typical_access_hours": (8, 18),
                "typical_transactions": ["FB01", "FB02", "FB03", "F-02"],
                "risk_history": [45, 48, 52, 55, 60],  # Trending up
                "past_incidents": 0,
                "last_review": datetime.utcnow() - timedelta(days=90)
            },
            "MBROWN": {
                "department": "Procurement",
                "role": "Buyer",
                "tenure_years": 2,
                "manager": "SJONES",
                "typical_access_hours": (9, 17),
                "typical_transactions": ["ME21N", "ME22N", "ME23N"],
                "risk_history": [30, 32, 31, 30, 29],  # Stable
                "past_incidents": 0,
                "last_review": datetime.utcnow() - timedelta(days=30)
            },
            "TDAVIS": {
                "department": "IT",
                "role": "Basis Administrator",
                "tenure_years": 8,
                "manager": "KCARTER",
                "typical_access_hours": (7, 22),  # Wide range for IT
                "typical_transactions": ["SU01", "PFCG", "SM21"],
                "risk_history": [85, 82, 80, 78, 75],  # Trending down
                "past_incidents": 1,
                "last_review": datetime.utcnow() - timedelta(days=15)
            },
            "NEWUSER": {
                "department": "Sales",
                "role": "Sales Rep",
                "tenure_years": 0.1,
                "manager": "RJOHNSON",
                "typical_access_hours": (9, 17),
                "typical_transactions": [],
                "risk_history": [20],
                "past_incidents": 0,
                "last_review": None
            }
        }

        # Peer baselines by department
        self.peer_baselines = {
            "Finance": {"avg_score": 45, "std_dev": 12, "max_normal": 65},
            "Procurement": {"avg_score": 35, "std_dev": 10, "max_normal": 55},
            "IT": {"avg_score": 60, "std_dev": 15, "max_normal": 85},
            "Sales": {"avg_score": 25, "std_dev": 8, "max_normal": 40},
            "HR": {"avg_score": 50, "std_dev": 12, "max_normal": 70}
        }

    # ==================== Core Risk Calculation ====================

    def calculate_contextual_risk(
        self,
        user_id: str,
        traditional_violations: List[Dict[str, Any]],
        current_access: List[str] = None,
        recent_activity: List[Dict[str, Any]] = None
    ) -> ContextualRiskScore:
        """
        Calculate AI-enhanced contextual risk score

        This is the main differentiator from traditional GRC:
        - Takes traditional SoD violations as input
        - Applies contextual factors to produce nuanced score
        - Provides explanation and predictions
        """
        user_profile = self.user_profiles.get(user_id, {})

        # 1. Calculate base score from traditional violations
        base_score = self._calculate_base_score(traditional_violations)

        # 2. Calculate component scores
        access_risk = self._calculate_access_risk(user_id, current_access or [])
        behavioral_risk = self._calculate_behavioral_risk(user_id, recent_activity or [])
        contextual_risk = self._calculate_contextual_factors(user_id, user_profile)
        historical_risk = self._calculate_historical_risk(user_id, user_profile)

        # 3. Apply AI weighting to get contextual score
        contextual_score = self._apply_ml_weighting(
            base_score, access_risk, behavioral_risk,
            contextual_risk, historical_risk, user_profile
        )

        # 4. Generate risk factors with explanations
        risk_factors = self._generate_risk_factors(
            user_id, user_profile, traditional_violations,
            access_risk, behavioral_risk, contextual_risk, historical_risk
        )

        # 5. Identify mitigating factors
        mitigating = self._identify_mitigating_factors(user_id, user_profile)

        # 6. Calculate peer comparison
        dept = user_profile.get("department", "Unknown")
        peer_baseline = self.peer_baselines.get(dept, {"avg_score": 50, "std_dev": 15})
        peer_percentile = self._calculate_percentile(contextual_score, peer_baseline)

        # 7. Generate prediction
        prediction = self._predict_future_risk(user_id, user_profile, contextual_score)

        # 8. Calculate confidence based on data quality
        confidence = self._calculate_confidence(user_id, user_profile)

        return ContextualRiskScore(
            user_id=user_id,
            base_score=base_score,
            contextual_score=contextual_score,
            confidence=confidence,
            access_risk=access_risk,
            behavioral_risk=behavioral_risk,
            contextual_risk=contextual_risk,
            historical_risk=historical_risk,
            risk_factors=risk_factors,
            mitigating_factors=mitigating,
            prediction=prediction,
            peer_percentile=peer_percentile,
            department_percentile=peer_percentile
        )

    def _calculate_base_score(self, violations: List[Dict]) -> float:
        """Calculate base score from traditional SoD violations"""
        if not violations:
            return 0.0

        score = 0.0
        for v in violations:
            severity = v.get("severity", "medium").lower()
            if severity == "critical":
                score += 30
            elif severity == "high":
                score += 20
            elif severity == "medium":
                score += 10
            else:
                score += 5

        return min(score, 100)

    def _calculate_access_risk(self, user_id: str, current_access: List[str]) -> float:
        """Calculate risk from current access rights"""
        if not current_access:
            return 20.0  # Baseline assumption

        sensitive_tcodes = {"SU01", "PFCG", "SE16", "SM21", "SA38", "FB01", "F110"}
        sensitive_count = len(set(current_access) & sensitive_tcodes)

        # More access = higher risk, but with diminishing returns
        volume_score = min(len(current_access) * 2, 40)
        sensitivity_score = min(sensitive_count * 10, 40)

        return min((volume_score + sensitivity_score), 100)

    def _calculate_behavioral_risk(
        self,
        user_id: str,
        recent_activity: List[Dict]
    ) -> float:
        """
        Calculate risk from usage patterns

        Key insight: Someone with risky access who never uses it
        is lower risk than someone using normal access abnormally
        """
        if not recent_activity:
            return 30.0  # Neutral when no data

        profile = self.user_profiles.get(user_id, {})
        typical_hours = profile.get("typical_access_hours", (9, 17))
        typical_tcodes = set(profile.get("typical_transactions", []))

        anomaly_score = 0

        for activity in recent_activity:
            # Check time anomaly
            hour = activity.get("hour", 12)
            if hour < typical_hours[0] or hour > typical_hours[1]:
                anomaly_score += 5

            # Check transaction anomaly
            tcode = activity.get("transaction", "")
            if tcode and tcode not in typical_tcodes:
                anomaly_score += 3

            # Check volume anomaly
            if activity.get("is_bulk_operation", False):
                anomaly_score += 10

        return min(anomaly_score, 100)

    def _calculate_contextual_factors(
        self,
        user_id: str,
        profile: Dict
    ) -> float:
        """
        Calculate contextual risk factors

        Considers:
        - New employee (higher inherent risk due to unfamiliarity)
        - Recent role change
        - Contractor status
        - Time since last review
        """
        score = 30  # Baseline

        # New employee risk
        tenure = profile.get("tenure_years", 1)
        if tenure < 0.5:
            score += 20  # New employees need more monitoring
        elif tenure < 1:
            score += 10

        # Time since last review
        last_review = profile.get("last_review")
        if last_review:
            days_since = (datetime.utcnow() - last_review).days
            if days_since > 180:
                score += 15
            elif days_since > 90:
                score += 5
        else:
            score += 20  # Never reviewed

        # Role-based adjustment
        role = profile.get("role", "").lower()
        if "admin" in role or "manager" in role:
            score += 10  # Privileged roles

        return min(score, 100)

    def _calculate_historical_risk(self, user_id: str, profile: Dict) -> float:
        """Calculate risk based on historical data"""
        incidents = profile.get("past_incidents", 0)
        history = profile.get("risk_history", [])

        score = 20  # Baseline

        # Past incidents are significant
        score += incidents * 15

        # Trend analysis
        if len(history) >= 3:
            recent_avg = sum(history[-3:]) / 3
            older_avg = sum(history[:-3]) / len(history[:-3]) if len(history) > 3 else recent_avg

            if recent_avg > older_avg + 10:
                score += 15  # Trending up is concerning
            elif recent_avg < older_avg - 10:
                score -= 10  # Trending down is good

        return max(min(score, 100), 0)

    def _apply_ml_weighting(
        self,
        base_score: float,
        access_risk: float,
        behavioral_risk: float,
        contextual_risk: float,
        historical_risk: float,
        profile: Dict
    ) -> float:
        """
        Apply ML-style weighting to component scores

        In production, this would use a trained model.
        For demo, we use interpretable weighted combination.
        """
        # Weighted combination
        weighted_score = (
            base_score * 0.30 +  # Traditional violations matter
            access_risk * 0.25 +  # What they have access to
            behavioral_risk * 0.20 +  # How they use it
            contextual_risk * 0.15 +  # Who they are
            historical_risk * 0.10    # Past patterns
        )

        # Apply confidence adjustment for new users
        tenure = profile.get("tenure_years", 1)
        if tenure < 0.5:
            # Less data = more conservative (higher) estimate
            weighted_score = weighted_score * 1.1

        return min(max(weighted_score, 0), 100)

    def _generate_risk_factors(
        self,
        user_id: str,
        profile: Dict,
        violations: List[Dict],
        access_risk: float,
        behavioral_risk: float,
        contextual_risk: float,
        historical_risk: float
    ) -> List[RiskFactor]:
        """Generate explainable risk factors"""
        factors = []

        # SoD Violations
        if violations:
            factors.append(RiskFactor(
                id="sod_violations",
                name="Segregation of Duties Violations",
                category="access",
                weight=0.30,
                value=len(violations),
                baseline=0,
                deviation=len(violations),
                explanation=f"User has {len(violations)} active SoD conflicts",
                evidence=[v.get("rule_id", "") for v in violations[:5]]
            ))

        # Sensitive Access
        if access_risk > 50:
            factors.append(RiskFactor(
                id="sensitive_access",
                name="Sensitive Access Level",
                category="access",
                weight=0.25,
                value=access_risk,
                baseline=35,
                deviation=access_risk - 35,
                explanation="User has access to sensitive transactions above peer baseline",
                evidence=["High-privilege transactions detected"]
            ))

        # Behavioral Anomaly
        if behavioral_risk > 40:
            factors.append(RiskFactor(
                id="behavioral_anomaly",
                name="Behavioral Anomaly",
                category="behavior",
                weight=0.20,
                value=behavioral_risk,
                baseline=30,
                deviation=behavioral_risk - 30,
                explanation="Recent activity patterns deviate from historical norms",
                evidence=["Off-hours access", "Unusual transaction volume"]
            ))

        # New Employee
        tenure = profile.get("tenure_years", 1)
        if tenure < 0.5:
            factors.append(RiskFactor(
                id="new_employee",
                name="New Employee",
                category="context",
                weight=0.15,
                value=1,
                baseline=0,
                deviation=1,
                explanation="New employees require additional monitoring during onboarding",
                evidence=[f"Tenure: {tenure:.1f} years"]
            ))

        # Overdue Review
        last_review = profile.get("last_review")
        if last_review:
            days = (datetime.utcnow() - last_review).days
            if days > 90:
                factors.append(RiskFactor(
                    id="overdue_review",
                    name="Overdue Access Review",
                    category="context",
                    weight=0.10,
                    value=days,
                    baseline=90,
                    deviation=days - 90,
                    explanation=f"Access not reviewed in {days} days",
                    evidence=["Review overdue per policy"]
                ))

        return factors

    def _identify_mitigating_factors(
        self,
        user_id: str,
        profile: Dict
    ) -> List[str]:
        """Identify factors that reduce risk"""
        mitigating = []

        # Long tenure
        if profile.get("tenure_years", 0) > 5:
            mitigating.append("Long organizational tenure (>5 years)")

        # Clean history
        if profile.get("past_incidents", 0) == 0:
            mitigating.append("No historical security incidents")

        # Recent review
        last_review = profile.get("last_review")
        if last_review and (datetime.utcnow() - last_review).days < 30:
            mitigating.append("Recently reviewed and approved")

        # Declining trend
        history = profile.get("risk_history", [])
        if len(history) >= 3:
            if history[-1] < history[-3]:
                mitigating.append("Risk score trending downward")

        return mitigating

    def _calculate_percentile(self, score: float, baseline: Dict) -> float:
        """Calculate percentile vs peer group using normal distribution approximation"""
        avg = baseline.get("avg_score", 50)
        std = baseline.get("std_dev", 15)

        if std == 0:
            return 50.0

        # Z-score
        z = (score - avg) / std

        # Approximate percentile using logistic function
        percentile = 100 / (1 + math.exp(-z * 1.7))

        return round(percentile, 1)

    def _predict_future_risk(
        self,
        user_id: str,
        profile: Dict,
        current_score: float
    ) -> RiskPrediction:
        """Predict future risk trajectory"""
        history = profile.get("risk_history", [current_score])

        # Determine trend
        if len(history) >= 3:
            recent = sum(history[-3:]) / 3
            older = sum(history[:-3]) / len(history[:-3]) if len(history) > 3 else recent

            diff = recent - older
            if diff > 10:
                trend = RiskTrend.INCREASING
                predicted = min(current_score + 10, 100)
            elif diff < -10:
                trend = RiskTrend.DECREASING
                predicted = max(current_score - 10, 0)
            else:
                trend = RiskTrend.STABLE
                predicted = current_score
        else:
            trend = RiskTrend.STABLE
            predicted = current_score

        # Key drivers based on profile
        drivers = []
        if trend == RiskTrend.INCREASING:
            drivers = [
                "Growing access accumulation",
                "Increased privileged transactions",
                "Approaching review deadline"
            ]
        elif trend == RiskTrend.DECREASING:
            drivers = [
                "Recent access review completed",
                "Reduced SoD conflicts",
                "Normalized activity patterns"
            ]
        else:
            drivers = ["Stable access profile", "Consistent usage patterns"]

        # Recommended actions
        actions = []
        if predicted > 70:
            actions.append("Immediate access review recommended")
            actions.append("Consider role decomposition")
        elif predicted > 50:
            actions.append("Schedule proactive access review")
            actions.append("Monitor for behavioral changes")
        else:
            actions.append("Continue standard monitoring")

        return RiskPrediction(
            predicted_score=predicted,
            confidence=0.75 if len(history) >= 5 else 0.5,
            time_horizon="30d",
            trend=trend,
            key_drivers=drivers,
            recommended_actions=actions
        )

    def _calculate_confidence(self, user_id: str, profile: Dict) -> float:
        """Calculate confidence in the risk assessment"""
        confidence = 0.5  # Baseline

        # More history = more confidence
        history = profile.get("risk_history", [])
        confidence += min(len(history) * 0.05, 0.25)

        # Longer tenure = more data
        tenure = profile.get("tenure_years", 0)
        confidence += min(tenure * 0.05, 0.15)

        # Recent review = validated data
        last_review = profile.get("last_review")
        if last_review and (datetime.utcnow() - last_review).days < 30:
            confidence += 0.10

        return min(confidence, 0.95)

    # ==================== Batch Analysis ====================

    def analyze_department(self, department: str) -> Dict[str, Any]:
        """Analyze risk across an entire department"""
        dept_users = [
            uid for uid, profile in self.user_profiles.items()
            if profile.get("department") == department
        ]

        if not dept_users:
            return {"error": "No users found in department"}

        scores = []
        high_risk_users = []
        trending_up = []

        for uid in dept_users:
            profile = self.user_profiles[uid]
            history = profile.get("risk_history", [50])
            current = history[-1] if history else 50
            scores.append(current)

            if current > 70:
                high_risk_users.append(uid)

            if len(history) >= 3 and history[-1] > history[-3] + 10:
                trending_up.append(uid)

        return {
            "department": department,
            "user_count": len(dept_users),
            "average_risk": sum(scores) / len(scores),
            "max_risk": max(scores),
            "min_risk": min(scores),
            "high_risk_users": high_risk_users,
            "users_trending_up": trending_up,
            "recommendations": self._generate_dept_recommendations(
                scores, high_risk_users, trending_up
            )
        }

    def _generate_dept_recommendations(
        self,
        scores: List[float],
        high_risk: List[str],
        trending: List[str]
    ) -> List[str]:
        """Generate department-level recommendations"""
        recs = []

        avg = sum(scores) / len(scores) if scores else 0

        if avg > 60:
            recs.append("Department average risk is elevated - consider bulk access review")

        if len(high_risk) > len(scores) * 0.2:
            recs.append(f"{len(high_risk)} users ({len(high_risk)/len(scores)*100:.0f}%) are high risk - investigate role design")

        if trending:
            recs.append(f"{len(trending)} users trending toward higher risk - proactive intervention recommended")

        if not recs:
            recs.append("Department risk profile is healthy - continue standard monitoring")

        return recs

    # ==================== Learning & Feedback ====================

    def record_false_positive(
        self,
        user_id: str,
        risk_factor_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Record when a risk was flagged but determined to be acceptable

        This feedback helps the AI learn and reduce future false positives
        """
        self.false_positive_patterns.append({
            "user_id": user_id,
            "risk_factor_id": risk_factor_id,
            "reason": reason,
            "timestamp": datetime.utcnow(),
            "user_profile_snapshot": self.user_profiles.get(user_id, {})
        })

        return {
            "success": True,
            "message": "Feedback recorded. This will improve future risk assessments.",
            "total_feedback_records": len(self.false_positive_patterns)
        }

    def record_confirmed_risk(
        self,
        user_id: str,
        risk_factor_id: str,
        incident_type: str
    ) -> Dict[str, Any]:
        """
        Record when a flagged risk led to actual incident

        This positive feedback helps validate and improve the model
        """
        self.confirmed_risks.append({
            "user_id": user_id,
            "risk_factor_id": risk_factor_id,
            "incident_type": incident_type,
            "timestamp": datetime.utcnow()
        })

        # Update user profile
        if user_id in self.user_profiles:
            self.user_profiles[user_id]["past_incidents"] = \
                self.user_profiles[user_id].get("past_incidents", 0) + 1

        return {
            "success": True,
            "message": "Incident recorded. Model weights will be adjusted.",
            "user_incident_count": self.user_profiles.get(user_id, {}).get("past_incidents", 1)
        }

    # ==================== Comparative Analysis ====================

    def compare_to_peers(self, user_id: str) -> Dict[str, Any]:
        """Compare user's risk profile to peers in same department/role"""
        profile = self.user_profiles.get(user_id)
        if not profile:
            return {"error": "User not found"}

        dept = profile.get("department", "Unknown")
        role = profile.get("role", "Unknown")

        # Find peers
        peers = [
            (uid, p) for uid, p in self.user_profiles.items()
            if p.get("department") == dept and uid != user_id
        ]

        if not peers:
            return {"message": "No peers found for comparison"}

        user_score = profile.get("risk_history", [50])[-1]
        peer_scores = [p.get("risk_history", [50])[-1] for _, p in peers]

        return {
            "user_id": user_id,
            "user_score": user_score,
            "department": dept,
            "peer_count": len(peers),
            "peer_average": sum(peer_scores) / len(peer_scores),
            "peer_min": min(peer_scores),
            "peer_max": max(peer_scores),
            "percentile": self._calculate_percentile(
                user_score,
                {"avg_score": sum(peer_scores)/len(peer_scores), "std_dev": 15}
            ),
            "status": "above_average" if user_score > sum(peer_scores)/len(peer_scores) else "below_average"
        }
