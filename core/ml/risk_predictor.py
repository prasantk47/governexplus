"""
Predictive Risk Scoring Module

Uses machine learning to predict risk levels and identify
potential compliance issues before they occur.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import uuid
import math
import random


class RiskCategory(Enum):
    """Categories of predicted risk"""
    SOD_VIOLATION = "sod_violation"
    EXCESSIVE_ACCESS = "excessive_access"
    DORMANT_ACCESS = "dormant_access"
    PRIVILEGE_CREEP = "privilege_creep"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    POLICY_VIOLATION = "policy_violation"
    SEPARATION_RISK = "separation_risk"


class PredictionConfidence(Enum):
    """Confidence levels for predictions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class RiskFactor:
    """A factor contributing to risk score"""
    factor_id: str
    name: str
    category: RiskCategory
    weight: float
    raw_value: float
    normalized_value: float  # 0-1
    description: str
    evidence: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "category": self.category.value,
            "weight": round(self.weight, 2),
            "raw_value": round(self.raw_value, 2),
            "normalized_value": round(self.normalized_value, 3),
            "contribution": round(self.weight * self.normalized_value, 3),
            "description": self.description,
            "evidence": self.evidence[:5]  # Limit evidence items
        }


@dataclass
class RiskPrediction:
    """A risk prediction for a user or access request"""
    prediction_id: str = field(default_factory=lambda: f"PRED-{uuid.uuid4().hex[:8].upper()}")
    target_type: str = "user"  # user, role, request
    target_id: str = ""

    # Scores
    overall_risk_score: float = 0.0  # 0-100
    risk_level: str = "low"  # low, medium, high, critical
    confidence: PredictionConfidence = PredictionConfidence.MEDIUM

    # Breakdown
    risk_factors: List[RiskFactor] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)

    # Predictions
    predicted_violations: List[Dict] = field(default_factory=list)
    probability_of_incident: float = 0.0  # 0-1

    # Recommendations
    risk_mitigation_suggestions: List[Dict] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)

    # Metadata
    model_version: str = "1.0"
    generated_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=1))

    def to_dict(self) -> Dict:
        return {
            "prediction_id": self.prediction_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "overall_risk_score": round(self.overall_risk_score, 1),
            "risk_level": self.risk_level,
            "confidence": self.confidence.value,
            "risk_factors": [f.to_dict() for f in self.risk_factors],
            "category_scores": {k: round(v, 1) for k, v in self.category_scores.items()},
            "predicted_violations": self.predicted_violations,
            "probability_of_incident": round(self.probability_of_incident, 3),
            "risk_mitigation_suggestions": self.risk_mitigation_suggestions,
            "recommended_actions": self.recommended_actions,
            "model_version": self.model_version,
            "generated_at": self.generated_at.isoformat()
        }


@dataclass
class UserRiskProfile:
    """Historical risk profile for a user"""
    user_id: str
    department: str = ""
    job_title: str = ""

    # Access metrics
    total_roles: int = 0
    total_permissions: int = 0
    sensitive_permissions: int = 0
    unused_permissions: int = 0

    # Historical metrics
    sod_violations_count: int = 0
    policy_violations_count: int = 0
    access_changes_90d: int = 0
    firefighter_usage_90d: int = 0

    # Behavioral metrics
    login_frequency: float = 0.0  # Logins per day
    avg_session_duration: float = 0.0  # Minutes
    after_hours_activity_pct: float = 0.0
    unusual_activity_count: int = 0

    # Peer comparison
    peer_group_size: int = 0
    access_vs_peers_pct: float = 0.0  # +/- % compared to peers

    # Time-based
    last_access_review: Optional[datetime] = None
    days_since_review: int = 0
    account_age_days: int = 0

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "department": self.department,
            "job_title": self.job_title,
            "total_roles": self.total_roles,
            "total_permissions": self.total_permissions,
            "sensitive_permissions": self.sensitive_permissions,
            "unused_permissions": self.unused_permissions,
            "sod_violations_count": self.sod_violations_count,
            "access_changes_90d": self.access_changes_90d,
            "firefighter_usage_90d": self.firefighter_usage_90d,
            "after_hours_activity_pct": round(self.after_hours_activity_pct, 1),
            "access_vs_peers_pct": round(self.access_vs_peers_pct, 1),
            "days_since_review": self.days_since_review
        }


