# ARA Real-Time Risk Evaluation Pipeline
# Orchestrates streaming risk analysis

"""
Real-Time Risk Evaluation Pipeline for GOVERNEX+.

Orchestrates:
- Event consumption from Kafka
- ML-enhanced risk evaluation
- Result publishing
- Audit trail generation

This is the core integration that makes GOVERNEX+ superior to SAP GRC:
- Sub-second risk evaluation
- ML-assisted anomaly detection
- Context-aware scoring
- Real-time alerts
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from .events import (
    BaseEvent,
    AccessEvent,
    FirefighterEvent,
    RiskResultEvent,
    AuditEvent,
    EventType,
)
from .consumer import ARAKafkaConsumer, ConsumerConfig, create_consumer
from .producer import ARAKafkaProducer, ProducerConfig, create_producer

# Import ARA engine components
from ..engine import AccessRiskEngine
from ..models import RiskContext, UserContext
from ..ml.features import FeatureExtractor, BehaviorFeatureVector, extract_session_features
from ..ml.anomaly_scorer import AnomalyScorer, AnomalyResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the ARA real-time pipeline."""
    # Kafka settings
    bootstrap_servers: List[str]
    consumer_group: str = "ara-engine"
    input_topics: List[str] = None
    output_topic: str = "risk-results"
    audit_topic: str = "audit-events"

    # Processing settings
    enable_ml: bool = True
    enable_peer_analysis: bool = True
    parallel_workers: int = 4

    # Performance settings
    batch_size: int = 1
    processing_timeout_ms: int = 5000

    # Security (optional)
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None

    def __post_init__(self):
        if self.input_topics is None:
            self.input_topics = ["access-events", "firefighter-events"]


