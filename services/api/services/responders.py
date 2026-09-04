"""Application service for emergency responder lookup and notification simulation."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import ClassVar

from packages.errors import ErrorCode, NotFoundError
from packages.geospatial.coordinates import calculate_geodesic_bearing
from packages.geospatial.distance import haversine_distance_meters
from packages.logging import get_logger
from packages.schemas.responders import (
    ChannelDeliveryStatus,
    ChannelResult,
    EmergencyResponder,
    EscalationDecision,
    EscalationState,
    EscalationType,
    EventResponseRecommendation,
    NotificationAction,
    NotificationChannel,
    NotificationMode,
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    ResponderType,
    ResponseActivityRecord,
    ResponsePriority,
)
from services.api.services.escalation import EscalationPolicyService
from services.api.services.events import EventQueryService
from services.api.services.notifications import NotificationService
from services.api.services.providers.fast2sms import mask_phone_number

logger = get_logger("services.api.services.responders")

_DATA_DIR = Path("data2/industrial_infra")
_FALLBACK_DATA_DIR = Path("data/industrial_infra")


class ResponderDirectoryService:
    """Service for loading and indexing static emergency responder datasets."""

    _cached_responders: ClassVar[list[dict] | None] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached responder records for testing or reloading."""
        with cls._lock:
            cls._cached_responders = None

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

                        records.append(
                            {
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
                            }
                        )
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
                            records.append(
                                {
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
                                }
                            )

                        # Apex Burn Hospital
                        hosp_id = f"hosp-{c_id.lower()}"
                        if hosp_id not in seen_ids and c.get(
                            "nearest_apex_burn_hospital"
                        ):
                            seen_ids.add(hosp_id)
                            records.append(
                                {
                                    "id": hosp_id,
                                    "name": str(c.get("nearest_apex_burn_hospital")),
                                    "type": ResponderType.BURN_ICU,
                                    "city": dist,
                                    "state": state,
                                    "latitude": lat + 0.015,
                                    "longitude": lon + 0.015,
                                    "phone": str(c.get("hospital_phone", "+91-112")),
                                    "capabilities": [
                                        "Apex Burn Trauma Center",
                                        "Industrial Toxicology & Burn Ward",
                                    ],
                                    "jurisdiction": f"{dist} Apex Medical Jurisdiction",
                                    "source": "National Trauma & Burn Registry",
                                }
                            )

                        # NDRF Battalion
                        ndrf_id = f"ndrf-{c_id.lower()}"
                        if ndrf_id not in seen_ids and c.get("ndrf_battalion"):
                            seen_ids.add(ndrf_id)
                            records.append(
                                {
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
                                }
                            )
                except Exception as e:
                    logger.warning(f"Failed to load emergency_services_india.json: {e}")

            cls._cached_responders = records
            return cls._cached_responders


