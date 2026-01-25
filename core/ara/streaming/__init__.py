# ARA Streaming Module
# Real-time risk evaluation via Kafka

"""
Kafka-based Real-Time Risk Evaluation for GOVERNEX+.

Provides:
- Event-driven risk evaluation
- Real-time access monitoring
- Firefighter session tracking
- Streaming analytics

Architecture:
- Kafka consumers for access events
- Real-time rule evaluation
- Risk results publishing
- Audit trail generation

Topics:
- access-events: Access requests and changes
- firefighter-events: Privileged session activity
- risk-results: Evaluated risk outcomes
- audit-events: Immutable audit trail
"""

from .events import (
    AccessEvent,
    FirefighterEvent,
    RiskResultEvent,
    AuditEvent,
    EventType,
)
from .consumer import (
    ARAKafkaConsumer,
    create_consumer,
)
from .producer import (
    ARAKafkaProducer,
    create_producer,
)
from .pipeline import (
    ARARealTimePipeline,
    PipelineConfig,
)

__all__ = [
    # Events
    "AccessEvent",
    "FirefighterEvent",
    "RiskResultEvent",
    "AuditEvent",
    "EventType",
    # Consumer
    "ARAKafkaConsumer",
    "create_consumer",
    # Producer
    "ARAKafkaProducer",
    "create_producer",
    # Pipeline
    "ARARealTimePipeline",
    "PipelineConfig",
]
