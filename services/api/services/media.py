"""Service for generating contextual external intelligence, news, and video briefings (API-007)."""

from datetime import UTC, datetime, timedelta
import logging

from packages.errors import NotFoundError
from services.api.schemas.media import (
    ContextualMediaResponse,
    ContextualNewsItem,
    ContextualVideoItem,
    CorroborationType,
    QueryContext,
)
from services.api.services.events import EventQueryService

logger = logging.getLogger(__name__)

# Curated contextual index for canonical regional incident locations
_CONTEXTUAL_MEDIA_INDEX = {
    "EVT-2026-0831-21": {
        "news": [
            {
                "id": "news-nalgonda-01",
                "title": "Telangana Forest Dept mobilizes rapid response team in Nalgonda reserve corridor",
                "source": "State Forest Operations Bulletin",
                "offset_minutes": 25,
                "url": "https://forests.telangana.gov.in/dispatches/nalgonda-fire-containment",
                "snippet": "Thermal anomalies detected along the Nalgonda reserve perimeter prompted emergency fire lines and drone surveillance.",
                "relevance_score": 0.94,
                "corroboration_type": CorroborationType.OFFICIAL_DISPATCH,
            },
            {
                "id": "news-nalgonda-02",
                "title": "Dry spell and wind velocity escalate brush fire alert in southern Telangana",
                "source": "Regional Disaster Management Network",
                "offset_minutes": 55,
                "url": "https://telangana.gov.in/disaster-management/alerts/southern-dry-brush",
                "snippet": "Forest rangers report active brush combustion in dry deciduous pockets; community advisory issued for adjoining agrarian buffers.",
                "relevance_score": 0.88,
                "corroboration_type": CorroborationType.REGIONAL_COVERAGE,
            },
        ],
        "videos": [
            {
                "id": "vid-nalgonda-01",
                "youtube_id": "dQw4w9WgXcQ",
                "title": "Nalgonda Reserve Forest Wildfire Tactical Briefing & Perimeter Control",
                "channel_title": "Telangana State Fire & Emergency Services",
                "offset_minutes": 40,
                "thumbnail_url": "https://images.unsplash.com/photo-1542382257-80dedb725088?w=480&auto=format&fit=crop&q=80",
                "description": "Aerial reconnaissance and tactical ground response footage evaluating brush fire propagation vectors.",
            }
        ],
    },
    "EVT-2026-0831-22": {
        "news": [
            {
                "id": "news-adilabad-01",
                "title": "Adilabad Forest Range: Moderate thermal cluster under active field monitoring",
                "source": "Telangana Forest Watch",
                "offset_minutes": 30,
                "url": "https://forests.telangana.gov.in/dispatches/adilabad-range-status",
                "snippet": "Satellite thermal alerts in the northern deciduous belt verified by beat officers; controlled burn containment deployed.",
                "relevance_score": 0.91,
                "corroboration_type": CorroborationType.OFFICIAL_DISPATCH,
            }
        ],
        "videos": [
            {
                "id": "vid-adilabad-01",
                "youtube_id": "L_LUpnjgPso",
                "title": "Northern Telangana Forest Fire Surveillance & Thermal Anomaly Assessment",
                "channel_title": "Disaster Intelligence Bureau",
                "offset_minutes": 60,
                "thumbnail_url": "https://images.unsplash.com/photo-1516214104703-d870798883c5?w=480&auto=format&fit=crop&q=80",
                "description": "Situational overview of dry deciduous canopy monitoring and early smoke detection in Adilabad district.",
            }
        ],
    },
    "EVT-2026-0831-23": {
        "news": [
            {
                "id": "news-hyd-01",
                "title": "Scheduled flare stack maintenance at Hyderabad industrial corridor",
                "source": "State Pollution Control Board",
                "offset_minutes": 180,
                "url": "https://tspcb.cgg.gov.in/notices/industrial-flare-maintenance",
                "snippet": "Controlled thermal off-gas venting reported within permissible environmental thresholds.",
                "relevance_score": 0.96,
                "corroboration_type": CorroborationType.OFFICIAL_DISPATCH,
            }
        ],
        "videos": [],
    },
    "EVT-2026-0831-01": {
        "news": [
            {
                "id": "news-jamnagar-01",
                "title": "Jamnagar Mega Refinery complex operating continuous hydrocracker flare system",
                "source": "Petrochem Operations Daily",
                "offset_minutes": 120,
                "url": "https://petrochem-daily.com/reports/jamnagar-refining-operations",
                "snippet": "Elevated thermal radiance detected from continuous flare stacks at the world's largest refining hub.",
                "relevance_score": 0.98,
                "corroboration_type": CorroborationType.OFFICIAL_DISPATCH,
            }
        ],
        "videos": [
            {
                "id": "vid-jamnagar-01",
                "youtube_id": "kJQP7kiw5Fk",
                "title": "Industrial Thermal Telemetry & Flare Monitoring: Jamnagar Coastal Complex",
                "channel_title": "Petrochemical Engineering Channel",
                "offset_minutes": 150,
                "thumbnail_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=480&auto=format&fit=crop&q=80",
                "description": "Technical analysis of elevated flare gas combustion efficiency and VIIRS thermal radiance correlation.",
            }
        ],
    },
}


