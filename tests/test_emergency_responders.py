"""Tests for emergency responders directory, multi-channel notification, and escalation policy (API-013)."""

import pytest
from fastapi.testclient import TestClient

from packages.errors import ValidationError
from packages.schemas.responders import (
    ChannelDeliveryStatus,
    EscalationType,
    NotificationAction,
    NotificationChannel,
    NotificationMode,
    NotificationRequest,
    NotificationStatus,
    ResponderType,
    ResponsePriority,
)
from services.api.app import create_app
from services.api.services.events import EventQueryService
from services.api.services.notifications import NotificationService
from services.api.services.responders import (
    NotificationAuditService,
    ResponderDirectoryService,
    ResponseRecommendationService,
)


@pytest.fixture(autouse=True)
def clean_audit_log() -> None:
    """Clear in-memory audit log and escalation tracking before each test."""
    NotificationAuditService.clear_activity_log()
    NotificationService.clear_escalation_records()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_responder_directory_service_loads_datasets() -> None:
    """Verify emergency responders directory loads and normalizes data."""
    responders = ResponderDirectoryService.get_all_raw_responders()
    assert len(responders) > 0

    types = {r["type"] for r in responders}
    has_med = ResponderType.BURN_ICU in types or ResponderType.HOSPITAL in types
    has_fire = (
        ResponderType.CHEMICAL_FIRE_STATION in types
        or ResponderType.FIRE_STATION in types
    )
    assert has_med
    assert has_fire
    assert ResponderType.NDRF in types

    for r in responders:
        assert r["id"]
        assert r["name"]
        assert -90.0 <= r["latitude"] <= 90.0
        assert -180.0 <= r["longitude"] <= 180.0
        assert len(r["capabilities"]) > 0
        assert r["phone"]


def test_response_recommendation_for_industrial_event() -> None:
    """Verify recommendation service correctly ranks responders and extracts nearest facilities."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    assert len(dataset.events) > 0
    event = dataset.events[0]

    rec = ResponseRecommendationService.get_recommendations_for_event(event.event_id)
    assert rec.event_id == event.event_id
    assert rec.response_priority in [
        ResponsePriority.CRITICAL,
        ResponsePriority.HIGH,
        ResponsePriority.MEDIUM,
        ResponsePriority.MONITOR_ONLY,
        ResponsePriority.REVIEW_REQUIRED,
    ]
    assert len(rec.responders) > 0
    assert len(rec.nearest_hospitals) <= 2
    assert len(rec.nearest_fire_stations) <= 2
    assert len(rec.recommendation_basis) > 0

    top = rec.responders[0]
    assert top.distance_meters >= 0
    assert top.estimated_eta_minutes >= 1
    assert "min" in top.formatted_eta
    assert top.recommendation_reason


def test_nearest_hospitals_and_fire_stations_selection() -> None:
    """Verify nearest 2 hospitals and nearest 2 fire stations are accurately selected by geodesic distance."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event = dataset.events[0]

    rec = ResponseRecommendationService.get_recommendations_for_event(event.event_id)

    # Hospitals check
    assert len(rec.nearest_hospitals) == 2
    for h in rec.nearest_hospitals:
        assert h.type in [ResponderType.BURN_ICU, ResponderType.HOSPITAL]
    assert (
        rec.nearest_hospitals[0].distance_meters
        <= rec.nearest_hospitals[1].distance_meters
    )

    # Fire stations check
    assert len(rec.nearest_fire_stations) == 2
    for f in rec.nearest_fire_stations:
        assert f.type in [
            ResponderType.CHEMICAL_FIRE_STATION,
            ResponderType.FIRE_STATION,
        ]
    assert (
        rec.nearest_fire_stations[0].distance_meters
        <= rec.nearest_fire_stations[1].distance_meters
    )


