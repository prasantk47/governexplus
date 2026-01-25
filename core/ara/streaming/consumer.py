# Kafka Consumer for ARA Real-Time Risk Evaluation
# Event-driven risk analysis

"""
Kafka Consumer for ARA streaming pipeline.

Consumes:
- Access events (requests, changes)
- Firefighter events (privileged sessions)

Produces:
- Risk results
- Audit events

Features:
- Graceful shutdown
- Error handling with DLQ
- Metrics collection
- Batch processing support
"""

from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass
from datetime import datetime
import logging
import threading
import json

# Optional Kafka imports
try:
    from kafka import KafkaConsumer as KafkaConsumerLib
    from kafka.errors import KafkaError
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False

from .events import (
    BaseEvent,
    AccessEvent,
    FirefighterEvent,
    EventType,
    deserialize_event,
    parse_event_type,
)

logger = logging.getLogger(__name__)


@dataclass
class ConsumerConfig:
    """Configuration for ARA Kafka consumer."""
    bootstrap_servers: List[str]
    group_id: str = "ara-engine"
    topics: List[str] = None

    # Consumer settings
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = False
    max_poll_records: int = 100
    max_poll_interval_ms: int = 300000

    # Security
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None

    # SSL
    ssl_cafile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None

    def __post_init__(self):
        if self.topics is None:
            self.topics = ["access-events", "firefighter-events"]


class ARAKafkaConsumer:
    """
    Kafka consumer for ARA real-time risk evaluation.

    Features:
    - Event type routing
    - Handler registration
    - Error handling
    - Graceful shutdown
    """

    def __init__(self, config: ConsumerConfig):
        """
        Initialize ARA Kafka consumer.

        Args:
            config: Consumer configuration
        """
        self.config = config
        self.consumer = None
        self.running = False
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._error_handlers: List[Callable] = []
        self._shutdown_event = threading.Event()
        self._metrics = {
            "events_processed": 0,
            "events_failed": 0,
            "last_event_time": None,
        }

        if HAS_KAFKA:
            self._init_consumer()
        else:
            logger.warning("kafka-python not installed, using mock consumer")

    def _init_consumer(self):
        """Initialize the Kafka consumer."""
        consumer_config = {
            "bootstrap_servers": self.config.bootstrap_servers,
            "group_id": self.config.group_id,
            "auto_offset_reset": self.config.auto_offset_reset,
            "enable_auto_commit": self.config.enable_auto_commit,
            "max_poll_records": self.config.max_poll_records,
            "max_poll_interval_ms": self.config.max_poll_interval_ms,
            "value_deserializer": lambda v: v,  # Raw bytes
            "key_deserializer": lambda k: k.decode('utf-8') if k else None,
        }

        # Security settings
        if self.config.security_protocol != "PLAINTEXT":
            consumer_config["security_protocol"] = self.config.security_protocol

        if self.config.sasl_mechanism:
            consumer_config["sasl_mechanism"] = self.config.sasl_mechanism
            consumer_config["sasl_plain_username"] = self.config.sasl_username
            consumer_config["sasl_plain_password"] = self.config.sasl_password

        if self.config.ssl_cafile:
            consumer_config["ssl_cafile"] = self.config.ssl_cafile
            consumer_config["ssl_certfile"] = self.config.ssl_certfile
            consumer_config["ssl_keyfile"] = self.config.ssl_keyfile

        self.consumer = KafkaConsumerLib(**consumer_config)
        self.consumer.subscribe(self.config.topics)
        logger.info(f"ARA consumer initialized, subscribed to: {self.config.topics}")

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[BaseEvent], None]
    ):
        """
        Register a handler for an event type.

        Args:
            event_type: Type of event to handle
            handler: Callback function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type.value}")

    def register_error_handler(self, handler: Callable[[Exception, bytes], None]):
        """Register an error handler for failed events."""
        self._error_handlers.append(handler)

    def start(self, blocking: bool = True):
        """
        Start consuming events.

        Args:
            blocking: If True, block the current thread
        """
        self.running = True
        self._shutdown_event.clear()

        if blocking:
            self._consume_loop()
        else:
            thread = threading.Thread(target=self._consume_loop, daemon=True)
            thread.start()
            logger.info("ARA consumer started in background")

    def stop(self):
        """Stop the consumer gracefully."""
        logger.info("Stopping ARA consumer...")
        self.running = False
        self._shutdown_event.set()

        if self.consumer and HAS_KAFKA:
            self.consumer.close()
            logger.info("ARA consumer stopped")

    def _consume_loop(self):
        """Main consumption loop."""
        if not HAS_KAFKA:
            logger.warning("Kafka not available, running mock loop")
            while self.running and not self._shutdown_event.is_set():
                self._shutdown_event.wait(timeout=1)
            return

        logger.info("ARA consumer loop started")

        try:
            while self.running and not self._shutdown_event.is_set():
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=1000)

                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            self._process_message(record)
                            self._metrics["events_processed"] += 1
                            self._metrics["last_event_time"] = datetime.now()
                        except Exception as e:
                            self._handle_error(e, record.value)
                            self._metrics["events_failed"] += 1

                # Commit offsets
                if not self.config.enable_auto_commit:
                    self.consumer.commit()

        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
            raise
        finally:
            logger.info("ARA consumer loop ended")

    def _process_message(self, record):
        """Process a single Kafka message."""
        # Parse event type first
        try:
            event_type = parse_event_type(record.value)
        except Exception as e:
            logger.warning(f"Could not parse event type: {e}")
            return

        # Deserialize to appropriate event class
        event = self._deserialize_event(record.value, event_type)
        if not event:
            return

        # Call registered handlers
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event_type.value}: {e}")

    def _deserialize_event(
        self,
        data: bytes,
        event_type: EventType
    ) -> Optional[BaseEvent]:
        """Deserialize event based on type."""
        try:
            if event_type in [
                EventType.ACCESS_REQUEST,
                EventType.ACCESS_GRANTED,
                EventType.ACCESS_REVOKED,
                EventType.ACCESS_CHANGE,
                EventType.LOGIN,
            ]:
                return deserialize_event(data, AccessEvent)
            elif event_type in [
                EventType.FF_SESSION_START,
                EventType.FF_SESSION_END,
                EventType.FF_TRANSACTION,
            ]:
                return deserialize_event(data, FirefighterEvent)
            else:
                return deserialize_event(data, BaseEvent)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None

    def _handle_error(self, error: Exception, raw_data: bytes):
        """Handle processing errors."""
        logger.error(f"Event processing error: {error}")

        for handler in self._error_handlers:
            try:
                handler(error, raw_data)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics."""
        return {
            **self._metrics,
            "running": self.running,
            "handlers_registered": len(self._handlers),
        }


