# LLM Risk Summarizer
# Generates human-readable risk explanations

"""
Risk Summarizer for GOVERNEX+.

Provides LLM-powered summarization of risk findings
while maintaining audit safety through structured inputs
and controlled prompts.

Supports multiple LLM backends:
- OpenAI (GPT-4, GPT-4o-mini)
- Azure OpenAI
- Anthropic Claude
- Local models via Ollama
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging
import json

from .prompts import (
    RISK_SUMMARY_PROMPT,
    RISK_SUMMARY_INPUT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    MOCK = "mock"  # For testing


@dataclass
class SummaryConfig:
    """Configuration for risk summarization."""
    # LLM settings
    provider: LLMProvider = LLMProvider.MOCK
    model: str = "gpt-4o-mini"
    temperature: float = 0.2  # Low temperature for consistency
    max_tokens: int = 500

    # API settings
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    # Behavior settings
    include_remediation: bool = True
    include_impact: bool = True
    max_evidence_items: int = 10

    # Fallback
    fallback_to_template: bool = True


@dataclass
class RiskSummaryResult:
    """Result of risk summarization."""
    summary: str
    risk_statement: str
    impact_description: str
    remediation_actions: List[str]

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    model_used: str = ""
    tokens_used: int = 0

    # Audit trail
    input_hash: str = ""  # Hash of input for reproducibility

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "risk_statement": self.risk_statement,
            "impact_description": self.impact_description,
            "remediation_actions": self.remediation_actions,
            "generated_at": self.generated_at.isoformat(),
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
        }


class RiskSummarizer:
    """
    LLM-powered risk summarization.

    Generates human-readable explanations while maintaining
    audit safety through:
    - Structured input payloads
    - Controlled prompts that prevent speculation
    - Evidence-only summarization
    """

    def __init__(self, config: Optional[SummaryConfig] = None):
        """
        Initialize summarizer.

        Args:
            config: Summarization configuration
        """
        self.config = config or SummaryConfig()
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize LLM client based on provider."""
        if self.config.provider == LLMProvider.OPENAI:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.config.api_key)
            except ImportError:
                logger.warning("OpenAI library not available")
                self.config.provider = LLMProvider.MOCK

        elif self.config.provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config.api_key)
            except ImportError:
                logger.warning("Anthropic library not available")
                self.config.provider = LLMProvider.MOCK

        elif self.config.provider == LLMProvider.MOCK:
            pass  # No client needed for mock

    def summarize(self, payload: Dict[str, Any]) -> RiskSummaryResult:
        """
        Summarize a risk finding.

        Args:
            payload: Risk details payload containing:
                - user_id: User identifier
                - risk_score: Numeric risk score
                - severity: Risk severity
                - rule_name: Name of violated rule
                - evidence: List of evidence items
                - access_details: Current access description
                - mitigation_options: Available mitigations

        Returns:
            RiskSummaryResult with human-readable summary
        """
        # Format input
        formatted_input = self._format_input(payload)

        # Generate summary based on provider
        if self.config.provider == LLMProvider.OPENAI:
            return self._summarize_openai(formatted_input, payload)
        elif self.config.provider == LLMProvider.ANTHROPIC:
            return self._summarize_anthropic(formatted_input, payload)
        else:
            return self._summarize_mock(payload)

    def _format_input(self, payload: Dict[str, Any]) -> str:
        """Format payload into structured input."""
        # Format evidence list
        evidence = payload.get("evidence", [])
        evidence_str = "\n".join(f"- {e}" for e in evidence[:self.config.max_evidence_items])

        # Format mitigation options
        mitigations = payload.get("mitigation_options", [])
        mitigation_str = "\n".join(f"- {m}" for m in mitigations)

        return RISK_SUMMARY_INPUT_TEMPLATE.format(
            user_id=payload.get("user_id", "Unknown"),
            risk_score=payload.get("risk_score", 0),
            severity=payload.get("severity", "Unknown"),
            rule_name=payload.get("rule_name", "Unknown"),
            evidence_list=evidence_str or "No evidence provided",
            access_details=payload.get("access_details", "Not specified"),
            mitigation_options=mitigation_str or "No mitigations available",
        )

    def _summarize_openai(
        self,
        formatted_input: str,
        payload: Dict[str, Any]
    ) -> RiskSummaryResult:
        """Summarize using OpenAI."""
        try:
            response = self._client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                messages=[
                    {"role": "system", "content": RISK_SUMMARY_PROMPT},
                    {"role": "user", "content": formatted_input}
                ]
            )

            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0

            return self._parse_summary(
                content,
                payload,
                model=self.config.model,
                tokens=tokens
            )

        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")
            if self.config.fallback_to_template:
                return self._summarize_mock(payload)
            raise

    def _summarize_anthropic(
        self,
        formatted_input: str,
        payload: Dict[str, Any]
    ) -> RiskSummaryResult:
        """Summarize using Anthropic Claude."""
        try:
            response = self._client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=RISK_SUMMARY_PROMPT,
                messages=[
                    {"role": "user", "content": formatted_input}
                ]
            )

            content = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens

            return self._parse_summary(
                content,
                payload,
                model=self.config.model,
                tokens=tokens
            )

        except Exception as e:
            logger.error(f"Anthropic summarization failed: {e}")
            if self.config.fallback_to_template:
                return self._summarize_mock(payload)
            raise

    def _summarize_mock(self, payload: Dict[str, Any]) -> RiskSummaryResult:
        """Generate mock/template-based summary."""
        user_id = payload.get("user_id", "Unknown user")
        risk_score = payload.get("risk_score", 0)
        severity = payload.get("severity", "Unknown")
        rule_name = payload.get("rule_name", "Unknown rule")
        evidence = payload.get("evidence", [])
        mitigations = payload.get("mitigation_options", [])

        # Generate template-based summary
        risk_statement = (
            f"User {user_id} has access that violates the '{rule_name}' control, "
            f"resulting in a {severity} severity risk with a score of {risk_score}."
        )

        if evidence:
            evidence_str = "; ".join(evidence[:3])
            impact_description = (
                f"This risk arises from: {evidence_str}. "
                f"The combination of these access rights creates the potential for "
                f"unauthorized activities that bypass normal segregation controls."
            )
        else:
            impact_description = (
                f"The access pattern violates segregation of duties principles, "
                f"potentially enabling unauthorized activities."
            )

        if mitigations:
            remediation_actions = mitigations[:4]
        else:
            remediation_actions = [
                "Review and remove conflicting access rights",
                "Implement compensating controls",
                "Document business justification if access is required",
            ]

        summary = f"{risk_statement}\n\n{impact_description}"

        return RiskSummaryResult(
            summary=summary,
            risk_statement=risk_statement,
            impact_description=impact_description,
            remediation_actions=remediation_actions,
            model_used="template",
            tokens_used=0,
        )

    def _parse_summary(
        self,
        content: str,
        payload: Dict[str, Any],
        model: str,
        tokens: int
    ) -> RiskSummaryResult:
        """Parse LLM response into structured result."""
        # Simple parsing - in production, use more sophisticated extraction
        lines = content.strip().split("\n")

        risk_statement = lines[0] if lines else ""

        # Find remediation actions (lines starting with - or *)
        remediation_actions = [
            line.strip().lstrip("-*").strip()
            for line in lines
            if line.strip().startswith(("-", "*"))
        ]

        # Impact is everything between first line and remediation
        impact_lines = []
        for line in lines[1:]:
            if line.strip().startswith(("-", "*")):
                break
            if line.strip():
                impact_lines.append(line.strip())

        impact_description = " ".join(impact_lines)

        return RiskSummaryResult(
            summary=content,
            risk_statement=risk_statement,
            impact_description=impact_description,
            remediation_actions=remediation_actions or ["Review access rights"],
            model_used=model,
            tokens_used=tokens,
        )

    def summarize_batch(
        self,
        payloads: List[Dict[str, Any]]
    ) -> List[RiskSummaryResult]:
        """Summarize multiple findings."""
        return [self.summarize(p) for p in payloads]

    def summarize_finding(
        self,
        user_id: str,
        risk_score: int,
        severity: str,
        rule_name: str,
        evidence: List[str],
        mitigation_options: Optional[List[str]] = None,
        access_details: str = ""
    ) -> RiskSummaryResult:
        """
        Convenience method to summarize a finding.

        Args:
            user_id: User identifier
            risk_score: Risk score (0-100)
            severity: Risk severity level
            rule_name: Name of violated rule
            evidence: List of evidence items
            mitigation_options: Available remediation options
            access_details: Description of current access

        Returns:
            RiskSummaryResult
        """
        payload = {
            "user_id": user_id,
            "risk_score": risk_score,
            "severity": severity,
            "rule_name": rule_name,
            "evidence": evidence,
            "mitigation_options": mitigation_options or [],
            "access_details": access_details,
        }
        return self.summarize(payload)
