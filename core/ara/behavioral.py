# Behavioral Risk Analysis
# Usage-based and behavioral anomaly detection for GOVERNEX+

"""
Behavioral Risk Analysis for Access Risk Analysis.

Provides:
- Usage-based risk assessment
- Transaction behavior analysis
- Peer deviation detection
- Anomaly scoring
- Risk trend analysis
"""

from typing import List, Optional, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import statistics

from .models import (
    Risk,
    RiskSeverity,
    RiskCategory,
    RiskType,
    RiskStatus,
    UserContext,
    RiskContext,
)

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Usage metrics for a user."""
    user_id: str
    period_start: datetime
    period_end: datetime

    # Transaction metrics
    total_transactions: int = 0
    unique_tcodes: int = 0
    sensitive_transactions: int = 0
    restricted_transactions: int = 0

    # Time distribution
    transactions_by_hour: Dict[int, int] = field(default_factory=dict)
    off_hours_transactions: int = 0
    weekend_transactions: int = 0

    # Tcode frequency
    tcode_counts: Dict[str, int] = field(default_factory=dict)
    top_tcodes: List[Tuple[str, int]] = field(default_factory=list)

    # Risk-related usage
    sod_conflict_executions: int = 0
    unused_sensitive_access: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "total_transactions": self.total_transactions,
            "unique_tcodes": self.unique_tcodes,
            "sensitive_transactions": self.sensitive_transactions,
            "restricted_transactions": self.restricted_transactions,
            "off_hours_transactions": self.off_hours_transactions,
            "weekend_transactions": self.weekend_transactions,
            "top_tcodes": self.top_tcodes[:10],
        }


@dataclass
class PeerGroup:
    """Peer group for comparison analysis."""
    group_id: str
    name: str
    members: List[str] = field(default_factory=list)

    # Aggregate metrics
    avg_transactions: float = 0
    avg_unique_tcodes: float = 0
    std_transactions: float = 0
    std_unique_tcodes: float = 0
    common_tcodes: Set[str] = field(default_factory=set)


@dataclass
class BehavioralAnomaly:
    """Detected behavioral anomaly."""
    anomaly_id: str = ""
    user_id: str = ""
    anomaly_type: str = ""  # volume, timing, pattern, peer_deviation
    description: str = ""
    severity: RiskSeverity = RiskSeverity.MEDIUM

    # Details
    observed_value: Any = None
    expected_value: Any = None
    deviation: float = 0.0

    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "user_id": self.user_id,
            "anomaly_type": self.anomaly_type,
            "description": self.description,
            "severity": self.severity.value,
            "observed_value": self.observed_value,
            "expected_value": self.expected_value,
            "deviation": self.deviation,
            "detected_at": self.detected_at.isoformat(),
        }


class BehavioralAnalyzer:
    """
    Behavioral risk analyzer.

    Analyzes usage patterns and detects anomalies.
    """

    # Sensitive tcodes for tracking
    SENSITIVE_TCODES = {
        "SE38", "SE80", "SE16", "SE16N", "SU01", "PFCG",
        "SM59", "STMS", "SM30", "FB01", "F110", "XK01",
    }

    # Off-hours definition (before 6 AM or after 8 PM)
    BUSINESS_HOURS_START = 6
    BUSINESS_HOURS_END = 20

    def __init__(self):
        # Baseline data (in production, load from database)
        self.user_baselines: Dict[str, UsageMetrics] = {}
        self.peer_groups: Dict[str, PeerGroup] = {}

    def analyze_usage(
        self,
        user_id: str,
        transactions: List[Dict[str, Any]],
        assigned_access: Dict[str, Any],
        period_days: int = 30
    ) -> Tuple[UsageMetrics, List[Risk]]:
        """
        Analyze user's transaction usage.

        Args:
            user_id: User identifier
            transactions: List of transaction records
            assigned_access: User's assigned access
            period_days: Analysis period

        Returns:
            Tuple of (usage metrics, detected risks)
        """
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)

        # Calculate metrics
        metrics = self._calculate_metrics(user_id, transactions, period_start, period_end)

        # Detect usage-based risks
        risks = []

        # 1. Unused access risk
        unused_risks = self._detect_unused_access(
            user_id, assigned_access, metrics
        )
        risks.extend(unused_risks)

        # 2. Off-hours activity risk
        if metrics.off_hours_transactions > 10:
            risk = Risk(
                risk_type=RiskType.BEHAVIORAL_ANOMALY,
                severity=RiskSeverity.MEDIUM,
                category=RiskCategory.SECURITY,
                user_id=user_id,
                title="Significant Off-Hours Activity",
                description=f"User has {metrics.off_hours_transactions} transactions outside business hours",
                base_score=50,
            )
            risks.append(risk)

        # 3. Excessive sensitive access usage
        if metrics.sensitive_transactions > metrics.total_transactions * 0.3:
            risk = Risk(
                risk_type=RiskType.BEHAVIORAL_ANOMALY,
                severity=RiskSeverity.HIGH,
                category=RiskCategory.SECURITY,
                user_id=user_id,
                title="High Sensitive Transaction Ratio",
                description=f"{metrics.sensitive_transactions} of {metrics.total_transactions} transactions are sensitive",
                base_score=65,
            )
            risks.append(risk)

        return metrics, risks

    def detect_anomalies(
        self,
        user_id: str,
        current_metrics: Optional[UsageMetrics] = None,
        context: Optional[RiskContext] = None
    ) -> List[BehavioralAnomaly]:
        """
        Detect behavioral anomalies by comparing to baseline.

        Args:
            user_id: User identifier
            current_metrics: Current period metrics (optional, uses baseline if not provided)
            context: Risk context

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Get baseline
        baseline = self.user_baselines.get(user_id)
        if not baseline:
            return anomalies  # No baseline to compare

        # If no current metrics provided, cannot compare
        if not current_metrics:
            return anomalies

        # 1. Volume anomaly
        if baseline.total_transactions > 0:
            volume_ratio = current_metrics.total_transactions / baseline.total_transactions
            if volume_ratio > 3.0:
                anomalies.append(BehavioralAnomaly(
                    anomaly_id=f"VOL_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                    user_id=user_id,
                    anomaly_type="volume",
                    description="Transaction volume significantly higher than baseline",
                    severity=RiskSeverity.MEDIUM,
                    observed_value=current_metrics.total_transactions,
                    expected_value=baseline.total_transactions,
                    deviation=volume_ratio,
                ))

        # 2. New tcode usage
        baseline_tcodes = set(baseline.tcode_counts.keys())
        current_tcodes = set(current_metrics.tcode_counts.keys())
        new_tcodes = current_tcodes - baseline_tcodes

        new_sensitive = new_tcodes & self.SENSITIVE_TCODES
        if new_sensitive:
            anomalies.append(BehavioralAnomaly(
                anomaly_id=f"NEW_SENS_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                anomaly_type="pattern",
                description=f"New sensitive transactions executed: {', '.join(new_sensitive)}",
                severity=RiskSeverity.HIGH,
                observed_value=list(new_sensitive),
                expected_value=[],
            ))

        # 3. Timing anomaly
        if baseline.off_hours_transactions == 0 and current_metrics.off_hours_transactions > 5:
            anomalies.append(BehavioralAnomaly(
                anomaly_id=f"TIMING_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                anomaly_type="timing",
                description="Off-hours activity where none existed before",
                severity=RiskSeverity.MEDIUM,
                observed_value=current_metrics.off_hours_transactions,
                expected_value=0,
            ))

        return anomalies

    def analyze_peer_deviation(
        self,
        user_id: str,
        metrics: UsageMetrics,
        peer_group: PeerGroup
    ) -> List[BehavioralAnomaly]:
        """
        Analyze deviation from peer group behavior.

        Args:
            user_id: User identifier
            metrics: User's metrics
            peer_group: Peer group for comparison

        Returns:
            List of peer deviation anomalies
        """
        anomalies = []

        if not peer_group.members or peer_group.std_transactions == 0:
            return anomalies

        # Calculate z-scores
        z_transactions = (
            (metrics.total_transactions - peer_group.avg_transactions)
            / peer_group.std_transactions
        )

        z_tcodes = 0
        if peer_group.std_unique_tcodes > 0:
            z_tcodes = (
                (metrics.unique_tcodes - peer_group.avg_unique_tcodes)
                / peer_group.std_unique_tcodes
            )

        # Flag significant deviations (> 2 standard deviations)
        if abs(z_transactions) > 2:
            direction = "higher" if z_transactions > 0 else "lower"
            anomalies.append(BehavioralAnomaly(
                anomaly_id=f"PEER_VOL_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                anomaly_type="peer_deviation",
                description=f"Transaction volume significantly {direction} than peers",
                severity=RiskSeverity.MEDIUM if abs(z_transactions) < 3 else RiskSeverity.HIGH,
                observed_value=metrics.total_transactions,
                expected_value=peer_group.avg_transactions,
                deviation=z_transactions,
            ))

        if abs(z_tcodes) > 2:
            direction = "more" if z_tcodes > 0 else "fewer"
            anomalies.append(BehavioralAnomaly(
                anomaly_id=f"PEER_TCODE_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                anomaly_type="peer_deviation",
                description=f"Uses significantly {direction} unique transactions than peers",
                severity=RiskSeverity.LOW,
                observed_value=metrics.unique_tcodes,
                expected_value=peer_group.avg_unique_tcodes,
                deviation=z_tcodes,
            ))

        # Check for unusual tcodes (not used by any peer)
        unusual_tcodes = set(metrics.tcode_counts.keys()) - peer_group.common_tcodes
        sensitive_unusual = unusual_tcodes & self.SENSITIVE_TCODES

        if sensitive_unusual:
            anomalies.append(BehavioralAnomaly(
                anomaly_id=f"PEER_SENS_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                anomaly_type="peer_deviation",
                description=f"Uses sensitive transactions not used by any peer: {', '.join(sensitive_unusual)}",
                severity=RiskSeverity.HIGH,
                observed_value=list(sensitive_unusual),
            ))

        return anomalies

    def record_usage(self, metrics: UsageMetrics):
        """
        Record usage metrics for a user.

        Args:
            metrics: Usage metrics to record
        """
        self.user_baselines[metrics.user_id] = metrics
        logger.debug(f"Recorded usage for user {metrics.user_id}")

    def calculate_identity_risk_score(
        self,
        user_id: str,
        assigned_risks: Optional[List[Risk]] = None,
        behavioral_anomalies: Optional[List[BehavioralAnomaly]] = None,
        usage_metrics: Optional[UsageMetrics] = None
    ) -> Dict[str, Any]:
        """
        Calculate aggregate identity risk score.

        Args:
            user_id: User identifier
            assigned_risks: Risks from access analysis
            behavioral_anomalies: Detected behavioral anomalies
            usage_metrics: Usage metrics

        Returns:
            Identity risk score and breakdown
        """
        # Initialize defaults
        assigned_risks = assigned_risks or []
        behavioral_anomalies = behavioral_anomalies or []

        # Base score from assigned risks
        if assigned_risks:
            access_score = sum(r.final_score for r in assigned_risks) / len(assigned_risks)
        else:
            access_score = 0

        # Behavioral score from anomalies
        behavioral_score = 0
        for anomaly in behavioral_anomalies:
            behavioral_score += anomaly.severity.score_weight * 30

        behavioral_score = min(100, behavioral_score)

        # Usage score
        usage_score = 0
        if usage_metrics:
            # Penalize high sensitive transaction ratio
            if usage_metrics.total_transactions > 0:
                sensitive_ratio = usage_metrics.sensitive_transactions / usage_metrics.total_transactions
                usage_score += sensitive_ratio * 40

            # Penalize off-hours activity
            if usage_metrics.total_transactions > 0:
                off_hours_ratio = usage_metrics.off_hours_transactions / usage_metrics.total_transactions
                usage_score += off_hours_ratio * 30

            # Penalize unused sensitive access
            usage_score += len(usage_metrics.unused_sensitive_access) * 5

        usage_score = min(100, usage_score)

        # Combined identity score (weighted)
        identity_score = int(
            access_score * 0.5 +
            behavioral_score * 0.3 +
            usage_score * 0.2
        )

        return {
            "user_id": user_id,
            "identity_risk_score": identity_score,
            "breakdown": {
                "access_risk_score": int(access_score),
                "behavioral_score": int(behavioral_score),
                "usage_score": int(usage_score),
            },
            "risk_count": len(assigned_risks),
            "anomaly_count": len(behavioral_anomalies),
            "risk_level": RiskSeverity.from_score(identity_score).value,
            "calculated_at": datetime.now().isoformat(),
        }

    def update_baseline(
        self,
        user_id: str,
        metrics: UsageMetrics
    ):
        """Update user's behavioral baseline."""
        self.user_baselines[user_id] = metrics
        logger.debug(f"Updated baseline for user {user_id}")

    def create_peer_group(
        self,
        group_id: str,
        name: str,
        member_metrics: List[UsageMetrics]
    ) -> PeerGroup:
        """
        Create peer group from member metrics.

        Args:
            group_id: Group identifier
            name: Group name
            member_metrics: Metrics for all group members

        Returns:
            Configured PeerGroup
        """
        group = PeerGroup(
            group_id=group_id,
            name=name,
            members=[m.user_id for m in member_metrics],
        )

        if member_metrics:
            transactions = [m.total_transactions for m in member_metrics]
            tcodes = [m.unique_tcodes for m in member_metrics]

            group.avg_transactions = statistics.mean(transactions)
            group.avg_unique_tcodes = statistics.mean(tcodes)

            if len(member_metrics) > 1:
                group.std_transactions = statistics.stdev(transactions)
                group.std_unique_tcodes = statistics.stdev(tcodes)

            # Find common tcodes (used by > 50% of members)
            tcode_member_count = defaultdict(int)
            for m in member_metrics:
                for tcode in m.tcode_counts.keys():
                    tcode_member_count[tcode] += 1

            threshold = len(member_metrics) * 0.5
            group.common_tcodes = {
                tcode for tcode, count in tcode_member_count.items()
                if count >= threshold
            }

        self.peer_groups[group_id] = group
        return group

    def _calculate_metrics(
        self,
        user_id: str,
        transactions: List[Dict[str, Any]],
        period_start: datetime,
        period_end: datetime
    ) -> UsageMetrics:
        """Calculate usage metrics from transactions."""
        metrics = UsageMetrics(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )

        tcode_counts = defaultdict(int)
        hour_counts = defaultdict(int)

        for txn in transactions:
            tcode = txn.get("tcode", "")
            if not tcode:
                continue

            metrics.total_transactions += 1
            tcode_counts[tcode] += 1

            # Check if sensitive
            if tcode in self.SENSITIVE_TCODES:
                metrics.sensitive_transactions += 1

            # Check timing
            txn_time = txn.get("datetime") or txn.get("time")
            if txn_time:
                if isinstance(txn_time, str):
                    try:
                        if "T" in txn_time:
                            txn_dt = datetime.fromisoformat(txn_time)
                        else:
                            hour = int(txn_time[:2])
                            txn_dt = datetime.now().replace(hour=hour)
                    except:
                        continue
                else:
                    txn_dt = txn_time

                hour = txn_dt.hour
                hour_counts[hour] += 1

                # Off-hours check
                if hour < self.BUSINESS_HOURS_START or hour >= self.BUSINESS_HOURS_END:
                    metrics.off_hours_transactions += 1

                # Weekend check
                if txn_dt.weekday() >= 5:
                    metrics.weekend_transactions += 1

        metrics.tcode_counts = dict(tcode_counts)
        metrics.unique_tcodes = len(tcode_counts)
        metrics.transactions_by_hour = dict(hour_counts)
        metrics.top_tcodes = sorted(
            tcode_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]

        return metrics

    def _detect_unused_access(
        self,
        user_id: str,
        assigned_access: Dict[str, Any],
        metrics: UsageMetrics
    ) -> List[Risk]:
        """Detect unused access risks."""
        risks = []

        assigned_tcodes = set(assigned_access.get("tcodes", []))
        used_tcodes = set(metrics.tcode_counts.keys())

        # Find unused sensitive tcodes
        unused = assigned_tcodes - used_tcodes
        unused_sensitive = unused & self.SENSITIVE_TCODES

        if unused_sensitive:
            metrics.unused_sensitive_access = list(unused_sensitive)

            risk = Risk(
                risk_type=RiskType.UNUSED_ACCESS,
                severity=RiskSeverity.HIGH,
                category=RiskCategory.COMPLIANCE,
                user_id=user_id,
                title="Unused Sensitive Access",
                description=f"User has {len(unused_sensitive)} sensitive transactions never used",
                conflicting_tcodes=list(unused_sensitive),
                base_score=60,
            )
            risks.append(risk)

        # High unused ratio
        if assigned_tcodes and len(used_tcodes) > 0:
            unused_ratio = len(unused) / len(assigned_tcodes)
            if unused_ratio > 0.7:
                risk = Risk(
                    risk_type=RiskType.EXCESSIVE_ACCESS,
                    severity=RiskSeverity.MEDIUM,
                    category=RiskCategory.COMPLIANCE,
                    user_id=user_id,
                    title="Excessive Unused Access",
                    description=f"{int(unused_ratio * 100)}% of assigned access is unused",
                    base_score=45,
                )
                risks.append(risk)

        return risks
