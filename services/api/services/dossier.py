"""Tactical incident dossier synthesis and reporting service (DOSSIER-002)."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path

from packages.errors import ErrorCode, NotFoundError
from packages.physics.plume import GaussianPlumeEngine
from packages.physics.pyrometry import DozierPyrometrySolver
from services.api.schemas.dossier import (
    HazmatProfileInfo,
    PlumeTelemetry,
    PyrometryTelemetry,
    TacticalDossierResponse,
)
from services.api.services.events import EventQueryService
from services.api.services.responders import ResponseRecommendationService

_HAZMAT_PATH = Path("data2/industrial_infra/hazmat_profiles.json")
_FALLBACK_HAZMAT_PATH = Path("data/industrial_infra/hazmat_profiles.json")


class TacticalDossierService:
    """Service synthesizing operational tactical dossiers for thermal incidents."""

    _hazmat_cache: dict | None = None

    @classmethod
    def get_hazmat_profiles(cls) -> dict:
        if cls._hazmat_cache is not None:
            return cls._hazmat_cache

        path = _HAZMAT_PATH if _HAZMAT_PATH.exists() else _FALLBACK_HAZMAT_PATH
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    cls._hazmat_cache = json.load(f)
                    return cls._hazmat_cache
            except Exception:
                pass
        return {}

    @classmethod
    def match_hazmat_profile(
        cls, facility_name: str | None, facility_type: str | None
    ) -> HazmatProfileInfo | None:
        profiles = cls.get_hazmat_profiles()
        if not profiles:
            return None

        fac_lower = (facility_name or "").lower()
        type_lower = (facility_type or "").lower()

        if "refin" in fac_lower or "refin" in type_lower or "petrol" in fac_lower:
            key_to_match = "Oil Refinery"
        elif (
            "petrochem" in fac_lower
            or "polymer" in fac_lower
            or "chemical" in fac_lower
        ):
            key_to_match = "Petrochemical & Polymer Complex"
        elif "fertil" in fac_lower or "ammonia" in fac_lower or "nitrate" in fac_lower:
            key_to_match = "Fertilizer & Chemical Complex"
        elif "chlor" in fac_lower or "alkali" in fac_lower:
            key_to_match = "Chlor-Alkali & Basic Chemicals"
        elif "power" in fac_lower or "thermal" in fac_lower or "tps" in fac_lower:
            key_to_match = "Thermal Power Plant"
        elif (
            "steel" in fac_lower
            or "iron" in fac_lower
            or "smelter" in fac_lower
            or "metal" in fac_lower
        ):
            key_to_match = "Iron, Steel & Smelting Works"
        elif "lng" in fac_lower or "gas" in fac_lower or "terminal" in fac_lower:
            key_to_match = "LNG & Cryogenic Gas Terminal"
        elif "coal" in fac_lower or "mine" in fac_lower:
            key_to_match = "Open Cast & Underground Coal Mining"
        else:
            key_to_match = "Oil Refinery"  # Default heavy industrial baseline

        data = profiles.get(key_to_match)
        if not data:
            return None

        return HazmatProfileInfo(
            facility_sector=data.get("sector", key_to_match),
            cameo_hazmat_class=data.get(
                "cameo_hazmat_class", "Class 3 - Flammable"
            ),
            primary_chemicals=data.get("primary_chemicals", []),
            un_na_numbers=data.get("un_na_numbers", []),
            primary_disaster_risk=data.get(
                "primary_disaster_risk",
                "Thermal Flashover & Toxic Inhalation",
            ),
            initial_isolation_distance_meters=data.get(
                "initial_isolation_distance_meters", 800
            ),
            downwind_evacuation_day_meters=data.get(
                "downwind_evacuation_day_meters", 1600
            ),
            downwind_evacuation_night_meters=data.get(
                "downwind_evacuation_night_meters", 2400
            ),
            toxic_combustion_byproducts=data.get(
                "toxic_combustion_byproducts", []
            ),
            firefighting_protocol=data.get(
                "firefighting_protocol",
                "Standard Industrial Foam & Water Deluge",
            ),
            idlh_ppm=data.get("idlh_ppm", {}),
        )

    @classmethod
    def generate_dossier(cls, event_id: str) -> TacticalDossierResponse:
        dataset = EventQueryService.get_canonical_enriched_dataset()
        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )

        if target_event is None:
            raise NotFoundError(
                message=f"Thermal event '{event_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 1. Resolve Classification & Context
        label = next(
            (lbl for lbl in dataset.reference_labels if lbl.entity_id == event_id),
            None,
        )
        classification = label.assigned_class if label else "UNKNOWN"
        confidence = label.confidence_score if label else 0.5
        tier = (
            label.label_tier.value
            if label and getattr(label, "label_tier", None)
            else "TIER_C"
        )
        uncertainty_state = (
            "CONFIDENT" if tier in ["TIER_A", "TIER_B"] else "REVIEW_REQUIRED"
        )

        # Nearby facility evidence
        nearby_ce = next(
            (ce for ce in dataset.context_evidence if ce.facility_name),
            None,
        )
        facility_name = (
            getattr(nearby_ce, "facility_name", None)
            if nearby_ce
            else "Industrial Infrastructure Facility"
        )
        ctx_t = getattr(nearby_ce, "context_type", None)
        facility_type = (
            ctx_t.value if hasattr(ctx_t, "value") else str(ctx_t or "heavy_industry")
        )
        facility_dist = getattr(nearby_ce, "distance_to_event_meters", 320.0) or 320.0

        lat = target_event.centroid_geometry.latitude
        lon = target_event.centroid_geometry.longitude
        frp = target_event.max_frp_mw

        # 2. Derive Planck Pyrometry Inversion
        bright_mwir = 310.0 + min(120.0, math.sqrt(max(1.0, frp)) * 8.5)
        bright_lwir = 295.0 + min(20.0, math.sqrt(max(1.0, frp)) * 1.5)
        pyro_result = DozierPyrometrySolver.solve(
            bright_mwir_k=bright_mwir,
            bright_lwir_k=bright_lwir,
            background_temp_k=295.0,
        )

        # 3. Derive Gaussian Plume & Evacuation Boundary
        plume_result = GaussianPlumeEngine.compute_plume(
            latitude=lat,
            longitude=lon,
            frp_mw=frp,
            wind_speed_ms=3.8,
            wind_direction_deg=235.0,
        )

        # 4. Derive Emergency Responders & Priority
        recs = ResponseRecommendationService.get_recommendations_for_event(
            event_id
        )

        # 5. Match CAMEO-NIOSH Hazmat Profile
        hazmat = cls.match_hazmat_profile(facility_name, facility_type)

        iso_dist = (
            hazmat.initial_isolation_distance_meters if hazmat else 800
        )
        lead_resp = (
            recs.responders[0].name
            if recs.responders
            else "Regional Fire Safety Command"
        )

        ops_recs = [
            f"Establish initial ERG safety boundary at {iso_dist}m radius.",
            f"Mobilize nearest brigade ({lead_resp}) with foam concentrate.",
            "Deploy air quality monitoring along downwind dispersion axis.",
            "Maintain satellite infrared tracking for thermal spread.",
        ]
        if recs.is_routine_flare:
            ops_recs = [
                "Routine operational flare verified. Maintain telemetry.",
                "Verify plant flare gas recovery system (FGRS) status.",
                "No external emergency mobilization indicated.",
            ]

        sector = (
            hazmat.facility_sector
            if hazmat
            else "Heavy Industrial Sector"
        )

        return TacticalDossierResponse(
            dossier_id=(
                f"DOSSIER-{event_id}-{datetime.now(UTC).strftime('%Y%m%d')}"
            ),
            event_id=event_id,
            generated_at=datetime.now(UTC),
            classification=classification,
            confidence=confidence,
            uncertainty_state=uncertainty_state,
            latitude=lat,
            longitude=lon,
            frp_mw=frp,
            detection_count=target_event.detection_count,
            started_at=target_event.started_at,
            location_name=f"Lat {lat:.4f}°N, Lon {lon:.4f}°E",
            facility_name=facility_name,
            facility_distance_meters=facility_dist,
            facility_sector=sector,
            response_priority=recs.response_priority,
            priority_reason=recs.priority_reason,
            hazmat=hazmat,
            pyrometry=PyrometryTelemetry(
                emitter_temp_k=pyro_result.emitter_temp_k,
                emitter_area_m2=pyro_result.emitter_area_m2,
                background_temp_k=pyro_result.background_temp_k,
                radiance_residual=pyro_result.radiance_residual,
                is_valid=pyro_result.is_valid,
                convergence_status=pyro_result.convergence_status,
            ),
            plume=PlumeTelemetry(
                wind_speed_ms=plume_result.wind_speed_ms,
                wind_direction_deg=plume_result.wind_direction_deg,
                downwind_azimuth_deg=plume_result.downwind_azimuth_deg,
                plume_length_km=plume_result.plume_length_km,
                plume_width_km=plume_result.plume_width_km,
                evacuation_radius_km=plume_result.evacuation_radius_km,
                stability_class=plume_result.stability_class,
                hazard_label=plume_result.hazard_label,
                plume_polygon_geojson=plume_result.plume_polygon_geojson,
                evacuation_circle_geojson=plume_result.evacuation_circle_geojson,
            ),
            recommended_responders=recs.responders,
            operational_recommendations=ops_recs,
            is_simulated_demo=True,
        )
