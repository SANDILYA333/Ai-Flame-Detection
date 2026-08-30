"""Tests for API-006: Events."""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_get_events_success() -> None:
    """Test successful retrieval of events without filters."""
    response = client.get("/events")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "sih26162-api"
    assert "pagination" in data
    assert "events" in data

    # Based on the pilot data, we should have events returned
    assert len(data["events"]) > 0

    first_event = data["events"][0]
    assert "event_id" in first_event
    assert "started_at" in first_event
    assert "centroid_latitude" in first_event
    assert "detection_count" in first_event
    # Check that it includes classification and persistence states
    assert "classification_state" in first_event
    assert "persistence_state" in first_event


def test_get_events_with_bbox_filter() -> None:
    """Test spatial filtering with bounding box."""
    # First get an event to know a valid bbox
    res = client.get("/events")
    all_events = res.json()["events"]
    assert len(all_events) > 0
    ev = all_events[0]
    lat, lon = ev["centroid_latitude"], ev["centroid_longitude"]

    # Tight bbox around the first event
    bbox = {
        "min_lat": lat - 0.1,
        "max_lat": lat + 0.1,
        "min_lon": lon - 0.1,
        "max_lon": lon + 0.1,
    }

    response = client.get("/events", params=bbox)
    assert response.status_code == 200
    filtered = response.json()["events"]
    assert len(filtered) > 0

    # Ensure all returned events fall inside the bbox
    for filtered_ev in filtered:
        assert bbox["min_lat"] <= filtered_ev["centroid_latitude"] <= bbox["max_lat"]
        assert bbox["min_lon"] <= filtered_ev["centroid_longitude"] <= bbox["max_lon"]


def test_get_events_invalid_bbox() -> None:
    """Test validation error when providing partial bbox."""
    response = client.get("/events", params={"min_lat": 20.0, "max_lat": 25.0})
    # Should trigger validation error
    assert response.status_code == 422
    assert "all four coordinates" in response.text


def test_get_events_time_filter() -> None:
    """Test temporal filtering."""
    # Based on default dummy data date ranges
    params = {
        "start_time": "2026-08-01T00:00:00Z",
        "end_time": "2026-08-03T23:59:59Z",
    }
    response = client.get("/events", params=params)
    assert response.status_code == 200


def test_get_events_classification_filter() -> None:
    """Test filtering by classification state."""
    response = client.get("/events", params={"classification_state": "industrial"})
    assert response.status_code == 200
    events = response.json()["events"]
    for ev in events:
        assert ev["classification_state"] == "industrial"


def test_get_events_status_filter() -> None:
    """Test filtering by status (persistence state)."""
    response = client.get(
        "/events", params={"status": "CANDIDATE_PERSISTENT_SOURCE"}
    )
    assert response.status_code == 200
    events = response.json()["events"]
    for ev in events:
        assert ev["persistence_state"] == "CANDIDATE_PERSISTENT_SOURCE"
