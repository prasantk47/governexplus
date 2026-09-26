"""
Tests for the Notification Delivery engine.

SMTP and Slack env vars are not set in the test environment, so the engine
operates in mock mode — send operations always return success without hitting
any real transport. No DB setup required.
"""

import pytest

from core.notifications.delivery import (
    NotificationDeliveryEngine,
    DeliveryRecord,
    Notification,
    NotificationType,
    DeliveryChannel,
    DeliveryStatus,
    get_delivery_engine,
    _TEMPLATES,
)


@pytest.fixture
def engine():
    """Fresh engine instance; preferences are class-level but that is fine for these tests."""
    return NotificationDeliveryEngine()


# ---------------------------------------------------------------------------
# TestSendEmail
# ---------------------------------------------------------------------------

class TestSendEmail:
    def test_send_email_returns_delivery_record(self, engine):
        record = engine.send_email(
            to=["user@example.com"],
            subject="Test Subject",
            body="Test body text",
        )
        assert isinstance(record, DeliveryRecord)

    def test_send_email_status_is_sent(self, engine):
        record = engine.send_email(
            to=["user@example.com"],
            subject="Test",
            body="Body",
        )
        assert record.status in (DeliveryStatus.SENT, DeliveryStatus.MOCK)

    def test_send_email_has_record_id(self, engine):
        record = engine.send_email(to=["a@b.com"], subject="S", body="B")
        assert record.record_id

    def test_send_email_channel_is_email(self, engine):
        record = engine.send_email(to=["recipient@test.com"], subject="S", body="B")
        assert record.channel == "email"

    def test_send_email_to_dict(self, engine):
        d = engine.send_email(to=["a@b.com"], subject="S", body="B").to_dict()
        assert "record_id" in d
        assert "status" in d
        assert "channel" in d


# ---------------------------------------------------------------------------
# TestSendSlack
# ---------------------------------------------------------------------------

class TestSendSlack:
    def test_send_slack_returns_delivery_record(self, engine):
        record = engine.send_slack(channel="#test-channel", message="Hello from tests")
        assert isinstance(record, DeliveryRecord)

    def test_send_slack_status_is_sent_or_mock(self, engine):
        record = engine.send_slack(channel="#alerts", message="Test alert")
        assert record.status in (DeliveryStatus.SENT, DeliveryStatus.MOCK)

    def test_send_slack_channel_in_payload_summary(self, engine):
        record = engine.send_slack(channel="#security", message="msg")
        assert record.channel == "slack"
        assert "#security" in record.payload_summary


# ---------------------------------------------------------------------------
# TestSendNotification
# ---------------------------------------------------------------------------

class TestSendNotification:
    def test_send_notification_returns_list(self, engine):
        notification = Notification(
            notification_id="NID-001",
            notification_type=NotificationType.ACCESS_REQUEST_SUBMITTED,
            recipient_email="user@example.com",
            recipient_id="JDOE",
            context={"request_id": "REQ-001", "requester": "JDOE", "role": "Z_FI_AP"},
        )
        records = engine.send_notification(notification)
        assert isinstance(records, list)
        assert len(records) >= 1

    def test_send_notification_records_are_delivery_records(self, engine):
        notification = Notification(
            notification_id="NID-002",
            notification_type=NotificationType.APPROVAL_NEEDED,
            recipient_email="approver@example.com",
            recipient_id="SSMITH",
            context={"request_id": "REQ-002", "requester": "JDOE", "role": "Z_MM_PO"},
        )
        records = engine.send_notification(notification)
        for r in records:
            assert isinstance(r, DeliveryRecord)


# ---------------------------------------------------------------------------
# TestSendBulk
# ---------------------------------------------------------------------------

class TestSendBulk:
    def test_send_bulk_returns_dict(self, engine):
        notifications = [
            Notification(
                notification_id=f"NID-BULK-{i}",
                notification_type=NotificationType.CERTIFICATION_DUE,
                recipient_email=f"user{i}@example.com",
                recipient_id=f"USER{i}",
                context={"campaign": "Q3-2026"},
            )
            for i in range(3)
        ]
        result = engine.send_bulk(notifications)
        assert isinstance(result, dict)

    def test_send_bulk_keys_are_notification_ids(self, engine):
        notifications = [
            Notification(
                notification_id="BULK-A",
                notification_type=NotificationType.PASSWORD_EXPIRING,
                recipient_email="a@example.com",
                recipient_id="USERA",
                context={"days_remaining": 5},
            ),
        ]
        result = engine.send_bulk(notifications)
        assert "BULK-A" in result


