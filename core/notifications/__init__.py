# Notification Service Module
from .service import (
    NotificationService, Notification, NotificationType,
    NotificationChannel, NotificationTemplate, NotificationPreference
)

from .template_engine import (
    NotificationTemplateEngine,
    template_engine,
    NotificationMessage,
    EventType,
    NotificationPriority
)

from .delivery import (
    NotificationDeliveryEngine,
    DeliveryRecord,
    DeliveryStatus,
    DeliveryChannel,
    NotificationType as DeliveryNotificationType,
    Notification as DeliveryNotification,
    EmailPayload,
    SlackPayload,
    get_delivery_engine,
)

__all__ = [
    # Service
    "NotificationService",
    "Notification",
    "NotificationType",
    "NotificationChannel",
    "NotificationTemplate",
    "NotificationPreference",
    # Template Engine
    "NotificationTemplateEngine",
    "template_engine",
    "NotificationMessage",
    "EventType",
    "NotificationPriority",
    # Delivery Engine
    "NotificationDeliveryEngine",
    "DeliveryRecord",
    "DeliveryStatus",
    "DeliveryChannel",
    "DeliveryNotificationType",
    "DeliveryNotification",
    "EmailPayload",
    "SlackPayload",
    "get_delivery_engine",
]