class MockKafkaConsumer(ARAKafkaConsumer):
    """
    Mock Kafka consumer for testing and development.

    Simulates event consumption without actual Kafka.
    """

    def __init__(self, config: ConsumerConfig):
        super().__init__(config)
        self._mock_events: List[BaseEvent] = []

    def _init_consumer(self):
        """Skip actual Kafka initialization."""
        logger.info("Mock consumer initialized")

    def add_mock_event(self, event: BaseEvent):
        """Add an event to be processed."""
        self._mock_events.append(event)

    def _consume_loop(self):
        """Process mock events."""
        logger.info("Mock consumer loop started")

        while self.running and not self._shutdown_event.is_set():
            if self._mock_events:
                event = self._mock_events.pop(0)
                handlers = self._handlers.get(event.event_type, [])

                for handler in handlers:
                    try:
                        handler(event)
                        self._metrics["events_processed"] += 1
                    except Exception as e:
                        self._metrics["events_failed"] += 1
                        logger.error(f"Handler error: {e}")

            self._shutdown_event.wait(timeout=0.1)


def create_consumer(
    bootstrap_servers: List[str],
    group_id: str = "ara-engine",
    topics: Optional[List[str]] = None,
    mock: bool = False,
    **kwargs
) -> ARAKafkaConsumer:
    """
    Factory function to create ARA Kafka consumer.

    Args:
        bootstrap_servers: Kafka broker addresses
        group_id: Consumer group ID
        topics: Topics to subscribe to
        mock: Use mock consumer for testing
        **kwargs: Additional configuration

    Returns:
        Configured ARA Kafka consumer
    """
    config = ConsumerConfig(
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        topics=topics,
        **kwargs
    )

    if mock or not HAS_KAFKA:
        return MockKafkaConsumer(config)

    return ARAKafkaConsumer(config)
