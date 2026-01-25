# Role Usage Analytics
# Evidence-based role analysis and cleanup recommendations

"""
Role Usage Analytics for GOVERNEX+.

Provides:
- Tcode execution counts per role
- Rarely/never used permissions
- Time-based usage patterns
- Business vs off-hours activity
- Evidence-based cleanup suggestions
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import logging

from .models import Role, Permission, PermissionType

logger = logging.getLogger(__name__)


class UsageLevel(Enum):
    """Usage classification levels."""
    HEAVILY_USED = "HEAVILY_USED"  # > 100 uses/month
    REGULARLY_USED = "REGULARLY_USED"  # 10-100 uses/month
    OCCASIONALLY_USED = "OCCASIONALLY_USED"  # 1-10 uses/month
    RARELY_USED = "RARELY_USED"  # < 1/month but used
    NEVER_USED = "NEVER_USED"  # Never used


@dataclass
class PermissionUsage:
    """Usage metrics for a single permission."""
    permission_id: str
    permission_value: str
    permission_type: PermissionType

    # Counts
    total_executions: int = 0
    unique_users: int = 0
    unique_days: int = 0

    # Time analysis
    first_used: Optional[datetime] = None
    last_used: Optional[datetime] = None
    days_since_last_use: int = 0

    # Pattern
    avg_daily_usage: float = 0.0
    peak_usage_hour: int = 0
    business_hours_ratio: float = 0.0  # % during 8am-6pm

    # Classification
    usage_level: UsageLevel = UsageLevel.NEVER_USED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permission_id": self.permission_id,
            "permission_value": self.permission_value,
            "permission_type": self.permission_type.value,
            "total_executions": self.total_executions,
            "unique_users": self.unique_users,
            "unique_days": self.unique_days,
            "first_used": self.first_used.isoformat() if self.first_used else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "days_since_last_use": self.days_since_last_use,
            "avg_daily_usage": round(self.avg_daily_usage, 2),
            "peak_usage_hour": self.peak_usage_hour,
            "business_hours_ratio": round(self.business_hours_ratio, 4),
            "usage_level": self.usage_level.value,
        }


@dataclass
class UsagePattern:
    """Usage pattern for a role."""
    role_id: str

    # Time distribution
    hourly_distribution: Dict[int, int] = field(default_factory=dict)  # hour -> count
    daily_distribution: Dict[int, int] = field(default_factory=dict)  # weekday -> count
    monthly_trend: Dict[str, int] = field(default_factory=dict)  # YYYY-MM -> count

    # Patterns
    is_business_hours_only: bool = True
    has_weekend_activity: bool = False
    has_after_hours_activity: bool = False

    # Anomalies
    unusual_hours: List[int] = field(default_factory=list)
    usage_spikes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "hourly_distribution": self.hourly_distribution,
            "daily_distribution": self.daily_distribution,
            "monthly_trend": self.monthly_trend,
            "is_business_hours_only": self.is_business_hours_only,
            "has_weekend_activity": self.has_weekend_activity,
            "has_after_hours_activity": self.has_after_hours_activity,
            "unusual_hours": self.unusual_hours,
            "usage_spikes": self.usage_spikes,
        }


@dataclass
class UsageTrend:
    """Usage trend over time."""
    role_id: str
    period_days: int

    # Trend
    trend_direction: str = "stable"  # "increasing", "stable", "decreasing"
    trend_slope: float = 0.0
    trend_confidence: float = 0.0

    # Comparison
    current_period_usage: int = 0
    previous_period_usage: int = 0
    change_percent: float = 0.0

    # Prediction
    predicted_next_period: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "period_days": self.period_days,
            "trend_direction": self.trend_direction,
            "trend_slope": round(self.trend_slope, 4),
            "trend_confidence": round(self.trend_confidence, 4),
            "current_period_usage": self.current_period_usage,
            "previous_period_usage": self.previous_period_usage,
            "change_percent": round(self.change_percent, 2),
            "predicted_next_period": self.predicted_next_period,
        }


@dataclass
class UsageMetrics:
    """Complete usage metrics for a role."""
    role_id: str
    role_name: str
    analysis_period_days: int = 90

    # Summary
    total_executions: int = 0
    unique_users: int = 0
    active_days: int = 0

    # Permission breakdown
    total_permissions: int = 0
    used_permissions: int = 0
    unused_permissions: int = 0
    rarely_used_permissions: int = 0

    # Usage density
    usage_density: float = 0.0  # % of permissions actively used

    # Permission details
    permission_usage: List[PermissionUsage] = field(default_factory=list)

    # Patterns
    usage_pattern: Optional[UsagePattern] = None
    usage_trend: Optional[UsageTrend] = None

    # Cleanup recommendations
    permissions_to_review: List[str] = field(default_factory=list)
    permissions_to_remove: List[str] = field(default_factory=list)
    cleanup_priority: str = "LOW"  # "LOW", "MEDIUM", "HIGH"

    # Timestamps
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "analysis_period_days": self.analysis_period_days,
            "total_executions": self.total_executions,
            "unique_users": self.unique_users,
            "active_days": self.active_days,
            "total_permissions": self.total_permissions,
            "used_permissions": self.used_permissions,
            "unused_permissions": self.unused_permissions,
            "rarely_used_permissions": self.rarely_used_permissions,
            "usage_density": round(self.usage_density, 4),
            "permission_usage": [p.to_dict() for p in self.permission_usage],
            "usage_pattern": self.usage_pattern.to_dict() if self.usage_pattern else None,
            "usage_trend": self.usage_trend.to_dict() if self.usage_trend else None,
            "permissions_to_review": self.permissions_to_review,
            "permissions_to_remove": self.permissions_to_remove,
            "cleanup_priority": self.cleanup_priority,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class RoleUsageAnalyzer:
    """
    Analyzes role usage patterns.

    Key capabilities:
    - Permission-level usage tracking
    - Time-based pattern analysis
    - Trend detection
    - Cleanup recommendations
    """

    # Thresholds
    RARELY_USED_THRESHOLD = 5  # < 5 uses in period
    NEVER_USED_DAYS = 90  # Not used in 90 days
    BUSINESS_HOURS_START = 8
    BUSINESS_HOURS_END = 18

    def __init__(self):
        """Initialize analyzer."""
        self._usage_cache: Dict[str, UsageMetrics] = {}

    def analyze_role(
        self,
        role: Role,
        usage_data: List[Dict[str, Any]],
        period_days: int = 90
    ) -> UsageMetrics:
        """
        Analyze usage for a role.

        Args:
            role: Role to analyze
            usage_data: List of usage records with fields:
                - permission_id
                - user_id
                - timestamp
                - tcode (optional)
            period_days: Analysis period

        Returns:
            UsageMetrics with complete analysis
        """
        cutoff = datetime.now() - timedelta(days=period_days)

        # Filter to analysis period
        recent_usage = [
            u for u in usage_data
            if datetime.fromisoformat(u["timestamp"]) >= cutoff
        ]

        metrics = UsageMetrics(
            role_id=role.role_id,
            role_name=role.role_name,
            analysis_period_days=period_days,
            total_permissions=len(role.permissions),
        )

        # Aggregate usage by permission
        permission_stats = self._aggregate_by_permission(recent_usage)

        # Analyze each permission
        for permission in role.permissions:
            perm_usage = self._analyze_permission(
                permission, permission_stats.get(permission.permission_id, [])
            )
            metrics.permission_usage.append(perm_usage)

        # Calculate summary metrics
        metrics.used_permissions = sum(
            1 for p in metrics.permission_usage
            if p.usage_level != UsageLevel.NEVER_USED
        )
        metrics.unused_permissions = sum(
            1 for p in metrics.permission_usage
            if p.usage_level == UsageLevel.NEVER_USED
        )
        metrics.rarely_used_permissions = sum(
            1 for p in metrics.permission_usage
            if p.usage_level == UsageLevel.RARELY_USED
        )

        # Usage density
        if metrics.total_permissions > 0:
            metrics.usage_density = metrics.used_permissions / metrics.total_permissions

        # Total executions and unique users
        metrics.total_executions = sum(p.total_executions for p in metrics.permission_usage)
        all_users = set()
        for u in recent_usage:
            all_users.add(u.get("user_id"))
        metrics.unique_users = len(all_users)

        # Active days
        active_dates = set()
        for u in recent_usage:
            ts = datetime.fromisoformat(u["timestamp"])
            active_dates.add(ts.date())
        metrics.active_days = len(active_dates)

        # Analyze patterns
        metrics.usage_pattern = self._analyze_pattern(role.role_id, recent_usage)
        metrics.usage_trend = self._analyze_trend(role.role_id, usage_data, period_days)

        # Generate recommendations
        self._generate_recommendations(metrics)

        # Cache result
        self._usage_cache[role.role_id] = metrics

        return metrics

    def _aggregate_by_permission(
        self,
        usage_data: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate usage records by permission."""
        result = defaultdict(list)
        for record in usage_data:
            perm_id = record.get("permission_id", record.get("tcode", ""))
            result[perm_id].append(record)
        return dict(result)

    def _analyze_permission(
        self,
        permission: Permission,
        usage_records: List[Dict[str, Any]]
    ) -> PermissionUsage:
        """Analyze usage for a single permission."""
        perm_usage = PermissionUsage(
            permission_id=permission.permission_id,
            permission_value=permission.value,
            permission_type=permission.permission_type,
        )

        if not usage_records:
            perm_usage.usage_level = UsageLevel.NEVER_USED
            return perm_usage

        # Basic counts
        perm_usage.total_executions = len(usage_records)
        unique_users = set(r.get("user_id") for r in usage_records)
        perm_usage.unique_users = len(unique_users)

        # Time analysis
        timestamps = [
            datetime.fromisoformat(r["timestamp"])
            for r in usage_records
        ]
        timestamps.sort()

        perm_usage.first_used = timestamps[0]
        perm_usage.last_used = timestamps[-1]
        perm_usage.days_since_last_use = (datetime.now() - timestamps[-1]).days

        # Unique days
        unique_dates = set(ts.date() for ts in timestamps)
        perm_usage.unique_days = len(unique_dates)

        # Average daily usage
        if perm_usage.unique_days > 0:
            perm_usage.avg_daily_usage = perm_usage.total_executions / perm_usage.unique_days

        # Business hours analysis
        business_hours = sum(
            1 for ts in timestamps
            if self.BUSINESS_HOURS_START <= ts.hour < self.BUSINESS_HOURS_END
        )
        perm_usage.business_hours_ratio = business_hours / len(timestamps)

        # Peak hour
        hour_counts = defaultdict(int)
        for ts in timestamps:
            hour_counts[ts.hour] += 1
        if hour_counts:
            perm_usage.peak_usage_hour = max(hour_counts.items(), key=lambda x: x[1])[0]

        # Classify usage level
        monthly_rate = perm_usage.total_executions / 3  # 90 days = 3 months

        if monthly_rate > 100:
            perm_usage.usage_level = UsageLevel.HEAVILY_USED
        elif monthly_rate > 10:
            perm_usage.usage_level = UsageLevel.REGULARLY_USED
        elif monthly_rate > 1:
            perm_usage.usage_level = UsageLevel.OCCASIONALLY_USED
        elif perm_usage.total_executions > 0:
            perm_usage.usage_level = UsageLevel.RARELY_USED
        else:
            perm_usage.usage_level = UsageLevel.NEVER_USED

        return perm_usage

    def _analyze_pattern(
        self,
        role_id: str,
        usage_records: List[Dict[str, Any]]
    ) -> UsagePattern:
        """Analyze usage patterns."""
        pattern = UsagePattern(role_id=role_id)

        if not usage_records:
            return pattern

        timestamps = [
            datetime.fromisoformat(r["timestamp"])
            for r in usage_records
        ]

        # Hourly distribution
        for ts in timestamps:
            pattern.hourly_distribution[ts.hour] = \
                pattern.hourly_distribution.get(ts.hour, 0) + 1

        # Daily distribution (0=Monday, 6=Sunday)
        for ts in timestamps:
            pattern.daily_distribution[ts.weekday()] = \
                pattern.daily_distribution.get(ts.weekday(), 0) + 1

        # Monthly trend
        for ts in timestamps:
            month_key = ts.strftime("%Y-%m")
            pattern.monthly_trend[month_key] = \
                pattern.monthly_trend.get(month_key, 0) + 1

        # Pattern flags
        after_hours = sum(
            count for hour, count in pattern.hourly_distribution.items()
            if hour < self.BUSINESS_HOURS_START or hour >= self.BUSINESS_HOURS_END
        )
        pattern.has_after_hours_activity = after_hours > 0

        weekend = sum(
            count for day, count in pattern.daily_distribution.items()
            if day >= 5  # Saturday, Sunday
        )
        pattern.has_weekend_activity = weekend > 0

        # Business hours only if <5% outside
        total = len(timestamps)
        if total > 0:
            pattern.is_business_hours_only = (after_hours / total) < 0.05

        # Unusual hours (significant activity outside 6am-10pm)
        for hour, count in pattern.hourly_distribution.items():
            if (hour < 6 or hour >= 22) and count > total * 0.02:
                pattern.unusual_hours.append(hour)

        return pattern

    def _analyze_trend(
        self,
        role_id: str,
        usage_data: List[Dict[str, Any]],
        period_days: int
    ) -> UsageTrend:
        """Analyze usage trend over time."""
        trend = UsageTrend(role_id=role_id, period_days=period_days)

        now = datetime.now()
        current_start = now - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)

        # Split into current and previous period
        current_period = [
            u for u in usage_data
            if datetime.fromisoformat(u["timestamp"]) >= current_start
        ]
        previous_period = [
            u for u in usage_data
            if previous_start <= datetime.fromisoformat(u["timestamp"]) < current_start
        ]

        trend.current_period_usage = len(current_period)
        trend.previous_period_usage = len(previous_period)

        # Calculate change
        if trend.previous_period_usage > 0:
            trend.change_percent = (
                (trend.current_period_usage - trend.previous_period_usage)
                / trend.previous_period_usage
            ) * 100
        elif trend.current_period_usage > 0:
            trend.change_percent = 100

        # Determine direction
        if trend.change_percent > 10:
            trend.trend_direction = "increasing"
        elif trend.change_percent < -10:
            trend.trend_direction = "decreasing"
        else:
            trend.trend_direction = "stable"

        # Simple prediction
        trend.predicted_next_period = int(
            trend.current_period_usage * (1 + trend.change_percent / 100)
        )

        return trend

    def _generate_recommendations(self, metrics: UsageMetrics):
        """Generate cleanup recommendations."""
        # Permissions never used - recommend removal
        for perm in metrics.permission_usage:
            if perm.usage_level == UsageLevel.NEVER_USED:
                metrics.permissions_to_remove.append(perm.permission_id)
            elif perm.usage_level == UsageLevel.RARELY_USED:
                metrics.permissions_to_review.append(perm.permission_id)
            elif perm.days_since_last_use > self.NEVER_USED_DAYS:
                metrics.permissions_to_review.append(perm.permission_id)

        # Determine priority
        unused_ratio = metrics.unused_permissions / max(metrics.total_permissions, 1)

        if unused_ratio > 0.5:
            metrics.cleanup_priority = "HIGH"
        elif unused_ratio > 0.25:
            metrics.cleanup_priority = "MEDIUM"
        else:
            metrics.cleanup_priority = "LOW"

    def get_unused_permissions(self, role_id: str) -> List[PermissionUsage]:
        """Get unused permissions for a role."""
        metrics = self._usage_cache.get(role_id)
        if not metrics:
            return []

        return [
            p for p in metrics.permission_usage
            if p.usage_level == UsageLevel.NEVER_USED
        ]

    def get_rarely_used_permissions(self, role_id: str) -> List[PermissionUsage]:
        """Get rarely used permissions for a role."""
        metrics = self._usage_cache.get(role_id)
        if not metrics:
            return []

        return [
            p for p in metrics.permission_usage
            if p.usage_level == UsageLevel.RARELY_USED
        ]

    def compare_roles(
        self,
        role1_id: str,
        role2_id: str
    ) -> Dict[str, Any]:
        """Compare usage between two roles."""
        m1 = self._usage_cache.get(role1_id)
        m2 = self._usage_cache.get(role2_id)

        if not m1 or not m2:
            return {"error": "Role metrics not available"}

        return {
            "role1": {
                "role_id": role1_id,
                "usage_density": m1.usage_density,
                "total_executions": m1.total_executions,
                "unused_permissions": m1.unused_permissions,
            },
            "role2": {
                "role_id": role2_id,
                "usage_density": m2.usage_density,
                "total_executions": m2.total_executions,
                "unused_permissions": m2.unused_permissions,
            },
            "comparison": {
                "density_difference": m1.usage_density - m2.usage_density,
                "more_active": role1_id if m1.total_executions > m2.total_executions else role2_id,
                "cleaner": role1_id if m1.unused_permissions < m2.unused_permissions else role2_id,
            }
        }