class RiskPredictor:
    """
    Machine Learning-based Risk Prediction Engine.

    Uses multiple features and historical data to predict:
    - User risk scores
    - Access request risk
    - Probability of policy violations
    - Anomalous access patterns
    """

    # Feature weights (would be learned from training data in production)
    FEATURE_WEIGHTS = {
        "sod_violation_count": 0.20,
        "sensitive_access_ratio": 0.15,
        "unused_access_ratio": 0.12,
        "peer_access_deviation": 0.10,
        "access_change_velocity": 0.08,
        "firefighter_usage": 0.10,
        "after_hours_activity": 0.05,
        "days_since_review": 0.08,
        "privileged_role_count": 0.12
    }

    # Risk level thresholds
    RISK_THRESHOLDS = {
        "low": 25,
        "medium": 50,
        "high": 75,
        "critical": 90
    }

    def __init__(self, rule_engine=None, audit_logger=None):
        self.rule_engine = rule_engine
        self.audit_logger = audit_logger

        self.user_profiles: Dict[str, UserRiskProfile] = {}
        self.prediction_cache: Dict[str, RiskPrediction] = {}
        self.model_version = "1.0"

        # Historical data for training (simplified)
        self.historical_incidents: List[Dict] = []
        self.peer_groups: Dict[str, List[str]] = defaultdict(list)  # dept -> user_ids

    def predict_user_risk(self, user_id: str, user_data: Dict = None) -> RiskPrediction:
        """
        Predict risk score for a user.

        Args:
            user_id: The user to analyze
            user_data: Optional user data dict with access info

        Returns:
            RiskPrediction with score, factors, and recommendations
        """
        # Build or update user profile
        profile = self._build_user_profile(user_id, user_data or {})
        self.user_profiles[user_id] = profile

        # Calculate risk factors
        factors = self._calculate_risk_factors(profile)

        # Calculate overall score
        overall_score = self._calculate_overall_score(factors)
        risk_level = self._determine_risk_level(overall_score)

        # Calculate category scores
        category_scores = self._calculate_category_scores(factors)

        # Predict violations
        predicted_violations = self._predict_violations(profile, factors)

        # Generate recommendations
        recommendations = self._generate_recommendations(profile, factors, risk_level)

        # Calculate confidence
        confidence = self._calculate_confidence(profile)

        prediction = RiskPrediction(
            target_type="user",
            target_id=user_id,
            overall_risk_score=overall_score,
            risk_level=risk_level,
            confidence=confidence,
            risk_factors=factors,
            category_scores=category_scores,
            predicted_violations=predicted_violations,
            probability_of_incident=self._calculate_incident_probability(overall_score, factors),
            risk_mitigation_suggestions=recommendations,
            recommended_actions=self._get_action_items(risk_level, factors),
            model_version=self.model_version
        )

        self.prediction_cache[user_id] = prediction
        return prediction

    def predict_request_risk(
        self,
        user_id: str,
        requested_roles: List[str],
        requested_permissions: List[Dict] = None
    ) -> RiskPrediction:
        """
        Predict risk of granting an access request.
        """
        # Get current user profile
        profile = self.user_profiles.get(user_id) or self._build_user_profile(user_id, {})

        # Simulate access addition
        simulated_profile = self._simulate_access_grant(profile, requested_roles, requested_permissions or [])

        # Calculate risk with new access
        factors = self._calculate_risk_factors(simulated_profile)
        overall_score = self._calculate_overall_score(factors)

        # Compare to current risk
        current_prediction = self.prediction_cache.get(user_id)
        current_score = current_prediction.overall_risk_score if current_prediction else 0

        risk_delta = overall_score - current_score

        # Predict new violations
        predicted_violations = self._predict_request_violations(
            profile, requested_roles, requested_permissions or []
        )

        prediction = RiskPrediction(
            target_type="request",
            target_id=f"{user_id}:REQUEST",
            overall_risk_score=overall_score,
            risk_level=self._determine_risk_level(overall_score),
            confidence=PredictionConfidence.HIGH if predicted_violations else PredictionConfidence.MEDIUM,
            risk_factors=factors,
            category_scores=self._calculate_category_scores(factors),
            predicted_violations=predicted_violations,
            probability_of_incident=self._calculate_incident_probability(overall_score, factors),
            risk_mitigation_suggestions=[
                {
                    "type": "risk_delta",
                    "description": f"Risk score will increase by {risk_delta:.1f} points",
                    "current_score": round(current_score, 1),
                    "new_score": round(overall_score, 1)
                }
            ] + self._generate_recommendations(simulated_profile, factors, self._determine_risk_level(overall_score)),
            recommended_actions=self._get_request_action_items(risk_delta, predicted_violations)
        )

        return prediction

    def predict_batch_risks(self, user_ids: List[str]) -> Dict[str, RiskPrediction]:
        """Predict risks for multiple users"""
        results = {}
        for user_id in user_ids:
            results[user_id] = self.predict_user_risk(user_id)
        return results

    def _build_user_profile(self, user_id: str, user_data: Dict) -> UserRiskProfile:
        """Build a user risk profile from available data"""
        profile = UserRiskProfile(
            user_id=user_id,
            department=user_data.get("department", ""),
            job_title=user_data.get("job_title", "")
        )

        # Access metrics
        roles = user_data.get("roles", [])
        permissions = user_data.get("permissions", [])

        profile.total_roles = len(roles)
        profile.total_permissions = len(permissions)

        # Count sensitive permissions (simplified check)
        sensitive_keywords = ["ADMIN", "DELETE", "CREATE", "MODIFY", "ALL", "DEBUG"]
        profile.sensitive_permissions = sum(
            1 for p in permissions
            if any(kw in str(p).upper() for kw in sensitive_keywords)
        )

        # Simulate other metrics (in production, query actual data)
        profile.sod_violations_count = user_data.get("sod_violations", random.randint(0, 5))
        profile.access_changes_90d = user_data.get("access_changes", random.randint(0, 15))
        profile.firefighter_usage_90d = user_data.get("firefighter_usage", random.randint(0, 3))
        profile.after_hours_activity_pct = user_data.get("after_hours_pct", random.uniform(0, 20))
        profile.unused_permissions = int(profile.total_permissions * random.uniform(0.1, 0.4))

        # Peer comparison
        if profile.department:
            peers = self.peer_groups.get(profile.department, [])
            profile.peer_group_size = len(peers)
            if peers:
                avg_peer_perms = sum(
                    self.user_profiles.get(p, UserRiskProfile(p)).total_permissions
                    for p in peers
                ) / len(peers) if peers else profile.total_permissions
                profile.access_vs_peers_pct = (
                    (profile.total_permissions - avg_peer_perms) / avg_peer_perms * 100
                    if avg_peer_perms > 0 else 0
                )

        # Time-based
        profile.days_since_review = user_data.get("days_since_review", random.randint(30, 365))
        profile.account_age_days = user_data.get("account_age", random.randint(100, 1500))

        return profile

    def _calculate_risk_factors(self, profile: UserRiskProfile) -> List[RiskFactor]:
        """Calculate all risk factors for a profile"""
        factors = []

        # SoD Violations
        sod_norm = min(1.0, profile.sod_violations_count / 5)
        factors.append(RiskFactor(
            factor_id="sod_violations",
            name="SoD Violations",
            category=RiskCategory.SOD_VIOLATION,
            weight=self.FEATURE_WEIGHTS["sod_violation_count"],
            raw_value=profile.sod_violations_count,
            normalized_value=sod_norm,
            description=f"User has {profile.sod_violations_count} active SoD violations",
            evidence=[{"type": "violation_count", "value": profile.sod_violations_count}]
        ))

        # Sensitive Access Ratio
        sens_ratio = profile.sensitive_permissions / profile.total_permissions if profile.total_permissions > 0 else 0
        factors.append(RiskFactor(
            factor_id="sensitive_access",
            name="Sensitive Access Ratio",
            category=RiskCategory.EXCESSIVE_ACCESS,
            weight=self.FEATURE_WEIGHTS["sensitive_access_ratio"],
            raw_value=sens_ratio,
            normalized_value=min(1.0, sens_ratio * 2),  # Scale up
            description=f"{profile.sensitive_permissions} of {profile.total_permissions} permissions are sensitive",
            evidence=[{"sensitive": profile.sensitive_permissions, "total": profile.total_permissions}]
        ))

        # Unused Access
        unused_ratio = profile.unused_permissions / profile.total_permissions if profile.total_permissions > 0 else 0
        factors.append(RiskFactor(
            factor_id="unused_access",
            name="Unused Access",
            category=RiskCategory.DORMANT_ACCESS,
            weight=self.FEATURE_WEIGHTS["unused_access_ratio"],
            raw_value=unused_ratio,
            normalized_value=unused_ratio,
            description=f"{profile.unused_permissions} permissions appear unused",
            evidence=[{"unused": profile.unused_permissions}]
        ))

        # Peer Deviation
        peer_dev_norm = min(1.0, abs(profile.access_vs_peers_pct) / 100)
        factors.append(RiskFactor(
            factor_id="peer_deviation",
            name="Peer Access Deviation",
            category=RiskCategory.PRIVILEGE_CREEP,
            weight=self.FEATURE_WEIGHTS["peer_access_deviation"],
            raw_value=profile.access_vs_peers_pct,
            normalized_value=peer_dev_norm if profile.access_vs_peers_pct > 0 else 0,
            description=f"User has {profile.access_vs_peers_pct:+.1f}% access vs peers",
            evidence=[{"deviation_pct": profile.access_vs_peers_pct}]
        ))

        # Access Change Velocity
        change_norm = min(1.0, profile.access_changes_90d / 20)
        factors.append(RiskFactor(
            factor_id="change_velocity",
            name="Access Change Velocity",
            category=RiskCategory.PRIVILEGE_CREEP,
            weight=self.FEATURE_WEIGHTS["access_change_velocity"],
            raw_value=profile.access_changes_90d,
            normalized_value=change_norm,
            description=f"{profile.access_changes_90d} access changes in last 90 days",
            evidence=[{"changes": profile.access_changes_90d}]
        ))

        # Firefighter Usage
        ff_norm = min(1.0, profile.firefighter_usage_90d / 5)
        factors.append(RiskFactor(
            factor_id="firefighter_usage",
            name="Emergency Access Usage",
            category=RiskCategory.ANOMALOUS_BEHAVIOR,
            weight=self.FEATURE_WEIGHTS["firefighter_usage"],
            raw_value=profile.firefighter_usage_90d,
            normalized_value=ff_norm,
            description=f"Used firefighter access {profile.firefighter_usage_90d} times recently",
            evidence=[{"ff_sessions": profile.firefighter_usage_90d}]
        ))

        # After Hours Activity
        after_hours_norm = min(1.0, profile.after_hours_activity_pct / 30)
        factors.append(RiskFactor(
            factor_id="after_hours",
            name="After Hours Activity",
            category=RiskCategory.ANOMALOUS_BEHAVIOR,
            weight=self.FEATURE_WEIGHTS["after_hours_activity"],
            raw_value=profile.after_hours_activity_pct,
            normalized_value=after_hours_norm,
            description=f"{profile.after_hours_activity_pct:.1f}% of activity outside business hours",
            evidence=[{"pct": profile.after_hours_activity_pct}]
        ))

        # Review Staleness
        review_norm = min(1.0, profile.days_since_review / 365)
        factors.append(RiskFactor(
            factor_id="review_staleness",
            name="Access Review Staleness",
            category=RiskCategory.POLICY_VIOLATION,
            weight=self.FEATURE_WEIGHTS["days_since_review"],
            raw_value=profile.days_since_review,
            normalized_value=review_norm,
            description=f"Last access review was {profile.days_since_review} days ago",
            evidence=[{"days": profile.days_since_review}]
        ))

        # Privileged Roles
        priv_count = sum(1 for r in range(profile.total_roles) if random.random() > 0.7)  # Simulated
        priv_norm = min(1.0, priv_count / 3)
        factors.append(RiskFactor(
            factor_id="privileged_roles",
            name="Privileged Role Count",
            category=RiskCategory.EXCESSIVE_ACCESS,
            weight=self.FEATURE_WEIGHTS["privileged_role_count"],
            raw_value=priv_count,
            normalized_value=priv_norm,
            description=f"User has {priv_count} privileged/admin roles",
            evidence=[{"count": priv_count}]
        ))

        return factors

    def _calculate_overall_score(self, factors: List[RiskFactor]) -> float:
        """Calculate weighted overall risk score"""
        total_weight = sum(f.weight for f in factors)
        weighted_sum = sum(f.weight * f.normalized_value * 100 for f in factors)
        return weighted_sum / total_weight if total_weight > 0 else 0

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score >= self.RISK_THRESHOLDS["critical"]:
            return "critical"
        elif score >= self.RISK_THRESHOLDS["high"]:
            return "high"
        elif score >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    def _calculate_category_scores(self, factors: List[RiskFactor]) -> Dict[str, float]:
        """Calculate risk scores by category"""
        category_factors = defaultdict(list)
        for f in factors:
            category_factors[f.category.value].append(f)

        scores = {}
        for cat, cat_factors in category_factors.items():
            if cat_factors:
                scores[cat] = sum(f.normalized_value * f.weight * 100 for f in cat_factors) / len(cat_factors)

        return scores

    def _predict_violations(self, profile: UserRiskProfile, factors: List[RiskFactor]) -> List[Dict]:
        """Predict potential violations"""
        violations = []

        # High SoD risk
        sod_factor = next((f for f in factors if f.factor_id == "sod_violations"), None)
        if sod_factor and sod_factor.normalized_value > 0.3:
            violations.append({
                "type": "sod_violation",
                "probability": round(0.5 + sod_factor.normalized_value * 0.4, 2),
                "description": "Likely to have additional SoD conflicts",
                "timeframe": "30 days"
            })

        # Dormant access risk
        unused_factor = next((f for f in factors if f.factor_id == "unused_access"), None)
        if unused_factor and unused_factor.normalized_value > 0.3:
            violations.append({
                "type": "dormant_access_abuse",
                "probability": round(0.2 + unused_factor.normalized_value * 0.3, 2),
                "description": "Unused access may be exploited",
                "timeframe": "90 days"
            })

        # Privilege creep
        peer_factor = next((f for f in factors if f.factor_id == "peer_deviation"), None)
        if peer_factor and peer_factor.normalized_value > 0.4:
            violations.append({
                "type": "privilege_creep",
                "probability": round(0.4 + peer_factor.normalized_value * 0.3, 2),
                "description": "Access accumulation exceeds role requirements",
                "timeframe": "60 days"
            })

        return violations

    def _predict_request_violations(
        self,
        profile: UserRiskProfile,
        requested_roles: List[str],
        requested_permissions: List[Dict]
    ) -> List[Dict]:
        """Predict violations that may occur if request is granted"""
        violations = []

        # Check for potential SoD (simplified)
        if len(requested_roles) > 2:
            violations.append({
                "type": "potential_sod",
                "probability": 0.6,
                "description": f"Granting {len(requested_roles)} roles may create SoD conflicts",
                "roles": requested_roles
            })

        # Check for excessive access
        new_total = profile.total_permissions + len(requested_permissions)
        if new_total > profile.total_permissions * 1.5:
            violations.append({
                "type": "excessive_access",
                "probability": 0.5,
                "description": f"Request increases permissions by {len(requested_permissions)}",
                "increase_pct": round((len(requested_permissions) / profile.total_permissions) * 100, 1)
                if profile.total_permissions > 0 else 100
            })

        return violations

    def _calculate_incident_probability(self, score: float, factors: List[RiskFactor]) -> float:
        """Calculate probability of a security incident"""
        # Base probability from score
        base_prob = score / 200  # Max 0.5 from score alone

        # Adjust for critical factors
        high_risk_factors = [f for f in factors if f.normalized_value > 0.7]
        factor_boost = len(high_risk_factors) * 0.05

        return min(0.95, base_prob + factor_boost)

    def _calculate_confidence(self, profile: UserRiskProfile) -> PredictionConfidence:
        """Calculate prediction confidence based on data quality"""
        data_points = sum([
            1 if profile.total_permissions > 0 else 0,
            1 if profile.days_since_review < 365 else 0,
            1 if profile.peer_group_size > 5 else 0,
            1 if profile.account_age_days > 90 else 0
        ])

        if data_points >= 4:
            return PredictionConfidence.VERY_HIGH
        elif data_points >= 3:
            return PredictionConfidence.HIGH
        elif data_points >= 2:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW

    def _generate_recommendations(
        self,
        profile: UserRiskProfile,
        factors: List[RiskFactor],
        risk_level: str
    ) -> List[Dict]:
        """Generate risk mitigation recommendations"""
        recommendations = []

        # Sort factors by contribution
        sorted_factors = sorted(
            factors,
            key=lambda f: f.weight * f.normalized_value,
            reverse=True
        )

        for factor in sorted_factors[:3]:  # Top 3 contributors
            if factor.normalized_value < 0.3:
                continue

            if factor.factor_id == "sod_violations":
                recommendations.append({
                    "priority": "high",
                    "category": "remediation",
                    "action": "Review and remediate SoD violations",
                    "impact": f"Could reduce risk score by {factor.weight * factor.normalized_value * 100:.1f} points"
                })

            elif factor.factor_id == "unused_access":
                recommendations.append({
                    "priority": "medium",
                    "category": "cleanup",
                    "action": f"Remove {profile.unused_permissions} unused permissions",
                    "impact": "Reduces attack surface and simplifies access reviews"
                })

            elif factor.factor_id == "peer_deviation":
                recommendations.append({
                    "priority": "medium",
                    "category": "review",
                    "action": "Conduct peer comparison access review",
                    "impact": "Align access with role requirements"
                })

            elif factor.factor_id == "review_staleness":
                recommendations.append({
                    "priority": "high",
                    "category": "compliance",
                    "action": "Schedule immediate access certification",
                    "impact": "Ensure compliance with review requirements"
                })

            elif factor.factor_id == "firefighter_usage":
                recommendations.append({
                    "priority": "medium",
                    "category": "investigation",
                    "action": "Review firefighter session logs",
                    "impact": "Ensure emergency access was appropriate"
                })

        return recommendations

    def _get_action_items(self, risk_level: str, factors: List[RiskFactor]) -> List[str]:
        """Get specific action items based on risk level"""
        actions = []

        if risk_level == "critical":
            actions.append("IMMEDIATE: Escalate to security team for review")
            actions.append("Temporarily restrict sensitive access pending review")

        if risk_level in ["critical", "high"]:
            actions.append("Schedule access review within 7 days")
            actions.append("Review recent activity logs for anomalies")

        # Factor-specific actions
        sod = next((f for f in factors if f.factor_id == "sod_violations" and f.normalized_value > 0.5), None)
        if sod:
            actions.append(f"Remediate {int(sod.raw_value)} SoD violations")

        unused = next((f for f in factors if f.factor_id == "unused_access" and f.normalized_value > 0.3), None)
        if unused:
            actions.append("Run unused access cleanup")

        return actions

    def _get_request_action_items(self, risk_delta: float, violations: List[Dict]) -> List[str]:
        """Get action items for access requests"""
        actions = []

        if risk_delta > 20:
            actions.append("Request requires additional approval level")
            actions.append("Document business justification thoroughly")

        if violations:
            actions.append("Review predicted violations before approval")
            if any(v["type"] == "potential_sod" for v in violations):
                actions.append("Run SoD simulation before granting access")

        if risk_delta > 10:
            actions.append("Consider time-limited access grant")

        return actions

    def _simulate_access_grant(
        self,
        profile: UserRiskProfile,
        roles: List[str],
        permissions: List[Dict]
    ) -> UserRiskProfile:
        """Simulate granting access to see impact"""
        simulated = UserRiskProfile(
            user_id=profile.user_id,
            department=profile.department,
            job_title=profile.job_title,
            total_roles=profile.total_roles + len(roles),
            total_permissions=profile.total_permissions + len(permissions),
            sensitive_permissions=profile.sensitive_permissions + sum(
                1 for p in permissions
                if any(kw in str(p).upper() for kw in ["ADMIN", "DELETE", "CREATE"])
            ),
            unused_permissions=profile.unused_permissions,
            sod_violations_count=profile.sod_violations_count + (1 if len(roles) > 2 else 0),
            access_changes_90d=profile.access_changes_90d + 1,
            firefighter_usage_90d=profile.firefighter_usage_90d,
            after_hours_activity_pct=profile.after_hours_activity_pct,
            peer_group_size=profile.peer_group_size,
            access_vs_peers_pct=profile.access_vs_peers_pct + len(permissions) * 2,
            days_since_review=profile.days_since_review,
            account_age_days=profile.account_age_days
        )
        return simulated

    def get_high_risk_users(self, threshold: float = 75.0, limit: int = 50) -> List[Dict]:
        """Get users with risk scores above threshold"""
        high_risk = []

        for user_id, prediction in self.prediction_cache.items():
            if prediction.overall_risk_score >= threshold:
                high_risk.append({
                    "user_id": user_id,
                    "risk_score": round(prediction.overall_risk_score, 1),
                    "risk_level": prediction.risk_level,
                    "top_factors": [f.name for f in prediction.risk_factors[:3]]
                })

        return sorted(high_risk, key=lambda x: x["risk_score"], reverse=True)[:limit]

    def get_risk_distribution(self) -> Dict:
        """Get distribution of risk scores"""
        if not self.prediction_cache:
            return {"low": 0, "medium": 0, "high": 0, "critical": 0}

        distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for prediction in self.prediction_cache.values():
            distribution[prediction.risk_level] += 1

        return distribution
