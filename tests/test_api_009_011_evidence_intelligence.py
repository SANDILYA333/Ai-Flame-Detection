"""Tests for API-009 (Evidence) and API-011 (Intelligence)."""

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


def test_api_009_get_event_evidence_success() -> None:
    """API-009: Test successful retrieval of event evidence."""
    event_id = get_valid_event_id()

    response = client.get(f"/events/{event_id}/evidence")
    assert response.status_code == 200

    data = response.json()
    assert data["event_id"] == event_id
    assert "context_evidence" in data
    assert "reference_evidence" in data
    assert isinstance(data["context_evidence"], list)
    assert isinstance(data["reference_evidence"], list)

    # Ensure no secrets leakage
    assert "FIRMS_MAP_KEY" not in str(data)
    assert "credentials" not in str(data)


def test_api_009_get_event_evidence_not_found() -> None:
    """API-009: Test unknown event ID returns 404."""
    response = client.get("/events/evt_unknown_12345/evidence")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert "not found" in data["message"].lower()


def test_api_011_get_event_intelligence_success() -> None:
    """API-011: Test successful retrieval of event intelligence."""
    event_id = get_valid_event_id()

    response = client.get(f"/events/{event_id}/intelligence")
    assert response.status_code == 200

    data = response.json()
    assert data["event_id"] == event_id
    assert "phenomenon" in data
    assert "context" in data
    assert "persistence" in data
    assert "attribution" in data
    assert "uncertainty" in data
    assert "evidence_completeness" in data

    # Check abstention format
    uncertainty = data["uncertainty"]
    assert "abstention_recommended" in uncertainty

    # Ensure no secrets leakage
    assert "FIRMS_MAP_KEY" not in str(data)
    assert "credentials" not in str(data)


def test_api_011_get_event_intelligence_not_found() -> None:
    """API-011: Test unknown event ID returns 404."""
    response = client.get("/events/evt_unknown_12345/intelligence")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert "not found" in data["message"].lower()