class ResponseRecommendationService:
    """Service calculating geodesic proximity, deterministic policy, and escalation state."""

    @classmethod
    def get_recommendations_for_event(
        cls,
        event_id: str,
        demo_phone: str | None = None,
    ) -> EventResponseRecommendation:
        """Derive prioritized responder recommendations and evaluate escalation for a given event."""
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
        classification = "UNKNOWN"
        if label and label.assigned_class:
            classification = label.assigned_class.strip().upper()
        elif getattr(target_event, "classification_state", None):
            classification = str(target_event.classification_state).strip().upper()
        else:
            try:
                intel = EventQueryService.get_event_intelligence(event_id)
                if intel.classification and intel.classification.assigned_class:
                    classification = (
                        str(intel.classification.assigned_class).strip().upper()
                    )
            except Exception:
                pass

        source = next(
            (s for s in dataset.persistent_sources if event_id in s.linked_event_ids),
            None,
        )
        is_persistent = source is not None and source.persistence_state.value in [
            "PERSISTENT",
            "RECURRING",
        ]

        ev_lat = target_event.centroid_geometry.latitude
        ev_lon = target_event.centroid_geometry.longitude
        max_frp = target_event.max_frp_mw

        # Calculate or extract calibrated confidence score
        confidence: float = 0.85
        if label and label.confidence_score is not None:
            confidence = float(label.confidence_score)
        else:
            try:
                intel = EventQueryService.get_event_intelligence(event_id)
                if intel.uncertainty.calibrated_confidence is not None:
                    confidence = float(intel.uncertainty.calibrated_confidence)
            except Exception:
                confidence = 0.95 if classification == "INDUSTRIAL" else 0.50

        # 2. Evaluate Deterministic Operational Response Policy
        is_abstained_or_unknown = classification == "UNKNOWN" or (
            label is not None
            and getattr(label, "label_tier", None)
            and label.label_tier.value == "TIER_C"
        )

        is_routine_flare = (
            is_persistent
            and classification == "INDUSTRIAL"
            and any(
                "flare" in (ce.facility_name or "").lower()
                or "flare" in str(ce.context_type).lower()
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
                recommendation_basis.append("High radiative thermal power (>50 MW FRP)")
            else:
                response_priority = ResponsePriority.HIGH
                priority_reason = (
                    "Industrial thermal anomaly within infrastructure perimeter. "
                    "Chemical fire brigade and burn trauma readiness recommended."
                )
            recommendation_basis.append("Industrial infrastructure proximity verified")
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
            recommendation_basis.append("Geodesic perimeter proximity matching")

        # Check if event is offshore
        is_offshore = (
            (18.0 <= ev_lat <= 21.0 and 70.0 <= ev_lon <= 72.3)
            or any(
                "offshore" in (ce.facility_name or "").lower()
                or "offshore" in str(ce.context_type).lower()
                or "platform" in (ce.facility_name or "").lower()
                for ce in dataset.context_evidence
                if haversine_distance_meters(
                    ev_lat, ev_lon, ce.geometry.latitude, ce.geometry.longitude
                )
                <= 15000.0
            )
        )

        if is_offshore:
            recommendation_basis.append(
                "Offshore marine event location — coastal command staging & air evacuation corridor applied"
            )

        # Check Atmospheric Dispersion & Downwind Hazard Corridor
        dispersion_res = None
        try:
            from packages.data.weather.dispersion_service import get_dispersion_service
            disp_svc = get_dispersion_service()
            dispersion_res = disp_svc.evaluate_event_dispersion(
                event_id=event_id,
                latitude=ev_lat,
                longitude=ev_lon,
                frp_mw=max_frp,
            )
        except Exception as e:
            logger.debug(f"Dispersion calculation skipped/unavailable for event {event_id}: {e}")

        if dispersion_res is not None:
            w = dispersion_res.wind
            disp = dispersion_res.dispersion
            recommendation_basis.append(
                f"Wind & Atmospheric Dispersion: {w.speed_ms:.1f} m/s from {w.direction_from_label} ({w.direction_from_deg:.0f}°) -> Downwind {w.downwind_direction_label} ({disp.plume_angle_deg:.0f}°), Hazard Reach: {disp.max_hazard_distance_km:.1f} km (Stability Class {disp.stability_class.value})"
            )

        # 3. Calculate Geodesic Distance, Modeled ETA & Plume Impact for All Responders
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
                    f"{dist_km:.1f} km" if dist_km < 10 else f"{round(dist_km)} km"
                )

            # Modeled ETA:
            if is_offshore:
                eta_mins = None
                fmt_eta = "Offshore Transit: Maritime / Heli Required (~90-120 min)"
            else:
                eta_mins = max(1, round((dist_km / 45.0) * 60.0 + 2.0))
                fmt_eta = f"~{eta_mins} min"

            # Evaluate Downwind Plume Impact Status
            plume_status = "UNAVAILABLE"
            if dispersion_res is not None:
                if dist_meters <= 200.0:
                    plume_status = "IN_ISOLATION_ZONE"
                else:
                    resp_bearing = calculate_geodesic_bearing(ev_lat, ev_lon, r_lat, r_lon)
                    downwind_bearing = dispersion_res.dispersion.plume_angle_deg
                    bearing_diff = abs((resp_bearing - downwind_bearing + 180.0) % 360.0 - 180.0)
                    max_hazard_km = dispersion_res.dispersion.max_hazard_distance_km

                    if dist_km <= max_hazard_km and bearing_diff <= 30.0:
                        plume_status = "IN_PLUME_CORRIDOR"
                    elif dist_km <= (max_hazard_km + 5.0) and bearing_diff <= 45.0:
                        plume_status = "DOWNWIND_SECTOR"
                    elif bearing_diff > 90.0:
                        plume_status = "UPWIND_CLEAR"
                    else:
                        plume_status = "CROSSWIND_CLEAR"

            # Explainable recommendation rationale per responder type
            r_type = r["type"]
            if is_offshore:
                if r_type in [
                    ResponderType.CHEMICAL_FIRE_STATION,
                    ResponderType.FIRE_STATION,
                    ResponderType.INDUSTRIAL_FIRE_SAFETY,
                    ResponderType.MUNICIPAL_FIRE_STATION,
                    ResponderType.PORT_EMERGENCY_SERVICES,
                ]:
                    reason = (
                        "Nearest coastal industrial port fire command staging base "
                        "for offshore platform maritime/air dispatch"
                    )
                elif r_type in [
                    ResponderType.BURN_ICU,
                    ResponderType.HOSPITAL,
                    ResponderType.BURN_INTENSIVE_CARE_HOSPITAL,
                ]:
                    reason = (
                        "Apex burn trauma center equipped for offshore helipad casualty air-evacuation"
                    )
                elif r_type in [
                    ResponderType.NDRF,
                    ResponderType.NDRF_DISASTER_BATTALION,
                ]:
                    reason = (
                        "Regional NDRF disaster battalion with air-droppable CBRN and coastal response capabilities"
                    )
                else:
                    reason = "Coastal disaster management support resource"
            else:
                if r_type in [
                    ResponderType.CHEMICAL_FIRE_STATION,
                    ResponderType.FIRE_STATION,
                    ResponderType.INDUSTRIAL_FIRE_SAFETY,
                    ResponderType.MUNICIPAL_FIRE_STATION,
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
                elif r_type in [
                    ResponderType.BURN_ICU,
                    ResponderType.HOSPITAL,
                    ResponderType.BURN_INTENSIVE_CARE_HOSPITAL,
                ]:
                    if r_type in [
                        ResponderType.BURN_ICU,
                        ResponderType.BURN_INTENSIVE_CARE_HOSPITAL,
                    ]:
                        reason = (
                            "Apex burn trauma ICU and toxic exposure treatment center "
                            "within operational corridor"
                        )
                    else:
                        reason = (
                            "Regional emergency medical facility with casualty admission"
                        )
                elif r_type in [
                    ResponderType.NDRF,
                    ResponderType.NDRF_DISASTER_BATTALION,
                ]:
                    reason = (
                        "Regional NDRF battalion equipped for specialized industrial "
                        "disaster & CBRN mitigation"
                    )
                elif r_type in [
                    ResponderType.SPECIALIZED_HAZMAT_UNIT,
                    ResponderType.PORT_EMERGENCY_SERVICES,
                ]:
                    reason = "Specialized industrial and hazardous materials containment unit"
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
                    plume_impact_status=plume_status,
                )
            )


        # 4. Extract Nearest 2 Hospitals, Nearest 2 Fire Stations, Specialized Responders, and NDRF
        # A. Fire Responders (Industrial prioritized for industrial events, then geodesic distance, stable tie-break)
        fire_candidates = [
            r
            for r in evaluated_responders
            if r.type
            in [
                ResponderType.CHEMICAL_FIRE_STATION,
                ResponderType.FIRE_STATION,
                ResponderType.INDUSTRIAL_FIRE_SAFETY,
                ResponderType.MUNICIPAL_FIRE_STATION,
            ]
        ]
        if classification == "INDUSTRIAL":
            fire_candidates.sort(
                key=lambda r: (
                    (
                        0
                        if r.type
                        in [
                            ResponderType.CHEMICAL_FIRE_STATION,
                            ResponderType.INDUSTRIAL_FIRE_SAFETY,
                        ]
                        else 1
                    ),
                    r.distance_meters,
                    r.id,
                )
            )
        else:
            fire_candidates.sort(key=lambda r: (r.distance_meters, r.id))
        nearest_fire_stations = fire_candidates[:2]

        # B. Hospitals (Burn ICU / Toxic trauma prioritized for critical/industrial events, then geodesic distance, stable tie-break)
        med_candidates = [
            r
            for r in evaluated_responders
            if r.type
            in [
                ResponderType.BURN_ICU,
                ResponderType.HOSPITAL,
                ResponderType.BURN_INTENSIVE_CARE_HOSPITAL,
            ]
        ]
        if (
            response_priority in [ResponsePriority.CRITICAL, ResponsePriority.HIGH]
            or classification == "INDUSTRIAL"
        ):
            med_candidates.sort(
                key=lambda r: (
                    (
                        0
                        if r.type
                        in [
                            ResponderType.BURN_ICU,
                            ResponderType.BURN_INTENSIVE_CARE_HOSPITAL,
                        ]
                        else 1
                    ),
                    r.distance_meters,
                    r.id,
                )
            )
        else:
            med_candidates.sort(key=lambda r: (r.distance_meters, r.id))
        nearest_hospitals = med_candidates[:2]

        # C. Specialized Responders (Port Emergency, Hazmat units)
        specialized_candidates = [
            r
            for r in evaluated_responders
            if r.type
            in [
                ResponderType.SPECIALIZED_HAZMAT_UNIT,
                ResponderType.PORT_EMERGENCY_SERVICES,
            ]
            or any(
                "port" in c.lower() or "hazmat" in c.lower() or "foam" in c.lower()
                for c in r.capabilities
            )
        ]
        selected_ids = {r.id for r in nearest_fire_stations + nearest_hospitals}
        specialized_candidates = [
            r for r in specialized_candidates if r.id not in selected_ids
        ]
        specialized_candidates.sort(key=lambda r: (r.distance_meters, r.id))
        specialized_responders = specialized_candidates[:2]

        # D. NDRF Regional Battalion
        ndrf_candidates = [
            r
            for r in evaluated_responders
            if r.type in [ResponderType.NDRF, ResponderType.NDRF_DISASTER_BATTALION]
        ]
        ndrf_candidates.sort(key=lambda r: (r.distance_meters, r.id))
        ndrf_responders = ndrf_candidates[:1]

        # E. Unified deterministic final responders list (Fire -> Hospitals -> Specialized -> NDRF)
        final_responders: list[EmergencyResponder] = []
        final_seen_ids: set[str] = set()
        for r in (
            nearest_fire_stations
            + nearest_hospitals
            + specialized_responders
            + ndrf_responders
        ):
            if r.id not in final_seen_ids:
                final_seen_ids.add(r.id)
                final_responders.append(r)

        # 5. Evaluate Authoritative Backend Escalation Policy
        escalation_decision = EscalationPolicyService.evaluate_decision(
            event_id=event_id,
            confidence=confidence,
            operational_priority=response_priority,
        )

        auto_escalation_eligible = (
            escalation_decision.automatic or escalation_decision.medical_escalation
        )
        escalation_type: EscalationType | None = None
        if (
            escalation_decision.medical_escalation
            and response_priority == ResponsePriority.CRITICAL
        ):
            escalation_type = EscalationType.CRITICAL_MEDICAL
        elif escalation_decision.automatic:
            escalation_type = EscalationType.HIGH_CONFIDENCE_AUTO
        elif (
            escalation_decision.escalation_state
            == EscalationState.ADMIN_REVIEW_REQUIRED
        ):
            escalation_type = EscalationType.ADMIN_CONFIRMED

        auto_escalation_triggered = NotificationService.is_escalation_processed(
            event_id, EscalationType.HIGH_CONFIDENCE_AUTO
        ) or NotificationService.is_escalation_processed(
            event_id, EscalationType.CRITICAL_MEDICAL
        )

        if (
            not auto_escalation_triggered
            and auto_escalation_eligible
            and demo_phone
            and escalation_type
        ):
            # Proactive authoritative trigger
            try:
                primary_responder = (
                    nearest_hospitals[0]
                    if escalation_decision.medical_escalation and nearest_hospitals
                    else nearest_fire_stations[0]
                    if nearest_fire_stations
                    else final_responders[0]
                )
                NotificationAuditService.process_notification(
                    event_id,
                    NotificationRequest(
                        responder_id=primary_responder.id,
                        action=NotificationAction.NOTIFY,
                        mode=NotificationMode.SIMULATED,
                        recipient_phone=demo_phone,
                        channels=[
                            NotificationChannel.SMS,
                            NotificationChannel.WHATSAPP,
                        ],
                        escalation_type=escalation_type,
                        analyst_notes=(
                            "Automatic high-confidence demo escalation"
                            if escalation_decision.automatic
                            else "Critical event medical escalation"
                        ),
                    ),
                )
                auto_escalation_triggered = True
            except Exception as e:
                logger.warning(f"Auto-escalation dispatch failed: {e}")

        return EventResponseRecommendation(
            event_id=event_id,
            response_priority=response_priority,
            priority_reason=priority_reason,
            confidence=round(confidence, 4),
            auto_escalation_eligible=auto_escalation_eligible,
            auto_escalation_triggered=auto_escalation_triggered,
            escalation_type=escalation_type,
            medical_escalation=escalation_decision.medical_escalation,
            policy_drivers=escalation_decision.policy_drivers,
            escalation_decision=escalation_decision,
            is_routine_flare=is_routine_flare,
            is_abstained_or_unknown=is_abstained_or_unknown,
            responders=final_responders,
            nearest_hospitals=nearest_hospitals,
            nearest_fire_stations=nearest_fire_stations,
            specialized_responders=specialized_responders,
            ndrf_responders=ndrf_responders,
            recommendation_basis=recommendation_basis,
            evaluated_at=datetime.now(UTC),
        )


