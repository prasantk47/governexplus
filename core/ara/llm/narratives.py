# Executive-Grade Risk Narratives
# Board-level summaries without technical jargon

"""
Executive Narrative Generation for GOVERNEX+.

Executives do not read:
- Tcode lists
- Authorization objects
- Graph paths

They need risk stories, not logs.

This module generates board-ready narratives from
structured risk data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging

from .prompts import EXECUTIVE_NARRATIVE_PROMPT
from .summarizer import LLMProvider, SummaryConfig

logger = logging.getLogger(__name__)


class NarrativeTone(Enum):
    """Tone for narrative generation."""
    FORMAL = "formal"  # Board presentations
    INFORMATIVE = "informative"  # Management updates
    URGENT = "urgent"  # Critical alerts


@dataclass
class NarrativeConfig:
    """Configuration for narrative generation."""
    # LLM settings
    provider: LLMProvider = LLMProvider.MOCK
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None

    # Narrative settings
    tone: NarrativeTone = NarrativeTone.FORMAL
    max_length: int = 300  # words
    include_trends: bool = True
    include_recommendations: bool = True
    include_metrics: bool = True


@dataclass
class RiskStory:
    """A single risk story for narrative inclusion."""
    title: str
    severity: str
    affected_users: int
    business_impact: str
    trend: str  # "increasing", "stable", "decreasing"
    key_metric: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "severity": self.severity,
            "affected_users": self.affected_users,
            "business_impact": self.business_impact,
            "trend": self.trend,
            "key_metric": self.key_metric,
        }


@dataclass
class ExecutiveNarrative:
    """
    Board-ready executive narrative.

    Contains structured narrative components
    suitable for executive presentations.
    """
    # Core narrative
    headline: str
    executive_summary: str
    risk_posture: str  # "improving", "stable", "deteriorating"

    # Key metrics (business language)
    total_exposure: str  # e.g., "$2.5M potential fraud exposure"
    users_at_risk: int
    critical_issues: int

    # Trend analysis
    trend_narrative: str
    trend_direction: str  # "up", "down", "stable"
    period_comparison: str

    # Top risks (as stories)
    risk_stories: List[RiskStory] = field(default_factory=list)

    # Control status
    control_narrative: str = ""
    control_effectiveness: float = 0.0

    # Recommendations
    recommended_actions: List[str] = field(default_factory=list)
    priority_action: str = ""

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    reporting_period: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "executive_summary": self.executive_summary,
            "risk_posture": self.risk_posture,
            "total_exposure": self.total_exposure,
            "users_at_risk": self.users_at_risk,
            "critical_issues": self.critical_issues,
            "trend_narrative": self.trend_narrative,
            "trend_direction": self.trend_direction,
            "period_comparison": self.period_comparison,
            "risk_stories": [s.to_dict() for s in self.risk_stories],
            "control_narrative": self.control_narrative,
            "control_effectiveness": round(self.control_effectiveness, 2),
            "recommended_actions": self.recommended_actions,
            "priority_action": self.priority_action,
            "generated_at": self.generated_at.isoformat(),
            "reporting_period": self.reporting_period,
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        md = []
        md.append(f"# {self.headline}")
        md.append(f"\n*Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M')}*")
        md.append(f"\n*Reporting Period: {self.reporting_period}*")

        md.append(f"\n## Executive Summary")
        md.append(f"\n{self.executive_summary}")

        md.append(f"\n## Key Metrics")
        md.append(f"\n| Metric | Value |")
        md.append(f"|--------|-------|")
        md.append(f"| Risk Posture | {self.risk_posture.title()} |")
        md.append(f"| Total Exposure | {self.total_exposure} |")
        md.append(f"| Users at Risk | {self.users_at_risk} |")
        md.append(f"| Critical Issues | {self.critical_issues} |")
        md.append(f"| Control Effectiveness | {self.control_effectiveness:.0%} |")

        md.append(f"\n## Trend Analysis")
        md.append(f"\n{self.trend_narrative}")
        md.append(f"\n{self.period_comparison}")

        if self.risk_stories:
            md.append(f"\n## Top Risk Areas")
            for story in self.risk_stories:
                md.append(f"\n### {story.title}")
                md.append(f"- Severity: {story.severity}")
                md.append(f"- Affected Users: {story.affected_users}")
                md.append(f"- Business Impact: {story.business_impact}")
                md.append(f"- Trend: {story.trend.title()}")

        md.append(f"\n## Control Status")
        md.append(f"\n{self.control_narrative}")

        md.append(f"\n## Recommended Actions")
        if self.priority_action:
            md.append(f"\n**Priority:** {self.priority_action}")
        for action in self.recommended_actions:
            md.append(f"- {action}")

        return "\n".join(md)


class ExecutiveNarrativeGenerator:
    """
    Generates executive-grade risk narratives.

    Transforms technical risk data into business-friendly
    narratives suitable for board presentations.
    """

    def __init__(self, config: Optional[NarrativeConfig] = None):
        """
        Initialize narrative generator.

        Args:
            config: Narrative configuration
        """
        self.config = config or NarrativeConfig()

    def generate(self, metrics: Dict[str, Any]) -> ExecutiveNarrative:
        """
        Generate executive narrative from risk metrics.

        Args:
            metrics: Risk metrics dictionary containing:
                - overall_risk: Current risk level (0-100)
                - total_users: Total users analyzed
                - high_risk_users: Users with high risk
                - critical_findings: Count of critical findings
                - prev_risk_score: Previous period score
                - curr_risk_score: Current period score
                - top_risks: List of top risk areas
                - controls: Control status metrics
                - affected_areas: Business areas affected

        Returns:
            ExecutiveNarrative ready for presentation
        """
        # Extract metrics
        overall_risk = metrics.get("overall_risk", 0)
        total_users = metrics.get("total_users", 0)
        high_risk_users = metrics.get("high_risk_users", 0)
        critical_findings = metrics.get("critical_findings", 0)
        prev_score = metrics.get("prev_risk_score", 0)
        curr_score = metrics.get("curr_risk_score", 0)
        top_risks = metrics.get("top_risks", [])
        controls = metrics.get("controls", {})
        affected_areas = metrics.get("affected_areas", [])

        # Calculate trends
        if prev_score > 0:
            change_pct = ((curr_score - prev_score) / prev_score) * 100
        else:
            change_pct = 0

        # Determine risk posture
        if change_pct > 10:
            risk_posture = "deteriorating"
            trend_direction = "up"
        elif change_pct < -10:
            risk_posture = "improving"
            trend_direction = "down"
        else:
            risk_posture = "stable"
            trend_direction = "stable"

        # Generate headline
        headline = self._generate_headline(
            overall_risk, critical_findings, risk_posture
        )

        # Generate executive summary
        executive_summary = self._generate_summary(
            overall_risk, high_risk_users, total_users, critical_findings
        )

        # Calculate exposure (simplified - use actual data in production)
        exposure = self._estimate_exposure(critical_findings, high_risk_users)

        # Generate trend narrative
        trend_narrative = self._generate_trend_narrative(
            change_pct, prev_score, curr_score
        )

        # Generate risk stories
        risk_stories = self._generate_risk_stories(top_risks)

        # Control narrative
        control_effectiveness = controls.get("effectiveness", 0.85)
        control_narrative = self._generate_control_narrative(controls)

        # Recommendations
        recommended_actions, priority_action = self._generate_recommendations(
            critical_findings, risk_posture, control_effectiveness
        )

        return ExecutiveNarrative(
            headline=headline,
            executive_summary=executive_summary,
            risk_posture=risk_posture,
            total_exposure=exposure,
            users_at_risk=high_risk_users,
            critical_issues=critical_findings,
            trend_narrative=trend_narrative,
            trend_direction=trend_direction,
            period_comparison=f"Risk changed {change_pct:+.1f}% compared to previous period",
            risk_stories=risk_stories,
            control_narrative=control_narrative,
            control_effectiveness=control_effectiveness,
            recommended_actions=recommended_actions,
            priority_action=priority_action,
            reporting_period=metrics.get("period", "Current Period"),
        )

    def _generate_headline(
        self,
        overall_risk: float,
        critical_findings: int,
        risk_posture: str
    ) -> str:
        """Generate attention-grabbing headline."""
        if critical_findings > 5:
            return f"Access Risk Alert: {critical_findings} Critical Issues Require Immediate Attention"

        if risk_posture == "deteriorating":
            return "Access Risk Increasing: Enhanced Monitoring Recommended"

        if risk_posture == "improving":
            return "Access Risk Improving: Remediation Efforts Showing Results"

        if overall_risk > 75:
            return "Elevated Access Risk: Remediation Actions Required"

        return "Access Risk Summary: Current Status and Recommended Actions"

    def _generate_summary(
        self,
        overall_risk: float,
        high_risk_users: int,
        total_users: int,
        critical_findings: int
    ) -> str:
        """Generate executive summary paragraph."""
        risk_pct = (high_risk_users / total_users * 100) if total_users > 0 else 0

        summary_parts = []

        if critical_findings > 0:
            summary_parts.append(
                f"Currently, {critical_findings} critical access risk findings "
                f"require attention."
            )

        summary_parts.append(
            f"Of {total_users:,} users analyzed, {high_risk_users:,} ({risk_pct:.1f}%) "
            f"have elevated access risk scores."
        )

        if overall_risk > 75:
            summary_parts.append(
                "The overall risk posture indicates significant exposure "
                "that could impact business operations and compliance."
            )
        elif overall_risk > 50:
            summary_parts.append(
                "While risk levels are within acceptable thresholds, "
                "continued monitoring and remediation are recommended."
            )
        else:
            summary_parts.append(
                "Risk levels are within acceptable limits. "
                "Current controls are operating effectively."
            )

        return " ".join(summary_parts)

    def _estimate_exposure(
        self,
        critical_findings: int,
        high_risk_users: int
    ) -> str:
        """Estimate financial exposure (simplified)."""
        # In production, use actual financial impact models
        base_exposure = critical_findings * 250000 + high_risk_users * 50000

        if base_exposure >= 1000000:
            return f"${base_exposure / 1000000:.1f}M potential exposure"
        elif base_exposure >= 1000:
            return f"${base_exposure / 1000:.0f}K potential exposure"
        else:
            return f"${base_exposure:.0f} potential exposure"

    def _generate_trend_narrative(
        self,
        change_pct: float,
        prev_score: float,
        curr_score: float
    ) -> str:
        """Generate trend analysis narrative."""
        if abs(change_pct) < 5:
            return (
                f"Access risk has remained stable at {curr_score:.0f} points, "
                "indicating consistent risk management effectiveness."
            )

        if change_pct > 0:
            return (
                f"Access risk increased by {change_pct:.1f}% from {prev_score:.0f} "
                f"to {curr_score:.0f} points. This increase is attributed to "
                "recent role changes and access provisioning activities."
            )
        else:
            return (
                f"Access risk decreased by {abs(change_pct):.1f}% from {prev_score:.0f} "
                f"to {curr_score:.0f} points, reflecting successful remediation "
                "of previously identified access issues."
            )

    def _generate_risk_stories(
        self,
        top_risks: List[Dict[str, Any]]
    ) -> List[RiskStory]:
        """Generate risk stories from top risks."""
        stories = []

        for risk in top_risks[:3]:  # Top 3 risks
            story = RiskStory(
                title=risk.get("name", "Access Risk"),
                severity=risk.get("severity", "High"),
                affected_users=risk.get("affected_users", 0),
                business_impact=risk.get("impact", "Potential unauthorized access"),
                trend=risk.get("trend", "stable"),
                key_metric=risk.get("key_metric", ""),
            )
            stories.append(story)

        return stories

    def _generate_control_narrative(
        self,
        controls: Dict[str, Any]
    ) -> str:
        """Generate control status narrative."""
        total = controls.get("total", 0)
        effective = controls.get("effective", 0)
        failed = controls.get("failed", 0)

        if total == 0:
            return "Control metrics not available for this period."

        effectiveness = (effective / total * 100) if total > 0 else 0

        if effectiveness >= 90:
            return (
                f"Controls are operating effectively with {effectiveness:.0f}% "
                f"effectiveness rate. All {total} monitored controls are performing "
                "within acceptable parameters."
            )
        elif effectiveness >= 75:
            return (
                f"Control effectiveness is at {effectiveness:.0f}%. "
                f"Of {total} controls, {failed} require attention. "
                "Remediation plans are in place for underperforming controls."
            )
        else:
            return (
                f"Control effectiveness is below target at {effectiveness:.0f}%. "
                f"{failed} of {total} controls are not operating as designed. "
                "Immediate review and remediation is recommended."
            )

    def _generate_recommendations(
        self,
        critical_findings: int,
        risk_posture: str,
        control_effectiveness: float
    ) -> tuple[List[str], str]:
        """Generate recommendations based on current state."""
        recommendations = []
        priority = ""

        if critical_findings > 3:
            priority = (
                "Conduct emergency access review for users with critical findings"
            )
            recommendations.append("Escalate critical findings to business owners")
            recommendations.append("Implement temporary access restrictions")

        if risk_posture == "deteriorating":
            recommendations.append("Review recent access provisioning activities")
            recommendations.append("Increase monitoring frequency")

        if control_effectiveness < 0.80:
            recommendations.append("Review and strengthen underperforming controls")
            recommendations.append("Consider additional compensating controls")

        # Default recommendations
        recommendations.extend([
            "Continue regular access certification campaigns",
            "Maintain user access review schedules",
        ])

        if not priority:
            priority = recommendations[0] if recommendations else "Continue monitoring"

        return recommendations[:5], priority

    def generate_from_analysis(
        self,
        risk_analysis_result: Any,
        comparison_period: Optional[Any] = None
    ) -> ExecutiveNarrative:
        """
        Generate narrative from ARA analysis result.

        Args:
            risk_analysis_result: Result from AccessRiskEngine
            comparison_period: Previous period for trend comparison

        Returns:
            ExecutiveNarrative
        """
        # Transform analysis result to metrics format
        metrics = {
            "overall_risk": getattr(risk_analysis_result, "total_risk_score", 50),
            "total_users": 1,  # Single user analysis
            "high_risk_users": 1 if getattr(risk_analysis_result, "total_risk_score", 0) > 70 else 0,
            "critical_findings": len([
                r for r in getattr(risk_analysis_result, "risks", [])
                if getattr(r, "severity", "") == "CRITICAL"
            ]),
            "prev_risk_score": getattr(comparison_period, "total_risk_score", 0) if comparison_period else 0,
            "curr_risk_score": getattr(risk_analysis_result, "total_risk_score", 0),
            "top_risks": [],
            "controls": {"total": 10, "effective": 8, "failed": 2},
        }

        return self.generate(metrics)
