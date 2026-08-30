"""Tests for API-001 FastAPI application foundation and health check."""

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from packages.config.settings import (
    AppEnvironment,
    LogLevel,
    get_test_settings,
)
from packages.errors import (
    ConflictError,
    DatabaseConnectionError,
    NotFoundError,
    ServiceTimeoutError,
    ValidationError,
)
from services.api.app import create_app
from services.api.dependencies import get_app_settings
from services.api.schemas.health import HealthResponse


@pytest.fixture
def test_app() -> FastAPI:
    """Create test FastAPI application instance with test settings."""
    settings = get_test_settings(
        ENVIRONMENT=AppEnvironment.TEST,
        DEBUG=True,
        LOG_LEVEL=LogLevel.DEBUG,
        CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"],
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_app_settings] = lambda: settings
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a TestClient for testing HTTP requests."""
    return TestClient(test_app)


class TestApi001Foundation:
    """Test suite for API-001 foundation, health endpoint, CORS, and errors."""

    def test_application_creation(self) -> None:
        """TEST 1: Application factory creates a valid FastAPI instance."""
        settings = get_test_settings(ENVIRONMENT=AppEnvironment.TEST)
        app = create_app(settings=settings)
        assert isinstance(app, FastAPI)
        expected_title = (
            "SIH26162 — Satellite Thermal Anomaly & Fire Intelligence System"
        )
        assert app.title == expected_title
        assert app.version == "0.1.0"
        assert app.state.settings == settings

    def test_health_endpoint_status_and_schema(self, client: TestClient) -> None:
        """TEST 2: GET /health returns HTTP 200 and conforms to HealthResponse."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        validated = HealthResponse.model_validate(data)
        assert validated.status == "ok"
        assert validated.service == "sih26162-api"
        assert validated.version == "0.1.0"
        assert validated.environment == AppEnvironment.TEST.value

    def test_cors_allowed_origin(self, client: TestClient) -> None:
        """TEST 3: Configured frontend origin receives correct CORS headers."""
        origin = "http://localhost:3000"
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_cors_disallowed_origin(self, client: TestClient) -> None:
        """TEST 4: Disallowed origin does not receive Access-Control-Allow-Origin."""
        unauthorized_origin = "http://unauthorized-malicious-site.example.com"
        response = client.get("/health", headers={"Origin": unauthorized_origin})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_cors_preflight_request(self, client: TestClient) -> None:
        """TEST 5: CORS OPTIONS preflight request succeeds for allowed origin."""
        origin = "http://localhost:5173"
        response = client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert "GET" in response.headers.get("access-control-allow-methods", "")

    def test_configuration_integration(self) -> None:
        """TEST 6: Application respects overridden environment settings."""
        prod_settings = get_test_settings(
            ENVIRONMENT=AppEnvironment.PRODUCTION,
            DEBUG=False,
            CORS_ORIGINS=["https://fireintel.example.com"],
        )
        app = create_app(settings=prod_settings)
        app.dependency_overrides[get_app_settings] = lambda: prod_settings
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["environment"] == "production"

        cors_resp = client.get(
            "/health", headers={"Origin": "https://fireintel.example.com"}
        )
        expected_origin = "https://fireintel.example.com"
        assert cors_resp.headers.get("access-control-allow-origin") == expected_origin

    def test_no_secret_leakage(
        self, client: TestClient, test_app: FastAPI
    ) -> None:
        """TEST 7: No secrets exposed in health, headers, or OpenAPI schema."""
        health_resp = client.get("/health")
        body_text = health_resp.text
        assert "FIRMS_MAP_KEY" not in body_text
        assert "POSTGRES_PASSWORD" not in body_text
        assert "SECRET_KEY" not in body_text
        assert "sih_dev_password" not in body_text

        # Check OpenAPI schema
        openapi_resp = client.get("/openapi.json")
        if openapi_resp.status_code == 200:
            openapi_text = openapi_resp.text
            assert "FIRMS_MAP_KEY" not in openapi_text
            assert "POSTGRES_PASSWORD" not in openapi_text
            assert "sih_dev_password" not in openapi_text

    def test_error_handling_mappings(self) -> None:
        """TEST 8: AppError subclasses mapped to standard HTTP statuses and JSON."""
        test_router = APIRouter(prefix="/test-errors")

        @test_router.get("/validation")
        def route_validation_error() -> None:
            raise ValidationError("Invalid input provided", details={"field": "bbox"})

        @test_router.get("/not-found")
        def route_not_found_error() -> None:
            raise NotFoundError("Event not found", details={"event_id": "evt_123"})

        @test_router.get("/conflict")
        def route_conflict_error() -> None:
            raise ConflictError("Resource already exists")

        @test_router.get("/timeout")
        def route_timeout_error() -> None:
            raise ServiceTimeoutError("Upstream timeout")

        @test_router.get("/db-unavailable")
        def route_db_error() -> None:
            raise DatabaseConnectionError("Postgres unreachable")

        app = create_app(settings=get_test_settings())
        app.include_router(test_router)
        client = TestClient(app, raise_server_exceptions=False)

        # 422 for ValidationError
        r = client.get("/test-errors/validation")
        assert r.status_code == 422
        d = r.json()
        assert d["code"] == "VALIDATION_ERROR"
        assert d["message"] == "Invalid input provided"
        assert d["category"] == "validation"
        assert d["details"]["field"] == "bbox"

        # 404 for NotFoundError
        r = client.get("/test-errors/not-found")
        assert r.status_code == 404
        d = r.json()
        assert d["code"] == "RESOURCE_NOT_FOUND"

        # 409 for ConflictError
        r = client.get("/test-errors/conflict")
        assert r.status_code == 409
        d = r.json()
        assert d["code"] == "RESOURCE_CONFLICT"

        # 504 for ServiceTimeoutError
        r = client.get("/test-errors/timeout")
        assert r.status_code == 504
        d = r.json()
        assert d["code"] == "SERVICE_TIMEOUT"

        # 503 for DatabaseConnectionError
        r = client.get("/test-errors/db-unavailable")
        assert r.status_code == 503
        d = r.json()
        assert d["code"] == "DATABASE_CONNECTION_ERROR"
        assert d["retryable"] is True
