"""Comprehensive Phase 5 tests for Real SMS (Fast2SMS) and WhatsApp (RichAutomate) Notification Engine."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
import httpx
import pytest
from pydantic import SecretStr

from fastapi.testclient import TestClient
from packages.config.settings import Settings, get_test_settings
from packages.errors import ValidationError
from packages.schemas.responders import (
    ChannelDeliveryStatus,
    ChannelResult,
    EscalationType,
    NotificationAction,
    NotificationChannel,
    NotificationMode,
    NotificationRequest,
    NotificationStatus,
    ResponsePriority,
)
from services.api.main import app
from services.api.services.notifications import NotificationService
from services.api.services.providers.fast2sms import Fast2SMSProvider
from services.api.services.providers.richautomate import RichAutomateWhatsAppProvider
from services.api.services.responders import NotificationAuditService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_audit_state():
    """Reset audit logs and idempotency states before and after each test."""
    NotificationAuditService.clear_activity_log()
    yield
    NotificationAuditService.clear_activity_log()


class TestPhoneNumberValidation:
    """Test suite for strict phone normalization and E.164 compliance."""

    def test_normalize_10_digit_indian_number(self):
        result = NotificationService.validate_and_normalize_phone("9876543210")
        assert result == "+919876543210"

    def test_normalize_with_spaces_and_dashes(self):
        result = NotificationService.validate_and_normalize_phone("+91 98765-43210")
        assert result == "+919876543210"

    def test_normalize_11_digit_with_leading_zero(self):
        result = NotificationService.validate_and_normalize_phone("09876543210")
        assert result == "+919876543210"

    def test_normalize_valid_e164_international(self):
        result = NotificationService.validate_and_normalize_phone("+14155552671")
        assert result == "+14155552671"

    def test_reject_empty_or_none(self):
        with pytest.raises(ValidationError):
            NotificationService.validate_and_normalize_phone("")
        with pytest.raises(ValidationError):
            NotificationService.validate_and_normalize_phone(None)

    def test_reject_invalid_characters_or_short(self):
        with pytest.raises(ValidationError):
            NotificationService.validate_and_normalize_phone("12345")
        with pytest.raises(ValidationError):
            NotificationService.validate_and_normalize_phone("abcdefghij")


class TestFast2SMSProvider:
    """Test suite for Fast2SMS provider abstraction, live dispatch, and simulation."""

    def test_fast2sms_simulation_mode(self):
        settings = get_test_settings(
            FAST2SMS_API_KEY=SecretStr("mock_key"),
            FAST2SMS_ENABLED=True,
        )
        provider = Fast2SMSProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.SMS,
            recipient="+919876543210",
            message="Test simulation alert",
            mode=NotificationMode.SIMULATED,
        )
        assert result.status == ChannelDeliveryStatus.SIMULATED
        assert result.provider == "fast2sms"
        assert result.provider_message_id is not None
        assert "simulated successfully" in result.message

    def test_fast2sms_fallback_when_api_key_missing(self):
        settings = get_test_settings(
            FAST2SMS_API_KEY=None,
            FAST2SMS_ENABLED=True,
        )
        provider = Fast2SMSProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.SMS,
            recipient="+919876543210",
            message="Live alert without key",
            mode=NotificationMode.LIVE,
        )
        assert result.status == ChannelDeliveryStatus.SIMULATED
        assert "simulated successfully" in result.message

    @patch("httpx.Client.post")
    def test_fast2sms_live_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "return": True,
            "request_id": "REQ_F2S_12345",
            "message": ["SMS sent successfully."],
        }
        mock_post.return_value = mock_resp

        settings = get_test_settings(
            FAST2SMS_API_KEY=SecretStr("real_api_key_123"),
            FAST2SMS_ENABLED=True,
        )
        provider = Fast2SMSProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.SMS,
            recipient="+919876543210",
            message="Emergency alert",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.SENT
        assert result.provider_message_id == "REQ_F2S_12345"
        assert "dispatched successfully" in result.message

        # Verify payload sent 10-digit number
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["numbers"] == "9876543210"
        assert kwargs["headers"]["authorization"] == "real_api_key_123"

    @patch("httpx.Client.post")
    def test_fast2sms_live_rejection(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "return": False,
            "status_code": 411,
            "message": ["Invalid Mobile Number"],
        }
        mock_post.return_value = mock_resp

        settings = get_test_settings(
            FAST2SMS_API_KEY=SecretStr("real_api_key_123"),
            FAST2SMS_ENABLED=True,
        )
        provider = Fast2SMSProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.SMS,
            recipient="+919876543210",
            message="Emergency alert",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.FAILED
        assert "rejected by Fast2SMS" in result.message
        assert result.error_details is not None

    @patch("httpx.Client.post")
    def test_fast2sms_live_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        settings = get_test_settings(
            FAST2SMS_API_KEY=SecretStr("real_api_key_123"),
            FAST2SMS_ENABLED=True,
        )
        provider = Fast2SMSProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.SMS,
            recipient="+919876543210",
            message="Emergency alert",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.FAILED
        assert "timed out" in result.message.lower() or "timeout" in str(result.error_details).lower()


class TestRichAutomateWhatsAppProvider:
    """Test suite for RichAutomate WhatsApp provider abstraction, live dispatch, and simulation."""

    def test_richautomate_simulation_mode(self):
        settings = get_test_settings(
            RICHAUTOMATE_API_KEY=SecretStr("mock_key"),
            RICHAUTOMATE_ENABLED=True,
        )
        provider = RichAutomateWhatsAppProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.WHATSAPP,
            recipient="+919876543210",
            message="Test WhatsApp alert",
            mode=NotificationMode.SIMULATED,
        )
        assert result.status == ChannelDeliveryStatus.SIMULATED
        assert result.provider == "richautomate"
        assert result.provider_message_id is not None
        assert "simulated successfully" in result.message

    @patch("httpx.Client.post")
    def test_richautomate_live_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "MSG_RA_998877",
            "status": "accepted",
        }
        mock_post.return_value = mock_resp

        settings = get_test_settings(
            RICHAUTOMATE_API_KEY=SecretStr("ra_secret_token_abc"),
            RICHAUTOMATE_ENABLED=True,
        )
        provider = RichAutomateWhatsAppProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.WHATSAPP,
            recipient="+919876543210",
            message="Critical thermal alert",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.SENT
        assert result.provider_message_id == "MSG_RA_998877"
        assert "dispatched successfully" in result.message

        # Verify Authorization header uses Bearer token
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer ra_secret_token_abc"
        assert kwargs["json"]["to"] == "+919876543210"

    @patch("httpx.Client.post")
    def test_richautomate_live_unauthorized_401(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized: Invalid API Key"
        mock_post.return_value = mock_resp

        settings = get_test_settings(
            RICHAUTOMATE_API_KEY=SecretStr("invalid_token"),
            RICHAUTOMATE_ENABLED=True,
        )
        provider = RichAutomateWhatsAppProvider(settings=settings)
        result = provider.send(
            channel=NotificationChannel.WHATSAPP,
            recipient="+919876543210",
            message="Critical alert",
            mode=NotificationMode.LIVE,
        )

        assert result.status == ChannelDeliveryStatus.FAILED
        assert "authentication failed" in result.message


class TestNotificationOrchestrationAndIdempotency:
    """Test suite for full notification pipeline, idempotency, and REST endpoint integration."""

    @pytest.fixture
    def test_event_and_responder(self):
        from services.api.services.events import EventQueryService
        from services.api.services.responders import ResponderDirectoryService

        dataset = EventQueryService.get_canonical_enriched_dataset()
        event_id = dataset.events[0].event_id
        responder_id = ResponderDirectoryService.get_all_raw_responders()[0]["id"]
        return event_id, responder_id

    def test_notify_endpoint_simulation_mode(self, test_event_and_responder):
        event_id, responder_id = test_event_and_responder
        payload = {
            "responder_id": responder_id,
            "action": "NOTIFY",
            "mode": "SIMULATED",
            "recipient_phone": "+91 9876543210",
            "channels": ["SMS", "WHATSAPP"],
            "escalation_type": "ADMIN_CONFIRMED",
            "analyst_notes": "Operator manual dispatch test",
        }
        res = client.post(f"/events/{event_id}/response/notify", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SIMULATED"
        assert data["recipient_phone"] == "+919876543210"
        assert len(data["channels"]) == 2
        for ch in data["channels"]:
            assert ch["status"] == "SIMULATED"

        # Verify audit activity updated
        act_res = client.get(f"/events/{event_id}/response/activity")
        assert act_res.status_code == 200
        act_data = act_res.json()
        assert act_data["total_records"] >= 1
        assert act_data["records"][0]["analyst_notes"] == "Operator manual dispatch test"

    def test_duplicate_automatic_escalation_suppression(self, test_event_and_responder):
        event_id, responder_id = test_event_and_responder
        payload = {
            "responder_id": responder_id,
            "action": "NOTIFY",
            "mode": "SIMULATED",
            "recipient_phone": "+91 9876543210",
            "channels": ["SMS", "WHATSAPP"],
            "escalation_type": "HIGH_CONFIDENCE_AUTO",
        }
        # First call succeeds
        res1 = client.post(f"/events/{event_id}/response/notify", json=payload)
        assert res1.status_code == 200
        assert res1.json()["status"] == "SIMULATED"

        # Second call with same automatic escalation type is suppressed
        res2 = client.post(f"/events/{event_id}/response/notify", json=payload)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "DUPLICATE_SUPPRESSED"
        assert "Duplicate" in data2["message"]
        for ch in data2["channels"]:
            assert ch["status"] == "DUPLICATE_SUPPRESSED"

    def test_notify_endpoint_live_mode(self, test_event_and_responder):
        event_id, responder_id = test_event_and_responder

        mock_f2s_result = ChannelResult(
            channel=NotificationChannel.SMS,
            status=ChannelDeliveryStatus.SENT,
            recipient="+919876543210",
            message="SMS alert dispatched successfully via Fast2SMS to +919876543210.",
            provider="fast2sms",
            provider_message_id="F2S_LIVE_888",
        )
        mock_ra_result = ChannelResult(
            channel=NotificationChannel.WHATSAPP,
            status=ChannelDeliveryStatus.SENT,
            recipient="+919876543210",
            message="WhatsApp alert dispatched successfully via RichAutomate to +919876543210.",
            provider="richautomate",
            provider_message_id="RA_LIVE_999",
        )

        with patch.object(Fast2SMSProvider, "send", return_value=mock_f2s_result), \
             patch.object(RichAutomateWhatsAppProvider, "send", return_value=mock_ra_result):

            payload = {
                "responder_id": responder_id,
                "action": "NOTIFY",
                "mode": "LIVE",
                "recipient_phone": "+91 9876543210",
                "channels": ["SMS", "WHATSAPP"],
                "escalation_type": "ADMIN_CONFIRMED",
            }
            res = client.post(f"/events/{event_id}/response/notify", json=payload)
            assert res.status_code == 200, f"Error body: {res.text}"
            data = res.json()
            assert data["status"] == "SENT"
            assert "Notification has been sent successfully" in data["message"]
            assert len(data["channels"]) == 2
            assert data["channels"][0]["provider_message_id"] == "F2S_LIVE_888"
            assert data["channels"][1]["provider_message_id"] == "RA_LIVE_999"
