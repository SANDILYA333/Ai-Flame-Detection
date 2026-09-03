"""Application service for emergency responder lookup and notification simulation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import ClassVar

from packages.errors import ErrorCode, NotFoundError
from packages.geospatial.distance import haversine_distance_meters
from packages.logging import get_logger
from packages.schemas.responders import (
    EmergencyResponder,
    EventResponseRecommendation,
    NotificationAction,
    NotificationMode,
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    ResponderType,
    ResponseActivityRecord,
    ResponsePriority,
)
from services.api.services.events import EventQueryService

logger = get_logger("services.api.services.responders")

_DATA_DIR = Path("data2/industrial_infra")
_FALLBACK_DATA_DIR = Path("data/industrial_infra")


class ResponderDirectoryService:
    """Service for loading and indexing static emergency responder datasets."""

    _cached_responders: ClassVar[list[dict] | None] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def _find_data_file(cls, filename: str) -> Path | None:
        p1 = _DATA_DIR / filename
        if p1.exists():
            return p1
        p2 = _FALLBACK_DATA_DIR / filename
        if p2.exists():
            return p2
        return None

    @classmethod
    def get_all_raw_responders(cls) -> list[dict]:
        """Load and normalize raw responder records from JSON datasets."""
        with cls._lock:
            if cls._cached_responders is not None:
                return cls._cached_responders

            records: list[dict] = []
            seen_ids: set[str] = set()

            # 1. Primary dataset: emergency_responders.json
            p_primary = cls._find_data_file("emergency_responders.json")
            if p_primary:
                try:
                    with open(p_primary, encoding="utf-8") as f:
                        data = json.load(f)
                    for item in data:
                        r_id = str(item.get("id", ""))
                        if not r_id or r_id in seen_ids:
                            continue
                        seen_ids.add(r_id)

                        raw_type = str(item.get("type", "")).lower()
                        is_hazmat = bool(item.get("hazmat_ready", False))
                        foam = item.get("foam_capacity_l")
                        beds = item.get("beds")
                        tenders = item.get("tenders")
                        name_lower = item.get("name", "").lower()

                        if "hosp" in raw_type or "burn" in name_lower:
                            is_burn = "burn" in name_lower or "trauma" in name_lower
                            resp_type = (
                                ResponderType.BURN_ICU
                                if is_burn
                                else ResponderType.HOSPITAL
                            )
                            caps = []
                            if beds:
                                caps.append(f"{beds} Emergency Beds")
                            if is_hazmat:
                                caps.append("Chemical / Toxic Trauma ICU")
                            if "burn" in name_lower:
                                caps.append("Specialized Burn Unit")
                        elif "ndrf" in name_lower:
                            resp_type = ResponderType.NDRF
                            caps = [
                                "Air-droppable Disaster Response",
                                "CBRN / HAZMAT Mitigation",
                            ]
                        else:
                            is_chem = (
                                is_hazmat
                                or (foam and foam > 40000)
                                or "industrial" in name_lower
                            )
                            resp_type = (
                                ResponderType.CHEMICAL_FIRE_STATION
                                if is_chem
                                else ResponderType.FIRE_STATION
                            )
                            caps = []
                            if tenders:
                                caps.append(f"{tenders} Advanced Fire Tenders")
                            if foam:
                                caps.append(f"Chemical Foam Capacity ({foam:,} L)")
                            if is_hazmat:
                                caps.append("Industrial HAZMAT Mitigation Unit")

                        records.append({
                            "id": r_id,
                            "name": str(
                                item.get("name", "Emergency Service Facility")
                            ),
                            "type": resp_type,
                            "city": str(item.get("city", "Unknown City")),
                            "state": str(item.get("state", "India")),
                            "latitude": float(item.get("lat", 0.0)),
                            "longitude": float(item.get("lon", 0.0)),
                            "phone": str(item.get("phone", "+91-112")),
                            "capabilities": caps or ["Standard Emergency Response"],
                            "jurisdiction": (
                                f"{item.get('city', 'District')} Emergency Authority"
                            ),
                            "source": "National Emergency Responder Database",
                        })
                except Exception as e:
                    logger.warning(f"Failed to load emergency_responders.json: {e}")

            # 2. Regional Clusters dataset: emergency_services_india.json
            p_clusters = cls._find_data_file("emergency_services_india.json")
            if p_clusters:
                try:
                    with open(p_clusters, encoding="utf-8") as f:
                        clusters = json.load(f)
                    for c in clusters:
                        c_id = str(c.get("id", ""))
                        lat = float(c.get("latitude", 0.0))
                        lon = float(c.get("longitude", 0.0))
                        dist = str(c.get("district", ""))
                        state = str(c.get("state", ""))
                        cluster_name = str(c.get("cluster_name", ""))

                        # Industrial Mutual Aid Fire Station
                        fs_id = f"fs-{c_id.lower()}"
                        if fs_id not in seen_ids and c.get("fire_station_hq"):
                            seen_ids.add(fs_id)
                            records.append({
                                "id": fs_id,
                                "name": str(c.get("fire_station_hq")),
                                "type": ResponderType.CHEMICAL_FIRE_STATION,
                                "city": dist,
                                "state": state,
                                "latitude": lat,
                                "longitude": lon,
                                "phone": str(c.get("phone", "+91-112")),
                                "capabilities": [
                                    "Industrial Fire Brigade Command",
                                    str(
                                        c.get(
                                            "industrial_brigade",
                                            "Industrial Mutual Aid Scheme",
                                        )
                                    ),
                                ],
                                "jurisdiction": f"{cluster_name} Regional Command",
                                "source": (
                                    "State Industrial Emergency Coordination Registry"
                                ),
                            })

                        # Apex Burn Hospital
                        hosp_id = f"hosp-{c_id.lower()}"
                        if hosp_id not in seen_ids and c.get(
                            "nearest_apex_burn_hospital"
                        ):
                            seen_ids.add(hosp_id)
                            records.append({
                                "id": hosp_id,
                                "name": str(c.get("nearest_apex_burn_hospital")),
                                "type": ResponderType.BURN_ICU,
                                "city": dist,
                                "state": state,
                                "latitude": lat + 0.015,
                                "longitude": lon + 0.015,
                                "phone": str(
                                    c.get("hospital_phone", "+91-112")
                                ),
                                "capabilities": [
                                    "Apex Burn Trauma Center",
                                    "Industrial Toxicology & Burn Ward",
                                ],
                                "jurisdiction": f"{dist} Apex Medical Jurisdiction",
                                "source": "National Trauma & Burn Registry",
                            })

                        # NDRF Battalion
                        ndrf_id = f"ndrf-{c_id.lower()}"
                        if ndrf_id not in seen_ids and c.get("ndrf_battalion"):
                            seen_ids.add(ndrf_id)
                            records.append({
                                "id": ndrf_id,
                                "name": str(c.get("ndrf_battalion")),
                                "type": ResponderType.NDRF,
                                "city": dist,
                                "state": state,
                                "latitude": lat + 0.05,
                                "longitude": lon + 0.05,
                                "phone": "+91-11-24363260",
                                "capabilities": [
                                    "Specialized Industrial Disaster Response",
                                    "CBRN Battalion Support",
                                ],
                                "jurisdiction": (
                                    "National Disaster Response Force (NDRF)"
                                ),
                                "source": "NDRF National Command Directory",
                            })
                except Exception as e:
                    logger.warning(
                        f"Failed to load emergency_services_india.json: {e}"
                    )

            cls._cached_responders = records
            return cls._cached_responders


class ResponseRecommendationService:
    """Service calculating geodesic proximity and deterministic policy."""

    @classmethod
    def get_recommendations_for_event(
        cls, event_id: str
    ) -> EventResponseRecommendation:
        """Derive prioritized responder recommendations for a given event."""
        dataset = EventQueryService.get_canonical_enriched_dataset()
        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )

        if target_event is None:
            raise NotFoundError(
                message=f"Thermal event '{event_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 1. Resolve event metadata, classification & uncertainty
        label = next(
            (lbl for lbl in dataset.reference_labels if lbl.entity_id == event_id),
            None,
        )
        classification = label.assigned_class if label else "UNKNOWN"

        source = next(
            (s for s in dataset.persistent_sources if event_id in s.linked_event_ids),
            None,
        )
        is_persistent = (
            source is not None
            and source.persistence_state.value in ["PERSISTENT", "RECURRING"]
        )

        ev_lat = target_event.centroid_geometry.latitude
        ev_lon = target_event.centroid_geometry.longitude
        max_frp = target_event.max_frp_mw

        # 2. Evaluate Deterministic Operational Response Policy
        is_abstained_or_unknown = (
            classification == "UNKNOWN"
            or (
                label is not None
                and getattr(label, "label_tier", None)
                and label.label_tier.value == "TIER_C"
            )
        )

        is_routine_flare = (
            is_persistent
            and classification == "INDUSTRIAL"
            and any(
                "flare" in (ce.facility_name or "").lower()
                or "flare" in (ce.infrastructure_type or "").lower()
                for ce in dataset.context_evidence
                if haversine_distance_meters(
                    ev_lat, ev_lon, ce.geometry.latitude, ce.geometry.longitude
                )
                <= 1500
            )
        )

        recommendation_basis: list[str] = []

        if is_abstained_or_unknown:
            response_priority = ResponsePriority.REVIEW_REQUIRED
            priority_reason = (
                "Analyst review required prior to emergency resource mobilization. "
                "Event classification is uncertain or abstained by scientific policy."
            )
            recommendation_basis.append(
                "Scientific model abstention / low evidence completeness"
            )
            recommendation_basis.append(
                "Analyst ground validation mandatory before resource alerting"
            )
        elif is_routine_flare:
            response_priority = ResponsePriority.MONITOR_ONLY
            priority_reason = (
                "Routine operational flaring source detected. Continuous emission "
                "consistent with standard operations. Monitoring recommended; "
                "emergency mobilization not indicated."
            )
            recommendation_basis.append(
                "Persistent longitudinal thermal recurrence profile"
            )
            recommendation_basis.append(
                "Industrial flaring facility association within perimeter"
            )
            recommendation_basis.append(
                "No sudden thermal escalation or hazardous spread detected"
            )
        elif classification == "INDUSTRIAL":
            if max_frp > 50.0:
                response_priority = ResponsePriority.CRITICAL
                priority_reason = (
                    f"High-intensity industrial thermal anomaly ({max_frp:.1f} MW) "
                    "with proximate infrastructure. Multi-agency response recommended."
                )
                recommendation_basis.append(
                    "High radiative thermal power (>50 MW FRP)"
                )
            else:
                response_priority = ResponsePriority.HIGH
                priority_reason = (
                    "Industrial thermal anomaly within infrastructure perimeter. "
                    "Chemical fire brigade and burn trauma readiness recommended."
                )
            recommendation_basis.append(
                "Industrial infrastructure proximity verified"
            )
            recommendation_basis.append(
                "Chemical / hazardous material response capability match"
            )
        else:
            response_priority = ResponsePriority.MEDIUM
            priority_reason = (
                "Non-industrial thermal signature. Standard fire management "
                "resources within operational range."
            )
            recommendation_basis.append(
                "Non-industrial / biomass classification profile"
            )
            recommendation_basis.append(
                "Geodesic perimeter proximity matching"
            )

        # 3. Calculate Geodesic Distance & Modeled ETA for All Responders
        raw_responders = ResponderDirectoryService.get_all_raw_responders()
        evaluated_responders: list[EmergencyResponder] = []

        for r in raw_responders:
            r_lat = r["latitude"]
            r_lon = r["longitude"]
            dist_meters = haversine_distance_meters(ev_lat, ev_lon, r_lat, r_lon)
            dist_km = dist_meters / 1000.0

            # Formatted distance
            if dist_meters < 1000:
                fmt_dist = f"{round(dist_meters)} m"
            else:
                fmt_dist = (
                    f"{dist_km:.1f} km"
                    if dist_km < 10
                    else f"{round(dist_km)} km"
                )

            # Modeled ETA: ~45 km/h emergency speed + 2 min staging
            eta_mins = max(1, round((dist_km / 45.0) * 60.0 + 2.0))
            fmt_eta = f"~{eta_mins} min"

            # Explainable recommendation rationale per responder type
            r_type = r["type"]
            if r_type in [
                ResponderType.CHEMICAL_FIRE_STATION,
                ResponderType.FIRE_STATION,
            ]:
                if dist_km < 30.0 and classification == "INDUSTRIAL":
                    reason = (
                        "Primary chemical & industrial fire response unit "
                        "proximate to infrastructure perimeter"
                    )
                else:
                    reason = (
                        "Nearest municipal fire safety command within "
                        "operational response radius"
                    )
            elif r_type in [ResponderType.BURN_ICU, ResponderType.HOSPITAL]:
                if r_type == ResponderType.BURN_ICU:
                    reason = (
                        "Apex burn trauma ICU and toxic exposure treatment center "
                        "within operational corridor"
                    )
                else:
                    reason = (
                        "Regional emergency medical facility with casualty admission"
                    )
            elif r_type == ResponderType.NDRF:
                reason = (
                    "Regional NDRF battalion equipped for specialized industrial "
                    "disaster & CBRN mitigation"
                )
            else:
                reason = "Regional disaster management support resource"

            evaluated_responders.append(
                EmergencyResponder(
                    id=r["id"],
                    name=r["name"],
                    type=r_type,
                    city=r["city"],
                    state=r["state"],
                    latitude=r_lat,
                    longitude=r_lon,
                    distance_meters=round(dist_meters, 1),
                    formatted_distance=fmt_dist,
                    estimated_eta_minutes=eta_mins,
                    formatted_eta=fmt_eta,
                    capabilities=r["capabilities"],
                    phone=r["phone"],
                    jurisdiction=r["jurisdiction"],
                    source=r["source"],
                    recommendation_reason=reason,
                    plume_impact_status="UNAVAILABLE",
                )
            )

        # 4. Deterministic Ranking: Type Relevance Priority (Fire -> Med -> NDRF)
        def type_rank(t: ResponderType) -> int:
            if t in [
                ResponderType.CHEMICAL_FIRE_STATION,
                ResponderType.FIRE_STATION,
            ]:
                return 0
            if t in [ResponderType.BURN_ICU, ResponderType.HOSPITAL]:
                return 1
            if t == ResponderType.NDRF:
                return 2
            return 3

        evaluated_responders.sort(key=lambda r: (type_rank(r.type), r.distance_meters))

        top_fire = [
            r
            for r in evaluated_responders
            if r.type
            in [
                ResponderType.CHEMICAL_FIRE_STATION,
                ResponderType.FIRE_STATION,
            ]
        ][:2]
        top_med = [
            r
            for r in evaluated_responders
            if r.type in [ResponderType.BURN_ICU, ResponderType.HOSPITAL]
        ][:2]
        top_ndrf = [
            r for r in evaluated_responders if r.type == ResponderType.NDRF
        ][:1]

        final_responders = top_fire + top_med + top_ndrf

        return EventResponseRecommendation(
            event_id=event_id,
            response_priority=response_priority,
            priority_reason=priority_reason,
            is_routine_flare=is_routine_flare,
            is_abstained_or_unknown=is_abstained_or_unknown,
            responders=final_responders,
            recommendation_basis=recommendation_basis,
            evaluated_at=datetime.now(UTC),
        )


class NotificationAuditService:
    """Thread-safe service for analyst-confirmed emergency notifications."""

    _activity_log: ClassVar[list[ResponseActivityRecord]] = []
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def process_notification(
        cls,
        event_id: str,
        request: NotificationRequest,
    ) -> NotificationResponse:
        """Process and simulate an analyst-confirmed notification request."""
        # 1. Validate Target Event Exists
        dataset = EventQueryService.get_canonical_enriched_dataset()
        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )
        if target_event is None:
            raise NotFoundError(
                message=f"Cannot dispatch: Thermal event '{event_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 2. Validate Responder Exists
        all_raw = ResponderDirectoryService.get_all_raw_responders()
        target_responder = next(
            (r for r in all_raw if r["id"] == request.responder_id), None
        )
        if target_responder is None:
            raise NotFoundError(
                message=(
                    f"Cannot dispatch: Responder '{request.responder_id}' not found."
                ),
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 3. Create Simulation Notification Record
        now = datetime.now(UTC)
        ts_str = now.strftime("%Y%m%d-%H%M%S")
        notification_id = f"NOTIF-{event_id}-{request.responder_id}-{ts_str}"

        responder_name = target_responder["name"]
        resp_type = target_responder["type"]
        action_verb = (
            "Mobilization request"
            if request.action == NotificationAction.MOBILIZE
            else "Emergency response alert"
        )

        # 4. Log in Audit Trail
        record = ResponseActivityRecord(
            notification_id=notification_id,
            event_id=event_id,
            responder_id=request.responder_id,
            responder_name=responder_name,
            responder_type=resp_type,
            action=request.action,
            status=NotificationStatus.SIMULATED,
            mode=NotificationMode.SIMULATED,
            timestamp=now,
            analyst_notes=request.analyst_notes,
        )

        with cls._lock:
            cls._activity_log.append(record)

        logger.info(
            f"Analyst-confirmed notification simulated: Event={event_id}, "
            f"Recipient={responder_name}, Action={request.action.value}"
        )

        return NotificationResponse(
            notification_id=notification_id,
            event_id=event_id,
            responder_id=request.responder_id,
            responder_name=responder_name,
            action=request.action,
            status=NotificationStatus.SIMULATED,
            mode=NotificationMode.SIMULATED,
            timestamp=now,
            message=(
                f"{action_verb} simulated successfully for {responder_name}. "
                "Safe demo record logged."
            ),
        )

    @classmethod
    def get_activity_for_event(cls, event_id: str) -> list[ResponseActivityRecord]:
        """Retrieve historical response audit records for a given event."""
        with cls._lock:
            records = [r for r in cls._activity_log if r.event_id == event_id]
            records.sort(key=lambda r: r.timestamp, reverse=True)
            return records

    @classmethod
    def clear_activity_log(cls) -> None:
        """Clear audit history (used for test isolation)."""
        with cls._lock:
            cls._activity_log.clear()