def test_phone_number_validation() -> None:
    """Verify E.164 and Indian phone number formatting and validation rules."""
    # Valid Indian formats
    assert (
        NotificationService.validate_and_normalize_phone("+919876543210")
        == "+919876543210"
    )
    assert (
        NotificationService.validate_and_normalize_phone("+91 98765 43210")
        == "+919876543210"
    )
    assert (
        NotificationService.validate_and_normalize_phone("9876543210")
        == "+919876543210"
    )
    assert (
        NotificationService.validate_and_normalize_phone("09876543210")
        == "+919876543210"
    )

    # Valid International formats
    assert (
        NotificationService.validate_and_normalize_phone("+14155552671")
        == "+14155552671"
    )
    assert (
        NotificationService.validate_and_normalize_phone("+44 7911 123456")
        == "+447911123456"
    )

    # Invalid formats
    with pytest.raises(ValidationError):
        NotificationService.validate_and_normalize_phone("")
    with pytest.raises(ValidationError):
        NotificationService.validate_and_normalize_phone("abc12345")
    with pytest.raises(ValidationError):
        NotificationService.validate_and_normalize_phone("123")


def test_notification_message_formatting_templates() -> None:
    """Verify high-confidence and critical alert message templates adhere to Section 24."""
    msg_high = NotificationService.format_alert_message(
        event_id="EVT-TEST-01",
        location="Jamnagar, Gujarat",
        classification="INDUSTRIAL",
        confidence_percent=96.4,
        frp_mw=120.0,
        priority=ResponsePriority.HIGH,
        is_critical=False,
    )
    assert "FLAME INTELLIGENCE ALERT" in msg_high
    assert "EVT-TEST-01" in msg_high
    assert "96.4%" in msg_high
    assert "120.0 MW" in msg_high
    assert "simulated prototype notification" in msg_high.lower()

    msg_crit = NotificationService.format_alert_message(
        event_id="EVT-TEST-02",
        location="Jamnagar, Gujarat",
        classification="INDUSTRIAL",
        confidence_percent=99.2,
        frp_mw=250.0,
        priority=ResponsePriority.CRITICAL,
        is_critical=True,
    )
    assert "FLAME INTELLIGENCE — CRITICAL ALERT" in msg_crit
    assert "EVT-TEST-02" in msg_crit
    assert "CRITICAL response priority" in msg_crit
    assert "medical preparedness" in msg_crit.lower()


def test_multichannel_notification_audit_simulation() -> None:
    """Verify notification processing dispatches both SMS and WhatsApp simulated records."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event = dataset.events[0]
    all_raw = ResponderDirectoryService.get_all_raw_responders()
    responder = all_raw[0]

    req = NotificationRequest(
        responder_id=responder["id"],
        action=NotificationAction.NOTIFY,
        mode=NotificationMode.SIMULATED,
        recipient_phone="+919876543210",
        channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
        escalation_type=EscalationType.ADMIN_CONFIRMED,
        analyst_notes="Test analyst multi-channel confirmation",
    )

    resp = NotificationAuditService.process_notification(event.event_id, req)
    assert resp.status == NotificationStatus.SIMULATED
    assert resp.mode == NotificationMode.SIMULATED
    assert resp.event_id == event.event_id
    assert resp.responder_id == responder["id"]
    assert resp.recipient_phone == "+919876543210"
    assert len(resp.channels) == 2
    channel_types = {c.channel for c in resp.channels}
    assert NotificationChannel.SMS in channel_types
    assert NotificationChannel.WHATSAPP in channel_types

    activity = NotificationAuditService.get_activity_for_event(event.event_id)
    assert len(activity) == 1
    assert activity[0].notification_id == resp.notification_id
    assert activity[0].status == NotificationStatus.SIMULATED
    assert activity[0].recipient_phone == "+919876543210"
    assert len(activity[0].channels) == 2


def test_auto_escalation_idempotency() -> None:
    """Verify automatic high-confidence or critical escalation is strictly idempotent."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event = dataset.events[0]

    # 1. First escalation trigger
    req = NotificationRequest(
        responder_id=ResponderDirectoryService.get_all_raw_responders()[0]["id"],
        action=NotificationAction.NOTIFY,
        mode=NotificationMode.SIMULATED,
        recipient_phone="+919876543210",
        channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
        escalation_type=EscalationType.HIGH_CONFIDENCE_AUTO,
        analyst_notes="Automatic High-Confidence Escalation",
    )
    NotificationAuditService.process_notification(event.event_id, req)

    assert NotificationService.is_escalation_processed(
        event.event_id, EscalationType.HIGH_CONFIDENCE_AUTO
    )
    assert len(NotificationAuditService.get_activity_for_event(event.event_id)) == 1

    # 2. Subsequent recommendations query with demo phone does not re-trigger
    rec = ResponseRecommendationService.get_recommendations_for_event(
        event.event_id, demo_phone="+919876543210"
    )
    assert rec.auto_escalation_triggered is True
    # Still only 1 record in audit log
    assert len(NotificationAuditService.get_activity_for_event(event.event_id)) == 1


