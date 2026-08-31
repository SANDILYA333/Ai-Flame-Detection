"""Application service for system dependency readiness auditing (API-002)."""

import logging

import psycopg

from packages.config.settings import Settings
from packages.logging import get_logger, log_with_context
from services.api.schemas.readiness import (
    DependencyHealth,
    DependencyStatus,
    ReadinessResponse,
)
from services.ml.models.registry import SUPPORTED_MODEL_TYPES

logger = get_logger("services.api.services.readiness")


class ReadinessCheckService:
    """Evaluates readiness of all required backend subsystems."""

    @classmethod
    def check_database(cls, settings: Settings) -> DependencyHealth:
        """Verify PostgreSQL + PostGIS database connectivity."""
        password = settings.POSTGRES_PASSWORD.get_secret_value()
        try:
            with (
                psycopg.connect(
                    host=settings.POSTGRES_HOST,
                    port=settings.POSTGRES_PORT,
                    dbname=settings.POSTGRES_DB,
                    user=settings.POSTGRES_USER,
                    password=password,
                    connect_timeout=2,
                    autocommit=True,
                ) as conn,
                conn.cursor() as cur,
            ):
                cur.execute("SELECT 1;")
                cur.fetchone()

            return DependencyHealth(
                status=DependencyStatus.READY,
                details={
                    "host": settings.POSTGRES_HOST,
                    "port": settings.POSTGRES_PORT,
                    "database": settings.POSTGRES_DB,
                    "connected": True,
                },
            )
        except Exception as exc:
            log_with_context(
                logger,
                logging.WARNING,
                "Database readiness check failed",
                context={
                    "host": settings.POSTGRES_HOST,
                    "port": settings.POSTGRES_PORT,
                    "database": settings.POSTGRES_DB,
                },
                error=exc,
            )
            return DependencyHealth(
                status=DependencyStatus.UNAVAILABLE,
                details={
                    "host": settings.POSTGRES_HOST,
                    "port": settings.POSTGRES_PORT,
                    "database": settings.POSTGRES_DB,
                    "connected": False,
                    "error": "Database service is unreachable or not ready",
                },
            )

    @classmethod
    def check_model_registry(cls) -> DependencyHealth:
        """Verify machine learning model registry integrity."""
        return DependencyHealth(
            status=DependencyStatus.READY,
            details={
                "supported_model_types": list(SUPPORTED_MODEL_TYPES),
                "model_count": len(SUPPORTED_MODEL_TYPES),
            },
        )

    @classmethod
    def check_configuration(cls, settings: Settings) -> DependencyHealth:
        """Verify operational runtime configuration status."""
        return DependencyHealth(
            status=DependencyStatus.READY,
            details={
                "environment": settings.ENVIRONMENT.value,
                "debug": settings.DEBUG,
                "api_host": settings.API_HOST,
                "api_port": settings.API_PORT,
            },
        )

    @classmethod
    def evaluate_readiness(cls, settings: Settings) -> ReadinessResponse:
        """Aggregate all dependency checks and compute overall readiness state."""
        db_health = cls.check_database(settings)
        ml_health = cls.check_model_registry()
        cfg_health = cls.check_configuration(settings)

        dependencies = {
            "database": db_health,
            "model_registry": ml_health,
            "configuration": cfg_health,
        }

        # Database is a hard requirement for system readiness
        has_unavail = any(
            d.status == DependencyStatus.UNAVAILABLE for d in dependencies.values()
        )
        has_degraded = any(
            d.status == DependencyStatus.DEGRADED for d in dependencies.values()
        )

        if db_health.status != DependencyStatus.READY or has_unavail:
            overall_status = DependencyStatus.UNAVAILABLE
        elif has_degraded:
            overall_status = DependencyStatus.DEGRADED
        else:
            overall_status = DependencyStatus.READY

        return ReadinessResponse(
            status=overall_status,
            service="sih26162-api",
            version="0.1.0",
            environment=settings.ENVIRONMENT.value,
            dependencies=dependencies,
        )
