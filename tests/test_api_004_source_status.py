"""Unit and integration tests for API-004 source status endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from packages.config.settings import (
    AppEnvironment,
    LogLevel,
    get_test_settings,
)
from packages.schemas.enums import SourceRole
from services.api.app import create_app
from services.api.dependencies import get_app_settings
from services.api.schemas.sources import (
    SourceAvailabilityState,
    SourceOperationalMode,
    SourcesStatusResponse,
)


@pytest.fixture
def test_app() -> FastAPI:
    """Create test FastAPI application instance."""
    settings = get_test_settings(
        ENVIRONMENT=AppEnvironment.TEST,
        DEBUG=True,
        LOG_LEVEL=LogLevel.DEBUG,
        FIRMS_MAP_KEY=SecretStr("mock_secret_firms_key_12345"),
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_app_settings] = lambda: settings
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a TestClient for testing HTTP requests."""
    return TestClient(test_app)


class TestApi004SourceStatus:
    """Test suite for API-004 /sources/status endpoint and provider metadata."""

    def test_sources_status_endpoint_and_schema(self, client: TestClient) -> None:
        """TEST 1: GET /sources/status returns 200 OK and conforms to schema."""
        response = client.get("/sources/status")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        validated = SourcesStatusResponse.model_validate(data)
        assert validated.service == "sih26162-api"
        assert validated.environment == AppEnvironment.TEST.value
        assert len(validated.sources) >= 5

    def test_sources_status_firms_live_mode(self, client: TestClient) -> None:
        """TEST 2: When FIRMS_MAP_KEY is set, FIRMS reports live and configured."""
        response = client.get("/sources/status")
        assert response.status_code == 200
        data = response.json()

        firms = next(s for s in data["sources"] if s["source_id"] == "nasa_firms")
        assert firms["provider"] == "NASA Earthdata / EOSDIS"
        assert firms["role"] == SourceRole.OBSERVATION.value
        assert firms["mode"] == SourceOperationalMode.LIVE.value
        assert firms["status"] == SourceAvailabilityState.CONFIGURED.value
        assert firms["details"]["has_map_key"] is True

    def test_sources_status_firms_offline_mode(self) -> None:
        """TEST 3: When FIRMS_MAP_KEY is None, FIRMS reports offline mode cleanly."""
        offline_settings = get_test_settings(
            ENVIRONMENT=AppEnvironment.TEST,
            FIRMS_MAP_KEY=None,
        )
        app = create_app(settings=offline_settings)
        app.dependency_overrides[get_app_settings] = lambda: offline_settings
        client = TestClient(app)

        response = client.get("/sources/status")
        assert response.status_code == 200
        data = response.json()

        firms = next(s for s in data["sources"] if s["source_id"] == "nasa_firms")
        assert firms["mode"] == SourceOperationalMode.OFFLINE.value
        assert firms["status"] == SourceAvailabilityState.OFFLINE_ONLY.value
        assert firms["details"]["has_map_key"] is False

    def test_sources_status_all_providers_and_roles(self, client: TestClient) -> None:
        """TEST 4: All registered context and observation providers are listed."""
        response = client.get("/sources/status")
        assert response.status_code == 200
        sources = {s["source_id"]: s for s in response.json()["sources"]}

        assert "nasa_firms" in sources
        assert sources["nasa_firms"]["role"] == SourceRole.OBSERVATION.value

        assert "osm" in sources
        assert sources["osm"]["role"] == SourceRole.CONTEXT.value

        assert "wri_power_plants" in sources
        assert sources["wri_power_plants"]["role"] == SourceRole.CONTEXT.value

        assert "gem_fossil_infrastructure" in sources
        assert sources["gem_fossil_infrastructure"]["role"] == SourceRole.CONTEXT.value

        assert "landcover" in sources
        assert sources["landcover"]["role"] == SourceRole.CONTEXT.value

    def test_sources_status_no_secret_leakage(self, client: TestClient) -> None:
        """TEST 5: Zero secret exposure in /sources/status response."""
        response = client.get("/sources/status")
        body_text = response.text
        assert "mock_secret_firms_key_12345" not in body_text
        assert "POSTGRES_PASSWORD" not in body_text
        assert "SECRET_KEY" not in body_text
        assert "sih_dev_password" not in body_text

    def test_openapi_documents_sources_status(self, client: TestClient) -> None:
        """TEST 6: /openapi.json contains /sources/status with 200 response."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/sources/status" in schema["paths"]
        status_get = schema["paths"]["/sources/status"]["get"]
        assert "200" in status_get["responses"]
