"""Unit and integration tests for API-003 version endpoint."""

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
from services.api.schemas.version import VersionResponse
from services.ml.features.standard_set import STANDARD_FEATURE_VERSION
from services.ml.labels.targets import STANDARD_TARGET_SET_VERSION


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


class TestApi003Version:
    """Test suite for API-003 /version endpoint and contract metadata."""

    def test_version_endpoint_status_and_schema(
        self, client: TestClient
    ) -> None:
        """TEST 1: GET /version returns HTTP 200 and conforms to VersionResponse."""
        response = client.get("/version")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        validated = VersionResponse.model_validate(data)
        assert validated.service == "sih26162-api"
        assert validated.version == "0.1.0"
        assert validated.api_version == "v1"
        assert validated.environment == AppEnvironment.TEST.value
        assert validated.contracts.features == STANDARD_FEATURE_VERSION
        assert validated.contracts.targets == STANDARD_TARGET_SET_VERSION

    def test_version_contracts_accuracy(self, client: TestClient) -> None:
        """TEST 2: Contract versions match canonical ML/Feature definitions."""
        response = client.get("/version")
        assert response.status_code == 200
        contracts = response.json()["contracts"]
        assert contracts["features"] == "feat_v1.0.0"
        assert contracts["targets"] == "target_v1.0.0"

    def test_version_configuration_integration(self) -> None:
        """TEST 3: Application respects overridden environment in /version."""
        prod_settings = get_test_settings(
            ENVIRONMENT=AppEnvironment.PRODUCTION,
            DEBUG=False,
        )
        app = create_app(settings=prod_settings)
        app.dependency_overrides[get_app_settings] = lambda: prod_settings
        client = TestClient(app)

        response = client.get("/version")
        assert response.status_code == 200
        assert response.json()["environment"] == "production"

    def test_version_no_secret_leakage(self, client: TestClient) -> None:
        """TEST 4: Zero secret exposure in /version response."""
        response = client.get("/version")
        body_text = response.text
        assert "FIRMS_MAP_KEY" not in body_text
        assert "POSTGRES_PASSWORD" not in body_text
        assert "SECRET_KEY" not in body_text
        assert "sih_dev_password" not in body_text

    def test_openapi_documents_version_endpoint(
        self, client: TestClient
    ) -> None:
        """TEST 5: /openapi.json contains /version with 200 response."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/version" in schema["paths"]
        version_get = schema["paths"]["/version"]["get"]
        assert "200" in version_get["responses"]
