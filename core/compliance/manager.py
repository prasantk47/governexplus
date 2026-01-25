"""
Compliance Management Module

Provides regulatory framework mapping, control objectives,
compliance assessments, and evidence collection.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid


class ComplianceStatus(Enum):
    """Compliance assessment status"""
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"
    NOT_APPLICABLE = "not_applicable"


class EvidenceType(Enum):
    """Types of compliance evidence"""
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    LOG = "log"
    REPORT = "report"
    CONFIGURATION = "configuration"
    ATTESTATION = "attestation"
    TEST_RESULT = "test_result"


@dataclass
class ComplianceEvidence:
    """Evidence supporting compliance"""
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    evidence_type: EvidenceType = EvidenceType.DOCUMENT
    name: str = ""
    description: str = ""
    reference: str = ""  # URL or file path
    collected_at: datetime = field(default_factory=datetime.now)
    collected_by: str = ""
    valid_until: Optional[datetime] = None
    is_automated: bool = False

    def to_dict(self) -> Dict:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "name": self.name,
            "description": self.description,
            "reference": self.reference,
            "collected_at": self.collected_at.isoformat(),
            "collected_by": self.collected_by,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "is_automated": self.is_automated
        }


@dataclass
class ControlObjective:
    """A control objective within a framework"""
    objective_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    framework_id: str = ""
    reference_id: str = ""  # e.g., "SOX-404", "GDPR-Art32"
    name: str = ""
    description: str = ""
    category: str = ""

    # Requirements
    control_requirements: List[str] = field(default_factory=list)
    testing_procedures: List[str] = field(default_factory=list)
    evidence_requirements: List[str] = field(default_factory=list)

    # Mapping to GRC controls
    mapped_controls: List[str] = field(default_factory=list)  # Control IDs
    mapped_policies: List[str] = field(default_factory=list)  # Policy IDs

    # Assessment
    current_status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    last_assessed: Optional[datetime] = None
    next_assessment_due: Optional[datetime] = None
    assessment_frequency_days: int = 90

    # Risk
    risk_level: str = "medium"
    is_key_control: bool = False

    def to_dict(self) -> Dict:
        return {
            "objective_id": self.objective_id,
            "framework_id": self.framework_id,
            "reference_id": self.reference_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "control_requirements": self.control_requirements,
            "testing_procedures": self.testing_procedures,
            "evidence_requirements": self.evidence_requirements,
            "mapped_controls": self.mapped_controls,
            "mapped_policies": self.mapped_policies,
            "current_status": self.current_status.value,
            "last_assessed": self.last_assessed.isoformat() if self.last_assessed else None,
            "next_assessment_due": self.next_assessment_due.isoformat() if self.next_assessment_due else None,
            "assessment_frequency_days": self.assessment_frequency_days,
            "risk_level": self.risk_level,
            "is_key_control": self.is_key_control
        }


@dataclass
class ComplianceFramework:
    """A regulatory/compliance framework"""
    framework_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    short_name: str = ""  # SOX, GDPR, SOC2, etc.
    description: str = ""
    version: str = ""

    # Framework structure
    categories: List[str] = field(default_factory=list)
    objectives: List[ControlObjective] = field(default_factory=list)

    # Applicability
    is_active: bool = True
    applicable_regions: List[str] = field(default_factory=list)
    applicable_industries: List[str] = field(default_factory=list)

    # Status
    compliance_score: float = 0.0
    last_assessment_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "framework_id": self.framework_id,
            "name": self.name,
            "short_name": self.short_name,
            "description": self.description,
            "version": self.version,
            "categories": self.categories,
            "objectives_count": len(self.objectives),
            "is_active": self.is_active,
            "applicable_regions": self.applicable_regions,
            "applicable_industries": self.applicable_industries,
            "compliance_score": self.compliance_score,
            "last_assessment_date": self.last_assessment_date.isoformat() if self.last_assessment_date else None
        }


@dataclass
class ComplianceAssessment:
    """An assessment of a control objective"""
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    objective_id: str = ""
    framework_id: str = ""

    # Assessment details
    assessment_date: datetime = field(default_factory=datetime.now)
    assessed_by: str = ""
    status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    score: float = 0.0  # 0-100

    # Findings
    findings: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Evidence
    evidence: List[ComplianceEvidence] = field(default_factory=list)

    # Review
    reviewed_by: str = ""
    reviewed_at: Optional[datetime] = None
    review_comments: str = ""

    def to_dict(self) -> Dict:
        return {
            "assessment_id": self.assessment_id,
            "objective_id": self.objective_id,
            "framework_id": self.framework_id,
            "assessment_date": self.assessment_date.isoformat(),
            "assessed_by": self.assessed_by,
            "status": self.status.value,
            "score": self.score,
            "findings": self.findings,
            "gaps": self.gaps,
            "recommendations": self.recommendations,
            "evidence": [e.to_dict() for e in self.evidence],
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_comments": self.review_comments
        }


class ComplianceManager:
    """
    Compliance Management System.

    Manages regulatory frameworks, control objectives,
    assessments, and evidence collection.
    """

    def __init__(self):
        self.frameworks: Dict[str, ComplianceFramework] = {}
        self.objectives: Dict[str, ControlObjective] = {}
        self.assessments: Dict[str, ComplianceAssessment] = {}
        self._initialize_standard_frameworks()

    def _initialize_standard_frameworks(self):
        """Initialize standard compliance frameworks"""
        # SOX Framework
        sox = ComplianceFramework(
            name="Sarbanes-Oxley Act",
            short_name="SOX",
            description="US federal law for financial reporting and corporate governance",
            version="2002",
            categories=["Access Control", "Change Management", "Financial Reporting", "IT General Controls"],
            applicable_regions=["US"],
            applicable_industries=["Public Companies"]
        )

        sox_objectives = [
            ControlObjective(
                framework_id=sox.framework_id,
                reference_id="SOX-AC01",
                name="User Access Management",
                description="Ensure appropriate user access to financial systems",
                category="Access Control",
                control_requirements=[
                    "Access requests require approval",
                    "Periodic access reviews performed",
                    "Termination process removes access timely"
                ],
                is_key_control=True,
                risk_level="high"
            ),
            ControlObjective(
                framework_id=sox.framework_id,
                reference_id="SOX-AC02",
                name="Segregation of Duties",
                description="Enforce SoD in financial processes",
                category="Access Control",
                control_requirements=[
                    "SoD rules defined and enforced",
                    "Conflicts monitored and mitigated",
                    "Regular SoD analysis performed"
                ],
                is_key_control=True,
                risk_level="high"
            ),
            ControlObjective(
                framework_id=sox.framework_id,
                reference_id="SOX-AC03",
                name="Privileged Access Management",
                description="Control and monitor privileged access",
                category="Access Control",
                control_requirements=[
                    "Privileged accounts inventoried",
                    "Emergency access controlled",
                    "Privileged actions logged"
                ],
                is_key_control=True,
                risk_level="critical"
            )
        ]

        for obj in sox_objectives:
            sox.objectives.append(obj)
            self.objectives[obj.objective_id] = obj

        self.frameworks[sox.framework_id] = sox

        # GDPR Framework
        gdpr = ComplianceFramework(
            name="General Data Protection Regulation",
            short_name="GDPR",
            description="EU regulation on data protection and privacy",
            version="2018",
            categories=["Data Protection", "Privacy Rights", "Accountability", "Security"],
            applicable_regions=["EU", "EEA"],
            applicable_industries=["All"]
        )

        gdpr_objectives = [
            ControlObjective(
                framework_id=gdpr.framework_id,
                reference_id="GDPR-Art32",
                name="Security of Processing",
                description="Implement appropriate security measures",
                category="Security",
                control_requirements=[
                    "Encryption of personal data",
                    "Access control to personal data",
                    "Regular security testing"
                ],
                risk_level="high"
            ),
            ControlObjective(
                framework_id=gdpr.framework_id,
                reference_id="GDPR-Art25",
                name="Data Protection by Design",
                description="Implement privacy by design principles",
                category="Data Protection",
                control_requirements=[
                    "Minimum data collection",
                    "Purpose limitation",
                    "Data minimization"
                ],
                risk_level="high"
            )
        ]

        for obj in gdpr_objectives:
            gdpr.objectives.append(obj)
            self.objectives[obj.objective_id] = obj

        self.frameworks[gdpr.framework_id] = gdpr

        # SOC 2 Framework
        soc2 = ComplianceFramework(
            name="SOC 2 Type II",
            short_name="SOC2",
            description="Service Organization Control 2 - Trust Services Criteria",
            version="2017",
            categories=["Security", "Availability", "Processing Integrity", "Confidentiality", "Privacy"],
            applicable_regions=["Global"],
            applicable_industries=["Service Providers", "SaaS", "Cloud"]
        )

        soc2_objectives = [
            ControlObjective(
                framework_id=soc2.framework_id,
                reference_id="CC6.1",
                name="Logical Access Security",
                description="Logical access is restricted through authentication",
                category="Security",
                control_requirements=[
                    "User identification and authentication",
                    "Access provisioning procedures",
                    "Access removal procedures"
                ],
                is_key_control=True,
                risk_level="high"
            ),
            ControlObjective(
                framework_id=soc2.framework_id,
                reference_id="CC6.2",
                name="Access Authorization",
                description="Access is authorized based on business requirements",
                category="Security",
                control_requirements=[
                    "Role-based access control",
                    "Access request approval",
                    "Periodic access review"
                ],
                is_key_control=True,
                risk_level="high"
            )
        ]

        for obj in soc2_objectives:
            soc2.objectives.append(obj)
            self.objectives[obj.objective_id] = obj

        self.frameworks[soc2.framework_id] = soc2

    # =========================================================================
    # Framework Management
    # =========================================================================

    def create_framework(
        self,
        name: str,
        short_name: str,
        description: str,
        version: str = "",
        categories: List[str] = None,
        **kwargs
    ) -> ComplianceFramework:
        """Create a new compliance framework"""
        framework = ComplianceFramework(
            name=name,
            short_name=short_name,
            description=description,
            version=version,
            categories=categories or []
        )

        for key, value in kwargs.items():
            if hasattr(framework, key):
                setattr(framework, key, value)

        self.frameworks[framework.framework_id] = framework
        return framework

    def get_framework(self, framework_id: str) -> Optional[ComplianceFramework]:
        """Get a framework by ID"""
        return self.frameworks.get(framework_id)

    def list_frameworks(
        self,
        is_active: bool = None,
        region: str = None
    ) -> List[ComplianceFramework]:
        """List frameworks with filters"""
        frameworks = list(self.frameworks.values())

        if is_active is not None:
            frameworks = [f for f in frameworks if f.is_active == is_active]
        if region:
            frameworks = [f for f in frameworks if region in f.applicable_regions or "Global" in f.applicable_regions]

        return frameworks

    # =========================================================================
    # Control Objectives
    # =========================================================================

    def add_objective(
        self,
        framework_id: str,
        reference_id: str,
        name: str,
        description: str,
        category: str,
        **kwargs
    ) -> ControlObjective:
        """Add a control objective to a framework"""
        if framework_id not in self.frameworks:
            raise ValueError(f"Framework {framework_id} not found")

        objective = ControlObjective(
            framework_id=framework_id,
            reference_id=reference_id,
            name=name,
            description=description,
            category=category
        )

        for key, value in kwargs.items():
            if hasattr(objective, key):
                setattr(objective, key, value)

        self.objectives[objective.objective_id] = objective
        self.frameworks[framework_id].objectives.append(objective)

        return objective

    def get_objective(self, objective_id: str) -> Optional[ControlObjective]:
        """Get an objective by ID"""
        return self.objectives.get(objective_id)

    def list_objectives(
        self,
        framework_id: str = None,
        category: str = None,
        status: ComplianceStatus = None,
        key_controls_only: bool = False
    ) -> List[ControlObjective]:
        """List objectives with filters"""
        objectives = list(self.objectives.values())

        if framework_id:
            objectives = [o for o in objectives if o.framework_id == framework_id]
        if category:
            objectives = [o for o in objectives if o.category == category]
        if status:
            objectives = [o for o in objectives if o.current_status == status]
        if key_controls_only:
            objectives = [o for o in objectives if o.is_key_control]

        return objectives

    def map_control_to_objective(
        self,
        objective_id: str,
        control_id: str
    ) -> ControlObjective:
        """Map a GRC control to an objective"""
        if objective_id not in self.objectives:
            raise ValueError(f"Objective {objective_id} not found")

        objective = self.objectives[objective_id]
        if control_id not in objective.mapped_controls:
            objective.mapped_controls.append(control_id)

        return objective

    # =========================================================================
    # Assessments
    # =========================================================================

    def create_assessment(
        self,
        objective_id: str,
        assessed_by: str,
        status: ComplianceStatus,
        score: float,
        findings: List[str] = None,
        gaps: List[str] = None,
        recommendations: List[str] = None
    ) -> ComplianceAssessment:
        """Create a compliance assessment"""
        if objective_id not in self.objectives:
            raise ValueError(f"Objective {objective_id} not found")

        objective = self.objectives[objective_id]

        assessment = ComplianceAssessment(
            objective_id=objective_id,
            framework_id=objective.framework_id,
            assessed_by=assessed_by,
            status=status,
            score=score,
            findings=findings or [],
            gaps=gaps or [],
            recommendations=recommendations or []
        )

        self.assessments[assessment.assessment_id] = assessment

        # Update objective
        objective.current_status = status
        objective.last_assessed = datetime.now()
        objective.next_assessment_due = datetime.now() + timedelta(
            days=objective.assessment_frequency_days
        )

        # Update framework score
        self._update_framework_score(objective.framework_id)

        return assessment

    def add_evidence(
        self,
        assessment_id: str,
        evidence_type: EvidenceType,
        name: str,
        description: str,
        reference: str,
        collected_by: str,
        valid_until: datetime = None
    ) -> ComplianceEvidence:
        """Add evidence to an assessment"""
        if assessment_id not in self.assessments:
            raise ValueError(f"Assessment {assessment_id} not found")

        evidence = ComplianceEvidence(
            evidence_type=evidence_type,
            name=name,
            description=description,
            reference=reference,
            collected_by=collected_by,
            valid_until=valid_until
        )

        self.assessments[assessment_id].evidence.append(evidence)
        return evidence

    def review_assessment(
        self,
        assessment_id: str,
        reviewed_by: str,
        comments: str = ""
    ) -> ComplianceAssessment:
        """Review an assessment"""
        if assessment_id not in self.assessments:
            raise ValueError(f"Assessment {assessment_id} not found")

        assessment = self.assessments[assessment_id]
        assessment.reviewed_by = reviewed_by
        assessment.reviewed_at = datetime.now()
        assessment.review_comments = comments

        return assessment

    def _update_framework_score(self, framework_id: str):
        """Update framework compliance score"""
        framework = self.frameworks.get(framework_id)
        if not framework or not framework.objectives:
            return

        scores = []
        for obj in framework.objectives:
            if obj.current_status == ComplianceStatus.COMPLIANT:
                scores.append(100)
            elif obj.current_status == ComplianceStatus.PARTIALLY_COMPLIANT:
                scores.append(50)
            elif obj.current_status == ComplianceStatus.NON_COMPLIANT:
                scores.append(0)
            # Skip NOT_ASSESSED and NOT_APPLICABLE

        framework.compliance_score = sum(scores) / len(scores) if scores else 0
        framework.last_assessment_date = datetime.now()

    # =========================================================================
    # Reports & Analytics
    # =========================================================================

    def get_framework_status(self, framework_id: str) -> Dict:
        """Get detailed status for a framework"""
        if framework_id not in self.frameworks:
            raise ValueError(f"Framework {framework_id} not found")

        framework = self.frameworks[framework_id]

        by_status = {}
        for status in ComplianceStatus:
            by_status[status.value] = len([
                o for o in framework.objectives if o.current_status == status
            ])

        by_category = {}
        for cat in framework.categories:
            cat_objectives = [o for o in framework.objectives if o.category == cat]
            compliant = len([o for o in cat_objectives if o.current_status == ComplianceStatus.COMPLIANT])
            by_category[cat] = {
                "total": len(cat_objectives),
                "compliant": compliant,
                "score": round(compliant / len(cat_objectives) * 100, 1) if cat_objectives else 0
            }

        overdue = [
            o for o in framework.objectives
            if o.next_assessment_due and o.next_assessment_due < datetime.now()
        ]

        return {
            "framework": framework.to_dict(),
            "compliance_score": framework.compliance_score,
            "by_status": by_status,
            "by_category": by_category,
            "total_objectives": len(framework.objectives),
            "key_controls": len([o for o in framework.objectives if o.is_key_control]),
            "overdue_assessments": len(overdue),
            "overdue_objectives": [o.reference_id for o in overdue]
        }

    def get_pending_assessments(self) -> List[Dict]:
        """Get objectives due for assessment"""
        now = datetime.now()
        pending = []

        for obj in self.objectives.values():
            if obj.next_assessment_due and obj.next_assessment_due <= now:
                framework = self.frameworks.get(obj.framework_id)
                pending.append({
                    "objective_id": obj.objective_id,
                    "reference_id": obj.reference_id,
                    "name": obj.name,
                    "framework": framework.short_name if framework else "Unknown",
                    "due_date": obj.next_assessment_due.isoformat(),
                    "days_overdue": (now - obj.next_assessment_due).days,
                    "is_key_control": obj.is_key_control
                })

        return sorted(pending, key=lambda x: x["days_overdue"], reverse=True)

    def get_compliance_dashboard(self) -> Dict:
        """Get compliance dashboard summary"""
        total_objectives = len(self.objectives)
        compliant = len([o for o in self.objectives.values() if o.current_status == ComplianceStatus.COMPLIANT])
        non_compliant = len([o for o in self.objectives.values() if o.current_status == ComplianceStatus.NON_COMPLIANT])

        framework_scores = {}
        for fid, framework in self.frameworks.items():
            framework_scores[framework.short_name] = framework.compliance_score

        return {
            "overall_compliance_rate": round(compliant / total_objectives * 100, 1) if total_objectives else 0,
            "total_objectives": total_objectives,
            "compliant": compliant,
            "partially_compliant": len([o for o in self.objectives.values() if o.current_status == ComplianceStatus.PARTIALLY_COMPLIANT]),
            "non_compliant": non_compliant,
            "not_assessed": len([o for o in self.objectives.values() if o.current_status == ComplianceStatus.NOT_ASSESSED]),
            "framework_scores": framework_scores,
            "pending_assessments": len(self.get_pending_assessments()),
            "key_controls_compliant": len([o for o in self.objectives.values() if o.is_key_control and o.current_status == ComplianceStatus.COMPLIANT]),
            "total_key_controls": len([o for o in self.objectives.values() if o.is_key_control])
        }

    def get_statistics(self) -> Dict:
        """Get compliance statistics"""
        return {
            "total_frameworks": len(self.frameworks),
            "active_frameworks": len([f for f in self.frameworks.values() if f.is_active]),
            "total_objectives": len(self.objectives),
            "total_assessments": len(self.assessments),
            "dashboard": self.get_compliance_dashboard()
        }
