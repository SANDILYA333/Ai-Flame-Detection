"""AGNI Voice Command Interpretation API Route (Phase 2)."""

from fastapi import APIRouter, Depends, status

from packages.config.settings import Settings, get_settings
from packages.schemas.agni import AgniCommandRequest, AgniCommandResponse
from services.api.services.agni_interpreter import AgniInterpreterService

router = APIRouter(prefix="", tags=["AGNI Voice Intelligence"])


def get_agni_service(
    settings: Settings = Depends(get_settings),
) -> AgniInterpreterService:
    """Dependency provider for AgniInterpreterService."""
    return AgniInterpreterService(settings=settings)


@router.post(
    "/api/v1/agni/interpret",
    response_model=AgniCommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Interpret natural language voice command into structured AGNI action",
)
@router.post(
    "/api/agni/command",
    response_model=AgniCommandResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def interpret_voice_command(
    request: AgniCommandRequest,
    service: AgniInterpreterService = Depends(get_agni_service),
) -> AgniCommandResponse:
    """Interpret a voice command transcript using Google Gemini AI or tactical fallback.

    Accepts natural language transcripts and returns a validated structured command
    ready for safe deterministic execution by the application.
    """
    return await service.interpret_command(request)
