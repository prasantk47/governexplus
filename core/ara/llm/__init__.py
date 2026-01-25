# LLM-Based Explanation Module
# Human-grade explanations without losing audit safety

"""
LLM-Based Risk Explanation for GOVERNEX+.

LLM is used ONLY for summarization, never for decisions.

Area           | Deterministic | LLM
---------------|---------------|-----
Risk detection | ✅            | ❌
Risk scoring   | ✅            | ❌
Evidence       | ✅            | ❌
Explanation    | ❌            | ✅

This ensures audit safety while providing human-readable summaries.
"""

from .prompts import (
    RISK_SUMMARY_PROMPT,
    EXECUTIVE_NARRATIVE_PROMPT,
    REMEDIATION_GUIDANCE_PROMPT,
    AUDIT_SUMMARY_PROMPT,
)

from .summarizer import (
    RiskSummarizer,
    SummaryConfig,
    RiskSummaryResult,
)

from .narratives import (
    ExecutiveNarrativeGenerator,
    NarrativeConfig,
    ExecutiveNarrative,
    RiskStory,
)

__all__ = [
    # Prompts
    "RISK_SUMMARY_PROMPT",
    "EXECUTIVE_NARRATIVE_PROMPT",
    "REMEDIATION_GUIDANCE_PROMPT",
    "AUDIT_SUMMARY_PROMPT",
    # Summarizer
    "RiskSummarizer",
    "SummaryConfig",
    "RiskSummaryResult",
    # Narratives
    "ExecutiveNarrativeGenerator",
    "NarrativeConfig",
    "ExecutiveNarrative",
    "RiskStory",
]
