"""Unit and integration tests for API-002 system readiness endpoint."""

from unittest.mock import patch

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
from services.api.schemas.readiness import (
    DependencyHealth,
    DependencyStatus,
    ReadinessResponse,
)
from services.api.services.readiness import ReadinessCheckService


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


class TestApi002Readiness:
    """Test suite for API-002 /ready endpoint, diagnostics, and status codes."""

    def test_readiness_happy_path(self, client: TestClient) -> None:
        """TEST 1: GET /ready returns 200 OK when all dependencies are ready."""
        healthy_db = DependencyHealth(
            status=DependencyStatus.READY,
            details={
                "host": "localhost",
                "port": 5432,
                "database": "sih26162",
                "connected": True,
            },
        )
        with patch.object(
            ReadinessCheckService, "check_database", return_value=healthy_db
        ):
            response = client.get("/ready")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")

            data = response.json()
            validated = ReadinessResponse.model_validate(data)
            assert validated.status == DependencyStatus.READY
            assert validated.service == "sih26162-api"
            assert validated.version == "0.1.0"
            assert validated.environment == AppEnvironment.TEST.value
            assert validated.dependencies["database"].status == DependencyStatus.READY
            assert (
                validated.dependencies["model_registry"].status
                == DependencyStatus.READY
            )
            assert (
                validated.dependencies["configuration"].status == DependencyStatus.READY
            )

    def test_readiness_database_unavailable(self, client: TestClient) -> None:
        """TEST 2: GET /ready returns 503 when database dependency is down."""
        unavailable_db = DependencyHealth(
            status=DependencyStatus.UNAVAILABLE,
            details={
                "host": "localhost",
                "port": 5432,
                "database": "sih26162",
                "connected": False,
                "error": "Database service is unreachable or not ready",
            },
        )
        with patch.object(
            ReadinessCheckService, "check_database", return_value=unavailable_db
        ):
            response = client.get("/ready")
            assert response.status_code == 503
            assert response.headers["content-type"].startswith("application/json")

            data = response.json()
            validated = ReadinessResponse.model_validate(data)
            assert validated.status == DependencyStatus.UNAVAILABLE
            assert (
                validated.dependencies["database"].status
                == DependencyStatus.UNAVAILABLE
            )

    def test_readiness_no_secret_leakage(self, client: TestClient) -> None:
        """TEST 3: Zero secret exposure in /ready response on success and fail."""
        # Test success response
        healthy_db = DependencyHealth(
            status=DependencyStatus.READY,
            details={
                "host": "localhost",
                "port": 5432,
                "database": "sih26162",
                "connected": True,
            },
        )
        with patch.object(
            ReadinessCheckService, "check_database", return_value=healthy_db
        ):
            resp_success = client.get("/ready")
            text_success = resp_success.text
            assert "FIRMS_MAP_KEY" not in text_success
            assert "POSTGRES_PASSWORD" not in text_success
            assert "SECRET_KEY" not in text_success
            assert "sih_dev_password" not in text_success

        # Test failure response
        unhealthy_db = DependencyHealth(
            status=DependencyStatus.UNAVAILABLE,
            details={
                "host": "localhost",
                "port": 5432,
                "database": "sih26162",
                "connected": False,
                "error": "Connection error",
            },
        )
        with patch.object(
            ReadinessCheckService, "check_database", return_value=unhealthy_db
        ):
            resp_fail = client.get("/ready")
            text_fail = resp_fail.text
            assert "FIRMS_MAP_KEY" not in text_fail
            assert "POSTGRES_PASSWORD" not in text_fail
            assert "SECRET_KEY" not in text_fail
            assert "sih_dev_password" not in text_fail

    def test_direct_service_execution_safe(self) -> None:
        """TEST 4: ReadinessCheckService executes safely with invalid host."""
        settings = get_test_settings(
            POSTGRES_HOST="invalid-nonexistent-host-99.internal",
            POSTGRES_PORT=5432,
        )
        result = ReadinessCheckService.evaluate_readiness(settings)
        assert isinstance(result, ReadinessResponse)
        assert result.status == DependencyStatus.UNAVAILABLE
        assert result.dependencies["database"].status == DependencyStatus.UNAVAILABLE
        assert "connected" in result.dependencies["database"].details

    def test_openapi_documents_ready_endpoint(self, client: TestClient) -> None:
        """TEST 5: /openapi.json contains /ready with 200 and 503 responses."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/ready" in schema["paths"]
        ready_get = schema["paths"]["/ready"]["get"]
        assert "200" in ready_get["responses"]
        assert "503" in ready_get["responses"]