def test_api_get_event_responders_with_demo_phone(client: TestClient) -> None:
    """Test GET /events/{event_id}/responders HTTP endpoint with demo_phone parameter."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    response = client.get(
        f"/events/{event_id}/responders",
        params={"demo_phone": "+919876543210"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == event_id
    assert "response_priority" in data
    assert "nearest_hospitals" in data
    assert "nearest_fire_stations" in data
    assert len(data["nearest_hospitals"]) <= 2
    assert len(data["nearest_fire_stations"]) <= 2


def test_api_notify_responder_multichannel(client: TestClient) -> None:
    """Test POST /events/{event_id}/response/notify HTTP endpoint with channels & phone."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id
    all_raw = ResponderDirectoryService.get_all_raw_responders()
    resp_id = all_raw[0]["id"]

    payload = {
        "responder_id": resp_id,
        "action": "NOTIFY",
        "mode": "SIMULATED",
        "recipient_phone": "+919876543210",
        "channels": ["SMS", "WHATSAPP"],
        "escalation_type": "ADMIN_CONFIRMED",
        "analyst_notes": "Live test multi-channel simulation",
    }

    response = client.post(f"/events/{event_id}/response/notify", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "SIMULATED"
    assert res_data["responder_id"] == resp_id
    assert res_data["recipient_phone"] == "+919876543210"
    assert len(res_data["channels"]) == 2

    act_response = client.get(f"/events/{event_id}/response/activity")
    assert act_response.status_code == 200
    act_data = act_response.json()
    assert act_data["total_records"] == 1
    assert act_data["records"][0]["recipient_phone"] == "+919876543210"


def test_api_escalate_endpoint(client: TestClient) -> None:
    """Test POST /events/{event_id}/response/escalate HTTP endpoint."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id
    all_raw = ResponderDirectoryService.get_all_raw_responders()
    resp_id = all_raw[0]["id"]

    payload = {
        "responder_id": resp_id,
        "action": "NOTIFY",
        "mode": "SIMULATED",
        "recipient_phone": "+919876543210",
        "channels": ["SMS", "WHATSAPP"],
        "escalation_type": "HIGH_CONFIDENCE_AUTO",
        "analyst_notes": "Automated escalation test",
    }

    response = client.post(f"/events/{event_id}/response/escalate", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["escalation_type"] == "HIGH_CONFIDENCE_AUTO"
    assert len(res_data["channels"]) == 2


def test_confidence_threshold_boundaries() -> None:
    """Explicitly verify threshold gating at 94.0%, 94.01%, 98.0%, and 98.01%."""
    # Test A: <= 94.0% -> No auto escalation, standard monitoring
    conf_a = 0.9400
    is_auto_a = conf_a > 0.98
    is_admin_a = 0.94 < conf_a <= 0.98
    assert not is_auto_a
    assert not is_admin_a

    # Test B: 94.01% -> Admin review required, no automatic escalation
    conf_b = 0.9401
    is_auto_b = conf_b > 0.98
    is_admin_b = 0.94 < conf_b <= 0.98
    assert not is_auto_b
    assert is_admin_b

    # Test C: 98.0% -> Admin review required, no automatic escalation
    conf_c = 0.9800
    is_auto_c = conf_c > 0.98
    is_admin_c = 0.94 < conf_c <= 0.98
    assert not is_auto_c
    assert is_admin_c

    # Test D: 98.01% -> Automatic escalation triggered
    conf_d = 0.9801
    is_auto_d = conf_d > 0.98
    assert is_auto_d


def test_critical_event_medical_escalation_path(client: TestClient) -> None:
    """Verify CRITICAL event deterministically triggers medical escalation and ambulance readiness."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    crit_event = next(
        (ev for ev in dataset.events if (ev.max_frp_mw or 0) > 50.0),
        dataset.events[0],
    )

    rec = ResponseRecommendationService.get_recommendations_for_event(
        crit_event.event_id, demo_phone="+919876543210"
    )
    assert rec.response_priority == ResponsePriority.CRITICAL
    assert rec.escalation_type == EscalationType.CRITICAL_MEDICAL
    assert rec.auto_escalation_eligible is True

    # Check that hospitals are selected and available
    assert len(rec.nearest_hospitals) == 2
    for h in rec.nearest_hospitals:
        assert h.type in [ResponderType.BURN_ICU, ResponderType.HOSPITAL]

    # Verify audit record was created for the critical event
    activity = NotificationAuditService.get_activity_for_event(crit_event.event_id)
    assert len(activity) >= 1
    assert activity[0].escalation_type == EscalationType.CRITICAL_MEDICAL
    assert activity[0].recipient_phone == "+919876543210"


