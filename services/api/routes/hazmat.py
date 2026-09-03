"""FastAPI route for CAMEO-NIOSH HAZMAT chemical risk profiles (HAZMAT-001)."""

from fastapi import APIRouter

from services.api.services.dossier import TacticalDossierService

router = APIRouter(tags=["hazmat"])


@router.get(
    "/api/hazmat-profiles",
    operation_id="get_hazmat_profiles",
    summary="Retrieve CAMEO-NIOSH industrial hazardous chemical profiles",
    description=(
        "Returns registry of industrial chemicals, UN numbers, IDLH limits, "
        "and isolation guidelines."
    ),
)
def get_hazmat_profiles() -> dict:
    """Retrieve CAMEO-NIOSH industrial hazardous chemical profiles."""
    return TacticalDossierService.get_hazmat_profiles()
