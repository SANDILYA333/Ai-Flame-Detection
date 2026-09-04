"""Comprehensive Phase 6 verification tests for Delivery Tracking, Audit Hardening, Automatic Escalation, Idempotency & Reliability."""

import concurrent.futures
from datetime import UTC, datetime
import time
from unittest.mock import MagicMock, patch
import httpx
import pytest
from pydantic import SecretStr

from fastapi.testclient import TestClient
from packages.config.settings import get_test_settings
from packages.schemas.responders import (
    ChannelDeliveryStatus,
    ChannelResult,
    EscalationState,
    EscalationType,
    NotificationAction,
    NotificationChannel,
    NotificationMode,
    NotificationRequest,
    NotificationStatus,
    ResponsePriority,
)
from services.api.main import app
from services.api.services.events import EventQueryService
from services.api.services.notifications import NotificationService
from services.api.services.providers.fast2sms import Fast2SMSProvider, mask_phone_number
from services.api.services.providers.richautomate import RichAutomateWhatsAppProvider
from services.api.services.responders import (
    NotificationAuditService,
    ResponderDirectoryService,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_audit_state():
    """Reset audit logs and idempotency states before and after each test."""
    NotificationAuditService.clear_activity_log()
    NotificationService.clear_escalation_records()
    yield
    NotificationAuditService.clear_activity_log()
    NotificationService.clear_escalation_records()


@pytest.fixture
def canonical_event_and_responder():
    """Fetch canonical event and responder ID for testing."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id
    responder_id = ResponderDirectoryService.get_all_raw_responders()[0]["id"]
    return event_id, responder_id


class TestPhoneMaskingAndPrivacy:
    """Verify phone masking for audit trails, logs, and UI protection."""

    def test_mask_indian_phone_number(self):
        masked = mask_phone_number("+919876543210")
        assert masked == "+91 ******3210"

    def test_mask_international_phone_number(self):
        masked = mask_phone_number("+14155552671")
        assert "******" in masked
        assert masked.endswith("2671")

    def test_mask_short_or_empty_phone(self):
        assert mask_phone_number(None) == "N/A"
        assert mask_phone_number("") == "N/A"
        assert mask_phone_number("1234") == "****"


class TestBoundedRetriesAndErrorClassification:
    """Verify bounded exponential backoff retries on transient errors and instant failure on client errors."""

    @patch("httpx.Client.post")
    def test_fast2sms_retries_transient_500_then_succeeds(self, mock_post):
        # First attempt: 500 error, Second attempt: 200 success
        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_500.text = "Internal Server Error"

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "return": True,
            "request_id": "REQ_RETRY_OK",
        }

        mock_post.side_effect = [mock_500, mock_200]

        settings = get_test_settings(
            FAST2SMS_API_KEY=SecretStr("real_key"),
            FAST2SMS_ENABLED=True,
            NOTIFICATION_MAX_RETRIES=2,
            NOTIFICATION_RETRY_BACKOFF_SECONDS=0.01,
        )
        provider = Fast2SMSProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.SMS,
            recipient="+919876543210",
            message="Test retry alert",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.SENT
        assert result.provider_message_id == "REQ_RETRY_OK"
        assert result.retry_count == 1
        assert mock_post.call_count == 2

    @patch("httpx.Client.post")
    def test_richautomate_does_not_retry_401_unauthorized(self, mock_post):
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_401.text = "Unauthorized: Invalid API Key"
        mock_post.return_value = mock_401

        settings = get_test_settings(
            RICHAUTOMATE_API_KEY=SecretStr("bad_key"),
            RICHAUTOMATE_ENABLED=True,
            NOTIFICATION_MAX_RETRIES=2,
            NOTIFICATION_RETRY_BACKOFF_SECONDS=0.01,
        )
        provider = RichAutomateWhatsAppProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.WHATSAPP,
            recipient="+919876543210",
            message="Test unauthorized",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.FAILED
        assert "authentication failed" in result.message.lower()
        # Should NOT retry client 401 error
        assert mock_post.call_count == 1

    @patch("httpx.Client.post")
    def test_fast2sms_exhausts_retries_on_continuous_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        settings = get_test_settings(
            FAST2SMS_API_KEY=SecretStr("real_key"),
            FAST2SMS_ENABLED=True,
            NOTIFICATION_MAX_RETRIES=2,
            NOTIFICATION_RETRY_BACKOFF_SECONDS=0.01,
        )
        provider = Fast2SMSProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.SMS,
            recipient="+919876543210",
            message="Test timeout",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.FAILED
        assert result.retry_count == 2
        assert mock_post.call_count == 3  # 1 initial + 2 retries


class TestIdempotencyAndConcurrency:
    """Verify thread-safe idempotency and duplicate suppression across analyst and worker retries."""

    def test_concurrent_identical_requests_suppress_duplicates(
        self, canonical_event_and_responder
    ):
        event_id, responder_id = canonical_event_and_responder
        req = NotificationRequest(
            responder_id=responder_id,
            action=NotificationAction.NOTIFY,
            mode=NotificationMode.SIMULATED,
            recipient_phone="+919876543210",
            channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
            escalation_type=EscalationType.HIGH_CONFIDENCE_AUTO,
        )

        # Launch 5 concurrent dispatches with identical payload
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    NotificationAuditService.process_notification, event_id, req
                )
                for _ in range(5)
            ]
            results = [f.result() for f in futures]

        statuses = [r.status for r in results]
        # Exactly one should be SIMULATED, and the other 4 DUPLICATE_SUPPRESSED
        assert statuses.count(NotificationStatus.SIMULATED) == 1
        assert statuses.count(NotificationStatus.DUPLICATE_SUPPRESSED) == 4

    def test_analyst_duplicate_suppression_via_idempotency_cache(
        self, canonical_event_and_responder
    ):
        event_id, responder_id = canonical_event_and_responder
        req = NotificationRequest(
            responder_id=responder_id,
            action=NotificationAction.NOTIFY,
            mode=NotificationMode.SIMULATED,
            recipient_phone="+919876543210",
            channels=[NotificationChannel.SMS],
            escalation_type=EscalationType.ADMIN_CONFIRMED,
            analyst_notes="Double-click test",
        )

        resp1 = NotificationAuditService.process_notification(event_id, req)
        assert resp1.status == NotificationStatus.SIMULATED
        assert resp1.channels[0].status == ChannelDeliveryStatus.SIMULATED

        # Immediate double submission by analyst
        resp2 = NotificationAuditService.process_notification(event_id, req)
        assert resp2.status == NotificationStatus.DUPLICATE_SUPPRESSED
        assert resp2.channels[0].status == ChannelDeliveryStatus.DUPLICATE_SUPPRESSED


class TestBackendControlledAutomaticEscalation:
    """Verify automatic escalation is triggered strictly backend-side without React dependencies."""

    def test_automatic_escalation_endpoint_and_idempotency(self):
        dataset = EventQueryService.get_canonical_enriched_dataset()
        event_id = dataset.events[0].event_id

        # First evaluation execution
        res1 = client.post(f"/events/{event_id}/response/auto-escalate?mode=SIMULATED")
        assert res1.status_code == 200
        data1 = res1.json()

        # Second evaluation execution must be idempotent
        res2 = client.post(f"/events/{event_id}/response/auto-escalate?mode=SIMULATED")
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2) == 0  # Already processed, no duplicate alerts triggered


class TestPartialChannelFailure:
    """Verify independent channel status when SMS succeeds but WhatsApp fails."""

    def test_partial_success_independent_reporting(self, canonical_event_and_responder):
        event_id, responder_id = canonical_event_and_responder

        mock_sms_success = ChannelResult(
            channel=NotificationChannel.SMS,
            status=ChannelDeliveryStatus.SENT,
            recipient="+919876543210",
            destination_masked="+91 ******3210",
            message="SMS alert dispatched successfully via Fast2SMS to +919876543210.",
            provider="fast2sms",
            provider_message_id="F2S_OK_123",
        )
        mock_wa_failure = ChannelResult(
            channel=NotificationChannel.WHATSAPP,
            status=ChannelDeliveryStatus.FAILED,
            recipient="+919876543210",
            destination_masked="+91 ******3210",
            message="WhatsApp delivery failed at gateway.",
            provider="richautomate",
            error_details="HTTP 500 Server Error",
        )

        with patch.object(Fast2SMSProvider, "send", return_value=mock_sms_success), \
             patch.object(RichAutomateWhatsAppProvider, "send", return_value=mock_wa_failure):

            req = NotificationRequest(
                responder_id=responder_id,
                action=NotificationAction.NOTIFY,
                mode=NotificationMode.LIVE,
                recipient_phone="+919876543210",
                channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
                escalation_type=EscalationType.ADMIN_CONFIRMED,
            )
            res = NotificationAuditService.process_notification(event_id, req)

            assert res.status == NotificationStatus.PARTIAL
            assert "SMS notification sent successfully" in res.message
            assert "WHATSAPP notification failed" in res.message
            assert len(res.channels) == 2
            assert res.channels[0].status == ChannelDeliveryStatus.SENT
            assert res.channels[1].status == ChannelDeliveryStatus.FAILED