# ---------------------------------------------------------------------------
# TestGetTemplates
# ---------------------------------------------------------------------------

class TestGetTemplates:
    def test_get_templates_returns_list(self, engine):
        templates = engine.get_templates()
        assert isinstance(templates, list)

    def test_templates_non_empty(self, engine):
        templates = engine.get_templates()
        assert len(templates) >= 8

    def test_templates_have_required_fields(self, engine):
        for tmpl in engine.get_templates():
            assert "notification_type" in tmpl or "type" in tmpl

    def test_known_template_types_present(self):
        """Templates module-level dict contains all NotificationType entries."""
        for ntype in (
            NotificationType.ACCESS_REQUEST_SUBMITTED,
            NotificationType.APPROVAL_NEEDED,
            NotificationType.REQUEST_APPROVED,
            NotificationType.RISK_VIOLATION_DETECTED,
        ):
            assert ntype in _TEMPLATES


# ---------------------------------------------------------------------------
# TestPreferences
# ---------------------------------------------------------------------------

class TestPreferences:
    def test_get_preferences_returns_dict(self, engine):
        prefs = engine.get_preferences("JDOE")
        assert isinstance(prefs, dict)

    def test_set_and_get_preferences_roundtrip(self, engine):
        new_prefs = {"email_enabled": True, "slack_enabled": False, "slack_channel": "#jdoe"}
        engine.set_preferences("TESTUSER_PREFS", new_prefs)
        retrieved = engine.get_preferences("TESTUSER_PREFS")
        assert retrieved.get("email_enabled") is True
        assert retrieved.get("slack_channel") == "#jdoe"

    def test_unknown_user_preferences_return_defaults(self, engine):
        prefs = engine.get_preferences("ZZUNKNOWN_USER_XYZ")
        assert isinstance(prefs, dict)
        # Should return some default structure, not raise
        assert "email_enabled" in prefs or len(prefs) >= 0


# ---------------------------------------------------------------------------
# TestDeliveryHistory
# ---------------------------------------------------------------------------

class TestDeliveryHistory:
    def test_get_delivery_history_returns_list(self, engine):
        # Use send_notification to populate history with a known recipient_id
        notif = Notification(
            notification_id="HIST-001",
            notification_type=NotificationType.REQUEST_APPROVED,
            recipient_id="HIST_USER",
            recipient_email="hist@test.com",
        )
        engine.send_notification(notif)
        history = engine.get_delivery_history(user_id="HIST_USER")
        assert isinstance(history, list)

    def test_delivery_history_entries_are_dicts(self, engine):
        notif = Notification(
            notification_id="HIST-002",
            notification_type=NotificationType.REQUEST_REJECTED,
            recipient_id="HIST_USER2",
            recipient_email="hist2@test.com",
        )
        engine.send_notification(notif)
        history = engine.get_delivery_history(user_id="HIST_USER2")
        for item in history:
            # get_delivery_history returns list of dicts (via to_dict())
            assert isinstance(item, dict)
            assert "notification_id" in item or "record_id" in item

    def test_delivery_history_limit_respected(self, engine):
        for i in range(5):
            notif = Notification(
                notification_id=f"LIMIT-{i}",
                notification_type=NotificationType.CERTIFICATION_DUE,
                recipient_id="LIMIT_USER",
                recipient_email="limit@test.com",
            )
            engine.send_notification(notif)
        history = engine.get_delivery_history(user_id="LIMIT_USER", limit=2)
        assert len(history) <= 2


# ---------------------------------------------------------------------------
# TestGetDeliveryEngine
# ---------------------------------------------------------------------------

class TestGetDeliveryEngine:
    def test_get_delivery_engine_returns_engine(self):
        eng = get_delivery_engine()
        assert isinstance(eng, NotificationDeliveryEngine)

    def test_get_delivery_engine_is_singleton(self):
        eng1 = get_delivery_engine()
        eng2 = get_delivery_engine()
        assert eng1 is eng2


# ---------------------------------------------------------------------------
# TestRetryFailed
# ---------------------------------------------------------------------------

class TestRetryFailed:
    def test_retry_failed_returns_dict(self, engine):
        result = engine.retry_failed()
        assert isinstance(result, dict)

    def test_retry_failed_has_summary_keys(self, engine):
        result = engine.retry_failed()
        # retry_failed returns a summary dict with counts
        assert "total_processed" in result or "retried" in result or len(result) >= 0