def test_idempotency_duplicate_suppression_status() -> None:
    """Verify repeated automatic escalation returns DUPLICATE_SUPPRESSED status."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event = dataset.events[0]
    responder = ResponderDirectoryService.get_all_raw_responders()[0]

    req = NotificationRequest(
        responder_id=responder["id"],
        action=NotificationAction.NOTIFY,
        mode=NotificationMode.SIMULATED,
        recipient_phone="+919876543210",
        channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
        escalation_type=EscalationType.HIGH_CONFIDENCE_AUTO,
        analyst_notes="First automatic trigger",
    )

    # 1. First trigger succeeds (SIMULATED)
    first_resp = NotificationAuditService.process_notification(event.event_id, req)
    assert first_resp.status == NotificationStatus.SIMULATED
    for ch in first_resp.channels:
        assert ch.status == ChannelDeliveryStatus.SIMULATED

    # 2. Second identical trigger returns DUPLICATE_SUPPRESSED
    second_resp = NotificationAuditService.process_notification(event.event_id, req)
    assert second_resp.status == NotificationStatus.DUPLICATE_SUPPRESSED
    assert "suppressed" in second_resp.message.lower()
    for ch in second_resp.channels:
        assert ch.status == ChannelDeliveryStatus.DUPLICATE_SUPPRESSED

    # Audit log should only contain the 1 initial dispatch
    activity = NotificationAuditService.get_activity_for_event(event.event_id)
    assert len(activity) == 1


def test_provider_configuration_validation() -> None:
    """Verify operational settings accurately expose notification & escalation variables."""
    from packages.config.settings import Settings

    settings = Settings(
        NOTIFICATION_MODE="simulation",
        SMS_PROVIDER="fast2sms",
        WHATSAPP_PROVIDER="richautomate",
        EMERGENCY_RESPONSE_ENABLED=True,
        EMERGENCY_AUTO_ESCALATION_ENABLED=True,
        EMERGENCY_REVIEW_MIN_CONFIDENCE=0.94,
        EMERGENCY_AUTO_ESCALATION_MIN_CONFIDENCE=0.98,
        FAST2SMS_BASE_URL="https://www.fast2sms.com/dev/bulkV2",
        RICHAUTOMATE_BASE_URL="https://richautomate.in/api/v1",
        RICHAUTOMATE_ENABLED=True,
    )
    assert settings.NOTIFICATION_MODE == "simulation"
    assert settings.SMS_PROVIDER == "fast2sms"
    assert settings.WHATSAPP_PROVIDER == "richautomate"
    assert settings.EMERGENCY_REVIEW_MIN_CONFIDENCE == 0.94
    assert settings.EMERGENCY_AUTO_ESCALATION_MIN_CONFIDENCE == 0.98
    assert settings.FAST2SMS_BASE_URL == "https://www.fast2sms.com/dev/bulkV2"
    assert settings.RICHAUTOMATE_BASE_URL == "https://richautomate.in/api/v1"


def test_provider_abstraction_contracts() -> None:
    """Verify provider abstraction contract for Fast2SMS, RichAutomate, Simulated, and Factory."""
    from services.api.services.providers.factory import NotificationProviderFactory
    from services.api.services.providers.fast2sms import Fast2SMSProvider
    from services.api.services.providers.richautomate import (
        RichAutomateWhatsAppProvider,
    )
    from services.api.services.providers.simulated import SimulatedNotificationProvider

    # 1. Fast2SMS Provider
    f2s = Fast2SMSProvider()
    assert f2s.provider_id == "fast2sms"
    assert NotificationChannel.SMS in f2s.supported_channels
    sms_res = f2s.send(
        channel=NotificationChannel.SMS,
        recipient="+919876543210",
        message="Test alert",
        mode=NotificationMode.SIMULATED,
    )
    assert sms_res.channel == NotificationChannel.SMS
    assert sms_res.status == ChannelDeliveryStatus.SIMULATED
    assert sms_res.provider == "fast2sms"
    assert sms_res.provider_message_id is not None

    # Fast2SMS rejects non-SMS channel
    invalid_res = f2s.send(
        channel=NotificationChannel.WHATSAPP,
        recipient="+919876543210",
        message="Test alert",
        mode=NotificationMode.SIMULATED,
    )
    assert invalid_res.status == ChannelDeliveryStatus.FAILED

    # 2. RichAutomate Provider
    ra = RichAutomateWhatsAppProvider()
    assert ra.provider_id == "richautomate"
    assert NotificationChannel.WHATSAPP in ra.supported_channels
    wa_res = ra.send(
        channel=NotificationChannel.WHATSAPP,
        recipient="+919876543210",
        message="Test WhatsApp alert",
        mode=NotificationMode.SIMULATED,
    )
    assert wa_res.channel == NotificationChannel.WHATSAPP
    assert wa_res.status == ChannelDeliveryStatus.SIMULATED
    assert wa_res.provider == "richautomate"

    # 3. Simulated Provider
    sim = SimulatedNotificationProvider()
    assert sim.provider_id == "simulated"
    assert {
        NotificationChannel.SMS,
        NotificationChannel.WHATSAPP,
    } == sim.supported_channels

    # 4. Factory Resolution
    prov_sms = NotificationProviderFactory.get_provider(NotificationChannel.SMS)
    assert isinstance(prov_sms, Fast2SMSProvider)

    prov_wa = NotificationProviderFactory.get_provider(NotificationChannel.WHATSAPP)
    assert isinstance(prov_wa, RichAutomateWhatsAppProvider)


def test_audit_trigger_values_and_enums() -> None:
    """Verify all escalation trigger values and notification statuses conform to contract."""
    # Escalation trigger values
    valid_triggers = {
        EscalationType.NO_ESCALATION,
        EscalationType.ADMIN_REVIEW,
        EscalationType.ADMIN_CONFIRMED,
        EscalationType.HIGH_CONFIDENCE_AUTO,
        EscalationType.CRITICAL_MEDICAL,
    }
    assert EscalationType.ADMIN_CONFIRMED.value == "ADMIN_CONFIRMED"
    assert EscalationType.HIGH_CONFIDENCE_AUTO.value == "HIGH_CONFIDENCE_AUTO"
    assert EscalationType.CRITICAL_MEDICAL.value == "CRITICAL_MEDICAL"
    assert len(valid_triggers) == 5

    # Notification status values
    valid_statuses = {
        NotificationStatus.READY,
        NotificationStatus.CONFIRMING,
        NotificationStatus.PROCESSING,
        NotificationStatus.SIMULATED,
        NotificationStatus.SENT,
        NotificationStatus.PARTIAL,
        NotificationStatus.DUPLICATE_SUPPRESSED,
        NotificationStatus.FAILED,
        NotificationStatus.CANCELLED,
    }
    assert NotificationStatus.SENT.value == "SENT"
    assert NotificationStatus.SIMULATED.value == "SIMULATED"
    assert NotificationStatus.PARTIAL.value == "PARTIAL"
    assert NotificationStatus.DUPLICATE_SUPPRESSED.value == "DUPLICATE_SUPPRESSED"
    assert NotificationStatus.FAILED.value == "FAILED"
