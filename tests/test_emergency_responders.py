"""Tests for emergency responders directory and simulation (API-013)."""

import pytest
from fastapi.testclient import TestClient

from packages.schemas.responders import (
    NotificationAction,
    NotificationMode,
    NotificationRequest,
    NotificationStatus,
    ResponderType,
    ResponsePriority,
)
from services.api.app import create_app
from services.api.services.events import EventQueryService
from services.api.services.responders import (
    NotificationAuditService,
    ResponderDirectoryService,
    ResponseRecommendationService,
)


@pytest.fixture(autouse=True)
def clean_audit_log() -> None:
    """Clear in-memory audit log before each test."""
    NotificationAuditService.clear_activity_log()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_responder_directory_service_loads_datasets() -> None:
    """Verify emergency responders directory loads and normalizes data."""
    responders = ResponderDirectoryService.get_all_raw_responders()
    assert len(responders) > 0

    types = {r["type"] for r in responders}
    has_med = (
        ResponderType.BURN_ICU in types or ResponderType.HOSPITAL in types
    )
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
    """Verify recommendation service correctly ranks responders."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    assert len(dataset.events) > 0
    event = dataset.events[0]

    rec = ResponseRecommendationService.get_recommendations_for_event(
        event.event_id
    )
    assert rec.event_id == event.event_id
    assert rec.response_priority in [
        ResponsePriority.CRITICAL,
        ResponsePriority.HIGH,
        ResponsePriority.MEDIUM,
        ResponsePriority.MONITOR_ONLY,
        ResponsePriority.REVIEW_REQUIRED,
    ]
    assert len(rec.responders) > 0
    assert len(rec.recommendation_basis) > 0

    top = rec.responders[0]
    assert top.distance_meters >= 0
    assert top.estimated_eta_minutes >= 1
    assert "min" in top.formatted_eta
    assert top.recommendation_reason


def test_response_recommendation_unknown_event_raises_404() -> None:
    """Verify querying recommendations for an invalid event raises 404."""
    with pytest.raises(Exception) as exc_info:
        ResponseRecommendationService.get_recommendations_for_event(
            "EVT-NONEXISTENT-999"
        )
    assert "not found" in str(exc_info.value).lower()


def test_notification_audit_service_simulation() -> None:
    """Verify notification processing creates truthful SIMULATED records."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event = dataset.events[0]
    all_raw = ResponderDirectoryService.get_all_raw_responders()
    responder = all_raw[0]

    req = NotificationRequest(
        responder_id=responder["id"],
        action=NotificationAction.NOTIFY,
        mode=NotificationMode.SIMULATED,
        analyst_notes="Test analyst emergency confirmation",
    )

    resp = NotificationAuditService.process_notification(event.event_id, req)
    assert resp.status == NotificationStatus.SIMULATED
    assert resp.mode == NotificationMode.SIMULATED
    assert resp.event_id == event.event_id
    assert resp.responder_id == responder["id"]
    assert resp.responder_name == responder["name"]
    assert "simulated" in resp.message.lower()

    activity = NotificationAuditService.get_activity_for_event(event.event_id)
    assert len(activity) == 1
    assert activity[0].notification_id == resp.notification_id
    assert activity[0].status == NotificationStatus.SIMULATED


def test_api_get_event_responders(client: TestClient) -> None:
    """Test GET /events/{event_id}/responders HTTP endpoint."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    response = client.get(f"/events/{event_id}/responders")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == event_id
    assert "response_priority" in data
    assert "responders" in data
    assert len(data["responders"]) > 0


def test_api_get_event_responders_404(client: TestClient) -> None:
    """Test GET /events/{event_id}/responders with invalid ID returns 404."""
    response = client.get("/events/INVALID_EVENT_XYZ/responders")
    assert response.status_code == 404
    err = response.json()
    assert "not found" in err["message"].lower()


def test_api_notify_responder(client: TestClient) -> None:
    """Test POST /events/{event_id}/response/notify HTTP endpoint."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id
    all_raw = ResponderDirectoryService.get_all_raw_responders()
    resp_id = all_raw[0]["id"]

    payload = {
        "responder_id": resp_id,
        "action": "NOTIFY",
        "mode": "SIMULATED",
        "analyst_notes": "Live test simulation",
    }

    response = client.post(f"/events/{event_id}/response/notify", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "SIMULATED"
    assert res_data["mode"] == "SIMULATED"
    assert res_data["responder_id"] == resp_id

    act_response = client.get(f"/events/{event_id}/response/activity")
    assert act_response.status_code == 200
    act_data = act_response.json()
    assert act_data["total_records"] == 1
    assert act_data["records"][0]["responder_id"] == resp_id


def test_api_notify_invalid_responder_404(client: TestClient) -> None:
    """Test POST notification with unknown responder returns 404."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    payload = {
        "responder_id": "NON_EXISTENT_RESPONDER",
        "action": "NOTIFY",
    }

    response = client.post(f"/events/{event_id}/response/notify", json=payload)
    assert response.status_code == 404
