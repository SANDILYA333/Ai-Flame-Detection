"""Forest Threat Intelligence Service (Phase 3 & 4).

Evaluates geographic proximity between NASA FIRMS fire events and OpenStreetMap
forest areas to determine boundary distances, threat radii, threat levels,
and dispatches deduplicated emergency notifications to forest responders.
"""

import logging
from datetime import UTC, datetime
from threading import Lock
from typing import Any, ClassVar

from packages.config.settings import Settings, get_settings
from packages.data.forests.repository import (
    ForestRepositoryProtocol,
    get_forest_repository,
)
from packages.errors import InvalidCoordinateError, NotFoundError
from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.geospatial.polygon_distance import calculate_point_to_polygon_distance_km
from packages.logging import get_logger, log_with_context
from packages.schemas.common import Coordinate
from packages.schemas.forest import (
    ForestProximityAlertEvent,
    ForestThreatAssessment,
    ForestThreatCandidateEvent,
    ForestThreatDetail,
    ForestThreatLevel,
    ForestThreatSummaryItem,
    GlobalForestMonitoringSummary,
    NearbyForestThreatItem,
)
from packages.schemas.responders import (
    EscalationType,
    NotificationChannel,
    NotificationMode,
)

logger = get_logger("packages.data.forests.threat_service")


