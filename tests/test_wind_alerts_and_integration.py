"""Comprehensive End-to-End Integration, Downwind Risk & Alert Tests for Phase 5."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from packages.geospatial.coordinates import calculate_geodesic_bearing, project_coordinate
from packages.schemas.dispersion import AtmosphericDispersionResult, PasquillStabilityClass
from packages.schemas.responders import (
    ChannelDeliveryStatus,
    EmergencyResponder,
    EscalationType,
    NotificationAction,
    NotificationChannel,
    NotificationMode,
    NotificationRequest,
    NotificationStatus,
    ResponderType,
    ResponsePriority,
)
from packages.schemas.weather import DataQuality, WindVector
from services.api.app import create_app
from services.api.services.events import EventQueryService
from services.api.services.notifications import NotificationService
from services.api.services.responders import (
    NotificationAuditService,
    ResponseRecommendationService,
)


@pytest.fixture(autouse=True)
def reset_audit_and_cache():
    NotificationAuditService.clear_activity_log()
    NotificationService.clear_escalation_records()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_geodesic_bearing_calculations():
    """Verify forward geodesic bearing calculation accuracy."""
    # North: (0, 0) -> (1, 0)
    assert calculate_geodesic_bearing(0.0, 0.0, 1.0, 0.0) == 0.0
    # East: (0, 0) -> (0, 1)
    assert calculate_geodesic_bearing(0.0, 0.0, 0.0, 1.0) == 90.0
    # South: (1, 0) -> (0, 0)
    assert calculate_geodesic_bearing(1.0, 0.0, 0.0, 0.0) == 180.0
    # West: (0, 1) -> (0, 0)
    assert calculate_geodesic_bearing(0.0, 1.0, 0.0, 0.0) == 270.0


def test_end_to_end_wind_incident_to_dispersion_to_responders(client: TestClient):
    """Test full pipeline: Event -> Weather -> Dispersion -> Responders Plume Classification."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    assert len(dataset.events) > 0
    event = dataset.events[0]
    event_id = event.event_id

    # 1. Query Responders endpoint
    resp = client.get(f"/events/{event_id}/responders")
    assert resp.status_code == 200
    data = resp.json()

    assert data["event_id"] == event_id
    assert "responders" in data
    assert len(data["responders"]) > 0

    # Verify each responder has a classified plume_impact_status
    valid_statuses = {
        "IN_ISOLATION_ZONE",
        "IN_PLUME_CORRIDOR",
        "DOWNWIND_SECTOR",
        "UPWIND_CLEAR",
        "CROSSWIND_CLEAR",
        "UNAVAILABLE",
    }
    for r in data["responders"]:
        assert r["plume_impact_status"] in valid_statuses
        assert r["distance_meters"] >= 0.0

    # Verify recommendation basis includes wind/dispersion summary
    has_wind_basis = any("Wind & Atmospheric Dispersion" in b for b in data["recommendation_basis"])
    assert has_wind_basis


def test_alert_notification_includes_downwind_hazard_and_deduplicates(client: TestClient):
    """Verify alert message formats wind data and obeys sector-based deduplication."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    rec = ResponseRecommendationService.get_recommendations_for_event(event_id)
    responder = rec.responders[0]

    # 1. Dispatch first notification
    payload = {
        "responder_id": responder.id,
        "action": "NOTIFY",
        "mode": "SIMULATED",
        "recipient_phone": "+919876543210",
        "channels": ["SMS", "WHATSAPP"],
        "escalation_type": "ADMIN_CONFIRMED",
        "analyst_notes": "First downwind dispatch",
    }

    res1 = client.post(f"/events/{event_id}/response/notify", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] in ["SENT", "SIMULATED"]

    # 2. Repeated dispatch with same wind sector -> Suppressed
    res2 = client.post(f"/events/{event_id}/response/notify", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "DUPLICATE_SUPPRESSED"
    assert "Duplicate notification request was suppressed" in data2["message"]

    # 3. Check activity log
    act_res = client.get(f"/events/{event_id}/response/activity")
    assert act_res.status_code == 200
    act_data = act_res.json()
    assert act_data["total_records"] >= 1


def test_wind_shift_allows_updated_alert_dispatch():
    """Verify that a meaningful wind direction shift (>30 deg) generates a distinct idempotency key."""
    event_id = "evt-test-wind-shift"
    responder_id = "resp-123"

    # Initial downwind bearing: 45° (Sector 30)
    key_sector_30 = NotificationService.make_idempotency_key(
        event_id=event_id,
        responder_id=responder_id,
        escalation_type=EscalationType.ADMIN_CONFIRMED,
        channel=NotificationChannel.SMS,
        trigger_source="ADMIN_CONFIRMED",
        wind_sector=30,
    )

    # Minor numerical fluctuation: 50° (Sector 30)
    key_minor_fluctuation = NotificationService.make_idempotency_key(
        event_id=event_id,
        responder_id=responder_id,
        escalation_type=EscalationType.ADMIN_CONFIRMED,
        channel=NotificationChannel.SMS,
        trigger_source="ADMIN_CONFIRMED",
        wind_sector=30,
    )
    assert key_sector_30 == key_minor_fluctuation

    # Meaningful wind shift: 95° (Sector 90)
    key_sector_90 = NotificationService.make_idempotency_key(
        event_id=event_id,
        responder_id=responder_id,
        escalation_type=EscalationType.ADMIN_CONFIRMED,
        channel=NotificationChannel.SMS,
        trigger_source="ADMIN_CONFIRMED",
        wind_sector=90,
    )
    assert key_sector_30 != key_sector_90


def test_alert_message_formatting_with_wind():
    """Verify format_alert_message output structure."""
    msg = NotificationService.format_alert_message(
        event_id="EVT-001",
        location="Hazira Industrial Area, Gujarat",
        classification="INDUSTRIAL",
        confidence_percent=98.5,
        frp_mw=65.4,
        priority=ResponsePriority.CRITICAL,
        is_critical=True,
        mode=NotificationMode.SIMULATED,
        wind_summary="6.2 m/s (SW -> NE)",
        hazard_reach_km=12.0,
        isolation_radius_m=200.0,
    )

    assert "FLAME INTELLIGENCE — CRITICAL ALERT" in msg
    assert "Hazira Industrial Area" in msg
    assert "6.2 m/s (SW -> NE)" in msg
    assert "Predicted Hazard Corridor: 12.0 km" in msg
    assert "Modeled Isolation Zone: 200 m" in msg
    assert "EVT-001" in msg


def test_weather_failure_resilience_in_responders_evaluation():
    """Verify that if weather/dispersion throws an error, responder recommendations still succeed gracefully."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    with patch("packages.data.weather.dispersion_service.AtmosphericDispersionService.evaluate_event_dispersion", side_effect=Exception("Weather API timeout")):
        rec = ResponseRecommendationService.get_recommendations_for_event(event_id)
        assert rec.event_id == event_id
        assert len(rec.responders) > 0
        # When dispersion fails, fallback status is UNAVAILABLE
        for r in rec.responders:
            assert r.plume_impact_status == "UNAVAILABLE"
