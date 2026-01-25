# Kafka Producer for ARA Risk Results
# Publishing risk evaluation outcomes

"""
Kafka Producer for ARA streaming pipeline.

Publishes:
- Risk evaluation results
- Audit events
- Alerts for critical risks

Features:
- Asynchronous publishing
- Retry logic
- Delivery confirmation
- Metrics collection
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import threading

# Optional Kafka imports
try:
    from kafka import KafkaProducer as KafkaProducerLib
    from kafka.errors import KafkaError
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False

from .events import (
    BaseEvent,
    RiskResultEvent,
    AuditEvent,
    serialize_event,
)

logger = logging.getLogger(__name__)


@dataclass
class ProducerConfig:
    """Configuration for ARA Kafka producer."""
    bootstrap_servers: List[str]

    # Producer settings
    acks: str = "all"  # Wait for all replicas
    retries: int = 3
    retry_backoff_ms: int = 100
    batch_size: int = 16384
    linger_ms: int = 10
    compression_type: str = "snappy"

    # Timeouts
    request_timeout_ms: int = 30000
    delivery_timeout_ms: int = 120000

    # Security
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None

    # SSL
    ssl_cafile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None


class ARAKafkaProducer:
    """
    Kafka producer for ARA risk results.

    Features:
    - Async publishing with callbacks
    - Topic routing
    - Error handling
    - Metrics collection
    """

    # Topic names
    TOPIC_RISK_RESULTS = "risk-results"
    TOPIC_AUDIT = "audit-events"
    TOPIC_ALERTS = "risk-alerts"

    def __init__(self, config: ProducerConfig):
        """
        Initialize ARA Kafka producer.

        Args:
            config: Producer configuration
        """
        self.config = config
        self.producer = None
        self._callbacks: Dict[str, List[Callable]] = {
            "success": [],
            "error": [],
        }
        self._metrics = {
            "events_sent": 0,
            "events_failed": 0,
            "last_send_time": None,
        }
        self._lock = threading.Lock()

        if HAS_KAFKA:
            self._init_producer()
        else:
            logger.warning("kafka-python not installed, using mock producer")

    def _init_producer(self):
        """Initialize the Kafka producer."""
        producer_config = {
            "bootstrap_servers": self.config.bootstrap_servers,
            "acks": self.config.acks,
            "retries": self.config.retries,
            "retry_backoff_ms": self.config.retry_backoff_ms,
            "batch_size": self.config.batch_size,
            "linger_ms": self.config.linger_ms,
            "compression_type": self.config.compression_type,
            "request_timeout_ms": self.config.request_timeout_ms,
            "value_serializer": lambda v: v,  # Already serialized
            "key_serializer": lambda k: k.encode('utf-8') if k else None,
        }

        # Security settings
        if self.config.security_protocol != "PLAINTEXT":
            producer_config["security_protocol"] = self.config.security_protocol

        if self.config.sasl_mechanism:
            producer_config["sasl_mechanism"] = self.config.sasl_mechanism
            producer_config["sasl_plain_username"] = self.config.sasl_username
            producer_config["sasl_plain_password"] = self.config.sasl_password

        if self.config.ssl_cafile:
            producer_config["ssl_cafile"] = self.config.ssl_cafile
            producer_config["ssl_certfile"] = self.config.ssl_certfile
            producer_config["ssl_keyfile"] = self.config.ssl_keyfile

        self.producer = KafkaProducerLib(**producer_config)
        logger.info("ARA producer initialized")

    def register_callback(
        self,
        event: str,  # "success" or "error"
        callback: Callable
    ):
        """Register callback for send events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def send_risk_result(
        self,
        result: RiskResultEvent,
        key: Optional[str] = None
    ):
        """
        Send risk evaluation result.

        Args:
            result: Risk result event
            key: Optional partition key (default: user_id)
        """
        key = key or result.user_id
        self._send(self.TOPIC_RISK_RESULTS, result, key)

        # Send to alerts topic if critical
        if result.critical_count > 0 or result.recommendation == "deny":
            self._send(self.TOPIC_ALERTS, result, key)

    def send_audit_event(
        self,
        event: AuditEvent,
        key: Optional[str] = None
    ):
        """
        Send audit event.

        Args:
            event: Audit event
            key: Optional partition key
        """
        key = key or event.subject_id
        self._send(self.TOPIC_AUDIT, event, key)

    def send_event(
        self,
        topic: str,
        event: BaseEvent,
        key: Optional[str] = None
    ):
        """
        Send any event to specified topic.

        Args:
            topic: Target topic
            event: Event to send
            key: Optional partition key
        """
        self._send(topic, event, key)

    def _send(
        self,
        topic: str,
        event: BaseEvent,
        key: Optional[str] = None
    ):
        """Internal send method."""
        if not HAS_KAFKA or not self.producer:
            logger.debug(f"Mock send to {topic}: {event.event_type.value}")
            with self._lock:
                self._metrics["events_sent"] += 1
                self._metrics["last_send_time"] = datetime.now()
            return

        try:
            data = serialize_event(event)

            future = self.producer.send(
                topic,
                value=data,
                key=key
            )

            # Add callback for async confirmation
            future.add_callback(
                lambda metadata: self._on_success(event, metadata)
            )
            future.add_errback(
                lambda exc: self._on_error(event, exc)
            )

        except Exception as e:
            logger.error(f"Error sending to {topic}: {e}")
            self._on_error(event, e)

    def _on_success(self, event: BaseEvent, metadata):
        """Handle successful send."""
        with self._lock:
            self._metrics["events_sent"] += 1
            self._metrics["last_send_time"] = datetime.now()

        for callback in self._callbacks["success"]:
            try:
                callback(event, metadata)
            except Exception as e:
                logger.error(f"Success callback error: {e}")

    def _on_error(self, event: BaseEvent, error: Exception):
        """Handle send error."""
        with self._lock:
            self._metrics["events_failed"] += 1

        logger.error(f"Send failed for {event.event_id}: {error}")

        for callback in self._callbacks["error"]:
            try:
                callback(event, error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")

    def flush(self, timeout: float = 30.0):
        """Flush pending messages."""
        if self.producer and HAS_KAFKA:
            self.producer.flush(timeout=timeout)
            logger.debug("Producer flushed")

    def close(self):
        """Close the producer."""
        if self.producer and HAS_KAFKA:
            self.producer.flush()
            self.producer.close()
            logger.info("ARA producer closed")

    def get_metrics(self) -> Dict[str, Any]:
        """Get producer metrics."""
        with self._lock:
            return {**self._metrics}


class MockKafkaProducer(ARAKafkaProducer):
    """
    Mock Kafka producer for testing.

    Collects sent events for verification.
    """

    def __init__(self, config: ProducerConfig):
        super().__init__(config)
        self._sent_events: List[Dict[str, Any]] = []

    def _init_producer(self):
        """Skip actual Kafka initialization."""
        logger.info("Mock producer initialized")

    def _send(
        self,
        topic: str,
        event: BaseEvent,
        key: Optional[str] = None
    ):
        """Store event instead of sending."""
        self._sent_events.append({
            "topic": topic,
            "event": event,
            "key": key,
            "timestamp": datetime.now(),
        })

        with self._lock:
            self._metrics["events_sent"] += 1
            self._metrics["last_send_time"] = datetime.now()

        logger.debug(f"Mock sent to {topic}: {event.event_type.value}")

    def get_sent_events(self) -> List[Dict[str, Any]]:
        """Get all sent events (for testing)."""
        return self._sent_events

    def clear_sent_events(self):
        """Clear sent events list."""
        self._sent_events.clear()


def create_producer(
    bootstrap_servers: List[str],
    mock: bool = False,
    **kwargs
) -> ARAKafkaProducer:
    """
    Factory function to create ARA Kafka producer.

    Args:
        bootstrap_servers: Kafka broker addresses
        mock: Use mock producer for testing
        **kwargs: Additional configuration

    Returns:
        Configured ARA Kafka producer
    """
    config = ProducerConfig(
        bootstrap_servers=bootstrap_servers,
        **kwargs
    )

    if mock or not HAS_KAFKA:
        return MockKafkaProducer(config)

    return ARAKafkaProducer(config)
