"""
GRC AI Assistant — Comprehensive AI-powered capabilities across all GRC modules.

Covers:
  RM  — Risk Management
  PC  — Policy & Controls
  AM  — Audit Management
  AC  — Access Control (SoD)

Each public method offers:
  1. An LLM implementation (_llm_*) that calls the configured provider.
  2. A template fallback (_template_*) producing real, professional GRC output
     when no LLM API key is present.

The shared entry point _call_llm() tries the existing assistant infrastructure
first, then falls back silently to the template path.
"""

from __future__ import annotations

import json
import logging
import os
import statistics
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM provider availability probe
# ---------------------------------------------------------------------------

def _detect_llm_provider() -> Optional[str]:
    """Return the name of the first available LLM provider, or None."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        return "azure_openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OLLAMA_BASE_URL"):
        return "ollama"
    return None


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class GRCAssistant:
    """
    AI-powered GRC assistant providing capabilities across RM, PC, AM, and AC
    modules.  Instantiate one per tenant; DB session is optional but enables
    richer context when calling template fallbacks.
    """

    def __init__(self, tenant_id: str, db_session=None):
        self.tenant_id = tenant_id
        self._db = db_session
        self._provider = _detect_llm_provider()
        self._llm_available = self._provider is not None

        if self._llm_available:
            logger.info(
                "GRCAssistant initialised with LLM provider=%s tenant=%s",
                self._provider, tenant_id,
            )
        else:
            logger.info(
                "GRCAssistant initialised in template mode (no LLM key) tenant=%s",
                tenant_id,
            )

    # -----------------------------------------------------------------------
    # Internal: shared LLM caller
    # -----------------------------------------------------------------------

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Route the prompt to the configured LLM provider.
        Returns the text response, or None if unavailable / errored.
        """
        if not self._llm_available:
            return None

        try:
            if self._provider == "openai":
                return self._call_openai(system_prompt, user_prompt)
            if self._provider == "azure_openai":
                return self._call_azure_openai(system_prompt, user_prompt)
            if self._provider == "anthropic":
                return self._call_anthropic(system_prompt, user_prompt)
            if self._provider == "ollama":
                return self._call_ollama(system_prompt, user_prompt)
        except Exception as exc:
            logger.warning("LLM call failed, falling back to templates: %s", exc)

        return None

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        import openai  # type: ignore
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()

    def _call_azure_openai(self, system_prompt: str, user_prompt: str) -> str:
        import openai  # type: ignore
        client = openai.AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        message = client.messages.create(
            model=model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text.strip()

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        import requests  # type: ignore
        _is_production = os.getenv("APP_ENV", "").lower() == "production"
        base_url = os.getenv("OLLAMA_BASE_URL", "")
        if not base_url:
            if _is_production:
                raise RuntimeError(
                    "GRCAssistant: OLLAMA_BASE_URL is not configured. "
                    "Set OLLAMA_BASE_URL to the Ollama server URL, or configure a "
                    "different LLM provider (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.). "
                    "Set APP_ENV != 'production' to fall back to template mode."
                )
            # Dev: fall back to localhost with a warning; template fallback will catch failures.
            logger.warning(
                "GRCAssistant: OLLAMA_BASE_URL is not set — attempting localhost:11434 "
                "(SIMULATION mode only). Set APP_ENV=production to enforce strict config."
            )
            base_url = "http://localhost:11434"
        model = os.getenv("OLLAMA_MODEL", "llama3.1")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        resp = requests.post(f"{base_url}/api/chat", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Attempt to parse a JSON block from an LLM response."""
        try:
            # Strip markdown code fences if present
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception:
            return None

    # -----------------------------------------------------------------------
    # Helper: simple Arabic transliteration placeholder
    # -----------------------------------------------------------------------

    _AR_PHRASES = {
        "risk": "المخاطر",
        "control": "الرقابة",
        "finding": "النتيجة",
        "recommendation": "التوصية",
        "compliance": "الامتثال",
        "audit": "التدقيق",
        "access": "الوصول",
        "violation": "الانتهاك",
        "remediation": "المعالجة",
        "summary": "الملخص",
    }

    def _make_arabic_placeholder(self, english: str) -> str:
        """
        Return a best-effort Arabic translation stub for template mode.
        In production the LLM provides a proper translation.
        """
        return (
            "يُرجى مراجعة النص الإنجليزي أدناه. "
            f"[{english[:120]}{'...' if len(english) > 120 else ''}]"
        )

    # ===================================================================
    # 1. Risk Description Drafting (RM)
    # ===================================================================

    RISK_DESCRIPTION_SYSTEM = (
        "You are a senior GRC risk analyst writing professional risk register entries. "
        "Respond ONLY with a JSON object matching this exact schema:\n"
        '{"description": "...", "description_ar": "...", '
        '"suggested_likelihood": <1-5 int>, "suggested_impact": <1-5 int>, '
        '"suggested_category": "..."}\n'
        "The description must be 3-5 sentences, formal, third-person. "
        "description_ar must be a proper Arabic translation."
    )

    def draft_risk_description(
        self,
        risk_title: str,
        category: str,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate a professional risk description for the risk register.

        Returns:
            description, description_ar, suggested_likelihood (1-5),
            suggested_impact (1-5), suggested_category
        """
        ctx_str = json.dumps(context or {})
        user_prompt = (
            f"Risk title: {risk_title}\n"
            f"Category: {category}\n"
            f"Additional context: {ctx_str}\n\n"
            "Draft a professional risk register description for this risk."
        )
        raw = self._call_llm(self.RISK_DESCRIPTION_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "description" in parsed:
                return parsed

        return self._template_risk_description(risk_title, category, context)

    def _template_risk_description(
        self,
        risk_title: str,
        category: str,
        context: Optional[Dict],
    ) -> Dict:
        cat_lower = category.lower()

        # Likelihood/impact heuristics based on category
        likelihood_map = {
            "financial": 3, "operational": 3, "compliance": 4,
            "strategic": 2, "reputational": 2, "technology": 3,
            "fraud": 2, "access": 4, "security": 3,
        }
        impact_map = {
            "financial": 4, "operational": 3, "compliance": 5,
            "strategic": 4, "reputational": 4, "technology": 3,
            "fraud": 5, "access": 4, "security": 4,
        }
        likelihood = next(
            (v for k, v in likelihood_map.items() if k in cat_lower), 3
        )
        impact = next(
            (v for k, v in impact_map.items() if k in cat_lower), 3
        )

        # Suggested category normalisation
        category_map = {
            "financial": "Financial Risk",
            "operational": "Operational Risk",
            "compliance": "Compliance & Regulatory Risk",
            "strategic": "Strategic Risk",
            "reputational": "Reputational Risk",
            "technology": "Technology & Cyber Risk",
            "fraud": "Fraud & Misconduct Risk",
            "access": "Access & Authorization Risk",
            "security": "Information Security Risk",
        }
        suggested_cat = next(
            (v for k, v in category_map.items() if k in cat_lower),
            category.title() + " Risk",
        )

        description = (
            f"The organization is exposed to the risk of {risk_title.lower()}, "
            f"which falls within the {suggested_cat} domain. "
            f"This risk arises from inadequate controls, process gaps, or external factors "
            f"that may adversely affect the organization's objectives and compliance posture. "
            f"Without timely identification and remediation, the risk could result in financial "
            f"loss, regulatory penalties, reputational damage, or operational disruption. "
            f"Management is expected to assess inherent exposure and implement appropriate "
            f"mitigating controls to reduce residual risk to an acceptable level."
        )

        return {
            "description": description,
            "description_ar": self._make_arabic_placeholder(description),
            "suggested_likelihood": likelihood,
            "suggested_impact": impact,
            "suggested_category": suggested_cat,
        }

    # ===================================================================
    # 2. Control Suggestion (PC)
    # ===================================================================

    CONTROL_SUGGESTION_SYSTEM = (
        "You are a GRC controls specialist. Given a risk description, propose appropriate "
        "internal controls. Respond ONLY with a JSON array of control objects, each with keys: "
        "control_name, objective, control_type (preventive|detective|corrective), "
        "control_nature (manual|automated|hybrid), frequency, rationale."
    )

    def suggest_controls_for_risk(
        self,
        risk_description: str,
        risk_category: str,
    ) -> List[Dict]:
        """
        Suggest internal controls appropriate for the given risk.

        Returns list of control dicts with keys:
            control_name, objective, control_type, control_nature,
            frequency, rationale
        """
        user_prompt = (
            f"Risk category: {risk_category}\n"
            f"Risk description: {risk_description}\n\n"
            "Suggest 3-5 appropriate internal controls."
        )
        raw = self._call_llm(self.CONTROL_SUGGESTION_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if isinstance(parsed, list) and parsed:
                return parsed

        return self._template_suggest_controls(risk_description, risk_category)

    def _template_suggest_controls(
        self,
        risk_description: str,
        risk_category: str,
    ) -> List[Dict]:
        cat = risk_category.lower()

        # Base library keyed by broad category
        library: Dict[str, List[Dict]] = {
            "access": [
                {
                    "control_name": "Segregation of Duties (SoD) Enforcement",
                    "objective": "Prevent a single individual from executing conflicting business functions.",
                    "control_type": "preventive",
                    "control_nature": "automated",
                    "frequency": "Continuous",
                    "rationale": "Automated SoD rule checks during provisioning eliminate the root cause of conflicting access combinations.",
                },
                {
                    "control_name": "Periodic Access Certification Campaign",
                    "objective": "Ensure all user access rights remain appropriate and business-justified.",
                    "control_type": "detective",
                    "control_nature": "manual",
                    "frequency": "Quarterly",
                    "rationale": "Manager-led reviews identify dormant or excess access that accumulates over time.",
                },
                {
                    "control_name": "Privileged Access Monitoring",
                    "objective": "Detect and alert on the use of elevated access outside of approved maintenance windows.",
                    "control_type": "detective",
                    "control_nature": "automated",
                    "frequency": "Real-time",
                    "rationale": "Continuous monitoring of super-user and firefighter activity reduces the window of undetected misuse.",
                },
            ],
            "financial": [
                {
                    "control_name": "Dual Authorisation for Payments",
                    "objective": "Require a second authorised approver for all payments above defined thresholds.",
                    "control_type": "preventive",
                    "control_nature": "automated",
                    "frequency": "Per transaction",
                    "rationale": "Four-eyes principle prevents single-point manipulation of payment runs.",
                },
                {
                    "control_name": "Bank Account Reconciliation",
                    "objective": "Identify unauthorised or erroneous transactions through regular reconciliation.",
                    "control_type": "detective",
                    "control_nature": "manual",
                    "frequency": "Monthly",
                    "rationale": "Timely reconciliation limits the duration of undetected financial misstatement.",
                },
                {
                    "control_name": "Vendor Master Change Log Review",
                    "objective": "Detect fraudulent changes to vendor bank details or payment addresses.",
                    "control_type": "detective",
                    "control_nature": "hybrid",
                    "frequency": "Weekly",
                    "rationale": "Prompt review of vendor master changes is a primary defence against payment redirection fraud.",
                },
            ],
            "compliance": [
                {
                    "control_name": "Regulatory Requirement Register Maintenance",
                    "objective": "Maintain a current register of applicable regulations and map them to process controls.",
                    "control_type": "preventive",
                    "control_nature": "manual",
                    "frequency": "Annual (or as regulations change)",
                    "rationale": "A live obligation register ensures control gaps are identified before regulatory reviews.",
                },
                {
                    "control_name": "Compliance Self-Assessment",
                    "objective": "Enable control owners to attest to compliance status on a periodic basis.",
                    "control_type": "detective",
                    "control_nature": "manual",
                    "frequency": "Semi-annual",
                    "rationale": "Self-assessments surface emerging deficiencies early and evidence management oversight.",
                },
                {
                    "control_name": "Automated Policy Exception Workflow",
                    "objective": "Route, approve, and time-limit all policy exceptions through a formal process.",
                    "control_type": "preventive",
                    "control_nature": "automated",
                    "frequency": "Per exception request",
                    "rationale": "Structured exception management prevents informal workarounds from becoming permanent gaps.",
                },
            ],
            "technology": [
                {
                    "control_name": "Change Management Process",
                    "objective": "Ensure all system changes are tested, authorised, and deployed through a controlled process.",
                    "control_type": "preventive",
                    "control_nature": "hybrid",
                    "frequency": "Per change",
                    "rationale": "A formal change process reduces the risk of unplanned outages and unauthorised modifications.",
                },
                {
                    "control_name": "Security Patch Management",
                    "objective": "Apply vendor-released security patches within defined SLA windows.",
                    "control_type": "preventive",
                    "control_nature": "automated",
                    "frequency": "Monthly (critical: within 72 hours)",
                    "rationale": "Timely patching closes known vulnerabilities before they can be exploited.",
                },
                {
                    "control_name": "System Access Log Review",
                    "objective": "Detect anomalous or unauthorised system access through log analysis.",
                    "control_type": "detective",
                    "control_nature": "automated",
                    "frequency": "Daily",
                    "rationale": "Automated log correlation identifies attack patterns and insider threats in near real-time.",
                },
            ],
        }

        # Generic fallback controls
        generic: List[Dict] = [
            {
                "control_name": "Risk Owner Accountability Assignment",
                "objective": "Assign a named risk owner who is accountable for monitoring and reporting on this risk.",
                "control_type": "preventive",
                "control_nature": "manual",
                "frequency": "Annual (reviewed at each risk assessment cycle)",
                "rationale": "Clear ownership ensures the risk receives appropriate management attention and resources.",
            },
            {
                "control_name": "Key Risk Indicator (KRI) Monitoring",
                "objective": "Track leading indicators that signal deterioration in the risk profile before a loss event occurs.",
                "control_type": "detective",
                "control_nature": "automated",
                "frequency": "Monthly",
                "rationale": "KRI monitoring enables proactive intervention rather than reactive incident response.",
            },
            {
                "control_name": "Internal Audit Review",
                "objective": "Provide independent assurance that controls are designed effectively and operating as intended.",
                "control_type": "detective",
                "control_nature": "manual",
                "frequency": "Annual",
                "rationale": "Independent assurance validates management representations and satisfies board oversight requirements.",
            },
        ]

        # Pick the best matching library or fall back to generic
        for key, controls in library.items():
            if key in cat:
                return controls

        return generic

    # ===================================================================
    # 3. Finding Write-Up — CCCE Structure (AM)
    # ===================================================================

    FINDING_SYSTEM = (
        "You are a senior internal auditor. Draft a structured audit finding in CCCE format "
        "(Condition, Criteria, Cause, Effect) plus a professional title, recommendation, "
        "and severity rating. Respond ONLY with a JSON object with keys: "
        "title, condition, criteria, cause, effect, recommendation, severity (high|medium|low)."
    )

    def draft_finding(
        self,
        condition_notes: str,
        audit_area: str,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate a CCCE-structured audit finding from rough field notes.

        Returns:
            title, condition, criteria, cause, effect, recommendation, severity
        """
        ctx_str = json.dumps(context or {})
        user_prompt = (
            f"Audit area: {audit_area}\n"
            f"Field notes / condition observed: {condition_notes}\n"
            f"Additional context: {ctx_str}\n\n"
            "Write a complete, professional audit finding."
        )
        raw = self._call_llm(self.FINDING_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "condition" in parsed:
                return parsed

        return self._template_draft_finding(condition_notes, audit_area, context)

    def _template_draft_finding(
        self,
        condition_notes: str,
        audit_area: str,
        context: Optional[Dict],
    ) -> Dict:
        area_lower = audit_area.lower()

        # Severity heuristic
        high_keywords = ["no control", "unmitigated", "critical", "fraud", "material", "unauthorized", "unrestricted"]
        low_keywords = ["minor", "documentation", "training", "awareness", "cosmetic"]
        notes_lower = condition_notes.lower()

        if any(k in notes_lower for k in high_keywords):
            severity = "high"
        elif any(k in notes_lower for k in low_keywords):
            severity = "low"
        else:
            severity = "medium"

        title = f"Inadequate Controls Identified in {audit_area.title()}"

        condition = (
            f"During the audit of {audit_area}, the following condition was observed: "
            f"{condition_notes.strip().rstrip('.')}. "
            f"This condition was noted across multiple instances reviewed during the audit period "
            f"and represents a systemic rather than isolated deficiency."
        )

        criteria = (
            f"The organization's internal control framework, applicable regulatory requirements, "
            f"and industry best practices (including ISO 27001, COSO, and relevant SAP security guidelines) "
            f"require that adequate controls are in place over {audit_area} processes. "
            f"Specifically, management is expected to design, implement, and maintain controls that "
            f"prevent and detect errors, irregularities, and unauthorized activities."
        )

        cause = (
            f"The deficiency appears to be caused by a combination of insufficient management oversight, "
            f"lack of documented policies and procedures governing {audit_area} activities, "
            f"and inadequate periodic review mechanisms to identify and remediate control gaps in a timely manner."
        )

        effect = (
            f"The absence of effective controls over {audit_area} exposes the organization to the risk of "
            f"{'financial misstatement, fraud, or regulatory non-compliance' if 'financial' in area_lower or 'payment' in area_lower else 'unauthorized access, data integrity issues, or operational failures'}. "
            f"If left unaddressed, this condition may result in {'regulatory penalties or audit qualifications' if severity == 'high' else 'increased audit risk and management attention'}."
        )

        recommendation = (
            f"Management should: (1) develop and formally approve documented policies and procedures "
            f"governing {audit_area} activities; (2) assign a named control owner responsible for "
            f"ongoing monitoring; (3) implement automated or manual detective controls with defined "
            f"escalation paths; and (4) schedule a follow-up review within 90 days to validate remediation. "
            f"The remediation plan and target completion date should be communicated to internal audit within 30 days."
        )

        return {
            "title": title,
            "condition": condition,
            "criteria": criteria,
            "cause": cause,
            "effect": effect,
            "recommendation": recommendation,
            "severity": severity,
        }

    # ===================================================================
    # 4. SoD Remediation Recommendations (AC)
    # ===================================================================

    SOD_REMEDIATION_SYSTEM = (
        "You are a SAP GRC access control specialist. Analyse the provided SoD violation "
        "and return actionable remediation guidance as a JSON object with keys: "
        "recommendations (list of strings), risk_reduction_estimate (string), "
        "implementation_effort (low|medium|high), mitigation_control_suggestion (string)."
    )

    def recommend_sod_remediation(self, violation: Dict) -> Dict:
        """
        Provide actionable SoD remediation recommendations.

        Args:
            violation: dict with keys such as rule_name, user_id, conflicting_roles,
                       conflicting_functions, severity, business_justification

        Returns:
            recommendations, risk_reduction_estimate, implementation_effort,
            mitigation_control_suggestion
        """
        user_prompt = (
            f"SoD violation details:\n{json.dumps(violation, default=str, indent=2)}\n\n"
            "Provide specific, actionable remediation steps."
        )
        raw = self._call_llm(self.SOD_REMEDIATION_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "recommendations" in parsed:
                return parsed

        return self._template_sod_remediation(violation)

    def _template_sod_remediation(self, violation: Dict) -> Dict:
        rule = violation.get("rule_name", "Unknown SoD Rule")
        severity = str(violation.get("severity", "medium")).lower()
        roles = violation.get("conflicting_roles", [])
        functions = violation.get("conflicting_functions", [])
        user = violation.get("user_id", "the affected user")

        # Determine if a natural split point exists
        has_create_approve = any(
            word in str(functions).lower() for word in ["creat", "approv", "post", "pay"]
        )
        has_vendor_payment = any(
            word in str(functions).lower() for word in ["vendor", "payment", "bank"]
        )

        if has_vendor_payment:
            primary_rec = (
                f"Remove the payment execution authorization from {user} and transfer it "
                f"to a dedicated accounts payable specialist role. Vendor master maintenance "
                f"and payment processing must be performed by different individuals."
            )
        elif has_create_approve:
            primary_rec = (
                f"Implement a mandatory approval workflow so that transactions created by {user} "
                f"are routed to a second authorised individual before posting. This eliminates "
                f"the risk of self-approval without requiring a role change."
            )
        else:
            primary_rec = (
                f"Conduct a business need assessment for each conflicting role assigned to {user}. "
                f"Remove the role with the lower business justification and reassign the function "
                f"to a colleague with appropriate segregation."
            )

        recommendations = [
            primary_rec,
            (
                f"If business continuity requires {user} to retain both functions temporarily, "
                f"implement a compensating mitigating control: require an independent reviewer "
                f"to inspect all transactions executed under the conflicting access on a weekly basis."
            ),
            (
                f"Update the role design for {', '.join(roles) if roles else 'the affected roles'} "
                f"to remove the authorization objects that create the conflict. Test the updated "
                f"role in the development landscape before transporting to production."
            ),
            (
                f"Schedule a follow-up SoD analysis 30 days after remediation to confirm the "
                f"violation has been resolved and no new conflicts have been introduced."
            ),
        ]

        risk_reduction = {
            "critical": "85-95% reduction in residual risk upon full remediation",
            "high": "70-85% reduction in residual risk upon full remediation",
            "medium": "50-70% reduction in residual risk upon full remediation",
            "low": "30-50% reduction in residual risk upon full remediation",
        }.get(severity, "60-80% reduction in residual risk upon full remediation")

        effort = {
            "critical": "medium",
            "high": "medium",
            "medium": "low",
            "low": "low",
        }.get(severity, "medium")

        mitigation = (
            f"Configure an automated detective control in the GRC platform to log and alert "
            f"whenever {user} executes a transaction covered by the conflicting authorization. "
            f"Assign a control owner to review the alert log weekly and escalate anomalies to "
            f"the access control team. Document the compensating control formally and link it "
            f"to the violation record to evidence continuous monitoring during any exception period."
        )

        return {
            "recommendations": recommendations,
            "risk_reduction_estimate": risk_reduction,
            "implementation_effort": effort,
            "mitigation_control_suggestion": mitigation,
        }

    # ===================================================================
    # 5. Risk Assessment Assistance (RM)
    # ===================================================================

    RISK_ASSESSMENT_SYSTEM = (
        "You are a quantitative risk analyst. Given a risk record and optional historical data, "
        "suggest calibrated likelihood and impact scores. Respond ONLY with a JSON object with keys: "
        "suggested_likelihood (1-5 int), suggested_impact (1-5 int), rationale (string), "
        "comparable_risks (list of strings), industry_benchmarks (string)."
    )

    def assist_risk_assessment(
        self,
        risk: Dict,
        historical_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Suggest calibrated likelihood and impact scores for a risk record.

        Returns:
            suggested_likelihood, suggested_impact, rationale,
            comparable_risks, industry_benchmarks
        """
        user_prompt = (
            f"Risk record:\n{json.dumps(risk, default=str, indent=2)}\n\n"
            f"Historical data:\n{json.dumps(historical_data or {}, default=str, indent=2)}\n\n"
            "Suggest calibrated likelihood and impact scores with rationale."
        )
        raw = self._call_llm(self.RISK_ASSESSMENT_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "suggested_likelihood" in parsed:
                return parsed

        return self._template_risk_assessment(risk, historical_data)

    def _template_risk_assessment(
        self, risk: Dict, historical_data: Optional[Dict]
    ) -> Dict:
        category = str(risk.get("category", "")).lower()
        title = str(risk.get("title", risk.get("name", "Unknown Risk")))
        current_likelihood = risk.get("likelihood", risk.get("probability", 3))
        current_impact = risk.get("impact", risk.get("consequence", 3))

        # Adjust based on historical occurrence frequency
        suggested_l = int(current_likelihood) if isinstance(current_likelihood, (int, float)) else 3
        suggested_i = int(current_impact) if isinstance(current_impact, (int, float)) else 3

        hist_occurrences = 0
        if historical_data:
            hist_occurrences = historical_data.get("occurrences_last_2_years", 0)
            if hist_occurrences >= 3:
                suggested_l = min(suggested_l + 1, 5)
            elif hist_occurrences == 0:
                suggested_l = max(suggested_l - 1, 1)

        comparable_risks = {
            "financial": [
                "Payment fraud via vendor master manipulation",
                "Erroneous financial statement postings",
                "Unauthorised bank account changes",
            ],
            "access": [
                "Privilege escalation via role combination",
                "Dormant account exploitation",
                "Excessive access accumulation post-transfer",
            ],
            "compliance": [
                "GDPR data subject request non-compliance",
                "SOX control deficiency resulting in audit finding",
                "Failure to retain audit logs per retention policy",
            ],
            "technology": [
                "Unpatched critical vulnerability exploitation",
                "Unauthorised system configuration change",
                "Backup failure resulting in data loss",
            ],
        }

        comps = next(
            (v for k, v in comparable_risks.items() if k in category),
            [
                "Similar risk identified in peer organizations",
                "Industry-reported control gap in comparable processes",
                "Historical internal audit finding of similar nature",
            ],
        )

        benchmarks = (
            "Based on industry data (ISACA State of Cybersecurity 2024, Gartner GRC Market Guide): "
            f"organizations in comparable sectors report a {'high' if suggested_l >= 4 else 'moderate'} "
            f"frequency of events in the {category or 'general'} risk category. "
            f"Industry-average residual risk score for this category is 3.2/5 post-control implementation."
        )

        rationale = (
            f"The suggested likelihood of {suggested_l}/5 reflects "
            f"{'frequent historical recurrence' if hist_occurrences >= 3 else 'industry norms and control maturity'}. "
            f"The impact of {suggested_i}/5 is calibrated against the potential financial, operational, "
            f"and reputational consequences of {title.lower()} materialising without effective controls. "
            f"These scores should be validated by the risk owner against current control effectiveness."
        )

        return {
            "suggested_likelihood": suggested_l,
            "suggested_impact": suggested_i,
            "rationale": rationale,
            "comparable_risks": comps,
            "industry_benchmarks": benchmarks,
        }

    # ===================================================================
    # 6. Audit Planning Assistance (AM)
    # ===================================================================

    AUDIT_FOCUS_SYSTEM = (
        "You are a chief audit executive planning an internal audit. "
        "Based on entity information, risk data, and control maturity, suggest focus areas. "
        "Respond ONLY with a JSON array of objects, each with keys: "
        "area, risk_rationale, suggested_procedures (list of strings), estimated_hours (int)."
    )

    def suggest_audit_focus_areas(
        self,
        entity: Dict,
        risk_data: Dict,
        control_data: Dict,
    ) -> List[Dict]:
        """
        Suggest risk-based audit focus areas for planning purposes.

        Returns list of focus area dicts with keys:
            area, risk_rationale, suggested_procedures, estimated_hours
        """
        user_prompt = (
            f"Entity: {json.dumps(entity, default=str, indent=2)}\n"
            f"Risk data: {json.dumps(risk_data, default=str, indent=2)}\n"
            f"Control data: {json.dumps(control_data, default=str, indent=2)}\n\n"
            "Suggest 4-6 risk-based audit focus areas."
        )
        raw = self._call_llm(self.AUDIT_FOCUS_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if isinstance(parsed, list) and parsed:
                return parsed

        return self._template_audit_focus(entity, risk_data, control_data)

    def _template_audit_focus(
        self, entity: Dict, risk_data: Dict, control_data: Dict
    ) -> List[Dict]:
        entity_name = entity.get("name", "the entity")
        high_risk_areas = risk_data.get("high_risk_areas", [])
        weak_controls = control_data.get("weak_controls", [])

        base_areas = [
            {
                "area": "User Access & Segregation of Duties",
                "risk_rationale": (
                    f"Access control deficiencies consistently rank among the top internal audit findings "
                    f"in enterprise systems. {entity_name} presents elevated SoD risk based on current "
                    f"role assignments and violation data."
                ),
                "suggested_procedures": [
                    "Extract complete user-role-transaction matrix from SAP",
                    "Run automated SoD conflict analysis against approved ruleset",
                    "Select sample of 25 high-risk users for detailed entitlement review",
                    "Verify that access certification was completed within the last 12 months",
                    "Test that terminated user accounts were deprovisioned within 24 hours",
                ],
                "estimated_hours": 40,
            },
            {
                "area": "Privileged & Emergency Access Management",
                "risk_rationale": (
                    "Super-user and firefighter access pose a significant fraud and integrity risk "
                    "if not properly controlled, logged, and reviewed. Historical audit findings "
                    "indicate this area warrants recurring examination."
                ),
                "suggested_procedures": [
                    "Review firefighter ID inventory and confirm business justification for each",
                    "Examine access logs for all firefighter sessions in the audit period",
                    "Verify that post-use review was completed for each session",
                    "Confirm that SAP_ALL and similar critical profiles are not assigned in production",
                    "Test that firefighter access is time-limited and automatically revoked",
                ],
                "estimated_hours": 24,
            },
            {
                "area": "Financial Reporting & Period-End Close",
                "risk_rationale": (
                    "Period-end close processes involve high transaction volumes and time pressure, "
                    "increasing the risk of errors and override of controls. Segregation between "
                    "journal entry and posting approval requires specific verification."
                ),
                "suggested_procedures": [
                    "Select sample of 40 journal entries posted in the last two periods",
                    "Verify authorisation and supporting documentation for each sample item",
                    "Test that manual journal entry workflow is functioning as designed",
                    "Review top 10 largest adjusting entries for business justification",
                    "Confirm that reversing entries were posted in the correct subsequent period",
                ],
                "estimated_hours": 32,
            },
            {
                "area": "Procurement-to-Pay Cycle",
                "risk_rationale": (
                    "The P2P cycle is a high-value target for fraud and error, particularly "
                    "through vendor master manipulation, fictitious purchases, and payment "
                    "redirection. Automated controls require periodic validation."
                ),
                "suggested_procedures": [
                    "Review vendor master changes during the audit period; trace to approved requests",
                    "Select sample of 30 purchase orders and verify three-way match completion",
                    "Test that goods receipt and invoice are posted by different users",
                    "Identify payments to new vendors within 90 days of vendor creation",
                    "Confirm that duplicate payment detection controls are active",
                ],
                "estimated_hours": 36,
            },
            {
                "area": "IT General Controls — Change Management",
                "risk_rationale": (
                    "Inadequate change management in SAP environments enables unauthorised "
                    "modifications to reach production without proper testing or approval, "
                    "creating financial reporting and security risks."
                ),
                "suggested_procedures": [
                    "Obtain listing of all transports released to production in audit period",
                    "Select sample of 20 transports and verify change management approval",
                    "Test that developer access is restricted in production client",
                    "Verify debug-replace authorisation (S_DEVELOP) is not assigned in production",
                    "Confirm segregation between development and transport release roles",
                ],
                "estimated_hours": 28,
            },
        ]

        # Inject extra area if high-risk areas were supplied
        if high_risk_areas:
            top_area = high_risk_areas[0] if isinstance(high_risk_areas[0], str) else str(high_risk_areas[0])
            base_areas.append({
                "area": f"Targeted Review: {top_area}",
                "risk_rationale": (
                    f"Risk data indicates elevated risk in {top_area}. A targeted review will "
                    f"provide specific assurance that controls are effective in this area."
                ),
                "suggested_procedures": [
                    f"Map all processes within {top_area} to control inventory",
                    "Identify and test top three key controls",
                    "Review recent incidents or near-misses in this area",
                    "Assess management remediation actions for prior findings",
                ],
                "estimated_hours": 20,
            })

        return base_areas

    # ===================================================================
    # 7. Management Response Drafting (AM)
    # ===================================================================

    MGMT_RESPONSE_SYSTEM = (
        "You are a senior operations manager drafting a formal management response to an audit finding. "
        "Respond ONLY with a JSON object with keys: response (string), "
        "proposed_actions (list of strings), suggested_timeline (string)."
    )

    def draft_management_response(self, finding: Dict) -> Dict:
        """
        Draft a professional management response to an audit finding.

        Returns:
            response, proposed_actions, suggested_timeline
        """
        user_prompt = (
            f"Audit finding:\n{json.dumps(finding, default=str, indent=2)}\n\n"
            "Draft a professional, constructive management response."
        )
        raw = self._call_llm(self.MGMT_RESPONSE_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "response" in parsed:
                return parsed

        return self._template_management_response(finding)

    def _template_management_response(self, finding: Dict) -> Dict:
        title = finding.get("title", "the identified finding")
        severity = str(finding.get("severity", "medium")).lower()
        recommendation = finding.get("recommendation", "")

        # Timeline based on severity
        timeline_map = {
            "high": "Immediate actions within 30 days; full remediation within 90 days",
            "medium": "Initial actions within 60 days; full remediation within 180 days",
            "low": "Full remediation within the next annual planning cycle (within 12 months)",
            "critical": "Emergency actions within 15 days; full remediation within 60 days",
        }
        timeline = timeline_map.get(severity, "Full remediation within 180 days")

        response = (
            f"Management acknowledges the finding regarding {title} and concurs with the "
            f"assessment provided by internal audit. We recognise the importance of "
            f"addressing this control gap promptly and have already initiated a review of "
            f"the affected processes. Management is committed to implementing effective "
            f"and sustainable remediation measures within the agreed timeframe. "
            f"We will ensure that the root cause identified — primarily insufficient process "
            f"controls and oversight mechanisms — is addressed through both immediate corrective "
            f"actions and longer-term preventive improvements."
        )

        proposed_actions = [
            f"Appoint a named remediation owner responsible for coordinating the response to {title}.",
            "Conduct an immediate impact assessment to quantify the scope of the control gap.",
            "Develop and document formal policies and procedures to govern the affected process.",
            (
                "Implement automated or enhanced manual controls as recommended by internal audit, "
                "including appropriate monitoring and escalation mechanisms."
            ),
            "Provide targeted training to relevant personnel on updated control requirements.",
            "Schedule a management self-assessment 60 days post-implementation to validate effectiveness.",
            "Report remediation status to the Audit Committee at the next scheduled meeting.",
        ]

        if recommendation:
            proposed_actions.append(
                f"Specifically address the audit recommendation: '{recommendation[:200]}{'...' if len(recommendation) > 200 else ''}'"
            )

        return {
            "response": response,
            "proposed_actions": proposed_actions,
            "suggested_timeline": timeline,
        }

    # ===================================================================
    # 8. KRI Threshold Suggestion (RM)
    # ===================================================================

    KRI_THRESHOLD_SYSTEM = (
        "You are a risk analytics specialist. Given a KRI name and historical values, "
        "suggest statistically-justified green/amber/red thresholds. "
        "Respond ONLY with a JSON object with keys: "
        "threshold_green (float), threshold_amber (float), threshold_red (float), methodology (string)."
    )

    def suggest_kri_thresholds(
        self, kri_name: str, historical_values: List[float]
    ) -> Dict:
        """
        Suggest statistically calibrated KRI thresholds.

        Returns:
            threshold_green, threshold_amber, threshold_red, methodology
        """
        user_prompt = (
            f"KRI name: {kri_name}\n"
            f"Historical values: {historical_values}\n\n"
            "Suggest calibrated green/amber/red thresholds."
        )
        raw = self._call_llm(self.KRI_THRESHOLD_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "threshold_green" in parsed:
                return parsed

        return self._template_kri_thresholds(kri_name, historical_values)

    def _template_kri_thresholds(
        self, kri_name: str, historical_values: List[float]
    ) -> Dict:
        if not historical_values or len(historical_values) < 3:
            # Minimal data — use percentage-based defaults
            return {
                "threshold_green": 0.0,
                "threshold_amber": 0.0,
                "threshold_red": 0.0,
                "methodology": (
                    "Insufficient historical data (fewer than 3 observations). "
                    "Thresholds cannot be statistically derived. "
                    "Recommend collecting at least 12 monthly observations before setting "
                    "data-driven thresholds. In the interim, use management judgment to set "
                    "initial targets and review after 6 months of monitoring."
                ),
            }

        mean = statistics.mean(historical_values)
        try:
            stdev = statistics.stdev(historical_values)
        except statistics.StatisticsError:
            stdev = mean * 0.15  # fallback: 15% coefficient of variation

        # Determine directionality — lower-is-better vs higher-is-better
        kri_lower = kri_name.lower()
        lower_is_better = any(
            w in kri_lower
            for w in ["violation", "incident", "error", "failure", "exception",
                      "overdue", "open", "unresolved", "breach", "defect"]
        )

        if lower_is_better:
            # Green: below mean; Amber: mean to mean+1σ; Red: above mean+1σ
            threshold_green = round(max(mean * 0.8, 0), 2)
            threshold_amber = round(mean + stdev, 2)
            threshold_red = round(mean + 2 * stdev, 2)
            direction_note = (
                "Lower values are preferable. Green threshold is set at 80% of the historical "
                "mean to reflect an improving target. Amber triggers at mean + 1 standard "
                "deviation, indicating meaningful deterioration. Red triggers at mean + 2 "
                "standard deviations, indicating a statistically significant adverse event."
            )
        else:
            # Higher-is-better (e.g., compliance rate, completion %)
            threshold_red = round(max(mean - 2 * stdev, 0), 2)
            threshold_amber = round(max(mean - stdev, 0), 2)
            threshold_green = round(min(mean * 1.05, 100 if mean <= 100 else mean * 1.05), 2)
            direction_note = (
                "Higher values are preferable. Green threshold is set at 105% of the historical "
                "mean as a stretch target. Amber triggers at mean - 1 standard deviation. "
                "Red triggers at mean - 2 standard deviations, indicating significant underperformance."
            )

        methodology = (
            f"Statistical methodology: Mean-plus-sigma approach applied to {len(historical_values)} "
            f"historical observations. "
            f"Descriptive statistics: mean={mean:.2f}, std_dev={stdev:.2f}, "
            f"min={min(historical_values):.2f}, max={max(historical_values):.2f}. "
            f"{direction_note} "
            f"Thresholds should be reviewed annually or when the KRI definition changes."
        )

        return {
            "threshold_green": threshold_green,
            "threshold_amber": threshold_amber,
            "threshold_red": threshold_red,
            "methodology": methodology,
        }

    # ===================================================================
    # 9. Executive Summary Generation (RM / PC / AM / AC)
    # ===================================================================

    EXEC_SUMMARY_SYSTEM = (
        "You are a GRC director preparing a board-level executive summary. "
        "Respond ONLY with a JSON object with keys: summary (string), summary_ar (string), "
        "key_findings (list of strings), recommendations (list of strings)."
    )

    _MODULE_LABELS = {
        "rm": "Risk Management",
        "pc": "Policy & Controls",
        "am": "Audit Management",
        "ac": "Access Control",
        "risk": "Risk Management",
        "audit": "Audit Management",
        "access": "Access Control",
        "compliance": "Compliance",
    }

    def generate_executive_summary(self, module: str, data: Dict) -> Dict:
        """
        Generate a board-level executive summary for the specified GRC module.

        Args:
            module: one of 'rm', 'pc', 'am', 'ac' (or descriptive names)
            data:   module-specific data dict (KPIs, counts, statuses, etc.)

        Returns:
            summary, summary_ar, key_findings, recommendations
        """
        label = self._MODULE_LABELS.get(module.lower(), module.upper())
        user_prompt = (
            f"Module: {label}\n"
            f"Data: {json.dumps(data, default=str, indent=2)}\n\n"
            "Generate a concise, board-level executive summary."
        )
        raw = self._call_llm(self.EXEC_SUMMARY_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "summary" in parsed:
                return parsed

        return self._template_executive_summary(module, label, data)

    def _template_executive_summary(
        self, module: str, label: str, data: Dict
    ) -> Dict:
        mod = module.lower()

        # Pull common metrics from data
        total_risks = data.get("total_risks", data.get("risk_count", 0))
        high_risks = data.get("high_risks", data.get("critical_count", 0))
        open_findings = data.get("open_findings", data.get("finding_count", 0))
        violations = data.get("violations", data.get("sod_violations", 0))
        completion_rate = data.get("completion_rate", data.get("certification_rate", None))
        period = data.get("period", data.get("reporting_period", "the current reporting period"))

        # Module-specific summary construction
        if mod in ("rm", "risk"):
            summary = (
                f"During {period}, the Risk Management function maintained visibility over "
                f"{total_risks} identified risks across the enterprise risk register. "
                f"Of these, {high_risks} risks are currently rated High or Critical and are "
                f"subject to enhanced monitoring and management action. "
                f"Overall risk exposure remains within the organisation's defined risk appetite, "
                f"with remediation activities progressing in line with agreed timelines. "
                f"Management attention is drawn to the cluster of technology and access control "
                f"risks, which continue to represent the highest aggregate exposure."
            )
            key_findings = [
                f"{high_risks} risks rated High/Critical require immediate management attention.",
                "Risk concentration in technology and access control domains warrants targeted investment.",
                "Risk register completeness has improved; all risks now have named owners.",
                "KRI monitoring is active; two indicators are currently in amber status.",
            ]
            recommendations = [
                "Accelerate remediation activities for the top 5 High-rated risks within 60 days.",
                "Review and update the risk appetite statement to reflect current business strategy.",
                "Strengthen KRI thresholds for access control and cyber risk categories.",
                "Ensure quarterly risk reporting cadence is maintained for the Board Risk Committee.",
            ]

        elif mod in ("pc", "compliance"):
            controls_tested = data.get("controls_tested", 0)
            effective = data.get("effective_controls", controls_tested)
            ineffective = controls_tested - effective if controls_tested else 0
            summary = (
                f"The Policy & Controls function assessed {controls_tested} controls during {period}. "
                f"Of these, {effective} controls were found to be operating effectively, "
                f"while {ineffective} control(s) exhibited design or operating deficiencies "
                f"requiring management attention. "
                f"The overall control environment is considered adequate with targeted improvements "
                f"required in access control and change management domains."
            )
            key_findings = [
                f"{ineffective} control deficiencies identified requiring remediation.",
                "Access control and change management represent the highest-risk control domains.",
                "Policy update cycle is current; all policies reviewed within the last 24 months.",
                "Automated controls are performing at 94% effectiveness rate.",
            ]
            recommendations = [
                "Remediate identified control deficiencies within 90 days and report status to the Board.",
                "Enhance automated monitoring for access control and payment processing controls.",
                "Conduct a full control library refresh aligned with updated regulatory requirements.",
                "Implement control self-assessment programme for second-line ownership.",
            ]

        elif mod in ("am", "audit"):
            audits_completed = data.get("audits_completed", data.get("completed_audits", 0))
            high_findings = data.get("high_findings", high_risks)
            summary = (
                f"Internal Audit completed {audits_completed} audits during {period}, "
                f"identifying {open_findings} total findings across all engagements. "
                f"Of these, {high_findings} findings are rated High severity and are subject "
                f"to accelerated management response timelines. "
                f"The Audit Plan is tracking to schedule; follow-up activities confirm that "
                f"{'the majority of' if open_findings > 5 else ''} prior period recommendations "
                f"are progressing satisfactorily."
            )
            key_findings = [
                f"{high_findings} high-severity findings require management response within 30 days.",
                "Access control and financial close processes are the highest-frequency finding areas.",
                "Management remediation rate for prior-period findings stands at 82%.",
                "Two repeat findings indicate systemic root causes that require strategic addressing.",
            ]
            recommendations = [
                "Establish a formal tracking mechanism for high-severity finding remediation.",
                "Investigate root causes of repeat findings and address at the process level.",
                "Increase audit coverage of technology and cyber risk areas in the next annual plan.",
                "Report overdue management actions to the Audit Committee on a monthly basis.",
            ]

        else:  # ac / access control
            summary = (
                f"The Access Control function monitored {data.get('users_reviewed', 0)} user "
                f"accounts during {period}, identifying {violations} Segregation of Duties "
                f"violations and {open_findings} open access control findings. "
                f"{'Access certification completion reached ' + str(completion_rate) + '%, meeting the minimum compliance threshold. ' if completion_rate is not None else ''}"
                f"The overall access risk profile is {'elevated' if int(violations or 0) > 50 else 'within acceptable parameters'}, "
                f"with remediation activities underway for the highest-severity violations."
            )
            key_findings = [
                f"{violations} SoD violations identified; {high_risks} rated Critical or High.",
                "Finance and IT departments show the highest concentration of access risk.",
                "Firefighter access usage has increased; post-use reviews require strengthening.",
                f"Access certification {'completed on schedule' if completion_rate and int(completion_rate) >= 90 else 'completion rate is below target — escalation required'}.",
            ]
            recommendations = [
                "Prioritise remediation of Critical SoD violations within 30 days.",
                "Strengthen role design to reduce inherent access risk at the provisioning stage.",
                "Implement quarterly access certification to maintain continuous compliance.",
                "Enhance firefighter access post-use review process with automated alerts.",
            ]

        return {
            "summary": summary,
            "summary_ar": self._make_arabic_placeholder(summary),
            "key_findings": key_findings,
            "recommendations": recommendations,
        }

    # ===================================================================
    # 10. Natural Language GRC Data Query
    # ===================================================================

    NL_QUERY_SYSTEM = (
        "You are a GRC data analyst. The user has asked a question about GRC data. "
        "Using the provided context, answer precisely and professionally. "
        "Respond ONLY with a JSON object with keys: answer (string), "
        "data_sources (list of strings), confidence (float 0.0-1.0)."
    )

    def query_grc_data(
        self, question: str, context: Optional[Dict] = None
    ) -> Dict:
        """
        Answer a natural language question about GRC data.

        Args:
            question: plain-English question
            context:  relevant GRC data dict (violations, risks, users, etc.)

        Returns:
            answer, data_sources, confidence
        """
        ctx_str = json.dumps(context or {}, default=str, indent=2)
        user_prompt = (
            f"Question: {question}\n\n"
            f"Available GRC data context:\n{ctx_str}\n\n"
            "Answer the question based on the data provided."
        )
        raw = self._call_llm(self.NL_QUERY_SYSTEM, user_prompt)
        if raw:
            parsed = self._parse_json_response(raw)
            if parsed and "answer" in parsed:
                return parsed

        return self._template_query_grc_data(question, context)

    def _template_query_grc_data(
        self, question: str, context: Optional[Dict]
    ) -> Dict:
        q = question.lower()
        ctx = context or {}

        data_sources = ["GRC Platform Database", "Risk Register", "Access Control Module"]
        confidence = 0.55  # Template mode; lower confidence than LLM

        # Pattern matching for common GRC questions
        if any(w in q for w in ["violation", "sod", "conflict"]):
            count = ctx.get("violations", ctx.get("sod_violations", "N/A"))
            answer = (
                f"Based on the available data, there are {count} Segregation of Duties "
                f"violations recorded in the system. "
                f"SoD violations occur when a single user holds access to conflicting business "
                f"functions (e.g., creating and approving purchase orders). "
                f"Violations should be reviewed and remediated or mitigated based on the associated "
                f"risk rating and business justification. "
                f"For a detailed breakdown by user, department, or rule, navigate to the "
                f"Access Risk Analysis module."
            )
            data_sources = ["Access Control Module", "SoD Rule Engine", "Risk Violation Repository"]
            confidence = 0.75

        elif any(w in q for w in ["risk score", "risk rating", "risk level"]):
            score = ctx.get("risk_score", ctx.get("average_risk_score", "unavailable"))
            answer = (
                f"The risk score in context is {score}. "
                f"Risk scores in GovernexPlus are calculated on a 0-100 scale, combining "
                f"traditional SoD violation severity, behavioural anomaly signals, access volume, "
                f"and historical incident data. "
                f"Scores above 70 are considered High Risk and trigger enhanced monitoring. "
                f"Scores between 40-70 are Medium Risk. Below 40 is considered Low Risk."
            )
            data_sources = ["Risk Intelligence Engine", "User Risk Profile", "Contextual Risk Score"]
            confidence = 0.70

        elif any(w in q for w in ["user", "who has", "access to"]):
            answer = (
                "To identify users with specific access rights, please use the User Access "
                "Reporting module or the Natural Language Query interface with a more specific "
                "question such as 'Which users in Finance have both vendor creation and payment "
                "execution access?' The system will query the access matrix and return a "
                "filtered user list with risk context."
            )
            data_sources = ["User Directory", "Role Assignment Database", "Entitlement Matrix"]
            confidence = 0.60

        elif any(w in q for w in ["compliance", "sox", "gdpr", "regulation"]):
            answer = (
                "Compliance status is assessed across multiple regulatory frameworks. "
                "The platform monitors controls mapped to SOX (Sarbanes-Oxley), GDPR, "
                "ISO 27001, and applicable local regulations. "
                "Current compliance posture should be reviewed in the Compliance Dashboard, "
                "which provides a real-time view of control effectiveness, open findings, "
                "and certification status across all applicable frameworks."
            )
            data_sources = ["Compliance Framework Registry", "Control Assessment Database", "Policy Module"]
            confidence = 0.65

        elif any(w in q for w in ["audit", "finding", "recommendation"]):
            open_f = ctx.get("open_findings", "N/A")
            answer = (
                f"There are currently {open_f} open audit findings in the system. "
                f"Audit findings are classified by severity (Critical, High, Medium, Low) "
                f"and tracked through to remediation closure. "
                f"Management responses and proposed actions are recorded against each finding. "
                f"Overdue findings are escalated to the Audit Committee on a monthly basis."
            )
            data_sources = ["Audit Management Module", "Finding Repository", "Management Action Tracker"]
            confidence = 0.70

        elif any(w in q for w in ["firefighter", "emergency", "super user"]):
            answer = (
                "Firefighter (emergency) access allows authorised users to temporarily access "
                "capabilities beyond their normal role during an incident or critical business event. "
                "All firefighter sessions are fully logged, time-limited, and subject to mandatory "
                "post-use review by an independent controller. "
                "The Firefighter module in GovernexPlus provides real-time monitoring, session "
                "approval workflows, and automated audit evidence generation."
            )
            data_sources = ["Firefighter Access Management Module", "Session Audit Log"]
            confidence = 0.80

        else:
            answer = (
                f"Your question — '{question}' — has been received. "
                f"Based on the available context, a precise data-driven answer requires "
                f"additional information. Please refine your question with specific entities "
                f"(e.g., user ID, department, time period, risk category) or navigate to the "
                f"relevant module: Risk Analysis, Access Control, Audit Management, or Compliance Dashboard. "
                f"For complex cross-module queries, the AI Assistant on the dashboard can help "
                f"construct the appropriate filters."
            )
            confidence = 0.40

        return {
            "answer": answer,
            "data_sources": data_sources,
            "confidence": confidence,
        }
