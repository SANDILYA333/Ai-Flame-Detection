"""Unit and integration tests for API-005 detections endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.config.settings import (
    AppEnvironment,
    LogLevel,
    get_test_settings,
)
from services.api.app import create_app
from services.api.dependencies import get_app_settings
from services.api.schemas.detections import DetectionsResponse
from services.api.services.detections import DetectionQueryService


@pytest.fixture(autouse=True)
def reset_detection_cache() -> None:
    """Ensure cached detections are fresh for every test."""
    DetectionQueryService._cached_detections = None


@pytest.fixture
def test_app() -> FastAPI:
    """Create test FastAPI application instance."""
    settings = get_test_settings(
        ENVIRONMENT=AppEnvironment.TEST,
        DEBUG=True,
        LOG_LEVEL=LogLevel.DEBUG,
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_app_settings] = lambda: settings
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a TestClient for testing HTTP requests."""
    return TestClient(test_app)


class TestApi005Detections:
    """Test suite for API-005 /detections endpoint and query filters."""

    def test_detections_endpoint_default(self, client: TestClient) -> None:
        """TEST 1: GET /detections returns 200 OK with default pagination."""
        response = client.get("/detections")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        validated = DetectionsResponse.model_validate(data)
        assert validated.service == "sih26162-api"
        assert validated.pagination.total_count == 6
        assert validated.pagination.limit == 50
        assert validated.pagination.offset == 0
        assert validated.pagination.has_next is False
        assert len(validated.detections) == 6

        # Check canonical fields on first detection
        first = validated.detections[0]
        assert first.detection_id.startswith("det_")
        assert first.source == "firms"
        assert first.satellite in ("NOAA-20", "Suomi-NPP", "Terra", "Aqua")
        assert first.instrument == "VIIRS"
        assert first.geometry.latitude >= -90.0
        assert first.geometry.longitude >= -180.0

    def test_detections_bbox_filter(self, client: TestClient) -> None:
        """TEST 2: Spatial bounding box filter returns only enclosed detections."""
        params = {
            "min_lat": 22.4500,
            "max_lat": 22.4520,
            "min_lon": 70.0500,
            "max_lon": 70.0530,
        }
        response = client.get("/detections", params=params)
        assert response.status_code == 200
        data = response.json()
        assert len(data["detections"]) > 0

        for det in data["detections"]:
            assert 22.4500 <= det["geometry"]["latitude"] <= 22.4520
            assert 70.0500 <= det["geometry"]["longitude"] <= 70.0530

    def test_detections_temporal_filter(self, client: TestClient) -> None:
        """TEST 3: Temporal filter isolates specific observation dates."""
        params = {
            "start_time": "2026-08-01T00:00:00Z",
            "end_time": "2026-08-01T23:59:59Z",
        }
        response = client.get("/detections", params=params)
        assert response.status_code == 200
        data = response.json()
        assert len(data["detections"]) == 3  # 3 detections on 2026-08-01

        for det in data["detections"]:
            assert det["acquired_at"].startswith("2026-08-01")

    def test_detections_source_and_metadata_filter(self, client: TestClient) -> None:
        """TEST 4: Day/night, satellite, and instrument filters operate cleanly."""
        # Day filter
        resp_day = client.get("/detections", params={"day_night": "D"})
        assert resp_day.status_code == 200
        for det in resp_day.json()["detections"]:
            assert det["day_night"] == "D"

        # Night filter
        resp_night = client.get("/detections", params={"day_night": "N"})
        assert resp_night.status_code == 200
        for det in resp_night.json()["detections"]:
            assert det["day_night"] == "N"

        # Instrument filter
        resp_inst = client.get("/detections", params={"instrument": "VIIRS"})
        assert resp_inst.status_code == 200
        assert len(resp_inst.json()["detections"]) == 6

    def test_detections_pagination(self, client: TestClient) -> None:
        """TEST 5: Pagination limit and offset traverse dataset deterministically."""
        resp_page1 = client.get("/detections", params={"limit": 2, "offset": 0})
        assert resp_page1.status_code == 200
        p1_data = resp_page1.json()
        assert len(p1_data["detections"]) == 2
        assert p1_data["pagination"]["total_count"] == 6
        assert p1_data["pagination"]["limit"] == 2
        assert p1_data["pagination"]["offset"] == 0
        assert p1_data["pagination"]["has_next"] is True

        resp_page2 = client.get("/detections", params={"limit": 2, "offset": 2})
        assert resp_page2.status_code == 200
        p2_data = resp_page2.json()
        assert len(p2_data["detections"]) == 2
        assert p2_data["pagination"]["offset"] == 2

        # Ensure distinct records across pages
        p1_ids = {d["detection_id"] for d in p1_data["detections"]}
        p2_ids = {d["detection_id"] for d in p2_data["detections"]}
        assert len(p1_ids.intersection(p2_ids)) == 0

        # Beyond bounds
        resp_page4 = client.get("/detections", params={"limit": 2, "offset": 6})
        assert resp_page4.status_code == 200
        p4_data = resp_page4.json()
        assert len(p4_data["detections"]) == 0
        assert p4_data["pagination"]["has_next"] is False

    def test_detections_empty_result(self, client: TestClient) -> None:
        """TEST 6: Valid query with zero matches returns 200 OK and empty list."""
        params = {
            "min_lat": 0.0,
            "max_lat": 1.0,
            "min_lon": 0.0,
            "max_lon": 1.0,
        }
        response = client.get("/detections", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_count"] == 0
        assert data["pagination"]["has_next"] is False
        assert data["detections"] == []

    def test_detections_validation_errors(self, client: TestClient) -> None:
        """TEST 7: Incomplete or inverted query parameters return 422."""
        # Partial bbox
        resp_partial = client.get("/detections", params={"min_lat": 22.0})
        assert resp_partial.status_code == 422

        # Inverted latitude
        resp_inv_lat = client.get(
            "/detections",
            params={
                "min_lat": 25.0,
                "max_lat": 20.0,
                "min_lon": 70.0,
                "max_lon": 75.0,
            },
        )
        assert resp_inv_lat.status_code == 422

        # Inverted time range
        resp_inv_time = client.get(
            "/detections",
            params={
                "start_time": "2026-08-05T00:00:00Z",
                "end_time": "2026-08-01T00:00:00Z",
            },
        )
        assert resp_inv_time.status_code == 422

    def test_detections_missingness_preserved(self, client: TestClient) -> None:
        """TEST 8: Null/optional measurements in raw data are preserved as None."""
        response = client.get("/detections")
        assert response.status_code == 200
        detections = response.json()["detections"]

        # Missing physical measurements must remain None
        has_null_ti5 = any(d["brightness_ti5_k"] is None for d in detections)
        has_null_confidence = any(d["confidence"] is None for d in detections)
        assert has_null_ti5 is True
        assert has_null_confidence is True

    def test_detections_no_secret_leakage(self, client: TestClient) -> None:
        """TEST 9: Zero secret exposure in /detections response."""
        response = client.get("/detections")
        body_text = response.text
        assert "FIRMS_MAP_KEY" not in body_text
        assert "POSTGRES_PASSWORD" not in body_text
        assert "SECRET_KEY" not in body_text
        assert "sih_dev_password" not in body_text

    def test_openapi_documents_detections(self, client: TestClient) -> None:
        """TEST 10: /openapi.json contains /detections with all query params."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/detections" in schema["paths"]
        det_get = schema["paths"]["/detections"]["get"]
        assert "200" in det_get["responses"]
        param_names = [p["name"] for p in det_get.get("parameters", [])]
        assert "min_lat" in param_names
        assert "max_lat" in param_names
        assert "min_lon" in param_names
        assert "max_lon" in param_names
        assert "start_time" in param_names
        assert "end_time" in param_names
        assert "limit" in param_names
        assert "offset" in param_names
