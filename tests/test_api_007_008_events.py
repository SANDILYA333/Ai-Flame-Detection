"""Tests for API-007 (Event detail) and API-008 (Event timeline)."""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def get_valid_event_id() -> str:
    """Helper to fetch a valid event ID from the API-006 endpoint."""
    response = client.get("/events?limit=1")
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) > 0, "No events available for testing"
    return str(events[0]["event_id"])


def test_api_007_get_event_detail_success() -> None:
    """API-007: Test successful retrieval of an event detail."""
    event_id = get_valid_event_id()

    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["event_id"] == event_id
    assert "geometry" in data
    assert data["geometry"]["type"] == "Point"
    assert len(data["geometry"]["coordinates"]) == 2
    assert "started_at" in data
    assert "ended_at" in data
    assert "detection_count" in data
    assert "context_status" in data
    assert "intelligence_status" in data
    # Ensure no secrets leakage
    assert "FIRMS_MAP_KEY" not in str(data)
    assert "credentials" not in str(data)


def test_api_007_get_event_not_found() -> None:
    """API-007: Test unknown event ID returns 404."""
    response = client.get("/events/evt_unknown_12345")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert "not found" in data["message"].lower()


def test_api_008_get_event_timeline_success() -> None:
    """API-008: Test successful retrieval of an event timeline."""
    event_id = get_valid_event_id()

    response = client.get(f"/events/{event_id}/timeline")
    assert response.status_code == 200

    data = response.json()
    assert data["event_id"] == event_id
    assert "timeline" in data

    timeline = data["timeline"]
    assert len(timeline) > 0

    # Test timeline sorting (deterministic chronological order)
    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        curr = timeline[i]
        assert prev["timestamp"] <= curr["timestamp"]
        if prev["timestamp"] == curr["timestamp"]:
            # Secondary sort is detection_id
            assert prev["detection_id"] <= curr["detection_id"]

    # Verify temporal bounds consistency
    started_at = data["started_at"]
    ended_at = data["ended_at"]
    assert timeline[0]["timestamp"] >= started_at
    assert timeline[-1]["timestamp"] <= ended_at


def test_api_008_get_timeline_not_found() -> None:
    """API-008: Test unknown event ID returns 404."""
    response = client.get("/events/evt_unknown_12345/timeline")
    assert response.status_code == 404


def test_integration_event_detail_and_timeline() -> None:
    """Integration test verifying consistency between API-007 and API-008."""
    event_id = get_valid_event_id()

    detail_res = client.get(f"/events/{event_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()

    timeline_res = client.get(f"/events/{event_id}/timeline")
    assert timeline_res.status_code == 200
    timeline_data = timeline_res.json()

    # The event IDs must match exactly
    assert detail_data["event_id"] == timeline_data["event_id"]

    # Temporal bounds must match exactly between the two endpoints
    assert detail_data["started_at"] == timeline_data["started_at"]
    assert detail_data["ended_at"] == timeline_data["ended_at"]

    # Detection count in detail should match the length of the timeline list
    assert detail_data["detection_count"] == len(timeline_data["timeline"])