class ARARealTimePipeline:
    """
    Real-time risk evaluation pipeline.

    Integrates:
    - Kafka consumer/producer
    - ARA rule engine
    - ML anomaly scorer
    - Audit logging

    This is the heart of GOVERNEX+ real-time intelligence.
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize the ARA pipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.running = False

        # Initialize components
        self.ara_engine = AccessRiskEngine()
        self.feature_extractor = FeatureExtractor()
        self.anomaly_scorer = AnomalyScorer()

        # Kafka components (lazy initialization)
        self.consumer: Optional[ARAKafkaConsumer] = None
        self.producer: Optional[ARAKafkaProducer] = None

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=config.parallel_workers)

        # Metrics
        self._metrics = {
            "events_received": 0,
            "events_processed": 0,
            "events_failed": 0,
            "avg_processing_ms": 0,
            "ml_adjustments_applied": 0,
            "critical_risks_detected": 0,
            "start_time": None,
        }
        self._lock = threading.Lock()

        # Event hooks
        self._hooks: Dict[str, List[Callable]] = {
            "pre_process": [],
            "post_process": [],
            "on_critical_risk": [],
            "on_error": [],
        }

    def register_hook(self, event: str, callback: Callable):
        """
        Register a hook for pipeline events.

        Args:
            event: Hook event name
            callback: Callback function
        """
        if event in self._hooks:
            self._hooks[event].append(callback)

    def start(self, blocking: bool = True, mock: bool = False):
        """
        Start the pipeline.

        Args:
            blocking: Block current thread if True
            mock: Use mock Kafka for testing
        """
        logger.info("Starting ARA real-time pipeline...")
        self.running = True
        self._metrics["start_time"] = datetime.now()

        # Initialize Kafka components
        self._init_kafka(mock)

        # Register event handlers
        self._register_handlers()

        # Start consumer
        self.consumer.start(blocking=blocking)

    def stop(self):
        """Stop the pipeline gracefully."""
        logger.info("Stopping ARA pipeline...")
        self.running = False

        if self.consumer:
            self.consumer.stop()

        if self.producer:
            self.producer.flush()
            self.producer.close()

        self.executor.shutdown(wait=True)
        logger.info("ARA pipeline stopped")

    def _init_kafka(self, mock: bool = False):
        """Initialize Kafka consumer and producer."""
        # Consumer
        self.consumer = create_consumer(
            bootstrap_servers=self.config.bootstrap_servers,
            group_id=self.config.consumer_group,
            topics=self.config.input_topics,
            mock=mock,
            security_protocol=self.config.security_protocol,
            sasl_mechanism=self.config.sasl_mechanism,
            sasl_username=self.config.sasl_username,
            sasl_password=self.config.sasl_password,
        )

        # Producer
        self.producer = create_producer(
            bootstrap_servers=self.config.bootstrap_servers,
            mock=mock,
            security_protocol=self.config.security_protocol,
            sasl_mechanism=self.config.sasl_mechanism,
            sasl_username=self.config.sasl_username,
            sasl_password=self.config.sasl_password,
        )

    def _register_handlers(self):
        """Register event type handlers with consumer."""
        # Access events
        for event_type in [
            EventType.ACCESS_REQUEST,
            EventType.ACCESS_GRANTED,
            EventType.ACCESS_CHANGE,
            EventType.LOGIN,
        ]:
            self.consumer.register_handler(
                event_type,
                self._handle_access_event
            )

        # Firefighter events
        for event_type in [
            EventType.FF_SESSION_START,
            EventType.FF_TRANSACTION,
            EventType.FF_SESSION_END,
        ]:
            self.consumer.register_handler(
                event_type,
                self._handle_firefighter_event
            )

        # Error handler
        self.consumer.register_error_handler(self._handle_error)

    def _handle_access_event(self, event: AccessEvent):
        """
        Handle access-related events.

        This is the main entry point for real-time risk evaluation.
        """
        start_time = datetime.now()
        with self._lock:
            self._metrics["events_received"] += 1

        try:
            # Pre-process hooks
            for hook in self._hooks["pre_process"]:
                hook(event)

            # Build context
            context = self._build_context(event)
            access_map = self._build_access_map(event)

            # Run ARA analysis
            result = self.ara_engine.analyze_user(
                user_id=event.user_id,
                access=access_map,
                context=context
            )

            # ML enhancement
            ml_result = None
            if self.config.enable_ml and self.anomaly_scorer.is_trained:
                ml_result = self._run_ml_scoring(event)

            # Build result event
            risk_event = self._build_risk_result(event, result, ml_result)

            # Publish results
            self.producer.send_risk_result(risk_event)

            # Generate audit event
            self._emit_audit_event(event, risk_event)

            # Check for critical risks
            if risk_event.critical_count > 0:
                self._handle_critical_risk(risk_event)

            # Post-process hooks
            for hook in self._hooks["post_process"]:
                hook(event, risk_event)

            # Update metrics
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics(duration, risk_event)

        except Exception as e:
            logger.error(f"Error processing access event: {e}")
            self._handle_error(e, event)

    def _handle_firefighter_event(self, event: FirefighterEvent):
        """
        Handle firefighter session events.

        High-priority monitoring for privileged access.
        """
        start_time = datetime.now()
        with self._lock:
            self._metrics["events_received"] += 1

        try:
            # Pre-process hooks
            for hook in self._hooks["pre_process"]:
                hook(event)

            # Build risk result for FF activity
            risk_event = RiskResultEvent(
                original_event_id=event.event_id,
                correlation_id=event.session_id,
                user_id=event.real_user_id,
                system=event.system,
            )

            # Check for restricted activity
            if event.is_restricted_tcode:
                risk_event.critical_count = 1
                risk_event.aggregate_risk_score = 85
                risk_event.recommendation = "review"
                risk_event.recommendation_reason = f"Restricted tcode {event.tcode} executed during firefighter session"

            if event.is_table_access and event.is_change:
                risk_event.high_count += 1
                risk_event.aggregate_risk_score = max(
                    risk_event.aggregate_risk_score, 70
                )
                risk_event.risks.append({
                    "type": "TABLE_MODIFICATION",
                    "table": event.table_name,
                    "change_type": event.change_type,
                    "severity": "HIGH",
                })

            risk_event.total_risks = (
                risk_event.critical_count +
                risk_event.high_count +
                risk_event.medium_count +
                risk_event.low_count
            )

            # Publish
            self.producer.send_risk_result(risk_event)
            self._emit_ff_audit_event(event, risk_event)

            if risk_event.critical_count > 0:
                self._handle_critical_risk(risk_event)

            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics(duration, risk_event)

        except Exception as e:
            logger.error(f"Error processing firefighter event: {e}")
            self._handle_error(e, event)

    def _build_context(self, event: AccessEvent) -> RiskContext:
        """Build risk context from event."""
        user_ctx = UserContext(
            user_id=event.user_id,
            department=event.department,
            current_location=event.context.get("location", "unknown"),
            is_business_hours=event.context.get("business_hours", True),
            device_trust_level=("high" if event.context.get("device_trusted", True)
                               else "low"),
        )

        return RiskContext(
            user_context=user_ctx,
            system_id=event.system,
        )

    def _build_access_map(self, event: AccessEvent) -> Dict[str, Any]:
        """Build access map from event."""
        return {
            "roles": event.roles + event.requested_roles,
            "tcodes": event.entitlements + event.requested_entitlements,
            "auth_objects": [],
            "system_id": event.system,
        }

    def _run_ml_scoring(self, event: AccessEvent) -> Optional[AnomalyResult]:
        """Run ML anomaly scoring on event."""
        try:
            # Build feature vector from event
            session_events = event.usage_snapshot.get("recent_transactions", [])

            features = extract_session_features(
                user_id=event.user_id,
                session_events=session_events,
                context={
                    "assigned_access": {
                        "roles": event.roles,
                        "tcodes": event.entitlements,
                    }
                }
            )

            # Score
            result = self.anomaly_scorer.score(features)

            if result.risk_adjustment > 0:
                with self._lock:
                    self._metrics["ml_adjustments_applied"] += 1

            return result

        except Exception as e:
            logger.warning(f"ML scoring failed: {e}")
            return None

    def _build_risk_result(
        self,
        event: AccessEvent,
        ara_result,
        ml_result: Optional[AnomalyResult]
    ) -> RiskResultEvent:
        """Build risk result event from analysis."""
        risk_event = RiskResultEvent(
            analysis_id=ara_result.analysis_id,
            original_event_id=event.event_id,
            correlation_id=event.correlation_id,
            user_id=event.user_id,
            system=event.system,
            total_risks=ara_result.total_risks,
            critical_count=ara_result.critical_count,
            high_count=ara_result.high_count,
            medium_count=ara_result.medium_count,
            low_count=ara_result.low_count,
            aggregate_risk_score=ara_result.aggregate_risk_score,
            max_risk_score=ara_result.max_risk_score,
            risks=[r.to_dict() for r in ara_result.risks],
            sod_conflicts=[c.to_dict() for c in ara_result.sod_conflicts],
            evaluation_duration_ms=ara_result.duration_ms,
        )

        # Add ML insights
        if ml_result:
            risk_event.ml_risk_adjustment = ml_result.risk_adjustment
            risk_event.anomaly_detected = ml_result.is_anomaly
            risk_event.anomaly_explanation = ml_result.explanation

            # Adjust aggregate score
            risk_event.aggregate_risk_score = min(
                100,
                risk_event.aggregate_risk_score + ml_result.risk_adjustment
            )

        # Generate recommendation
        risk_event.recommendation, risk_event.recommendation_reason = (
            self._generate_recommendation(risk_event)
        )

        return risk_event

    def _generate_recommendation(
        self,
        result: RiskResultEvent
    ) -> tuple:
        """Generate recommendation based on risk results."""
        if result.critical_count > 0:
            return "deny", f"Critical risks detected: {result.critical_count}"

        if result.high_count > 2:
            return "review", f"Multiple high-severity risks: {result.high_count}"

        if result.aggregate_risk_score > 70:
            return "review", f"High aggregate risk score: {result.aggregate_risk_score}"

        if result.anomaly_detected:
            return "review", f"Behavioral anomaly: {result.anomaly_explanation}"

        return "approve", "Risk within acceptable limits"

    def _emit_audit_event(
        self,
        input_event: AccessEvent,
        result: RiskResultEvent
    ):
        """Emit audit event for risk evaluation."""
        audit = AuditEvent(
            correlation_id=input_event.correlation_id,
            action="risk_evaluated",
            action_category="risk",
            subject_type="user",
            subject_id=input_event.user_id,
            actor_id="ara_engine",
            actor_type="system",
            details={
                "input_event_id": input_event.event_id,
                "analysis_id": result.analysis_id,
                "total_risks": result.total_risks,
                "aggregate_score": result.aggregate_risk_score,
                "recommendation": result.recommendation,
                "ml_adjustment": result.ml_risk_adjustment,
            },
        )
        self.producer.send_audit_event(audit)

    def _emit_ff_audit_event(
        self,
        input_event: FirefighterEvent,
        result: RiskResultEvent
    ):
        """Emit audit event for firefighter activity."""
        audit = AuditEvent(
            correlation_id=input_event.session_id,
            action="ff_activity_evaluated",
            action_category="risk",
            subject_type="user",
            subject_id=input_event.real_user_id,
            actor_id="ara_engine",
            actor_type="system",
            details={
                "session_id": input_event.session_id,
                "ff_user": input_event.ff_user_id,
                "tcode": input_event.tcode,
                "risk_score": result.aggregate_risk_score,
                "is_restricted": input_event.is_restricted_tcode,
            },
            compliance_tags=["SOX", "privileged_access"],
        )
        self.producer.send_audit_event(audit)

    def _handle_critical_risk(self, result: RiskResultEvent):
        """Handle detection of critical risks."""
        with self._lock:
            self._metrics["critical_risks_detected"] += 1

        logger.warning(
            f"CRITICAL RISK: User {result.user_id} - "
            f"{result.critical_count} critical, score {result.aggregate_risk_score}"
        )

        # Notify hooks
        for hook in self._hooks["on_critical_risk"]:
            try:
                hook(result)
            except Exception as e:
                logger.error(f"Critical risk hook error: {e}")

    def _handle_error(self, error: Exception, event: Optional[BaseEvent] = None):
        """Handle processing errors."""
        with self._lock:
            self._metrics["events_failed"] += 1

        logger.error(f"Pipeline error: {error}")

        # Notify hooks
        for hook in self._hooks["on_error"]:
            try:
                hook(error, event)
            except Exception as e:
                logger.error(f"Error hook failed: {e}")

    def _update_metrics(self, duration_ms: float, result: RiskResultEvent):
        """Update pipeline metrics."""
        with self._lock:
            self._metrics["events_processed"] += 1

            # Rolling average processing time
            n = self._metrics["events_processed"]
            current_avg = self._metrics["avg_processing_ms"]
            self._metrics["avg_processing_ms"] = (
                (current_avg * (n - 1) + duration_ms) / n
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics."""
        with self._lock:
            metrics = {**self._metrics}

        # Add uptime
        if metrics["start_time"]:
            uptime = datetime.now() - metrics["start_time"]
            metrics["uptime_seconds"] = uptime.total_seconds()
            metrics["events_per_second"] = (
                metrics["events_processed"] / uptime.total_seconds()
                if uptime.total_seconds() > 0 else 0
            )

        return metrics

    def train_ml_model(self, historical_vectors: List[BehaviorFeatureVector]):
        """
        Train the ML anomaly scorer.

        Args:
            historical_vectors: Historical behavior data for training
        """
        result = self.anomaly_scorer.train(historical_vectors)
        logger.info(f"ML model trained: {result}")
        return result


def create_pipeline(
    bootstrap_servers: List[str],
    **kwargs
) -> ARARealTimePipeline:
    """
    Factory function to create ARA pipeline.

    Args:
        bootstrap_servers: Kafka broker addresses
        **kwargs: Additional configuration

    Returns:
        Configured pipeline
    """
    config = PipelineConfig(
        bootstrap_servers=bootstrap_servers,
        **kwargs
    )
    return ARARealTimePipeline(config)