class ForestThreatService:
    """Service evaluating fire-to-forest proximity and spatial threat levels."""

    _alert_history: ClassVar[dict[str, ForestThreatLevel]] = {}
    _dispatched_alerts: ClassVar[set[str]] = set()
    _lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        repository: ForestRepositoryProtocol | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository or get_forest_repository()
        self.settings = settings or get_settings()
        if self.repository.count() == 0:
            try:
                from services.api.services.forests import _bootstrap_initial_forests

                _bootstrap_initial_forests(self.repository)
            except Exception:
                pass

    def evaluate_fire_point(
        self,
        latitude: float,
        longitude: float,
        fire_event_id: str | None = None,
        search_radius_km: float | None = None,
        threat_radius_km: float | None = None,
    ) -> ForestThreatAssessment:
        """Evaluate spatial proximity of a fire coordinate to all nearby forests.

        Invariants:
        1. Fire inside forest returns distance = 0.0 km and INSIDE_FOREST.
        2. Threat level is classified strictly on boundary distance.
        3. All forests within search_radius_km are returned, sorted ascending.

        Args:
            latitude: Fire point latitude in degrees [-90.0, 90.0].
            longitude: Fire point longitude in degrees [-180.0, 180.0].
            fire_event_id: Optional FIRMS event identifier.
            search_radius_km: Optional override for candidate search radius in km.
            threat_radius_km: Optional override for proximity threat radius in km.

        Returns:
            ForestThreatAssessment domain model.
        """
        try:
            val_lat, val_lon = validate_wgs84_coordinates(latitude, longitude)
        except Exception as e:
            raise InvalidCoordinateError(
                f"Invalid fire coordinate ({latitude}, {longitude}): {e}"
            ) from e

        # Resolve radius thresholds
        s_radius = float(
            search_radius_km
            if search_radius_km is not None
            else self.settings.FOREST_SEARCH_RADIUS_KM
        )
        t_radius = float(
            threat_radius_km
            if threat_radius_km is not None
            else self.settings.FOREST_THREAT_RADIUS_KM
        )
        aware_radius = float(self.settings.FOREST_AWARENESS_DISTANCE_KM)
        warn_radius = float(self.settings.FOREST_WARNING_DISTANCE_KM)
        crit_radius = float(self.settings.FOREST_CRITICAL_DISTANCE_KM)
        high_radius = float(self.settings.FOREST_HIGH_DISTANCE_KM)
        mod_radius = float(self.settings.FOREST_MODERATE_DISTANCE_KM)

        # Retrieve all forest records and calculate exact boundary distance
        nearby_items: list[NearbyForestThreatItem] = []
        now = datetime.now(UTC)

        all_forests, _ = self.repository.list_forests(limit=10000)

        for forest in all_forests:
            try:
                dist_km, nearest_coord = calculate_point_to_polygon_distance_km(
                    latitude=val_lat,
                    longitude=val_lon,
                    geometry=forest.geometry,
                )
            except Exception as err:
                log_with_context(
                    logger,
                    logging.WARNING,
                    (
                        "Skipping malformed forest during proximity check: "
                        f"{forest.forest_id}"
                    ),
                    context={"forest_id": forest.forest_id, "error": str(err)},
                )
                continue

            # Only include forests within search radius
            if dist_km <= s_radius:
                is_inside = dist_km == 0.0
                is_within_threat = dist_km <= t_radius

                # Classify threat level based on distance thresholds
                if is_inside:
                    threat_lvl = ForestThreatLevel.INSIDE_FOREST
                elif not is_within_threat:
                    threat_lvl = ForestThreatLevel.NONE
                elif dist_km <= crit_radius:
                    threat_lvl = ForestThreatLevel.CRITICAL
                elif dist_km <= warn_radius:
                    threat_lvl = ForestThreatLevel.WARNING
                elif dist_km <= aware_radius:
                    threat_lvl = ForestThreatLevel.AWARENESS
                else:
                    threat_lvl = ForestThreatLevel.NONE

                item = NearbyForestThreatItem(
                    forest_id=forest.forest_id,
                    osm_identity=forest.osm_identity,
                    name=forest.name or forest.name_en,
                    country_code=forest.country_code,
                    forest_type=forest.forest_type,
                    osm_tag=forest.osm_tag,
                    distance_km=dist_km,
                    inside_forest=is_inside,
                    is_within_threat_radius=is_within_threat or is_inside,
                    threat_level=threat_lvl,
                    nearest_point=nearest_coord,
                    centroid=forest.centroid,
                    area_km2=forest.area_km2,
                )
                nearby_items.append(item)

        # Sort ascending by boundary distance
        nearby_items.sort(key=lambda x: x.distance_km)

        nearest = nearby_items[0] if nearby_items else None
        threatened_count = sum(
            1 for item in nearby_items if item.is_within_threat_radius
        )
        overall_is_threatened = threatened_count > 0

        # Overall event threat level is the highest among threatened forests
        if nearest and nearest.is_within_threat_radius:
            overall_threat_level = nearest.threat_level
        else:
            overall_threat_level = ForestThreatLevel.NONE

        assessment = ForestThreatAssessment(
            fire_event_id=fire_event_id,
            fire_coordinate=Coordinate(latitude=val_lat, longitude=val_lon),
            search_radius_km=s_radius,
            threat_radius_km=t_radius,
            awareness_radius_km=aware_radius,
            warning_radius_km=warn_radius,
            critical_radius_km=crit_radius,
            high_radius_km=high_radius,
            moderate_radius_km=mod_radius,
            is_threatened=overall_is_threatened,
            threat_level=overall_threat_level,
            nearest_forest=nearest,
            nearby_forests=nearby_items[:5],
            total_threatened_forests=threatened_count,
            evaluated_at=now,
        )

        log_with_context(
            logger,
            logging.INFO,
            f"[FOREST_THREAT] Evaluated fire event {fire_event_id or 'ad-hoc'}: "
            f"threatened={overall_is_threatened} (level={overall_threat_level.value})",
            context={
                "fire_event_id": fire_event_id,
                "latitude": val_lat,
                "longitude": val_lon,
                "search_radius_km": s_radius,
                "threat_radius_km": t_radius,
                "total_nearby": len(nearby_items),
                "total_threatened": threatened_count,
                "nearest_forest_id": nearest.forest_id if nearest else None,
                "nearest_distance_km": nearest.distance_km if nearest else None,
                "threat_level": overall_threat_level.value,
            },
        )

        return assessment

    def evaluate_fire_event_by_id(
        self,
        event_id: str,
        search_radius_km: float | None = None,
        threat_radius_km: float | None = None,
    ) -> ForestThreatAssessment:
        """Evaluate forest proximity for an existing canonical thermal event.

        Args:
            event_id: Unique event ID.
            search_radius_km: Optional candidate search radius in km.
            threat_radius_km: Optional proximity threat radius in km.

        Returns:
            ForestThreatAssessment domain model.
        """
        from services.api.services.events import EventQueryService

        try:
            event_detail = EventQueryService.get_event(event_id)
        except Exception as e:
            raise NotFoundError(f"Thermal event '{event_id}' not found: {e}") from e

        coords = event_detail.geometry.get("coordinates", [0.0, 0.0])
        lon, lat = float(coords[0]), float(coords[1])

        return self.evaluate_fire_point(
            latitude=lat,
            longitude=lon,
            fire_event_id=event_id,
            search_radius_km=search_radius_km,
            threat_radius_km=threat_radius_km,
        )

    def create_forest_proximity_alert(
        self,
        event_id: str,
        forest_id: str,
        fire_confidence: float = 95.0,
        recipient_phone: str | None = None,
        channels: list[str] | None = None,
        force_dispatch: bool = False,
    ) -> ForestProximityAlertEvent:
        """Create, deduplicate, and optionally dispatch a forest proximity alert.

        Deduplication Invariant:
        Alert identity is determined by `(event_id, forest_id, threat_level)`.
        Repeated calls for the same state will NOT trigger duplicate dispatches.

        Escalation Invariant:
        If an event progresses to higher severity (e.g. WARNING -> CRITICAL),
        a new escalation alert is generated and dispatched.
        """
        # 1. Run proximity evaluation for the event
        assessment = self.evaluate_fire_event_by_id(event_id)

        # Find target forest
        target_item = next(
            (f for f in assessment.nearby_forests if f.forest_id == forest_id),
            assessment.nearest_forest,
        )
        if target_item is None or target_item.forest_id != forest_id:
            # Load single forest detail to calculate exact distance
            target_record = self.repository.get_forest_by_id(forest_id)
            if target_record is None:
                raise NotFoundError(f"Forest '{forest_id}' not found.")
            dist_km, nearest_coord = calculate_point_to_polygon_distance_km(
                latitude=assessment.fire_coordinate.latitude,
                longitude=assessment.fire_coordinate.longitude,
                geometry=target_record.geometry,
            )
            is_inside = dist_km == 0.0
            crit_radius = float(self.settings.FOREST_CRITICAL_DISTANCE_KM)
            warn_radius = float(self.settings.FOREST_WARNING_DISTANCE_KM)
            aware_radius = float(self.settings.FOREST_AWARENESS_DISTANCE_KM)
            if is_inside:
                threat_lvl = ForestThreatLevel.INSIDE_FOREST
            elif dist_km <= crit_radius:
                threat_lvl = ForestThreatLevel.CRITICAL
            elif dist_km <= warn_radius:
                threat_lvl = ForestThreatLevel.WARNING
            elif dist_km <= aware_radius:
                threat_lvl = ForestThreatLevel.AWARENESS
            else:
                threat_lvl = ForestThreatLevel.NONE

            target_item = NearbyForestThreatItem(
                forest_id=target_record.forest_id,
                osm_identity=target_record.osm_identity,
                name=target_record.name or target_record.name_en,
                country_code=target_record.country_code,
                forest_type=target_record.forest_type,
                osm_tag=target_record.osm_tag,
                distance_km=dist_km,
                inside_forest=is_inside,
                is_within_threat_radius=dist_km
                <= float(self.settings.FOREST_THREAT_RADIUS_KM),
                threat_level=threat_lvl,
                nearest_point=nearest_coord,
                centroid=target_record.centroid,
                area_km2=target_record.area_km2,
            )

        state_key = f"{event_id}:{forest_id}"
        alert_id = f"alert:{event_id}:{forest_id}:{target_item.threat_level.value}"
        now = datetime.now(UTC)

        with self._lock:
            prior_level = self._alert_history.get(state_key)
            is_escalation = (
                prior_level is not None
                and prior_level != target_item.threat_level
                and target_item.threat_level
                in (ForestThreatLevel.CRITICAL, ForestThreatLevel.INSIDE_FOREST)
            )
            self._alert_history[state_key] = target_item.threat_level

            # Determine whether to dispatch notification
            is_active_threat = (
                target_item.is_within_threat_radius
                or target_item.threat_level != ForestThreatLevel.NONE
            )
            should_dispatch = is_active_threat and (
                alert_id not in self._dispatched_alerts
                or force_dispatch
                or is_escalation
            )

            notification_id = None
            notif_dispatched = False

            if should_dispatch:
                try:
                    from services.api.services.notifications import NotificationService

                    channel_enums = []
                    for c in channels or ["sms", "whatsapp"]:
                        if c.lower() == "sms":
                            channel_enums.append(NotificationChannel.SMS)
                        elif c.lower() == "whatsapp":
                            channel_enums.append(NotificationChannel.WHATSAPP)

                    if not channel_enums:
                        channel_enums = [
                            NotificationChannel.SMS,
                            NotificationChannel.WHATSAPP,
                        ]

                    phone = recipient_phone or "+91-9876543210"
                    message_text = NotificationService.format_forest_proximity_message(
                        event_id=event_id,
                        forest_name=target_item.name or "Monitored Forest Area",
                        distance_km=target_item.distance_km,
                        threat_level=target_item.threat_level.value,
                        inside_forest=target_item.inside_forest,
                        mode=NotificationMode.SIMULATED,
                    )

                    dispatch_res = NotificationService.dispatch_multichannel(
                        event_id=event_id,
                        recipient_phone=phone,
                        message_text=message_text,
                        channels=channel_enums,
                        mode=NotificationMode.SIMULATED,
                        responder_id=f"forest_ranger_{forest_id}",
                        escalation_type=(
                            EscalationType.HIGH_CONFIDENCE_AUTO
                            if is_escalation
                            else EscalationType.ADMIN_CONFIRMED
                        ),
                        trigger_source=(
                            f"FOREST_PROXIMITY_ENGINE_FORCE_{now.strftime('%H%M%S%f')}"
                            if force_dispatch
                            else "FOREST_PROXIMITY_ENGINE"
                        ),
                        settings=self.settings,
                    )

                    notif_dispatched = any(
                        r.status.value in ("DELIVERED", "QUEUED", "SIMULATED")
                        for r in dispatch_res
                    )
                    notification_id = (
                        f"notif_{event_id}_{forest_id}_{now.strftime('%H%M%S')}"
                    )
                    self._dispatched_alerts.add(alert_id)
                except Exception as ex:
                    logger.warning(
                        f"Forest proximity notification dispatch error: {ex}"
                    )

            alert_event = ForestProximityAlertEvent(
                alert_id=alert_id,
                event_id=event_id,
                forest_id=forest_id,
                forest_name=target_item.name,
                distance_km=target_item.distance_km,
                inside_forest=target_item.inside_forest,
                threat_level=target_item.threat_level,
                fire_confidence=fire_confidence,
                fire_coordinate=assessment.fire_coordinate,
                created_at=now,
                is_escalation=is_escalation,
                notification_dispatched=notif_dispatched,
                notification_id=notification_id,
            )

            log_with_context(
                logger,
                logging.INFO,
                (
                    f"[FOREST_ALERT_GENERATED] event={event_id} "
                    f"forest={forest_id} threat={target_item.threat_level.value} "
                    f"dispatched={notif_dispatched}"
                ),
                context={
                    "alert_id": alert_id,
                    "event_id": event_id,
                    "forest_id": forest_id,
                    "threat_level": target_item.threat_level.value,
                    "distance_km": target_item.distance_km,
                    "notification_dispatched": notif_dispatched,
                },
            )

            return alert_event

    def get_all_active_events_for_evaluation(self) -> list[dict[str, Any]]:
        """Retrieve canonical active thermal events for forest threat monitoring."""
        try:
            from services.api.services.events import EventQueryService

            dataset = EventQueryService.get_canonical_enriched_dataset()
            label_lookup = {
                lbl.entity_id: lbl for lbl in dataset.reference_labels
            }

            event_items: list[dict[str, Any]] = []
            for ev in dataset.events:
                lbl = label_lookup.get(ev.event_id)
                confidence = 95.0
                classification = "UNKNOWN"
                if lbl:
                    classification = lbl.assigned_class or "UNKNOWN"
                    if lbl.confidence_score is not None:
                        confidence = round(lbl.confidence_score * 100.0, 1)

                event_items.append(
                    {
                        "event_id": ev.event_id,
                        "latitude": ev.centroid_geometry.latitude,
                        "longitude": ev.centroid_geometry.longitude,
                        "frp_mw": ev.max_frp_mw or ev.mean_frp_mw or 10.0,
                        "confidence": confidence,
                        "classification": classification,
                        "detected_at": ev.started_at,
                    }
                )
            return event_items
        except Exception as e:
            logger.warning(f"Could not load active thermal events from service: {e}")
            return []

    def get_global_monitoring_dashboard(
        self,
        status_filter: str | None = None,
        country_code: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[GlobalForestMonitoringSummary, list[ForestThreatSummaryItem], int]:
        """Aggregate global threat status across all monitored forests and active fires.

        Evaluates every forest against active FIRMS events, prioritizing the most
        severe threat for forests exposed to multiple fires, generating grounded
        explainability bullets, and computing system-wide KPI statistics.

        Args:
            status_filter: Optional filter by threat level (e.g. 'CRITICAL', 'WARNING').
            country_code: Optional ISO country code filter.
            search: Optional text query matching forest name, OSM ID, or region.
            limit: Maximum items to return for pagination.
            offset: Items to skip for pagination.

        Returns:
            Tuple of (summary, paged_items, total_filtered_count).
        """
        all_forests, _ = self.repository.list_forests(limit=10000)
        active_events = self.get_all_active_events_for_evaluation()
        now = datetime.now(UTC)

        crit_radius = float(self.settings.FOREST_CRITICAL_DISTANCE_KM)
        warn_radius = float(self.settings.FOREST_WARNING_DISTANCE_KM)
        aware_radius = float(self.settings.FOREST_AWARENESS_DISTANCE_KM)

        # Threat severity weight mapping for multi-event prioritization & sorting
        severity_weight = {
            ForestThreatLevel.ACTIVE_FIRE: 5,
            ForestThreatLevel.INSIDE_FOREST: 5,
            ForestThreatLevel.CRITICAL: 4,
            ForestThreatLevel.HIGH: 4,
            ForestThreatLevel.WARNING: 3,
            ForestThreatLevel.MODERATE: 3,
            ForestThreatLevel.AWARENESS: 2,
            ForestThreatLevel.SAFE: 1,
            ForestThreatLevel.NONE: 1,
            ForestThreatLevel.LOW: 1,
        }

        forest_summary_items: list[ForestThreatSummaryItem] = []
        safe_count = 0
        awareness_count = 0
        warning_count = 0
        critical_count = 0
        active_fire_count = 0

        for forest in all_forests:
            # Find all threatening candidate events within awareness radius
            candidate_events: list[ForestThreatCandidateEvent] = []

            for ev in active_events:
                try:
                    dist_km, _ = calculate_point_to_polygon_distance_km(
                        latitude=ev["latitude"],
                        longitude=ev["longitude"],
                        geometry=forest.geometry,
                    )
                except Exception:
                    continue

                if dist_km <= aware_radius:
                    is_inside = dist_km == 0.0
                    if is_inside:
                        t_lvl = ForestThreatLevel.ACTIVE_FIRE
                    elif dist_km <= crit_radius:
                        t_lvl = ForestThreatLevel.CRITICAL
                    elif dist_km <= warn_radius:
                        t_lvl = ForestThreatLevel.WARNING
                    else:
                        t_lvl = ForestThreatLevel.AWARENESS

                    candidate = ForestThreatCandidateEvent(
                        event_id=ev["event_id"],
                        coordinate=Coordinate(
                            latitude=ev["latitude"], longitude=ev["longitude"]
                        ),
                        distance_km=dist_km,
                        inside_forest=is_inside,
                        threat_level=t_lvl,
                        confidence=ev["confidence"],
                        frp_mw=ev["frp_mw"],
                        classification=ev["classification"],
                        detected_at=ev["detected_at"],
                    )
                    candidate_events.append(candidate)

            # Sort: 1. Severity weight desc, 2. Distance asc, 3. FRP desc
            candidate_events.sort(
                key=lambda c: (
                    -severity_weight.get(c.threat_level, 0),
                    c.distance_km,
                    -c.frp_mw,
                )
            )

            primary_candidate = candidate_events[0] if candidate_events else None

            if primary_candidate is None:
                forest_threat_lvl = ForestThreatLevel.SAFE
                is_inside = False
                p_event_id = None
                p_distance = None
                p_confidence = None
                p_frp = None
                active_threat_count_val = 0
                trend = "STATIONARY"
                why_bullets = [
                    "No thermal anomalies detected within 10 km monitoring boundary.",
                    (
                        "Forest perimeter status is normal with zero active "
                        "proximity alerts."
                    ),
                ]
                safe_count += 1
            else:
                forest_threat_lvl = primary_candidate.threat_level
                is_inside = primary_candidate.inside_forest
                p_event_id = primary_candidate.event_id
                p_distance = primary_candidate.distance_km
                p_confidence = primary_candidate.confidence
                p_frp = primary_candidate.frp_mw
                active_threat_count_val = len(candidate_events)

                if is_inside or forest_threat_lvl == ForestThreatLevel.ACTIVE_FIRE:
                    active_fire_count += 1
                    trend = "INTERIOR"
                    dist_bullet = (
                        "CRITICAL: Active thermal fire detected inside "
                        "forest polygon perimeter (0.0 km)."
                    )
                elif forest_threat_lvl == ForestThreatLevel.CRITICAL:
                    critical_count += 1
                    trend = "APPROACHING"
                    dist_bullet = (
                        f"CRITICAL PROXIMITY: Active thermal {p_distance:.2f} km "
                        "from forest boundary (within 2.0 km critical threshold)."
                    )
                elif forest_threat_lvl == ForestThreatLevel.WARNING:
                    warning_count += 1
                    trend = "APPROACHING"
                    dist_bullet = (
                        f"WARNING: Active thermal anomaly {p_distance:.2f} km "
                        "from forest boundary (within 5.0 km warning threshold)."
                    )
                else:
                    awareness_count += 1
                    trend = "STATIONARY"
                    dist_bullet = (
                        f"AWARENESS: Thermal anomaly detected {p_distance:.2f} km "
                        "from forest boundary (monitoring perimeter)."
                    )

                frp_bullet = (
                    f"Fire radiative power: {p_frp:.1f} MW "
                    f"(Detection confidence: {p_confidence:.1f}%)."
                )
                class_bullet = (
                    f"Classified as {primary_candidate.classification} "
                    "thermal activity source."
                )

                why_bullets = [dist_bullet, frp_bullet, class_bullet]
                if len(candidate_events) > 1:
                    why_bullets.append(
                        f"Multi-threat condition: {len(candidate_events)} active "
                        "thermal events detected in proximity."
                    )

            item = ForestThreatSummaryItem(
                forest_id=forest.forest_id,
                osm_identity=forest.osm_identity,
                name=forest.name or forest.name_en,
                country_code=forest.country_code,
                forest_type=forest.forest_type,
                osm_tag=forest.osm_tag,
                area_km2=forest.area_km2,
                centroid=forest.centroid,
                threat_level=forest_threat_lvl,
                inside_forest=is_inside,
                primary_event_id=p_event_id,
                primary_distance_km=p_distance,
                primary_confidence=p_confidence,
                primary_frp_mw=p_frp,
                active_threat_count=active_threat_count_val,
                why_at_risk=why_bullets,
                progression_trend=trend,
                evaluated_at=now,
            )
            forest_summary_items.append(item)

        total_monitored = len(all_forests)
        total_threatened = (
            awareness_count + warning_count + critical_count + active_fire_count
        )

        summary = GlobalForestMonitoringSummary(
            total_monitored_forests=total_monitored,
            safe_forests=safe_count,
            awareness_forests=awareness_count,
            warning_forests=warning_count,
            critical_forests=critical_count,
            active_fire_forests=active_fire_count,
            total_threatened_forests=total_threatened,
            active_thermal_events_evaluated=len(active_events),
            evaluated_at=now,
        )

        # Filter items
        filtered_items = forest_summary_items

        if status_filter and status_filter.upper() != "ALL":
            status_clean = status_filter.upper()
            if status_clean in ("ACTIVE_FIRE", "INSIDE_FOREST"):
                filtered_items = [
                    f
                    for f in filtered_items
                    if f.threat_level
                    in (ForestThreatLevel.ACTIVE_FIRE, ForestThreatLevel.INSIDE_FOREST)
                ]
            elif status_clean in ("CRITICAL", "HIGH"):
                filtered_items = [
                    f
                    for f in filtered_items
                    if f.threat_level
                    in (ForestThreatLevel.CRITICAL, ForestThreatLevel.HIGH)
                ]
            elif status_clean in ("WARNING", "MODERATE"):
                filtered_items = [
                    f
                    for f in filtered_items
                    if f.threat_level
                    in (ForestThreatLevel.WARNING, ForestThreatLevel.MODERATE)
                ]
            elif status_clean == "AWARENESS":
                filtered_items = [
                    f
                    for f in filtered_items
                    if f.threat_level == ForestThreatLevel.AWARENESS
                ]
            elif status_clean in ("SAFE", "NONE"):
                filtered_items = [
                    f
                    for f in filtered_items
                    if f.threat_level
                    in (ForestThreatLevel.SAFE, ForestThreatLevel.NONE)
                ]

        if country_code:
            c_code = country_code.strip().upper()
            filtered_items = [
                f for f in filtered_items if f.country_code.upper() == c_code
            ]

        if search:
            q = search.strip().lower()
            filtered_items = [
                f
                for f in filtered_items
                if q in (f.name or "").lower()
                or q in f.osm_identity.lower()
                or q in f.country_code.lower()
            ]

        # Sort: 1. Severity weight desc, 2. Distance asc (None at end), 3. Name asc
        filtered_items.sort(
            key=lambda x: (
                -severity_weight.get(x.threat_level, 0),
                x.primary_distance_km if x.primary_distance_km is not None else 99999.0,
                x.name or "",
            )
        )

        total_filtered = len(filtered_items)
        paged_items = filtered_items[offset : offset + limit]

        return summary, paged_items, total_filtered

    def get_forest_threat_detail_by_id(
        self,
        forest_id: str,
    ) -> ForestThreatDetail:
        """Generate comprehensive threat intelligence report for a single forest.

        Args:
            forest_id: Unique forest canonical identifier.

        Returns:
            ForestThreatDetail domain model.

        Raises:
            NotFoundError: If forest is not found.
        """
        forest = self.repository.get_forest_by_id(forest_id)
        if forest is None:
            raise NotFoundError(f"Forest '{forest_id}' not found.")

        active_events = self.get_all_active_events_for_evaluation()
        now = datetime.now(UTC)

        crit_radius = float(self.settings.FOREST_CRITICAL_DISTANCE_KM)
        warn_radius = float(self.settings.FOREST_WARNING_DISTANCE_KM)
        aware_radius = float(self.settings.FOREST_AWARENESS_DISTANCE_KM)
        search_radius = float(self.settings.FOREST_SEARCH_RADIUS_KM)

        candidate_events: list[ForestThreatCandidateEvent] = []
        nearest_coord_overall: Coordinate | None = None
        min_dist_overall = float("inf")

        for ev in active_events:
            try:
                dist_km, nearest_coord = calculate_point_to_polygon_distance_km(
                    latitude=ev["latitude"],
                    longitude=ev["longitude"],
                    geometry=forest.geometry,
                )
            except Exception:
                continue

            if dist_km < min_dist_overall:
                min_dist_overall = dist_km
                nearest_coord_overall = nearest_coord

            if dist_km <= search_radius:
                is_inside = dist_km == 0.0
                if is_inside:
                    t_lvl = ForestThreatLevel.ACTIVE_FIRE
                elif dist_km <= crit_radius:
                    t_lvl = ForestThreatLevel.CRITICAL
                elif dist_km <= warn_radius:
                    t_lvl = ForestThreatLevel.WARNING
                elif dist_km <= aware_radius:
                    t_lvl = ForestThreatLevel.AWARENESS
                else:
                    t_lvl = ForestThreatLevel.NONE

                candidate = ForestThreatCandidateEvent(
                    event_id=ev["event_id"],
                    coordinate=Coordinate(
                        latitude=ev["latitude"], longitude=ev["longitude"]
                    ),
                    distance_km=dist_km,
                    inside_forest=is_inside,
                    threat_level=t_lvl,
                    confidence=ev["confidence"],
                    frp_mw=ev["frp_mw"],
                    classification=ev["classification"],
                    detected_at=ev["detected_at"],
                )
                candidate_events.append(candidate)

        # Sort candidate events: 1. Distance asc, 2. FRP desc
        candidate_events.sort(key=lambda c: (c.distance_km, -c.frp_mw))

        # Threatening events are those within awareness/threat radius
        threatening = [
            c for c in candidate_events if c.distance_km <= aware_radius
        ]

        if not threatening:
            return ForestThreatDetail(
                forest=forest,
                threat_level=ForestThreatLevel.SAFE,
                is_threatened=False,
                inside_forest=False,
                nearest_event_id=(
                    candidate_events[0].event_id if candidate_events else None
                ),
                nearest_distance_km=(
                    candidate_events[0].distance_km if candidate_events else None
                ),
                nearest_point=nearest_coord_overall,
                primary_confidence=None,
                primary_frp_mw=None,
                threatening_events=[],
                why_at_risk=[
                    "No active thermal anomalies within 10 km monitoring boundary.",
                    "Forest perimeter is completely clear of fire threats.",
                ],
                progression_trend="STATIONARY",
                evaluated_at=now,
            )

        primary = threatening[0]
        is_inside = primary.inside_forest
        p_threat = primary.threat_level

        if is_inside or p_threat == ForestThreatLevel.ACTIVE_FIRE:
            trend = "INTERIOR"
            dist_bullet = (
                "CRITICAL: Active thermal fire detected inside forest boundary "
                "(0.0 km)."
            )
        elif p_threat == ForestThreatLevel.CRITICAL:
            trend = "APPROACHING"
            dist_bullet = (
                f"CRITICAL PROXIMITY: Fire anomaly {primary.distance_km:.2f} km "
                "from perimeter (within 2.0 km critical threshold)."
            )
        elif p_threat == ForestThreatLevel.WARNING:
            trend = "APPROACHING"
            dist_bullet = (
                f"WARNING: Fire anomaly {primary.distance_km:.2f} km "
                "from perimeter (within 5.0 km warning threshold)."
            )
        else:
            trend = "STATIONARY"
            dist_bullet = (
                f"AWARENESS: Fire anomaly {primary.distance_km:.2f} km "
                "from perimeter (monitoring threshold 10.0 km)."
            )

        why_bullets = [
            dist_bullet,
            (
                f"Primary thermal intensity: {primary.frp_mw:.1f} MW FRP "
                f"(Detection confidence: {primary.confidence:.1f}%)."
            ),
            f"Adjudicated classification: {primary.classification}.",
        ]

        if len(threatening) > 1:
            why_bullets.append(
                f"Multiple fire threat: {len(threatening)} active events within 10 km."
            )

        return ForestThreatDetail(
            forest=forest,
            threat_level=p_threat,
            is_threatened=True,
            inside_forest=is_inside,
            nearest_event_id=primary.event_id,
            nearest_distance_km=primary.distance_km,
            nearest_point=nearest_coord_overall,
            primary_confidence=primary.confidence,
            primary_frp_mw=primary.frp_mw,
            threatening_events=threatening,
            why_at_risk=why_bullets,
            progression_trend=trend,
            evaluated_at=now,
        )


# Global singleton threat service instance
_default_threat_service: ForestThreatService | None = None


def get_forest_threat_service() -> ForestThreatService:
    """Retrieve canonical ForestThreatService singleton instance."""
    global _default_threat_service
    if _default_threat_service is None:
        _default_threat_service = ForestThreatService()
    return _default_threat_service