class NotificationAuditService:
    """Thread-safe service for emergency notifications and audit logging."""

    _activity_log: ClassVar[list[ResponseActivityRecord]] = []
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def process_notification(
        cls,
        event_id: str,
        request: NotificationRequest,
    ) -> NotificationResponse:
        """Process and dispatch an emergency notification request with multi-channel tracking and idempotency."""
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

        # 3. Determine phone number & multi-channel dispatch
        phone = request.recipient_phone or target_responder.get("phone") or "+91-112"
        phone_normalized = "+91-112"
        try:
            phone_normalized = NotificationService.validate_and_normalize_phone(phone)
        except Exception:
            if request.recipient_phone:
                raise
            phone_normalized = "+911120000000"

        masked_phone = mask_phone_number(phone_normalized)
        correlation_id = NotificationService.generate_correlation_id(event_id)
        now = datetime.now(UTC)
        ts_str = now.strftime("%Y%m%d-%H%M%S")
        notification_id = f"NOTIF-{event_id}-{request.responder_id}-{ts_str}"

        # 3b. Atomic Idempotency Check for Automatic Escalation
        is_auto = request.escalation_type in [
            EscalationType.HIGH_CONFIDENCE_AUTO,
            EscalationType.CRITICAL_MEDICAL,
        ]
        if is_auto and not NotificationService.record_escalation(
            event_id, request.escalation_type
        ):
            logger.info(
                f"Duplicate automatic escalation suppressed for Event={event_id}, "
                f"Type={request.escalation_type.value}, Correlation={correlation_id}"
            )
            suppressed_channels = [
                ChannelResult(
                    channel=ch,
                    status=ChannelDeliveryStatus.DUPLICATE_SUPPRESSED,
                    recipient=phone_normalized,
                    destination_masked=masked_phone,
                    message=f"Duplicate automatic escalation suppressed for {ch.value}.",
                    provider="idempotency_guard",
                    provider_message_id=None,
                    correlation_id=correlation_id,
                    submitted_at=now,
                    retry_count=0,
                )
                for ch in (
                    request.channels
                    or [NotificationChannel.SMS, NotificationChannel.WHATSAPP]
                )
            ]
            return NotificationResponse(
                notification_id=f"SUPPRESSED-{event_id}-{request.responder_id}",
                event_id=event_id,
                responder_id=request.responder_id,
                responder_name=target_responder["name"],
                action=request.action,
                status=NotificationStatus.DUPLICATE_SUPPRESSED,
                mode=request.mode,
                escalation_type=request.escalation_type,
                trigger_source=request.escalation_type,
                recipient_phone=phone_normalized,
                destination_masked=masked_phone,
                correlation_id=correlation_id,
                channels=suppressed_channels,
                timestamp=now,
                message="Duplicate automatic escalation request was suppressed.",
            )

        # Format message template
        label = next(
            (lbl for lbl in dataset.reference_labels if lbl.entity_id == event_id),
            None,
        )
        classification = label.assigned_class if label else "UNCLASSIFIED"
        confidence_val = (
            float(label.confidence_score * 100.0)
            if label and label.confidence_score is not None
            else 95.0
        )
        frp_val = float(target_event.max_frp_mw or 25.0)
        is_critical = (
            request.escalation_type == EscalationType.CRITICAL_MEDICAL or frp_val > 50.0
        )

        # Fetch dispersion context if available for wind intelligence enrichment
        wind_summary_str = None
        hazard_reach_val = None
        wind_sector_val = None
        try:
            from packages.data.weather.dispersion_service import get_dispersion_service
            disp_svc = get_dispersion_service()
            disp_data = disp_svc.evaluate_event_dispersion(
                event_id=event_id,
                latitude=target_event.centroid_geometry.latitude,
                longitude=target_event.centroid_geometry.longitude,
                frp_mw=frp_val,
            )
            if disp_data:
                w_obj = disp_data.wind
                d_obj = disp_data.dispersion
                wind_summary_str = f"{w_obj.speed_ms:.1f} m/s ({w_obj.direction_from_label} -> {w_obj.downwind_direction_label})"
                hazard_reach_val = d_obj.max_hazard_distance_km
                wind_sector_val = int((d_obj.plume_angle_deg % 360.0) // 30) * 30
        except Exception as e:
            logger.debug(f"Dispersion lookup for alert notification skipped: {e}")

        alert_text = NotificationService.format_alert_message(
            event_id=event_id,
            location=f"{target_responder['city']}, {target_responder['state']}",
            classification=classification,
            confidence_percent=confidence_val,
            frp_mw=frp_val,
            priority=ResponsePriority.CRITICAL
            if is_critical
            else ResponsePriority.HIGH,
            is_critical=is_critical,
            mode=request.mode,
            wind_summary=wind_summary_str,
            hazard_reach_km=hazard_reach_val,
            isolation_radius_m=200.0,
        )

        # Execute Multi-channel dispatch with idempotency protection and bounded retries
        channels = request.channels or [
            NotificationChannel.SMS,
            NotificationChannel.WHATSAPP,
        ]
        channel_results = NotificationService.dispatch_multichannel(
            event_id=event_id,
            recipient_phone=phone_normalized,
            message_text=alert_text,
            channels=channels,
            mode=request.mode,
            responder_id=request.responder_id,
            escalation_type=request.escalation_type,
            trigger_source=request.escalation_type.value,
            wind_sector=wind_sector_val,
            correlation_id=correlation_id,
        )


        # 4. Create Notification Record & Audit
        responder_name = target_responder["name"]
        resp_type = target_responder["type"]
        action_verb = (
            "Mobilization request"
            if request.action == NotificationAction.MOBILIZE
            else "Emergency response alert"
        )

        # Determine overall status
        failed_count = sum(
            1 for c in channel_results if c.status == ChannelDeliveryStatus.FAILED
        )
        suppressed_count = sum(
            1
            for c in channel_results
            if c.status == ChannelDeliveryStatus.DUPLICATE_SUPPRESSED
        )

        if suppressed_count == len(channel_results):
            overall_status = NotificationStatus.DUPLICATE_SUPPRESSED
        elif failed_count == len(channel_results):
            overall_status = NotificationStatus.FAILED
        elif failed_count > 0:
            overall_status = NotificationStatus.PARTIAL
        elif request.mode == NotificationMode.LIVE:
            overall_status = NotificationStatus.SENT
        else:
            overall_status = NotificationStatus.SIMULATED

        record = ResponseActivityRecord(
            notification_id=notification_id,
            event_id=event_id,
            responder_id=request.responder_id,
            responder_name=responder_name,
            responder_type=resp_type,
            action=request.action,
            status=overall_status,
            mode=request.mode,
            escalation_type=request.escalation_type,
            trigger_source=request.escalation_type,
            recipient_phone=phone_normalized,
            destination_masked=masked_phone,
            correlation_id=correlation_id,
            channels=channel_results,
            timestamp=now,
            analyst_notes=request.analyst_notes,
        )

        with cls._lock:
            cls._activity_log.append(record)

        logger.info(
            f"Notification processed: Event={event_id}, Recipient={responder_name}, "
            f"Phone={masked_phone}, Type={request.escalation_type.value}, "
            f"Status={overall_status.value}, Correlation={correlation_id}"
        )

        # Construct actionable summary message preserving exact required success wording
        if overall_status == NotificationStatus.DUPLICATE_SUPPRESSED:
            message = "Duplicate notification request was suppressed."
        elif failed_count == 0:
            if request.mode == NotificationMode.LIVE:
                message = (
                    f"Notification has been sent successfully to {phone_normalized}."
                )
            else:
                message = f"Notification has been sent successfully to {phone_normalized}. (SIMULATED)"
        elif failed_count < len(channel_results):
            succeeded = [
                c.channel.value
                for c in channel_results
                if c.status != ChannelDeliveryStatus.FAILED
            ]
            failed = [
                c.channel.value
                for c in channel_results
                if c.status == ChannelDeliveryStatus.FAILED
            ]
            message = f"{', '.join(succeeded)} notification sent successfully. {', '.join(failed)} notification failed."
        else:
            message = "Notification could not be sent."

        return NotificationResponse(
            notification_id=notification_id,
            event_id=event_id,
            responder_id=request.responder_id,
            responder_name=responder_name,
            action=request.action,
            status=overall_status,
            mode=request.mode,
            escalation_type=request.escalation_type,
            trigger_source=request.escalation_type,
            recipient_phone=phone_normalized,
            destination_masked=masked_phone,
            correlation_id=correlation_id,
            channels=channel_results,
            timestamp=now,
            message=message,
        )

    @classmethod
    def evaluate_and_trigger_automatic_escalation(
        cls,
        event_id: str,
        mode: NotificationMode = NotificationMode.SIMULATED,
    ) -> list[NotificationResponse]:
        """Backend-controlled evaluation and execution of automatic emergency notification workflows.

        Strictly enforces:
        - >98% model confidence -> Automatic high-confidence notification to nearest fire responder and hospital.
        - CRITICAL priority with medical escalation -> Automatic critical trauma notification to nearest burn unit.
        - Idempotent: Never re-triggers if already executed.
        - Decoupled from React lifecycle or frontend rendering.
        """
        from services.api.services.escalation import EscalationPolicyService

        responses: list[NotificationResponse] = []
        dataset = EventQueryService.get_canonical_enriched_dataset()
        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )
        if target_event is None:
            return responses

        rec = ResponseRecommendationService.get_recommendations_for_event(event_id)
        decision = EscalationPolicyService.evaluate_event(event_id)

        # 1. Automatic High-Confidence Escalation (>98%)
        if (
            decision.automatic
            and decision.escalation_state == EscalationState.AUTOMATIC_ESCALATION
            and not NotificationService.is_escalation_processed(
                event_id, EscalationType.HIGH_CONFIDENCE_AUTO
            )
        ):
            logger.info(
                f"[Auto-Escalation] Executing automatic dispatch for Event={event_id} (Confidence={conf_val})"
            )
            # Notify top fire station
            if rec.nearest_fire_stations:
                top_fire = rec.nearest_fire_stations[0]
                resp = cls.process_notification(
                    event_id,
                    NotificationRequest(
                        responder_id=top_fire.id,
                        action=NotificationAction.NOTIFY,
                        mode=mode,
                        recipient_phone=top_fire.phone if top_fire.phone != "N/A" else "+919876543210",
                        channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
                        escalation_type=EscalationType.HIGH_CONFIDENCE_AUTO,
                        analyst_notes="System automatic emergency escalation (>98% confidence)",
                    ),
                )
                responses.append(resp)

        # 2. Critical Medical Escalation (CRITICAL priority + medical escalation)
        if (
            decision.medical_escalation
            and not NotificationService.is_escalation_processed(
                event_id, EscalationType.CRITICAL_MEDICAL
            )
        ):
            logger.info(
                f"[Critical-Escalation] Executing critical medical dispatch for Event={event_id}"
            )
            if rec.nearest_hospitals:
                top_hosp = rec.nearest_hospitals[0]
                resp = cls.process_notification(
                    event_id,
                    NotificationRequest(
                        responder_id=top_hosp.id,
                        action=NotificationAction.MOBILIZE,
                        mode=mode,
                        recipient_phone=top_hosp.phone if top_hosp.phone != "N/A" else "+919876543210",
                        channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
                        escalation_type=EscalationType.CRITICAL_MEDICAL,
                        analyst_notes="System automatic critical medical emergency mobilization",
                    ),
                )
                responses.append(resp)

        return responses

    @classmethod
    def get_activity_for_event(cls, event_id: str) -> list[ResponseActivityRecord]:
        """Retrieve historical response audit records for a given event."""
        with cls._lock:
            records = [r for r in cls._activity_log if r.event_id == event_id]
            records.sort(key=lambda r: r.timestamp, reverse=True)
            return records

    @classmethod
    def clear_activity_log(cls) -> None:
        """Clear audit history and idempotency states (used for test isolation)."""
        with cls._lock:
            cls._activity_log.clear()
        NotificationService.clear_escalation_records()
