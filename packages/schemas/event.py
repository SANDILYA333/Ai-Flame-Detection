"""Canonical Thermal Event domain model."""

import math

from pydantic import Field, field_validator, model_validator

from packages.schemas.common import (
    BaseDomainModel,
    BoundingBox,
    Coordinate,
    UtcDatetime,
)
from packages.schemas.context import ContextEvidence
from packages.schemas.ml import LabelDecision, ReferenceEvidence
from packages.schemas.source import PersistentSource


class Event(BaseDomainModel):
    """Canonical representation of a thermal event formed by clustering detections.

    An event represents a spatio-temporal cluster of individual detections
    believed to correspond to a coherent physical heating episode.

    IMPORTANT ARCHITECTURAL INVARIANTS:
    - centroid_geometry is an event representation, NOT exact facility location.
    - No clustering parameters (radius, time gap) are hard-coded in this model.
    - An event must retain its member detection references for provenance.
    """

    event_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical identifier for the thermal event.",
    )
    detection_ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of unique detection identifiers composing event.",
    )
    detection_count: int = Field(
        ...,
        ge=1,
        description="Total count of member detections (matches detection_ids).",
    )
    started_at: UtcDatetime = Field(
        ...,
        description="Earliest acquisition timestamp among detections in UTC.",
    )
    ended_at: UtcDatetime = Field(
        ...,
        description="Latest acquisition timestamp among detections in UTC.",
    )
    centroid_geometry: Coordinate = Field(
        ...,
        description="Representative spatial centroid of the event cluster.",
    )
    formation_configuration_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of event formation configuration contract used.",
    )
    formation_configuration_version: str = Field(
        ...,
        min_length=1,
        description="Version string of event formation algorithm/configuration.",
    )

    # Optional descriptive summary and lineage fields
    bounding_box: BoundingBox | None = Field(
        None,
        description="Spatial bounding envelope encompassing member detections.",
    )
    formation_run_id: str | None = Field(
        None,
        min_length=1,
        description="Lineage pipeline run identifier that formed this event.",
    )
    duration_seconds: float | None = Field(
        None,
        ge=0.0,
        description="Duration of the event in seconds (ended_at - started_at).",
    )
    mean_frp_mw: float | None = Field(
        None,
        ge=0.0,
        description="Mean Fire Radiative Power across detections in MW.",
    )
    max_frp_mw: float | None = Field(
        None,
        ge=0.0,
        description="Maximum Fire Radiative Power across detections in MW.",
    )
    notes: str | None = Field(
        None,
        description="Operational or diagnostic notes on event formation.",
    )

    @field_validator("detection_ids", mode="after")
    @classmethod
    def _validate_unique_detection_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Event must contain at least one detection ID.")
        cleaned = [d.strip() for d in v if d and d.strip()]
        if len(cleaned) != len(v):
            raise ValueError("detection_ids cannot contain empty or blank strings.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("detection_ids must contain unique identifiers.")
        return cleaned

    @field_validator("duration_seconds", "mean_frp_mw", "max_frp_mw", mode="after")
    @classmethod
    def _validate_finite_optional(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Numeric metrics must be finite.")
        return v

    @model_validator(mode="after")
    def _validate_event_invariants(self) -> "Event":
        if self.ended_at < self.started_at:
            raise ValueError(
                f"ended_at ({self.ended_at}) cannot precede "
                f"started_at ({self.started_at})."
            )
        if self.detection_count != len(self.detection_ids):
            raise ValueError(
                f"detection_count ({self.detection_count}) must match "
                f"number of detection_ids ({len(self.detection_ids)})."
            )
        return self


class RealThermalEventDataset(BaseDomainModel):
    """Canonical container for derived thermal events and persistent sources."""

    dataset_id: str = Field(
        default="ds_real_events_v1.0.0",
        min_length=1,
        description="Unique identifier for the thermal event dataset.",
    )
    dataset_version: str = Field(
        default="v1.0.0",
        min_length=1,
        description="Semantic version of the thermal event dataset.",
    )
    detection_dataset_id: str = Field(
        ...,
        description="Originating detection dataset ID (e.g. ds_real_firms_v1.0.0).",
    )
    detection_dataset_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Cryptographic SHA-256 hash of originating detection dataset.",
    )
    study_area_id: str = Field(
        ...,
        description="Identifier of study area (e.g. jamnagar_kutch).",
    )
    study_area_name: str = Field(
        ...,
        description="Human-readable study area title.",
    )
    bounding_box: BoundingBox = Field(
        ...,
        description="Geographic WGS-84 spatial bounding envelope.",
    )
    events: list[Event] = Field(
        default_factory=list,
        description="Deterministically ordered canonical Event domain objects.",
    )
    persistent_sources: list[PersistentSource] = Field(
        default_factory=list,
        description="Deterministically ordered canonical PersistentSource objects.",
    )
    config_fingerprint: str = Field(
        ...,
        description="SHA-256 fingerprint of governing ScientificConfig.",
    )
    spatial_cluster_radius_meters: float = Field(
        ...,
        gt=0.0,
        description="Spatial clustering radius in meters used for event formation.",
    )
    temporal_window_hours: float = Field(
        ...,
        gt=0.0,
        description="Temporal clustering window in hours used for event formation.",
    )
    persistent_source_radius_meters: float = Field(
        ...,
        gt=0.0,
        description="Spatial association radius in meters used for source tracking.",
    )
    event_count: int = Field(
        ...,
        ge=0,
        description="Total number of thermal events in dataset.",
    )
    persistent_source_count: int = Field(
        ...,
        ge=0,
        description="Total number of persistent sources in dataset.",
    )
    canonical_dataset_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Deterministic SHA-256 hash across sorted events and sources.",
    )
    created_at: UtcDatetime = Field(
        ...,
        description="Timestamp when event dataset was compiled in UTC.",
    )
    processing_version: str = Field(
        default="v1.0.0",
        description="Version of event derivation software pipeline.",
    )

    def compute_canonical_hash(self) -> str:
        """Compute deterministic SHA-256 hash across sorted events and sources."""
        import hashlib
        import json

        sorted_events = sorted(
            self.events,
            key=lambda e: (
                e.started_at.isoformat(),
                e.centroid_geometry.latitude,
                e.centroid_geometry.longitude,
                e.event_id,
            ),
        )
        sorted_sources = sorted(
            self.persistent_sources,
            key=lambda s: (
                s.first_seen_at.isoformat(),
                s.centroid_geometry.latitude,
                s.centroid_geometry.longitude,
                s.source_id,
            ),
        )

        canonical_events = [
            {
                "event_id": e.event_id,
                "detection_ids": sorted(e.detection_ids),
                "detection_count": e.detection_count,
                "started_at": e.started_at.isoformat(),
                "ended_at": e.ended_at.isoformat(),
                "centroid_lat": round(e.centroid_geometry.latitude, 6),
                "centroid_lon": round(e.centroid_geometry.longitude, 6),
                "duration_seconds": (
                    round(e.duration_seconds, 2)
                    if e.duration_seconds is not None
                    else None
                ),
                "mean_frp_mw": (
                    round(e.mean_frp_mw, 4) if e.mean_frp_mw is not None else None
                ),
                "max_frp_mw": (
                    round(e.max_frp_mw, 4) if e.max_frp_mw is not None else None
                ),
            }
            for e in sorted_events
        ]

        canonical_sources = [
            {
                "source_id": s.source_id,
                "linked_event_ids": sorted(s.linked_event_ids),
                "total_event_count": s.total_event_count,
                "first_seen_at": s.first_seen_at.isoformat(),
                "last_seen_at": s.last_seen_at.isoformat(),
                "centroid_lat": round(s.centroid_geometry.latitude, 6),
                "centroid_lon": round(s.centroid_geometry.longitude, 6),
                "active_days_count": s.active_days_count,
                "persistence_state": s.persistence_state.value,
                "recurrence_ratio": (
                    round(s.recurrence_ratio, 4)
                    if s.recurrence_ratio is not None
                    else None
                ),
            }
            for s in sorted_sources
        ]

        payload = {
            "detection_dataset_id": self.detection_dataset_id,
            "detection_dataset_hash": self.detection_dataset_hash,
            "study_area_id": self.study_area_id,
            "config_fingerprint": self.config_fingerprint,
            "spatial_cluster_radius_meters": self.spatial_cluster_radius_meters,
            "temporal_window_hours": self.temporal_window_hours,
            "persistent_source_radius_meters": self.persistent_source_radius_meters,
            "events": canonical_events,
            "persistent_sources": canonical_sources,
        }

        json_bytes = json.dumps(
            payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()


class RealEnrichedEventDataset(BaseDomainModel):
    """Canonical container for contextually enriched events and reference labels (ML-012)."""

    dataset_id: str = Field(
        default="ds_real_enriched_v1.0.0",
        min_length=1,
        description="Unique identifier for the enriched event dataset.",
    )
    dataset_version: str = Field(
        default="v1.0.0",
        min_length=1,
        description="Semantic version of the enriched event dataset.",
    )
    source_detection_dataset_id: str = Field(
        ...,
        description="Originating detection dataset ID (e.g. ds_real_firms_v1.0.0).",
    )
    source_detection_dataset_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 digest of originating detection dataset.",
    )
    source_event_dataset_id: str = Field(
        ...,
        description="Originating thermal event dataset ID (e.g. ds_real_events_v1.0.0).",
    )
    source_event_dataset_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 digest of originating thermal event dataset.",
    )
    study_area_id: str = Field(
        ...,
        description="Identifier of study area (e.g. jamnagar_kutch).",
    )
    study_area_name: str = Field(
        ...,
        description="Human-readable study area title.",
    )
    bounding_box: BoundingBox = Field(
        ...,
        description="Geographic WGS-84 spatial bounding envelope.",
    )
    events: list[Event] = Field(
        default_factory=list,
        description="Deterministically ordered canonical Event domain objects.",
    )
    persistent_sources: list[PersistentSource] = Field(
        default_factory=list,
        description="Deterministically ordered canonical PersistentSource objects.",
    )
    context_evidence: list[ContextEvidence] = Field(
        default_factory=list,
        description="Associated external contextual evidence records.",
    )
    reference_evidence: list[ReferenceEvidence] = Field(
        default_factory=list,
        description="Synthesized reference evidence claims with quality tiers.",
    )
    reference_labels: list[LabelDecision] = Field(
        default_factory=list,
        description="Auditable adjudicated label decisions for prediction targets.",
    )
    context_snapshot_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="SHA-256 content hashes of external context source snapshots.",
    )
    config_fingerprint: str = Field(
        ...,
        description="SHA-256 fingerprint of governing ScientificConfig.",
    )
    canonical_dataset_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Deterministic SHA-256 hash across sorted events, context, and labels.",
    )
    data_status: str = Field(
        default="OFFLINE_FIXTURE",
        description="Data provenance tier: REAL, OFFLINE_FIXTURE, or SYNTHETIC.",
    )
    created_at: UtcDatetime = Field(
        ...,
        description="Timestamp when enriched dataset was compiled in UTC.",
    )
    processing_version: str = Field(
        default="v1.0.0",
        description="Version of contextual enrichment & label adjudication pipeline.",
    )

    def compute_canonical_hash(self) -> str:
        """Compute deterministic SHA-256 hash across sorted events, context, and labels."""
        import hashlib
        import json

        sorted_events = sorted(
            self.events,
            key=lambda e: (
                e.started_at.isoformat(),
                e.centroid_geometry.latitude,
                e.centroid_geometry.longitude,
                e.event_id,
            ),
        )
        sorted_sources = sorted(
            self.persistent_sources,
            key=lambda s: (
                s.first_seen_at.isoformat(),
                s.centroid_geometry.latitude,
                s.centroid_geometry.longitude,
                s.source_id,
            ),
        )
        sorted_context = sorted(
            self.context_evidence,
            key=lambda c: (
                c.source_type,
                c.context_id,
                c.distance_to_event_meters or 0.0,
            ),
        )
        sorted_ref = sorted(
            self.reference_evidence,
            key=lambda r: (r.entity_id, r.source_name, r.evidence_id),
        )
        sorted_labels = sorted(
            self.reference_labels,
            key=lambda l: (l.target_id, l.entity_id, l.decision_id),
        )

        canonical_events = [
            {
                "event_id": e.event_id,
                "detection_ids": sorted(e.detection_ids),
                "started_at": e.started_at.isoformat(),
                "centroid_lat": round(e.centroid_geometry.latitude, 6),
                "centroid_lon": round(e.centroid_geometry.longitude, 6),
            }
            for e in sorted_events
        ]

        canonical_context = [
            {
                "context_id": c.context_id,
                "source_type": c.source_type,
                "context_type": c.context_type.value,
                "distance_to_event_meters": (
                    round(c.distance_to_event_meters, 2)
                    if c.distance_to_event_meters is not None
                    else None
                ),
                "facility_name": c.facility_name,
            }
            for c in sorted_context
        ]

        canonical_ref = [
            {
                "evidence_id": r.evidence_id,
                "entity_id": r.entity_id,
                "source_name": r.source_name,
                "claim_class": r.claim_class,
                "tier": r.tier.value,
                "confidence_score": round(r.confidence_score, 4),
            }
            for r in sorted_ref
        ]

        canonical_labels = [
            {
                "decision_id": l.decision_id,
                "target_id": l.target_id,
                "entity_id": l.entity_id,
                "assigned_class": l.assigned_class,
                "label_tier": l.label_tier.value,
                "confidence_score": round(l.confidence_score, 4),
                "has_conflicting_evidence": l.has_conflicting_evidence,
                "is_train_eligible": l.is_train_eligible,
            }
            for l in sorted_labels
        ]

        payload = {
            "source_detection_dataset_id": self.source_detection_dataset_id,
            "source_detection_dataset_hash": self.source_detection_dataset_hash,
            "source_event_dataset_id": self.source_event_dataset_id,
            "source_event_dataset_hash": self.source_event_dataset_hash,
            "study_area_id": self.study_area_id,
            "config_fingerprint": self.config_fingerprint,
            "data_status": self.data_status,
            "context_snapshot_hashes": {
                k: self.context_snapshot_hashes[k]
                for k in sorted(self.context_snapshot_hashes.keys())
            },
            "events": canonical_events,
            "sources": [s.source_id for s in sorted_sources],
            "context_evidence": canonical_context,
            "reference_evidence": canonical_ref,
            "reference_labels": canonical_labels,
        }

        json_bytes = json.dumps(
            payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
