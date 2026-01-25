"""
Approval Behavior Analytics Engine

Analyzes approver behavior patterns to ensure approvals are meaningful,
not ceremonial. This addresses the auditor question:
"Are approvals meaningful or rubber-stamps?"

Key Capabilities:
- Rubber-stamp detection
- Approval bias analysis
- Manager risk profiles
- Approval anomaly detection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import math
from collections import defaultdict


class ApprovalAction(Enum):
    """Possible approval actions"""
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    DELEGATED = "delegated"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"


class RiskBehaviorPattern(Enum):
    """Identified risk behavior patterns"""
    NORMAL = "normal"
    RUBBER_STAMPER = "rubber_stamper"
    RISK_AVERSE = "risk_averse"
    INCONSISTENT = "inconsistent"
    BIASED = "biased"
    OVERWHELMED = "overwhelmed"
    DISENGAGED = "disengaged"


@dataclass
class ApprovalRecord:
    """A single approval action record"""
    approval_id: str
    approver_id: str
    request_id: str
    request_type: str  # role_request, firefighter, certification
    action: ApprovalAction
    risk_level: str
    timestamp: datetime
    decision_time_seconds: int
    requestor_id: str
    requestor_department: str
    comments: str = ""
    items_in_request: int = 1
    reviewed_details: bool = False
    accessed_risk_report: bool = False


@dataclass
class ApproverProfile:
    """Comprehensive approver behavior profile"""
    approver_id: str
    approver_name: str
    department: str
    manager_level: int  # 1 = first line, 2 = senior, 3 = executive

    # Volume metrics
    total_decisions: int = 0
    approvals: int = 0
    rejections: int = 0
    delegations: int = 0
    timeouts: int = 0

    # Timing patterns
    avg_decision_time_seconds: float = 0.0
    median_decision_time_seconds: float = 0.0
    std_dev_decision_time: float = 0.0
    decisions_under_1_minute: int = 0
    decisions_under_5_minutes: int = 0

    # Risk handling
    high_risk_approved: int = 0
    high_risk_rejected: int = 0
    critical_risk_approved: int = 0
    critical_risk_rejected: int = 0

    # Quality indicators
    rubber_stamp_score: float = 0.0
    risk_awareness_score: float = 0.0
    consistency_score: float = 0.0
    engagement_score: float = 0.0

    # Behavioral pattern
    primary_pattern: RiskBehaviorPattern = RiskBehaviorPattern.NORMAL
    secondary_patterns: List[RiskBehaviorPattern] = field(default_factory=list)
    pattern_confidence: float = 0.0

    # Bias indicators
    department_bias: Dict[str, float] = field(default_factory=dict)  # dept -> approval rate
    requestor_bias: Dict[str, float] = field(default_factory=dict)   # requestor -> approval rate
    time_of_day_bias: Dict[int, float] = field(default_factory=dict) # hour -> approval rate

    # Anomalies
    anomalies_detected: List[Dict] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ApprovalAnomaly:
    """An detected anomaly in approval behavior"""
    anomaly_id: str
    approver_id: str
    anomaly_type: str
    severity: str  # low, medium, high, critical
    description: str
    evidence: List[str]
    detected_at: datetime
    related_approvals: List[str]
    recommended_action: str


class ApprovalBehaviorEngine:
    """
    Engine for analyzing approval behavior patterns.

    Detects:
    - Rubber-stamping (ceremonial approvals)
    - Bias (toward certain requestors/departments)
    - Inconsistent decision making
    - Risk blindness
    - Anomalous patterns
    """

    def __init__(self):
        self.approval_records: List[ApprovalRecord] = []
        self.approver_profiles: Dict[str, ApproverProfile] = {}
        self.anomalies: List[ApprovalAnomaly] = []

    def record_approval(
        self,
        approval_id: str,
        approver_id: str,
        approver_name: str,
        approver_department: str,
        manager_level: int,
        request_id: str,
        request_type: str,
        action: ApprovalAction,
        risk_level: str,
        decision_time_seconds: int,
        requestor_id: str,
        requestor_department: str,
        comments: str = "",
        items_in_request: int = 1,
        reviewed_details: bool = False,
        accessed_risk_report: bool = False
    ):
        """Record an approval action for analysis"""

        record = ApprovalRecord(
            approval_id=approval_id,
            approver_id=approver_id,
            request_id=request_id,
            request_type=request_type,
            action=action,
            risk_level=risk_level,
            timestamp=datetime.utcnow(),
            decision_time_seconds=decision_time_seconds,
            requestor_id=requestor_id,
            requestor_department=requestor_department,
            comments=comments,
            items_in_request=items_in_request,
            reviewed_details=reviewed_details,
            accessed_risk_report=accessed_risk_report
        )

        self.approval_records.append(record)

        # Initialize or update approver profile
        if approver_id not in self.approver_profiles:
            self.approver_profiles[approver_id] = ApproverProfile(
                approver_id=approver_id,
                approver_name=approver_name,
                department=approver_department,
                manager_level=manager_level
            )

        # Analyze after each approval
        self._update_approver_analysis(approver_id)

        # Check for anomalies
        self._check_for_anomalies(record)

    def _update_approver_analysis(self, approver_id: str):
        """Update comprehensive analysis for an approver"""

        records = [r for r in self.approval_records if r.approver_id == approver_id]
        if not records:
            return

        profile = self.approver_profiles[approver_id]

        # Basic metrics
        profile.total_decisions = len(records)
        profile.approvals = len([r for r in records if r.action == ApprovalAction.APPROVED])
        profile.rejections = len([r for r in records if r.action == ApprovalAction.REJECTED])
        profile.delegations = len([r for r in records if r.action == ApprovalAction.DELEGATED])
        profile.timeouts = len([r for r in records if r.action == ApprovalAction.TIMED_OUT])

        # Timing analysis
        decision_times = [r.decision_time_seconds for r in records]
        profile.avg_decision_time_seconds = statistics.mean(decision_times)
        profile.median_decision_time_seconds = statistics.median(decision_times)
        profile.std_dev_decision_time = statistics.stdev(decision_times) if len(decision_times) > 1 else 0
        profile.decisions_under_1_minute = len([t for t in decision_times if t < 60])
        profile.decisions_under_5_minutes = len([t for t in decision_times if t < 300])

        # Risk handling
        high_risk = [r for r in records if r.risk_level == "high"]
        critical_risk = [r for r in records if r.risk_level == "critical"]

        profile.high_risk_approved = len([r for r in high_risk if r.action == ApprovalAction.APPROVED])
        profile.high_risk_rejected = len([r for r in high_risk if r.action == ApprovalAction.REJECTED])
        profile.critical_risk_approved = len([r for r in critical_risk if r.action == ApprovalAction.APPROVED])
        profile.critical_risk_rejected = len([r for r in critical_risk if r.action == ApprovalAction.REJECTED])

        # Calculate scores
        profile.rubber_stamp_score = self._calculate_rubber_stamp_score(records, profile)
        profile.risk_awareness_score = self._calculate_risk_awareness_score(records, profile)
        profile.consistency_score = self._calculate_consistency_score(records, profile)
        profile.engagement_score = self._calculate_engagement_score(records, profile)

        # Analyze bias
        self._analyze_bias(records, profile)

        # Determine behavior pattern
        self._determine_behavior_pattern(profile)

        # Generate recommendations
        self._generate_recommendations(profile)

    def _calculate_rubber_stamp_score(self, records: List[ApprovalRecord], profile: ApproverProfile) -> float:
        """
        Calculate rubber stamp score (0-100).

        Higher score = more likely rubber stamping.

        Factors:
        1. Very fast decisions (< 60 seconds for complex items)
        2. Very high approval rate (> 95%)
        3. No comments on approvals
        4. Never reviewing risk reports
        5. Approving high-risk without hesitation
        """
        score = 0.0

        if len(records) < 5:
            return 0.0  # Not enough data

        # Factor 1: Speed (30 points)
        fast_ratio = profile.decisions_under_1_minute / len(records)
        if fast_ratio > 0.7:
            score += 30
        elif fast_ratio > 0.5:
            score += 20
        elif fast_ratio > 0.3:
            score += 10

        # Factor 2: Approval rate (25 points)
        approval_rate = profile.approvals / len(records) if records else 0
        if approval_rate > 0.98:
            score += 25
        elif approval_rate > 0.95:
            score += 18
        elif approval_rate > 0.90:
            score += 10

        # Factor 3: No comments (15 points)
        no_comment_ratio = len([r for r in records if not r.comments]) / len(records)
        if no_comment_ratio > 0.9:
            score += 15
        elif no_comment_ratio > 0.7:
            score += 10

        # Factor 4: Never reviewing risk reports (15 points)
        no_risk_review = len([r for r in records if not r.accessed_risk_report]) / len(records)
        if no_risk_review > 0.9:
            score += 15
        elif no_risk_review > 0.7:
            score += 10

        # Factor 5: High-risk approval pattern (15 points)
        high_risk = [r for r in records if r.risk_level in ["high", "critical"]]
        if high_risk:
            hr_approval_rate = len([r for r in high_risk if r.action == ApprovalAction.APPROVED]) / len(high_risk)
            if hr_approval_rate > 0.95:
                score += 15
            elif hr_approval_rate > 0.85:
                score += 10

        return min(score, 100)

    def _calculate_risk_awareness_score(self, records: List[ApprovalRecord], profile: ApproverProfile) -> float:
        """
        Calculate risk awareness score (0-100).

        Higher score = better risk awareness.
        """
        score = 50.0  # Start at neutral

        if len(records) < 5:
            return 50.0

        # Bonus for rejecting high-risk items
        high_risk = [r for r in records if r.risk_level in ["high", "critical"]]
        if high_risk:
            rejection_rate = len([r for r in high_risk if r.action == ApprovalAction.REJECTED]) / len(high_risk)
            score += rejection_rate * 25

        # Bonus for reviewing risk reports
        review_rate = len([r for r in records if r.accessed_risk_report]) / len(records)
        score += review_rate * 15

        # Bonus for adding comments on high-risk
        if high_risk:
            comment_rate = len([r for r in high_risk if r.comments]) / len(high_risk)
            score += comment_rate * 10

        # Penalty for instant approvals of high-risk
        instant_high_risk = [
            r for r in high_risk
            if r.action == ApprovalAction.APPROVED and r.decision_time_seconds < 60
        ]
        if high_risk:
            instant_ratio = len(instant_high_risk) / len(high_risk)
            score -= instant_ratio * 20

        return max(0, min(100, score))

    def _calculate_consistency_score(self, records: List[ApprovalRecord], profile: ApproverProfile) -> float:
        """
        Calculate consistency score (0-100).

        Measures if similar requests get similar treatment.
        """
        if len(records) < 10:
            return 75.0  # Not enough data

        score = 100.0

        # Group by risk level and check consistency
        by_risk = defaultdict(list)
        for r in records:
            by_risk[r.risk_level].append(r)

        for risk_level, risk_records in by_risk.items():
            if len(risk_records) < 3:
                continue

            approval_rate = len([r for r in risk_records if r.action == ApprovalAction.APPROVED]) / len(risk_records)

            # High variance in decision times is inconsistent
            times = [r.decision_time_seconds for r in risk_records]
            if len(times) > 1:
                cv = statistics.stdev(times) / statistics.mean(times) if statistics.mean(times) > 0 else 0
                if cv > 1.5:  # Very high coefficient of variation
                    score -= 10

            # Check if same requestor gets wildly different treatment
            by_requestor = defaultdict(list)
            for r in risk_records:
                by_requestor[r.requestor_id].append(r)

            for requestor, req_records in by_requestor.items():
                if len(req_records) < 2:
                    continue
                rates = [r.action == ApprovalAction.APPROVED for r in req_records]
                if not all(rates) and not all(not r for r in rates):
                    # Mixed decisions for same person - could be good or bad
                    pass

        return max(0, min(100, score))

    def _calculate_engagement_score(self, records: List[ApprovalRecord], profile: ApproverProfile) -> float:
        """
        Calculate engagement score (0-100).

        Higher = more engaged with approval process.
        """
        score = 50.0

        if len(records) < 5:
            return 50.0

        # Positive: Reviews details
        detail_review_rate = len([r for r in records if r.reviewed_details]) / len(records)
        score += detail_review_rate * 20

        # Positive: Accesses risk reports
        risk_report_rate = len([r for r in records if r.accessed_risk_report]) / len(records)
        score += risk_report_rate * 15

        # Positive: Adds comments
        comment_rate = len([r for r in records if r.comments]) / len(records)
        score += comment_rate * 15

        # Negative: Timeouts
        timeout_rate = profile.timeouts / len(records)
        score -= timeout_rate * 30

        # Negative: Heavy delegation
        delegation_rate = profile.delegations / len(records)
        if delegation_rate > 0.3:
            score -= 20

        return max(0, min(100, score))

    def _analyze_bias(self, records: List[ApprovalRecord], profile: ApproverProfile):
        """Analyze for various types of bias"""

        # Department bias
        by_dept = defaultdict(list)
        for r in records:
            by_dept[r.requestor_department].append(r)

        for dept, dept_records in by_dept.items():
            if len(dept_records) >= 3:
                approval_rate = len([r for r in dept_records if r.action == ApprovalAction.APPROVED]) / len(dept_records)
                profile.department_bias[dept] = approval_rate * 100

        # Requestor bias
        by_requestor = defaultdict(list)
        for r in records:
            by_requestor[r.requestor_id].append(r)

        for requestor, req_records in by_requestor.items():
            if len(req_records) >= 3:
                approval_rate = len([r for r in req_records if r.action == ApprovalAction.APPROVED]) / len(req_records)
                profile.requestor_bias[requestor] = approval_rate * 100

        # Time of day bias
        by_hour = defaultdict(list)
        for r in records:
            by_hour[r.timestamp.hour].append(r)

        for hour, hour_records in by_hour.items():
            if len(hour_records) >= 3:
                approval_rate = len([r for r in hour_records if r.action == ApprovalAction.APPROVED]) / len(hour_records)
                profile.time_of_day_bias[hour] = approval_rate * 100

    def _determine_behavior_pattern(self, profile: ApproverProfile):
        """Determine primary and secondary behavior patterns"""

        patterns = []

        # Rubber stamper
        if profile.rubber_stamp_score > 70:
            patterns.append((RiskBehaviorPattern.RUBBER_STAMPER, profile.rubber_stamp_score))

        # Risk averse
        if profile.risk_awareness_score > 80 and profile.rejections > profile.approvals * 0.3:
            patterns.append((RiskBehaviorPattern.RISK_AVERSE, profile.risk_awareness_score))

        # Inconsistent
        if profile.consistency_score < 50:
            patterns.append((RiskBehaviorPattern.INCONSISTENT, 100 - profile.consistency_score))

        # Biased (check for significant variance in department/requestor treatment)
        if profile.department_bias:
            rates = list(profile.department_bias.values())
            if len(rates) > 1 and max(rates) - min(rates) > 30:
                patterns.append((RiskBehaviorPattern.BIASED, max(rates) - min(rates)))

        # Overwhelmed (high timeouts, high delegation)
        if profile.total_decisions > 0:
            overwhelm_score = (profile.timeouts / profile.total_decisions * 50 +
                              profile.delegations / profile.total_decisions * 50)
            if overwhelm_score > 30:
                patterns.append((RiskBehaviorPattern.OVERWHELMED, overwhelm_score))

        # Disengaged
        if profile.engagement_score < 40:
            patterns.append((RiskBehaviorPattern.DISENGAGED, 100 - profile.engagement_score))

        # Sort by confidence and assign
        patterns.sort(key=lambda x: x[1], reverse=True)

        if patterns:
            profile.primary_pattern = patterns[0][0]
            profile.pattern_confidence = patterns[0][1]
            profile.secondary_patterns = [p[0] for p in patterns[1:3]]
        else:
            profile.primary_pattern = RiskBehaviorPattern.NORMAL
            profile.pattern_confidence = 80.0

    def _generate_recommendations(self, profile: ApproverProfile):
        """Generate actionable recommendations"""

        profile.recommendations = []

        if profile.primary_pattern == RiskBehaviorPattern.RUBBER_STAMPER:
            profile.recommendations.append(
                "HIGH PRIORITY: Coaching required on approval responsibilities. "
                "Consider requiring comments for all high-risk approvals."
            )
            profile.recommendations.append(
                "Implement mandatory risk report review before approval."
            )

        if profile.primary_pattern == RiskBehaviorPattern.BIASED:
            profile.recommendations.append(
                "Review approval patterns for potential favoritism. "
                "Consider rotating approvers or adding secondary approval."
            )

        if profile.primary_pattern == RiskBehaviorPattern.OVERWHELMED:
            profile.recommendations.append(
                "Approver may have excessive workload. Consider "
                "delegating lower-risk approvals or adding team capacity."
            )

        if profile.primary_pattern == RiskBehaviorPattern.DISENGAGED:
            profile.recommendations.append(
                "Low engagement detected. Review if approver understands "
                "importance of role. Consider training or reassignment."
            )

        if profile.risk_awareness_score < 50:
            profile.recommendations.append(
                "Risk awareness training recommended. Approver may not "
                "fully understand risk implications of approvals."
            )

    def _check_for_anomalies(self, record: ApprovalRecord):
        """Check for anomalous approval behavior"""

        approver_records = [r for r in self.approval_records if r.approver_id == record.approver_id]
        if len(approver_records) < 10:
            return  # Not enough history

        # Anomaly 1: Sudden change in approval rate
        recent = approver_records[-10:]
        older = approver_records[-20:-10] if len(approver_records) >= 20 else []

        if older:
            recent_rate = len([r for r in recent if r.action == ApprovalAction.APPROVED]) / len(recent)
            older_rate = len([r for r in older if r.action == ApprovalAction.APPROVED]) / len(older)

            if abs(recent_rate - older_rate) > 0.3:
                self.anomalies.append(ApprovalAnomaly(
                    anomaly_id=f"ANOM-{len(self.anomalies)+1}",
                    approver_id=record.approver_id,
                    anomaly_type="approval_rate_change",
                    severity="medium",
                    description=f"Approval rate changed from {older_rate*100:.0f}% to {recent_rate*100:.0f}%",
                    evidence=[f"Recent 10: {recent_rate*100:.0f}%", f"Previous 10: {older_rate*100:.0f}%"],
                    detected_at=datetime.utcnow(),
                    related_approvals=[r.approval_id for r in recent],
                    recommended_action="Review recent approvals for quality"
                ))

        # Anomaly 2: Critical risk approved instantly
        if (record.risk_level == "critical" and
            record.action == ApprovalAction.APPROVED and
            record.decision_time_seconds < 30):
            self.anomalies.append(ApprovalAnomaly(
                anomaly_id=f"ANOM-{len(self.anomalies)+1}",
                approver_id=record.approver_id,
                anomaly_type="instant_critical_approval",
                severity="high",
                description="Critical risk item approved in under 30 seconds",
                evidence=[
                    f"Decision time: {record.decision_time_seconds}s",
                    f"Request: {record.request_id}",
                    f"Risk level: {record.risk_level}"
                ],
                detected_at=datetime.utcnow(),
                related_approvals=[record.approval_id],
                recommended_action="Immediate review of approval decision"
            ))

        # Anomaly 3: Bulk approvals (many in short time)
        last_hour = [
            r for r in approver_records
            if r.timestamp > datetime.utcnow() - timedelta(hours=1)
        ]
        if len(last_hour) > 20:
            self.anomalies.append(ApprovalAnomaly(
                anomaly_id=f"ANOM-{len(self.anomalies)+1}",
                approver_id=record.approver_id,
                anomaly_type="bulk_approvals",
                severity="medium",
                description=f"{len(last_hour)} approvals in last hour",
                evidence=[f"Count: {len(last_hour)}", "Possible batch processing"],
                detected_at=datetime.utcnow(),
                related_approvals=[r.approval_id for r in last_hour],
                recommended_action="Sample review of bulk approvals"
            ))

    def get_approver_profile(self, approver_id: str) -> Optional[ApproverProfile]:
        """Get detailed profile for an approver"""
        return self.approver_profiles.get(approver_id)

    def get_behavior_analytics_report(self) -> Dict:
        """Generate comprehensive behavior analytics report"""

        profiles = list(self.approver_profiles.values())

        if not profiles:
            return {"error": "No approval data available"}

        # Pattern distribution
        pattern_counts = defaultdict(int)
        for p in profiles:
            pattern_counts[p.primary_pattern.value] += 1

        # Risk concerns
        rubber_stampers = [p for p in profiles if p.rubber_stamp_score > 60]
        low_risk_awareness = [p for p in profiles if p.risk_awareness_score < 50]
        biased = [p for p in profiles if p.primary_pattern == RiskBehaviorPattern.BIASED]
        overwhelmed = [p for p in profiles if p.primary_pattern == RiskBehaviorPattern.OVERWHELMED]

        return {
            "summary": {
                "total_approvers_analyzed": len(profiles),
                "total_approvals_analyzed": sum(p.total_decisions for p in profiles),
                "rubber_stampers_identified": len(rubber_stampers),
                "low_risk_awareness": len(low_risk_awareness),
                "bias_concerns": len(biased),
                "overwhelmed_approvers": len(overwhelmed)
            },
            "pattern_distribution": dict(pattern_counts),
            "average_scores": {
                "rubber_stamp_score": round(statistics.mean([p.rubber_stamp_score for p in profiles]), 1),
                "risk_awareness_score": round(statistics.mean([p.risk_awareness_score for p in profiles]), 1),
                "consistency_score": round(statistics.mean([p.consistency_score for p in profiles]), 1),
                "engagement_score": round(statistics.mean([p.engagement_score for p in profiles]), 1)
            },
            "high_risk_approvers": [
                {
                    "approver_id": p.approver_id,
                    "approver_name": p.approver_name,
                    "primary_pattern": p.primary_pattern.value,
                    "rubber_stamp_score": round(p.rubber_stamp_score, 1),
                    "recommendations": p.recommendations
                }
                for p in rubber_stampers + biased
            ],
            "recent_anomalies": [
                {
                    "anomaly_id": a.anomaly_id,
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "description": a.description,
                    "approver_id": a.approver_id
                }
                for a in self.anomalies[-10:]
            ],
            "audit_conclusion": self._generate_audit_conclusion(profiles, rubber_stampers, biased)
        }

    def _generate_audit_conclusion(
        self,
        profiles: List[ApproverProfile],
        rubber_stampers: List[ApproverProfile],
        biased: List[ApproverProfile]
    ) -> str:
        """Generate audit conclusion on approval quality"""

        concern_count = len(rubber_stampers) + len(biased)
        total = len(profiles)

        if total == 0:
            return "Insufficient data for assessment."

        concern_ratio = concern_count / total

        if concern_ratio < 0.1:
            return (
                "Approval processes demonstrate STRONG governance. The majority of "
                "approvers show appropriate decision-making patterns with adequate "
                "risk awareness and engagement."
            )
        elif concern_ratio < 0.25:
            return (
                f"Approval governance is ADEQUATE with areas for improvement. "
                f"{concern_count} of {total} approvers ({concern_ratio*100:.0f}%) show "
                f"concerning patterns that should be addressed through training or process changes."
            )
        else:
            return (
                f"SIGNIFICANT GOVERNANCE CONCERNS identified. {concern_count} of {total} "
                f"approvers ({concern_ratio*100:.0f}%) demonstrate rubber-stamping, bias, "
                f"or other concerning patterns. Immediate action required to ensure "
                f"approvals are meaningful controls, not ceremonial checkboxes."
            )
