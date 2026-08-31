"""Tests for API-010 (Sources)."""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_api_010_list_sources_success() -> None:
    """API-010: Test successful retrieval of all sources."""
    response = client.get("/sources")
    assert response.status_code == 200

    data = response.json()
    assert "sources" in data
    sources = data["sources"]
    assert isinstance(sources, list)
    assert len(sources) > 0

    # Verify schema of the first source
    source = sources[0]
    assert "source_id" in source
    assert "name" in source
    assert "provider" in source
    assert "role" in source
    assert "status" in source

    # Ensure no secrets leakage
    assert "FIRMS_MAP_KEY" not in str(data)
    assert "credentials" not in str(data)


def test_api_010_get_source_success() -> None:
    """API-010: Test successful retrieval of a single source."""
    # First get a valid source ID
    list_response = client.get("/sources")
    sources = list_response.json()["sources"]
    source_id = sources[0]["source_id"]

    response = client.get(f"/sources/{source_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["source_id"] == source_id
    assert "name" in data
    assert "provider" in data
    assert "role" in data
    assert "status" in data


def test_api_010_get_source_not_found() -> None:
    """API-010: Test unknown source ID returns 404."""
    response = client.get("/sources/unknown_source_id_999")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert "not found" in data["message"].lower()
