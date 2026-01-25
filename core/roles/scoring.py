# Role Risk Scoring
# Risk score per role (0-100) based on multiple factors

"""
Role Risk Scoring for GOVERNEX+.

Risk score based on:
- SoD exposure
- Sensitive access
- Usage pattern
- Toxicity (graph-based)
- Trend over time

Provides prioritized remediation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import Role, Permission

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for roles."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskFactor:
    """A single risk factor contributing to role risk."""
    factor_id: str
    factor_name: str
    description: str

    # Scoring
    weight: float = 1.0  # Factor weight
    raw_score: float = 0.0  # Raw score (0-100)
    weighted_score: float = 0.0  # After weight applied

    # Evidence
    evidence: List[str] = field(default_factory=list)
    affected_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "factor_name": self.factor_name,
            "description": self.description,
            "weight": round(self.weight, 2),
            "raw_score": round(self.raw_score, 2),
            "weighted_score": round(self.weighted_score, 2),
            "evidence": self.evidence,
            "affected_items": self.affected_items,
        }


@dataclass
class RiskTrend:
    """Risk trend for a role over time."""
    role_id: str
    period_days: int

    # Current vs historical
    current_score: float = 0.0
    score_30d_ago: float = 0.0
    score_60d_ago: float = 0.0
    score_90d_ago: float = 0.0

    # Trend
    direction: str = "stable"  # "increasing", "stable", "decreasing"
    velocity: float = 0.0  # Points per month

    # History
    score_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "period_days": self.period_days,
            "current_score": round(self.current_score, 2),
            "score_30d_ago": round(self.score_30d_ago, 2),
            "score_60d_ago": round(self.score_60d_ago, 2),
            "score_90d_ago": round(self.score_90d_ago, 2),
            "direction": self.direction,
            "velocity": round(self.velocity, 2),
            "score_history": self.score_history,
        }


@dataclass
class RoleRiskScore:
    """Complete risk score for a role."""
    role_id: str
    role_name: str

    # Overall score
    total_score: float = 0.0  # 0-100
    risk_level: RiskLevel = RiskLevel.LOW

    # Factor breakdown
    risk_factors: List[RiskFactor] = field(default_factory=list)

    # Top contributors
    primary_risk_factor: str = ""
    top_contributors: List[str] = field(default_factory=list)

    # Trend
    risk_trend: Optional[RiskTrend] = None

    # Remediation
    remediation_priority: str = "LOW"
    recommended_actions: List[str] = field(default_factory=list)

    # Comparison
    percentile: float = 0.0  # Role risk percentile in organization
    above_average: bool = False

    # Metadata
    scored_at: datetime = field(default_factory=datetime.now)
    scoring_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "total_score": round(self.total_score, 2),
            "risk_level": self.risk_level.value,
            "risk_factors": [f.to_dict() for f in self.risk_factors],
            "primary_risk_factor": self.primary_risk_factor,
            "top_contributors": self.top_contributors,
            "risk_trend": self.risk_trend.to_dict() if self.risk_trend else None,
            "remediation_priority": self.remediation_priority,
            "recommended_actions": self.recommended_actions,
            "percentile": round(self.percentile, 2),
            "above_average": self.above_average,
            "scored_at": self.scored_at.isoformat(),
        }


class RoleRiskScorer:
    """
    Calculates risk scores for roles.

    Scoring factors:
    1. SoD exposure (weight: 0.25)
    2. Sensitive access (weight: 0.20)
    3. Privilege breadth (weight: 0.15)
    4. Wildcard usage (weight: 0.10)
    5. Usage pattern risk (weight: 0.10)
    6. Toxicity index (weight: 0.10)
    7. Assignment count (weight: 0.05)
    8. Age/review status (weight: 0.05)
    """

    # Factor weights
    FACTOR_WEIGHTS = {
        "sod_exposure": 0.25,
        "sensitive_access": 0.20,
        "privilege_breadth": 0.15,
        "wildcard_usage": 0.10,
        "usage_pattern": 0.10,
        "toxicity": 0.10,
        "assignment_count": 0.05,
        "review_status": 0.05,
    }

    # Thresholds
    CRITICAL_THRESHOLD = 80
    HIGH_THRESHOLD = 60
    MEDIUM_THRESHOLD = 40

    def __init__(self):
        """Initialize scorer."""
        self._score_cache: Dict[str, RoleRiskScore] = {}
        self._score_history: Dict[str, List[Dict[str, Any]]] = {}

    def score_role(
        self,
        role: Role,
        sod_conflicts: List[str] = None,
        usage_metrics: Optional[Dict[str, Any]] = None,
        toxicity_score: float = 0,
        peer_average: float = 50
    ) -> RoleRiskScore:
        """
        Calculate risk score for a role.

        Args:
            role: Role to score
            sod_conflicts: List of SoD conflicts involving this role
            usage_metrics: Usage analytics data
            toxicity_score: Toxicity score from graph analysis
            peer_average: Average risk score across all roles

        Returns:
            RoleRiskScore with complete breakdown
        """
        score = RoleRiskScore(
            role_id=role.role_id,
            role_name=role.role_name,
        )

        sod_conflicts = sod_conflicts or []
        usage_metrics = usage_metrics or {}

        # Calculate each factor
        factors = []

        # 1. SoD Exposure
        factors.append(self._score_sod_exposure(role, sod_conflicts))

        # 2. Sensitive Access
        factors.append(self._score_sensitive_access(role))

        # 3. Privilege Breadth
        factors.append(self._score_privilege_breadth(role))

        # 4. Wildcard Usage
        factors.append(self._score_wildcard_usage(role))

        # 5. Usage Pattern Risk
        factors.append(self._score_usage_pattern(role, usage_metrics))

        # 6. Toxicity
        factors.append(self._score_toxicity(role, toxicity_score))

        # 7. Assignment Count
        factors.append(self._score_assignment_count(role))

        # 8. Review Status
        factors.append(self._score_review_status(role))

        score.risk_factors = factors

        # Calculate total score
        score.total_score = sum(f.weighted_score for f in factors)

        # Determine risk level
        if score.total_score >= self.CRITICAL_THRESHOLD:
            score.risk_level = RiskLevel.CRITICAL
        elif score.total_score >= self.HIGH_THRESHOLD:
            score.risk_level = RiskLevel.HIGH
        elif score.total_score >= self.MEDIUM_THRESHOLD:
            score.risk_level = RiskLevel.MEDIUM
        else:
            score.risk_level = RiskLevel.LOW

        # Find top contributors
        sorted_factors = sorted(factors, key=lambda f: f.weighted_score, reverse=True)
        score.primary_risk_factor = sorted_factors[0].factor_name if sorted_factors else ""
        score.top_contributors = [f.factor_name for f in sorted_factors[:3]]

        # Comparison with peer average
        score.above_average = score.total_score > peer_average
        score.percentile = self._calculate_percentile(score.total_score)

        # Generate recommendations
        score.recommended_actions = self._generate_recommendations(score)

        # Set remediation priority
        if score.risk_level == RiskLevel.CRITICAL:
            score.remediation_priority = "CRITICAL"
        elif score.risk_level == RiskLevel.HIGH:
            score.remediation_priority = "HIGH"
        elif score.risk_level == RiskLevel.MEDIUM:
            score.remediation_priority = "MEDIUM"
        else:
            score.remediation_priority = "LOW"

        # Update history and trend
        self._update_score_history(role.role_id, score.total_score)
        score.risk_trend = self._calculate_trend(role.role_id)

        # Cache result
        self._score_cache[role.role_id] = score

        return score

    def _score_sod_exposure(
        self,
        role: Role,
        sod_conflicts: List[str]
    ) -> RiskFactor:
        """Score SoD exposure."""
        factor = RiskFactor(
            factor_id="sod_exposure",
            factor_name="SoD Exposure",
            description="Segregation of duties conflicts",
            weight=self.FACTOR_WEIGHTS["sod_exposure"],
        )

        conflict_count = len(sod_conflicts)

        if conflict_count == 0:
            factor.raw_score = 0
        elif conflict_count <= 2:
            factor.raw_score = 40
        elif conflict_count <= 5:
            factor.raw_score = 70
        else:
            factor.raw_score = 100

        factor.weighted_score = factor.raw_score * factor.weight
        factor.evidence = [f"Role involved in {conflict_count} SoD conflicts"]
        factor.affected_items = sod_conflicts[:5]

        return factor

    def _score_sensitive_access(self, role: Role) -> RiskFactor:
        """Score sensitive access."""
        factor = RiskFactor(
            factor_id="sensitive_access",
            factor_name="Sensitive Access",
            description="Access to sensitive transactions/data",
            weight=self.FACTOR_WEIGHTS["sensitive_access"],
        )

        sensitive_count = role.sensitive_permission_count
        total_count = role.permission_count

        if total_count == 0:
            factor.raw_score = 0
        else:
            sensitive_ratio = sensitive_count / total_count

            if sensitive_ratio > 0.5:
                factor.raw_score = 100
            elif sensitive_ratio > 0.25:
                factor.raw_score = 70
            elif sensitive_ratio > 0.1:
                factor.raw_score = 40
            elif sensitive_count > 0:
                factor.raw_score = 20
            else:
                factor.raw_score = 0

        factor.weighted_score = factor.raw_score * factor.weight
        factor.evidence = [f"{sensitive_count} sensitive permissions out of {total_count}"]
        factor.affected_items = [
            p.value for p in role.permissions if p.is_sensitive
        ][:10]

        return factor

    def _score_privilege_breadth(self, role: Role) -> RiskFactor:
        """Score privilege breadth (too many permissions)."""
        factor = RiskFactor(
            factor_id="privilege_breadth",
            factor_name="Privilege Breadth",
            description="Total number of permissions",
            weight=self.FACTOR_WEIGHTS["privilege_breadth"],
        )

        permission_count = role.permission_count

        if permission_count > 100:
            factor.raw_score = 100
        elif permission_count > 50:
            factor.raw_score = 70
        elif permission_count > 25:
            factor.raw_score = 40
        elif permission_count > 10:
            factor.raw_score = 20
        else:
            factor.raw_score = 0

        factor.weighted_score = factor.raw_score * factor.weight
        factor.evidence = [f"Role has {permission_count} permissions"]

        return factor

    def _score_wildcard_usage(self, role: Role) -> RiskFactor:
        """Score wildcard authorization usage."""
        factor = RiskFactor(
            factor_id="wildcard_usage",
            factor_name="Wildcard Usage",
            description="Wildcard (*) in authorization objects",
            weight=self.FACTOR_WEIGHTS["wildcard_usage"],
        )

        wildcard_objects = []
        for perm in role.permissions:
            if perm.auth_object and perm.auth_object.has_wildcard():
                wildcard_objects.append(perm.auth_object.object_id)

        wildcard_count = len(wildcard_objects)

        if wildcard_count > 10:
            factor.raw_score = 100
        elif wildcard_count > 5:
            factor.raw_score = 70
        elif wildcard_count > 2:
            factor.raw_score = 50
        elif wildcard_count > 0:
            factor.raw_score = 30
        else:
            factor.raw_score = 0

        factor.weighted_score = factor.raw_score * factor.weight
        factor.evidence = [f"{wildcard_count} authorization objects with wildcards"]
        factor.affected_items = wildcard_objects[:10]

        return factor

    def _score_usage_pattern(
        self,
        role: Role,
        usage_metrics: Dict[str, Any]
    ) -> RiskFactor:
        """Score based on usage patterns."""
        factor = RiskFactor(
            factor_id="usage_pattern",
            factor_name="Usage Pattern Risk",
            description="Risky usage patterns (off-hours, unused access)",
            weight=self.FACTOR_WEIGHTS["usage_pattern"],
        )

        after_hours_ratio = usage_metrics.get("after_hours_ratio", 0)
        unused_ratio = usage_metrics.get("unused_permissions_ratio", 0)

        # Risk from off-hours usage
        pattern_score = 0
        if after_hours_ratio > 0.2:
            pattern_score += 40

        # Risk from unused permissions (privilege creep)
        if unused_ratio > 0.5:
            pattern_score += 60
        elif unused_ratio > 0.25:
            pattern_score += 30

        factor.raw_score = min(100, pattern_score)
        factor.weighted_score = factor.raw_score * factor.weight

        evidence = []
        if after_hours_ratio > 0:
            evidence.append(f"{after_hours_ratio:.0%} activity outside business hours")
        if unused_ratio > 0:
            evidence.append(f"{unused_ratio:.0%} permissions never used")
        factor.evidence = evidence

        return factor

    def _score_toxicity(
        self,
        role: Role,
        toxicity_score: float
    ) -> RiskFactor:
        """Score based on graph toxicity."""
        factor = RiskFactor(
            factor_id="toxicity",
            factor_name="Toxicity Index",
            description="Graph-based toxicity (fraud paths enabled)",
            weight=self.FACTOR_WEIGHTS["toxicity"],
        )

        factor.raw_score = min(100, toxicity_score)
        factor.weighted_score = factor.raw_score * factor.weight

        if toxicity_score > 0:
            factor.evidence = [f"Toxicity score: {toxicity_score:.0f}"]
        else:
            factor.evidence = ["No toxic patterns detected"]

        return factor

    def _score_assignment_count(self, role: Role) -> RiskFactor:
        """Score based on number of users assigned."""
        factor = RiskFactor(
            factor_id="assignment_count",
            factor_name="Assignment Count",
            description="Number of users with this role",
            weight=self.FACTOR_WEIGHTS["assignment_count"],
        )

        count = role.assignment_count

        # More users = higher blast radius
        if count > 100:
            factor.raw_score = 80
        elif count > 50:
            factor.raw_score = 60
        elif count > 20:
            factor.raw_score = 40
        elif count > 5:
            factor.raw_score = 20
        else:
            factor.raw_score = 0

        factor.weighted_score = factor.raw_score * factor.weight
        factor.evidence = [f"Role assigned to {count} users"]

        return factor

    def _score_review_status(self, role: Role) -> RiskFactor:
        """Score based on review/certification status."""
        factor = RiskFactor(
            factor_id="review_status",
            factor_name="Review Status",
            description="Overdue reviews and certifications",
            weight=self.FACTOR_WEIGHTS["review_status"],
        )

        score = 0

        if role.metadata:
            # Check last review
            if role.metadata.last_review_date:
                days_since = (datetime.now() - role.metadata.last_review_date).days
                if days_since > 365:
                    score += 50
                elif days_since > 180:
                    score += 30
                elif days_since > 90:
                    score += 10
            else:
                score += 40  # Never reviewed

            # Check certification
            if role.metadata.certification_expires:
                if role.metadata.certification_expires < datetime.now():
                    score += 50  # Expired

        factor.raw_score = min(100, score)
        factor.weighted_score = factor.raw_score * factor.weight

        return factor

    def _calculate_percentile(self, score: float) -> float:
        """Calculate score percentile (simplified)."""
        # In production, compare against all cached scores
        if not self._score_cache:
            return 50.0

        scores = [s.total_score for s in self._score_cache.values()]
        lower = sum(1 for s in scores if s < score)
        return (lower / len(scores)) * 100

    def _update_score_history(self, role_id: str, score: float):
        """Update score history for trend analysis."""
        if role_id not in self._score_history:
            self._score_history[role_id] = []

        self._score_history[role_id].append({
            "score": score,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep last 12 months
        if len(self._score_history[role_id]) > 365:
            self._score_history[role_id] = self._score_history[role_id][-365:]

    def _calculate_trend(self, role_id: str) -> RiskTrend:
        """Calculate risk trend for a role."""
        trend = RiskTrend(role_id=role_id, period_days=90)
        history = self._score_history.get(role_id, [])

        if not history:
            return trend

        trend.current_score = history[-1]["score"]
        trend.score_history = history[-12:]  # Last 12 entries

        # Find historical scores
        now = datetime.now()
        for entry in history:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            days_ago = (now - entry_time).days

            if 28 <= days_ago <= 32:
                trend.score_30d_ago = entry["score"]
            elif 58 <= days_ago <= 62:
                trend.score_60d_ago = entry["score"]
            elif 88 <= days_ago <= 92:
                trend.score_90d_ago = entry["score"]

        # Calculate velocity
        if trend.score_90d_ago > 0:
            trend.velocity = (trend.current_score - trend.score_90d_ago) / 3  # Per month

        # Determine direction
        if trend.velocity > 5:
            trend.direction = "increasing"
        elif trend.velocity < -5:
            trend.direction = "decreasing"
        else:
            trend.direction = "stable"

        return trend

    def _generate_recommendations(self, score: RoleRiskScore) -> List[str]:
        """Generate remediation recommendations."""
        recommendations = []

        for factor in score.risk_factors:
            if factor.weighted_score > 15:  # Significant contributor
                if factor.factor_id == "sod_exposure":
                    recommendations.append("Split role to eliminate SoD conflicts")
                elif factor.factor_id == "sensitive_access":
                    recommendations.append("Review and remove unnecessary sensitive access")
                elif factor.factor_id == "privilege_breadth":
                    recommendations.append("Decompose role into smaller, focused roles")
                elif factor.factor_id == "wildcard_usage":
                    recommendations.append("Replace wildcards with specific values")
                elif factor.factor_id == "usage_pattern":
                    recommendations.append("Remove unused permissions")
                elif factor.factor_id == "toxicity":
                    recommendations.append("Redesign role to eliminate toxic patterns")
                elif factor.factor_id == "review_status":
                    recommendations.append("Complete overdue role review")

        if not recommendations:
            recommendations.append("Continue regular monitoring")

        return recommendations[:5]

    def get_high_risk_roles(
        self,
        threshold: float = None
    ) -> List[RoleRiskScore]:
        """Get roles above risk threshold."""
        threshold = threshold or self.HIGH_THRESHOLD

        return [
            score for score in self._score_cache.values()
            if score.total_score >= threshold
        ]

    def get_score(self, role_id: str) -> Optional[RoleRiskScore]:
        """Get cached score for a role."""
        return self._score_cache.get(role_id)
