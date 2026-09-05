"""Unit and integration tests for Contextual External Intelligence and Media API (API-007)."""

import pytest
from fastapi.testclient import TestClient

from services.api.app import create_app

app = create_app()
client = TestClient(app)


def test_get_event_media_success_nalgonda():
    """Verify contextual media endpoint returns structured news and videos for Nalgonda."""
    response = client.get("/events/EVT-2026-0831-21/media")
    assert response.status_code == 200
    data = response.json()

    assert data["event_id"] == "EVT-2026-0831-21"
    assert "query_context" in data
    assert "Nalgonda" in data["query_context"]["location_query"]
    assert len(data["news"]) >= 1
    assert data["news"][0]["relevance_score"] >= 0.8
    assert len(data["videos"]) >= 1
    assert data["videos"][0]["youtube_id"] is not None
    assert "disclaimer" in data


def test_get_event_media_alias_success():
    """Verify alias route /events/{id}/external-intelligence works."""
    response = client.get("/events/EVT-2026-0831-21/external-intelligence")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "EVT-2026-0831-21"


def test_get_event_media_unindexed_event_returns_empty_gracefully():
    """Verify unindexed event returns query context and empty lists, not 500 error."""
    # EVT-2026-0831-02 (Singrauli) exists in catalog but has no fake news/video manufactured
    response = client.get("/events/EVT-2026-0831-02/media")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "EVT-2026-0831-02"
    assert isinstance(data["news"], list)
    assert isinstance(data["videos"], list)


def test_get_event_media_not_found():
    """Verify 404 is returned if event does not exist in catalog."""
    response = client.get("/events/EVT-NON-EXISTENT-9999/media")
    assert response.status_code == 404
