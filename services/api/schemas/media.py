"""Schemas for Contextual External Intelligence, News, and Media (API-007)."""

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class CorroborationType(StrEnum):
    """External news corroboration confidence level."""

    OFFICIAL_DISPATCH = "OFFICIAL_DISPATCH"
    REGIONAL_COVERAGE = "REGIONAL_COVERAGE"
    POTENTIALLY_RELEVANT = "POTENTIALLY_RELEVANT"
    UNVERIFIED = "UNVERIFIED"


class ContextualNewsItem(BaseModel):
    """Normalized external news report matching incident context."""

    id: str = Field(description="Unique identifier for news record")
    title: str = Field(description="Headline / Article title")
    source: str = Field(description="Publishing organization / domain name")
    published_at: datetime = Field(description="Publication timestamp (UTC)")
    url: str = Field(description="Original article URL")
    snippet: str = Field(description="Relevant contextual excerpt")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Calibrated contextual relevance score"
    )
    corroboration_type: CorroborationType = Field(
        default=CorroborationType.POTENTIALLY_RELEVANT,
        description="Scientific corroboration classification",
    )


class ContextualVideoItem(BaseModel):
    """Tactical briefing or situational YouTube video."""

    id: str = Field(description="Unique identifier for video record")
    youtube_id: str = Field(description="YouTube alphanumeric Video ID")
    title: str = Field(description="Video briefing title")
    channel_title: str = Field(description="Author / Channel name")
    published_at: datetime = Field(description="Publication timestamp (UTC)")
    thumbnail_url: str = Field(description="Thumbnail image URL")
    description: str = Field(description="Contextual briefing synopsis")


class QueryContext(BaseModel):
    """Derived contextual search parameters used for external retrieval."""

    location_query: str = Field(description="Normalized location string")
    classification: str = Field(description="Event classification")
    facility_name: str | None = Field(default=None, description="Industrial/forest facility")
    temporal_window: str = Field(description="Event observation time window")


class ContextualMediaResponse(BaseModel):
    """Complete external intelligence package for an event."""

    event_id: str = Field(description="Canonical event identifier")
    query_context: QueryContext = Field(description="Search parameters derived from event")
    news: list[ContextualNewsItem] = Field(
        default_factory=list, description="Relevant external news items"
    )
    videos: list[ContextualVideoItem] = Field(
        default_factory=list, description="Tactical video briefings"
    )
    disclaimer: str = Field(
        default=(
            "External news and media are retrieved via contextual indexing and are "
            "supplementary to PyroSat-AI canonical satellite telemetry."
        ),
        description="Standard scientific intelligence disclaimer",
    )
    is_live_service: bool = Field(
        default=False, description="Whether live search providers were contacted"
    )