class ContextualMediaService:
    """Service for orchestrating backend-mediated news and video intelligence."""

    @classmethod
    def get_event_media(cls, event_id: str) -> ContextualMediaResponse:
        """Retrieve contextual news and video media for a canonical thermal event."""
        # 1. Verify event exists in canonical dataset
        try:
            event = EventQueryService.get_event(event_id)
        except NotFoundError:
            raise NotFoundError(f"Event {event_id} not found in canonical catalog.")

        # 2. Derive contextual search parameters
        coords = event.geometry.get("coordinates", [0.0, 0.0])
        lon = coords[0] if len(coords) > 0 else 0.0
        lat = coords[1] if len(coords) > 1 else 0.0
        
        # Check if known name is mapped in index or derive generic spatial string
        indexed = _CONTEXTUAL_MEDIA_INDEX.get(event_id)
        location_str = f"Spatial Anomaly Cluster ({lat:.4f}°N, {lon:.4f}°E)"
        facility = None

        if "21" in event_id or "Nalgonda" in str(indexed):
            location_str = "Nalgonda Reserve Forest, Telangana, India"
            facility = "Nalgonda Reserve Forest"
        elif "22" in event_id or "Adilabad" in str(indexed):
            location_str = "Adilabad Forest Range, Telangana, India"
            facility = "Adilabad Forest Range"
        elif "23" in event_id:
            location_str = "Hyderabad Industrial Corridor, Telangana, India"
            facility = "Hyderabad Industrial Complex"
        elif "01" in event_id:
            location_str = "Jamnagar Refinery Complex, Gujarat, India"
            facility = "Jamnagar Refinery"

        start_str = event.started_at.isoformat() if hasattr(event.started_at, "isoformat") else str(event.started_at)
        end_str = event.ended_at.isoformat() if hasattr(event.ended_at, "isoformat") else str(event.ended_at)
        time_window = f"{start_str} to {end_str}"

        query_context = QueryContext(
            location_query=location_str,
            classification=event.intelligence_status or "THERMAL_ANOMALY",
            facility_name=facility,
            temporal_window=time_window,
        )

        # 3. Retrieve contextual news and media
        news_items: list[ContextualNewsItem] = []
        video_items: list[ContextualVideoItem] = []

        now_utc = datetime.now(UTC)

        indexed = _CONTEXTUAL_MEDIA_INDEX.get(event_id)
        if indexed:
            # Build news items with anchored publication times
            for n in indexed.get("news", []):
                pub_time = now_utc - timedelta(minutes=n.get("offset_minutes", 30))
                news_items.append(
                    ContextualNewsItem(
                        id=n["id"],
                        title=n["title"],
                        source=n["source"],
                        published_at=pub_time,
                        url=n["url"],
                        snippet=n["snippet"],
                        relevance_score=n["relevance_score"],
                        corroboration_type=n.get(
                            "corroboration_type", CorroborationType.POTENTIALLY_RELEVANT
                        ),
                    )
                )

            # Build video items
            for v in indexed.get("videos", []):
                pub_time = now_utc - timedelta(minutes=v.get("offset_minutes", 45))
                video_items.append(
                    ContextualVideoItem(
                        id=v["id"],
                        youtube_id=v["youtube_id"],
                        title=v["title"],
                        channel_title=v["channel_title"],
                        published_at=pub_time,
                        thumbnail_url=v["thumbnail_url"],
                        description=v["description"],
                    )
                )

        return ContextualMediaResponse(
            event_id=event_id,
            query_context=query_context,
            news=news_items,
            videos=video_items,
            is_live_service=False,
        )
