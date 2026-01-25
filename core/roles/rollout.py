# SAP Rollout Timeline Tracker
# AI checkpoints for implementation phases

"""
SAP Rollout Timeline Tracker for GOVERNEX+.

Tracks implementation phases with AI checkpoints:
- Phase 0: Mobilization
- Phase 1: Discovery & Baseline
- Phase 2: AI-Assisted Role Design
- Phase 3: Build & Test
- Phase 4: Go-Live & Hypercare
- Phase 5: Continuous Governance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Phase(Enum):
    """Implementation phases."""
    MOBILIZATION = "MOBILIZATION"
    DISCOVERY = "DISCOVERY"
    ROLE_DESIGN = "ROLE_DESIGN"
    BUILD_TEST = "BUILD_TEST"
    GO_LIVE = "GO_LIVE"
    CONTINUOUS = "CONTINUOUS"


class TaskStatus(Enum):
    """Task completion status."""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class AICheckpointType(Enum):
    """Types of AI checkpoints."""
    DATA_CAPTURE = "DATA_CAPTURE"
    CLUSTERING = "CLUSTERING"
    TOXIC_DETECTION = "TOXIC_DETECTION"
    ROLE_GENERATION = "ROLE_GENERATION"
    RISK_SIMULATION = "RISK_SIMULATION"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    PREDICTION = "PREDICTION"


@dataclass
class AICheckpoint:
    """An AI checkpoint in the implementation."""
    checkpoint_id: str
    name: str
    checkpoint_type: AICheckpointType
    phase: Phase
    description: str

    # Status
    status: TaskStatus = TaskStatus.NOT_STARTED
    completed_at: Optional[datetime] = None

    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    findings: List[str] = field(default_factory=list)

    # Outputs
    output_artifacts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "type": self.checkpoint_type.value,
            "phase": self.phase.value,
            "description": self.description,
            "status": self.status.value,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics": self.metrics,
            "findings": self.findings,
        }


@dataclass
class PhaseTask:
    """A task within a phase."""
    task_id: str
    name: str
    description: str
    phase: Phase

    # Status
    status: TaskStatus = TaskStatus.NOT_STARTED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Progress
    progress_pct: float = 0.0

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)

    # AI checkpoints in this task
    ai_checkpoints: List[str] = field(default_factory=list)

    # Notes
    notes: str = ""
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "phase": self.phase.value,
            "status": self.status.value,
            "progress_pct": self.progress_pct,
            "depends_on": self.depends_on,
            "ai_checkpoints": self.ai_checkpoints,
        }


@dataclass
class PhaseDefinition:
    """Definition of an implementation phase."""
    phase: Phase
    name: str
    description: str
    typical_weeks: int
    tasks: List[PhaseTask] = field(default_factory=list)
    ai_checkpoints: List[AICheckpoint] = field(default_factory=list)

    # Status
    status: TaskStatus = TaskStatus.NOT_STARTED
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Deliverables
    deliverables: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "name": self.name,
            "description": self.description,
            "typical_weeks": self.typical_weeks,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "task_count": len(self.tasks),
            "ai_checkpoint_count": len(self.ai_checkpoints),
            "deliverables": self.deliverables,
        }


@dataclass
class RolloutTimeline:
    """Complete rollout timeline."""
    project_id: str
    project_name: str
    created_at: datetime = field(default_factory=datetime.now)

    # Dates
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None

    # Phases
    phases: List[PhaseDefinition] = field(default_factory=list)

    # Current state
    current_phase: Phase = Phase.MOBILIZATION
    overall_progress: float = 0.0

    # Metrics
    total_tasks: int = 0
    completed_tasks: int = 0
    ai_checkpoints_passed: int = 0
    ai_checkpoints_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "current_phase": self.current_phase.value,
            "overall_progress": round(self.overall_progress, 1),
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "ai_checkpoints": {
                "passed": self.ai_checkpoints_passed,
                "total": self.ai_checkpoints_total,
            },
            "phases": [p.to_dict() for p in self.phases],
        }


class RolloutTimelineTracker:
    """
    Tracks SAP rollout implementation with AI checkpoints.

    Based on the timeline:
    - Phase 0: Mobilization (Week 0-2)
    - Phase 1: Discovery & Baseline (Week 3-6)
    - Phase 2: AI-Assisted Role Design (Week 7-10)
    - Phase 3: Build & Test (Week 11-14)
    - Phase 4: Go-Live & Hypercare (Week 15-18)
    - Phase 5: Continuous Governance (Post Go-Live)
    """

    def __init__(self):
        """Initialize tracker."""
        self._timelines: Dict[str, RolloutTimeline] = {}

    def create_timeline(
        self,
        project_name: str,
        planned_start: datetime,
        user_count: int = 1000
    ) -> RolloutTimeline:
        """
        Create a new rollout timeline.

        Args:
            project_name: Name of the project
            planned_start: Planned start date
            user_count: Number of users in scope

        Returns:
            RolloutTimeline with all phases defined
        """
        project_id = f"PROJ-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        timeline = RolloutTimeline(
            project_id=project_id,
            project_name=project_name,
            planned_start=planned_start,
        )

        # Create phases
        timeline.phases = self._create_phases(planned_start, user_count)

        # Calculate totals
        timeline.total_tasks = sum(len(p.tasks) for p in timeline.phases)
        timeline.ai_checkpoints_total = sum(len(p.ai_checkpoints) for p in timeline.phases)
        timeline.planned_end = planned_start + timedelta(weeks=18)

        self._timelines[project_id] = timeline
        return timeline

    def _create_phases(
        self,
        start_date: datetime,
        user_count: int
    ) -> List[PhaseDefinition]:
        """Create all phase definitions."""
        phases = []

        # Phase 0: Mobilization
        phase0 = PhaseDefinition(
            phase=Phase.MOBILIZATION,
            name="Mobilization",
            description="Prepare data and governance guardrails",
            typical_weeks=2,
            start_date=start_date,
            end_date=start_date + timedelta(weeks=2),
            deliverables=[
                "Access baseline",
                "Initial risk heatmap",
                "Role inventory & ownership map",
            ],
        )
        phase0.tasks = [
            PhaseTask(
                task_id="P0-T1",
                name="Identify in-scope SAP systems",
                description="Document DEV/QA/PRD systems",
                phase=Phase.MOBILIZATION,
            ),
            PhaseTask(
                task_id="P0-T2",
                name="Create read-only extraction users",
                description="Set up technical users for data extraction",
                phase=Phase.MOBILIZATION,
            ),
            PhaseTask(
                task_id="P0-T3",
                name="Freeze current role catalog",
                description="Snapshot current state",
                phase=Phase.MOBILIZATION,
            ),
            PhaseTask(
                task_id="P0-T4",
                name="Define risk appetite",
                description="Set auto-approval thresholds",
                phase=Phase.MOBILIZATION,
            ),
        ]
        phases.append(phase0)

        # Phase 1: Discovery & Baseline
        phase1 = PhaseDefinition(
            phase=Phase.DISCOVERY,
            name="Discovery & Baseline",
            description="Understand how access is actually used",
            typical_weeks=4,
            start_date=start_date + timedelta(weeks=2),
            end_date=start_date + timedelta(weeks=6),
            deliverables=[
                "As-Is usage-based access map",
                "Toxic roles list",
                "Roles with >40% unused permissions",
            ],
        )
        phase1.tasks = [
            PhaseTask(
                task_id="P1-T1",
                name="Extract STAD data",
                description="Collect transaction usage data",
                phase=Phase.DISCOVERY,
                ai_checkpoints=["AI-P1-1"],
            ),
            PhaseTask(
                task_id="P1-T2",
                name="Extract role assignments",
                description="AGR_USERS / AGR_1251",
                phase=Phase.DISCOVERY,
            ),
            PhaseTask(
                task_id="P1-T3",
                name="Run SoD analysis",
                description="Classic + graph-based SoD",
                phase=Phase.DISCOVERY,
                ai_checkpoints=["AI-P1-2", "AI-P1-3"],
            ),
        ]
        phase1.ai_checkpoints = [
            AICheckpoint(
                checkpoint_id="AI-P1-1",
                name="Behavior Clustering",
                checkpoint_type=AICheckpointType.CLUSTERING,
                phase=Phase.DISCOVERY,
                description="Discover real job patterns",
            ),
            AICheckpoint(
                checkpoint_id="AI-P1-2",
                name="Toxic Role Detection",
                checkpoint_type=AICheckpointType.TOXIC_DETECTION,
                phase=Phase.DISCOVERY,
                description="Single-role fraud paths",
            ),
            AICheckpoint(
                checkpoint_id="AI-P1-3",
                name="Privilege Creep Detection",
                checkpoint_type=AICheckpointType.ANOMALY_DETECTION,
                phase=Phase.DISCOVERY,
                description="Identify over-privileged roles",
            ),
        ]
        phases.append(phase1)

        # Phase 2: AI-Assisted Role Design
        phase2 = PhaseDefinition(
            phase=Phase.ROLE_DESIGN,
            name="AI-Assisted Role Design",
            description="Redesign roles based on reality, not assumptions",
            typical_weeks=4,
            start_date=start_date + timedelta(weeks=6),
            end_date=start_date + timedelta(weeks=10),
            deliverables=[
                "Target role model",
                "Risk reduction forecast",
                "Migration plan",
            ],
        )
        phase2.tasks = [
            PhaseTask(
                task_id="P2-T1",
                name="ML cluster users by behavior",
                description="Behavior-based clustering",
                phase=Phase.ROLE_DESIGN,
                ai_checkpoints=["AI-P2-1"],
            ),
            PhaseTask(
                task_id="P2-T2",
                name="Generate role blueprints",
                description="AI-suggested role designs",
                phase=Phase.ROLE_DESIGN,
                ai_checkpoints=["AI-P2-2"],
            ),
            PhaseTask(
                task_id="P2-T3",
                name="Block unsafe designs",
                description="Graph engine validation",
                phase=Phase.ROLE_DESIGN,
                ai_checkpoints=["AI-P2-3"],
            ),
            PhaseTask(
                task_id="P2-T4",
                name="Security & business approval",
                description="Human gate for role designs",
                phase=Phase.ROLE_DESIGN,
            ),
        ]
        phase2.ai_checkpoints = [
            AICheckpoint(
                checkpoint_id="AI-P2-1",
                name="Role Blueprint Generation",
                checkpoint_type=AICheckpointType.ROLE_GENERATION,
                phase=Phase.ROLE_DESIGN,
                description="Generate candidate roles from clusters",
            ),
            AICheckpoint(
                checkpoint_id="AI-P2-2",
                name="Auto SoD Rule Discovery",
                checkpoint_type=AICheckpointType.TOXIC_DETECTION,
                phase=Phase.ROLE_DESIGN,
                description="Discover new SoD rules from data",
            ),
            AICheckpoint(
                checkpoint_id="AI-P2-3",
                name="Risk Delta Simulation",
                checkpoint_type=AICheckpointType.RISK_SIMULATION,
                phase=Phase.ROLE_DESIGN,
                description="Before vs after risk comparison",
            ),
        ]
        phases.append(phase2)

        # Phase 3: Build & Test
        phase3 = PhaseDefinition(
            phase=Phase.BUILD_TEST,
            name="Build & Test",
            description="Validate roles before production",
            typical_weeks=4,
            start_date=start_date + timedelta(weeks=10),
            end_date=start_date + timedelta(weeks=14),
            deliverables=[
                "Approved role catalog",
                "Zero critical SoD at design time",
            ],
        )
        phase3.tasks = [
            PhaseTask(
                task_id="P3-T1",
                name="Build roles in DEV",
                description="Create role objects",
                phase=Phase.BUILD_TEST,
            ),
            PhaseTask(
                task_id="P3-T2",
                name="Simulate assignments",
                description="Pre-provisioning risk simulation",
                phase=Phase.BUILD_TEST,
                ai_checkpoints=["AI-P3-1"],
            ),
            PhaseTask(
                task_id="P3-T3",
                name="Run AI validation",
                description="Drift and toxicity tests",
                phase=Phase.BUILD_TEST,
                ai_checkpoints=["AI-P3-2"],
            ),
        ]
        phase3.ai_checkpoints = [
            AICheckpoint(
                checkpoint_id="AI-P3-1",
                name="Pre-Go-Live Risk Prediction",
                checkpoint_type=AICheckpointType.PREDICTION,
                phase=Phase.BUILD_TEST,
                description="30/60/90 day risk forecast",
            ),
            AICheckpoint(
                checkpoint_id="AI-P3-2",
                name="Auto Role Refactor Validation",
                checkpoint_type=AICheckpointType.RISK_SIMULATION,
                phase=Phase.BUILD_TEST,
                description="Validate refactoring suggestions",
            ),
        ]
        phases.append(phase3)

        # Phase 4: Go-Live & Hypercare
        phase4 = PhaseDefinition(
            phase=Phase.GO_LIVE,
            name="Go-Live & Hypercare",
            description="Controlled rollout with learning loop",
            typical_weeks=4,
            start_date=start_date + timedelta(weeks=14),
            end_date=start_date + timedelta(weeks=18),
            deliverables=[
                "Stable access",
                "No emergency cleanups",
            ],
        )
        phase4.tasks = [
            PhaseTask(
                task_id="P4-T1",
                name="Gradual role assignment",
                description="Phased rollout",
                phase=Phase.GO_LIVE,
            ),
            PhaseTask(
                task_id="P4-T2",
                name="Enable real-time ARA",
                description="Kafka-based processing",
                phase=Phase.GO_LIVE,
                ai_checkpoints=["AI-P4-1"],
            ),
            PhaseTask(
                task_id="P4-T3",
                name="Monitor deviations",
                description="Watch for usage anomalies",
                phase=Phase.GO_LIVE,
                ai_checkpoints=["AI-P4-2"],
            ),
        ]
        phase4.ai_checkpoints = [
            AICheckpoint(
                checkpoint_id="AI-P4-1",
                name="Real-Time Anomaly Detection",
                checkpoint_type=AICheckpointType.ANOMALY_DETECTION,
                phase=Phase.GO_LIVE,
                description="Detect unusual access patterns",
            ),
            AICheckpoint(
                checkpoint_id="AI-P4-2",
                name="Risk-Based Auto-Approval",
                checkpoint_type=AICheckpointType.PREDICTION,
                phase=Phase.GO_LIVE,
                description="Enable low-risk auto-approvals",
            ),
        ]
        phases.append(phase4)

        # Phase 5: Continuous Governance
        phase5 = PhaseDefinition(
            phase=Phase.CONTINUOUS,
            name="Continuous Governance",
            description="Never repeat role redesign projects again",
            typical_weeks=0,  # Ongoing
            start_date=start_date + timedelta(weeks=18),
            deliverables=[
                "Continuous control monitoring",
                "Predictive risk dashboards",
                "Autonomous cleanup",
            ],
        )
        phase5.tasks = [
            PhaseTask(
                task_id="P5-T1",
                name="Enable CCM",
                description="Continuous control monitoring",
                phase=Phase.CONTINUOUS,
            ),
            PhaseTask(
                task_id="P5-T2",
                name="Configure predictive risk",
                description="Risk forecasting dashboards",
                phase=Phase.CONTINUOUS,
                ai_checkpoints=["AI-P5-1"],
            ),
            PhaseTask(
                task_id="P5-T3",
                name="Enable autonomous cleanup",
                description="Policy-gated auto-revocation",
                phase=Phase.CONTINUOUS,
                ai_checkpoints=["AI-P5-2"],
            ),
        ]
        phase5.ai_checkpoints = [
            AICheckpoint(
                checkpoint_id="AI-P5-1",
                name="Predictive Access Risk",
                checkpoint_type=AICheckpointType.PREDICTION,
                phase=Phase.CONTINUOUS,
                description="30/60/90 day forecasting",
            ),
            AICheckpoint(
                checkpoint_id="AI-P5-2",
                name="Autonomous Revocation",
                checkpoint_type=AICheckpointType.ANOMALY_DETECTION,
                phase=Phase.CONTINUOUS,
                description="Guarded auto-cleanup",
            ),
        ]
        phases.append(phase5)

        return phases

    def update_task_status(
        self,
        project_id: str,
        task_id: str,
        status: TaskStatus,
        progress_pct: float = 0.0,
        notes: str = ""
    ) -> bool:
        """Update status of a task."""
        timeline = self._timelines.get(project_id)
        if not timeline:
            return False

        for phase in timeline.phases:
            for task in phase.tasks:
                if task.task_id == task_id:
                    task.status = status
                    task.progress_pct = progress_pct
                    task.notes = notes

                    if status == TaskStatus.IN_PROGRESS and not task.started_at:
                        task.started_at = datetime.now()
                    elif status == TaskStatus.COMPLETED:
                        task.completed_at = datetime.now()
                        task.progress_pct = 100.0
                        timeline.completed_tasks += 1

                    self._update_timeline_progress(timeline)
                    return True

        return False

    def complete_ai_checkpoint(
        self,
        project_id: str,
        checkpoint_id: str,
        results: Dict[str, Any],
        metrics: Dict[str, float],
        findings: List[str]
    ) -> bool:
        """Complete an AI checkpoint."""
        timeline = self._timelines.get(project_id)
        if not timeline:
            return False

        for phase in timeline.phases:
            for checkpoint in phase.ai_checkpoints:
                if checkpoint.checkpoint_id == checkpoint_id:
                    checkpoint.status = TaskStatus.COMPLETED
                    checkpoint.completed_at = datetime.now()
                    checkpoint.results = results
                    checkpoint.metrics = metrics
                    checkpoint.findings = findings
                    timeline.ai_checkpoints_passed += 1

                    self._update_timeline_progress(timeline)
                    return True

        return False

    def _update_timeline_progress(self, timeline: RolloutTimeline) -> None:
        """Update overall progress calculation."""
        total_weight = 0
        completed_weight = 0

        for phase in timeline.phases:
            phase_weight = len(phase.tasks) + len(phase.ai_checkpoints)
            phase_completed = (
                sum(1 for t in phase.tasks if t.status == TaskStatus.COMPLETED) +
                sum(1 for c in phase.ai_checkpoints if c.status == TaskStatus.COMPLETED)
            )

            total_weight += phase_weight
            completed_weight += phase_completed

            # Update phase status
            if phase_completed == phase_weight:
                phase.status = TaskStatus.COMPLETED
            elif phase_completed > 0:
                phase.status = TaskStatus.IN_PROGRESS

        if total_weight > 0:
            timeline.overall_progress = completed_weight / total_weight * 100

        # Update current phase
        for phase in timeline.phases:
            if phase.status == TaskStatus.IN_PROGRESS:
                timeline.current_phase = phase.phase
                break
            elif phase.status == TaskStatus.NOT_STARTED:
                timeline.current_phase = phase.phase
                break

    def get_timeline(self, project_id: str) -> Optional[RolloutTimeline]:
        """Get a timeline by ID."""
        return self._timelines.get(project_id)

    def get_phase_status(
        self,
        project_id: str,
        phase: Phase
    ) -> Optional[Dict[str, Any]]:
        """Get detailed status for a phase."""
        timeline = self._timelines.get(project_id)
        if not timeline:
            return None

        for p in timeline.phases:
            if p.phase == phase:
                tasks_completed = sum(
                    1 for t in p.tasks if t.status == TaskStatus.COMPLETED
                )
                checkpoints_completed = sum(
                    1 for c in p.ai_checkpoints if c.status == TaskStatus.COMPLETED
                )

                return {
                    "phase": phase.value,
                    "name": p.name,
                    "status": p.status.value,
                    "tasks": {
                        "total": len(p.tasks),
                        "completed": tasks_completed,
                        "in_progress": sum(
                            1 for t in p.tasks if t.status == TaskStatus.IN_PROGRESS
                        ),
                    },
                    "ai_checkpoints": {
                        "total": len(p.ai_checkpoints),
                        "passed": checkpoints_completed,
                    },
                    "deliverables": p.deliverables,
                }

        return None

    def get_ai_checkpoint_summary(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Get summary of all AI checkpoints."""
        timeline = self._timelines.get(project_id)
        if not timeline:
            return {}

        checkpoints = []
        for phase in timeline.phases:
            for checkpoint in phase.ai_checkpoints:
                checkpoints.append({
                    "id": checkpoint.checkpoint_id,
                    "name": checkpoint.name,
                    "type": checkpoint.checkpoint_type.value,
                    "phase": checkpoint.phase.value,
                    "status": checkpoint.status.value,
                    "metrics": checkpoint.metrics,
                })

        return {
            "total": len(checkpoints),
            "completed": sum(1 for c in checkpoints if c["status"] == "COMPLETED"),
            "checkpoints": checkpoints,
        }
