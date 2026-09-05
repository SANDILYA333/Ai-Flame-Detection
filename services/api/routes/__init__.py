"""API route handlers and router registration."""

from fastapi import APIRouter

from services.api.routes.agni import router as agni_router
from services.api.routes.detections import router as detections_router
from services.api.routes.dispersion import router as dispersion_router
from services.api.routes.dossier import router as dossier_router
from services.api.routes.events import router as events_router
from services.api.routes.forests import router as forests_router
from services.api.routes.gis_layers import router as gis_layers_router
from services.api.routes.hazmat import router as hazmat_router
from services.api.routes.health import router as health_router
from services.api.routes.historical import router as historical_router
from services.api.routes.industrial import router as industrial_router
from services.api.routes.inference import router as inference_router
from services.api.routes.layers import router as layers_router
from services.api.routes.media import router as media_router
from services.api.routes.readiness import router as readiness_router
from services.api.routes.responders import router as responders_router
from services.api.routes.simulation import router as simulation_router
from services.api.routes.sources import router as sources_router
from services.api.routes.version import router as version_router
from services.api.routes.weather import router as weather_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(readiness_router)
api_router.include_router(version_router)
api_router.include_router(sources_router)
api_router.include_router(detections_router)
api_router.include_router(events_router)
api_router.include_router(media_router)
api_router.include_router(layers_router)
api_router.include_router(inference_router)
api_router.include_router(responders_router)
api_router.include_router(dossier_router)
api_router.include_router(simulation_router)
api_router.include_router(historical_router)
api_router.include_router(industrial_router)
api_router.include_router(hazmat_router)
api_router.include_router(gis_layers_router)
api_router.include_router(forests_router)
api_router.include_router(weather_router)
api_router.include_router(dispersion_router)
api_router.include_router(agni_router)

__all__ = [
    "agni_router",
    "api_router",
    "detections_router",
    "dispersion_router",
    "dossier_router",
    "events_router",
    "forests_router",
    "gis_layers_router",
    "hazmat_router",
    "health_router",
    "historical_router",
    "industrial_router",
    "inference_router",
    "layers_router",
    "media_router",
    "readiness_router",
    "responders_router",
    "simulation_router",
    "sources_router",
    "version_router",
    "weather_router",
]
