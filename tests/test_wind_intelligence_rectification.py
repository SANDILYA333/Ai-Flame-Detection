"""Automated verification tests for Wind Intelligence Demoability & Integration Rectification."""

import pytest
from fastapi.testclient import TestClient

from packages.data.weather.open_meteo import OpenMeteoWeatherProvider
from packages.schemas.weather import DataQuality
from services.api.main import app
from services.api.services.events import EventQueryService


@pytest.fixture(autouse=True)
def reset_dataset_cache():
    """Ensure clean dataset cache before each test."""
    EventQueryService.set_mock_dataset(None)
    yield
    EventQueryService.set_mock_dataset(None)


@pytest.fixture
def client():
    return TestClient(app)


class TestWindIntelligenceRectification:
    """Test suite confirming Wind Intelligence routes and catalog event resilience."""

    def test_weather_current_coordinates(self, client: TestClient):
        """Verify GET /weather/current returns 200 OK with wind vector."""
        res = client.get("/weather/current?lat=21.65&lon=69.60")
        assert res.status_code == 200
        data = res.json()
        assert "wind" in data
        assert "speed_ms" in data["wind"]
        assert "direction_from_deg" in data["wind"]
        assert "direction_to_deg" in data["wind"]
        assert "downwind_direction_label" in data["wind"]
        assert "data_quality" in data

    def test_event_dispersion_for_catalog_event(self, client: TestClient):
        """Verify GET /events/{event_id}/dispersion succeeds for catalog event EVT-2026-0831-15."""
        res = client.get("/events/EVT-2026-0831-15/dispersion")
        assert res.status_code == 200
        data = res.json()
        assert data["event_id"] == "EVT-2026-0831-15"
        assert "wind" in data
        assert "dispersion" in data
        assert "trajectory" in data
        assert data["dispersion"]["max_hazard_distance_km"] > 0
        assert data["dispersion"]["plume_angle_deg"] >= 0

    def test_dispersion_events_route_without_query_params(self, client: TestClient):
        """Verify GET /dispersion/events/{event_id} resolves coordinates automatically."""
        res = client.get("/dispersion/events/EVT-2026-0831-15")
        assert res.status_code == 200
        data = res.json()
        assert data["event_id"] == "EVT-2026-0831-15"
        assert data["source_location"]["latitude"] == 21.65
        assert data["source_location"]["longitude"] == 69.60

    def test_event_responders_for_catalog_event(self, client: TestClient):
        """Verify GET /events/{event_id}/responders resolves responders and calculates plume impact."""
        res = client.get("/events/EVT-2026-0831-15/responders")
        assert res.status_code == 200
        data = res.json()
        assert data["event_id"] == "EVT-2026-0831-15"
        assert "responders" in data
        assert len(data["responders"]) > 0
        for r in data["responders"]:
            assert "plume_impact_status" in r
            assert r["plume_impact_status"] in [
                "IN_ISOLATION_ZONE",
                "IN_PLUME_CORRIDOR",
                "DOWNWIND_SECTOR",
                "UPWIND_CLEAR",
                "CROSSWIND_CLEAR",
                "UNAVAILABLE",
            ]

    def test_physical_wind_and_plume_direction_consistency(self, client: TestClient):
        """Verify that downwind trajectory direction matches (wind_from + 180) % 360."""
        res = client.get("/events/EVT-2026-0831-01/dispersion")
        assert res.status_code == 200
        data = res.json()
        wind_from = data["wind"]["direction_from_deg"]
        wind_to = data["wind"]["direction_to_deg"]
        plume_angle = data["dispersion"]["plume_angle_deg"]

        expected_downwind = (wind_from + 180.0) % 360.0
        assert pytest.approx(wind_to, abs=0.5) == expected_downwind
        assert pytest.approx(plume_angle, abs=0.5) == expected_downwind

    def test_fallback_simulation_on_weather_failure(self, monkeypatch, client: TestClient):
        """Verify that when external weather is unavailable, fallback/simulation state is explicit."""
        def mock_execute(*args, **kwargs):
            raise RuntimeError("Simulated Open-Meteo connection timeout")

        monkeypatch.setattr(
            OpenMeteoWeatherProvider,
            "_execute_http_request",
            mock_execute,
        )

        res = client.get("/weather/current?lat=21.65&lon=69.60&allow_cached=false")
        assert res.status_code == 200
        data = res.json()
        assert data["data_quality"] == DataQuality.FALLBACK.value
        assert data["wind"]["speed_ms"] > 0
