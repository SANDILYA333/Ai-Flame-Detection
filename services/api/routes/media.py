"""FastAPI routes for Contextual External Intelligence, News, and Media (API-007)."""

from fastapi import APIRouter

from services.api.schemas.media import ContextualMediaResponse
from services.api.services.media import ContextualMediaService

router = APIRouter(tags=["external-intelligence"])


@router.get(
    "/events/{event_id}/media",
    response_model=ContextualMediaResponse,
    operation_id="get_event_contextual_media",
    summary="Retrieve contextual news and video media for an event",
    description=(
        "Returns backend-mediated and relevance-ranked external news articles "
        "and tactical video briefings matching the incident's geographic and "
        "facility context."
    ),
)
@router.get(
    "/events/{event_id}/external-intelligence",
    response_model=ContextualMediaResponse,
    operation_id="get_event_external_intelligence_alias",
    summary="Alias for contextual external intelligence",
    include_in_schema=False,
)
def get_event_media(event_id: str) -> ContextualMediaResponse:
    """Retrieve contextual news and media intelligence for an event."""
    return ContextualMediaService.get_event_media(event_id)
