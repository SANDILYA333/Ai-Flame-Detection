"""Authoritative Agricultural & Non-Industrial Ground-Truth Ingestion Layer (DATA-002).

Provides an auditable, provenance-preserving boundary for ingesting external ground truth
registries (e.g. ICAR crop residue burning records, PAU agricultural surveys, state fire registries)
and deterministically matching them to physical thermal events without geographic auto-labeling,
circularity, or missingness-to-negative conversion.
"""

import csv
import hashlib
import json
import math
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.data.firms.activation import _audit_no_secrets
from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.common import BaseDomainModel, Coordinate, UtcDatetime
from packages.schemas.enums import SourceRole
from packages.schemas.event import Event
from packages.schemas.ml import (
    LabelProvenanceType,
    LabelTier,
    ReferenceEvidence,
)


class ExternalReferenceRecord(BaseDomainModel):
    """Canonical representation of an external ground-truth observation record."""

    source_id: str
    source_name: str
    source_type: str  # e.g. "AUTHORITATIVE_REGISTRY", "AGRICULTURAL_SURVEY", "GOVERNMENT_MONITORING"
    source_record_id: str
    observed_at: UtcDatetime
    geometry: Coordinate
    claim_class: str  # "industrial", "non_industrial", "crop_residue", "wildfire"
    confidence: float
    tier: LabelTier = LabelTier.TIER_A_AUTHORITATIVE_GT
    source_snapshot_hash: str
    metadata: dict[str, Any] = {}


class GroundTruthIngestionService:
    """Service ingesting authoritative reference datasets and matching them to physical events."""

    @classmethod
    def load_ground_truth_from_json(
        cls,
        json_path: Path | str,
    ) -> tuple[list[ExternalReferenceRecord], str]:
        """Load external ground truth records from a structured JSON snapshot file.

        Args:
            json_path: Path to external ground truth JSON fixture.

        Returns:
            tuple[list[ExternalReferenceRecord], str]:
                List of validated ExternalReferenceRecord objects and file SHA-256 hash.
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {path}")

        raw_bytes = path.read_bytes()
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        data = json.loads(raw_bytes.decode("utf-8"))
        _audit_no_secrets(data)

        source_metadata = data.get("source_metadata", {})
        source_id = source_metadata.get("source_id", path.stem)
        source_name = source_metadata.get("source_name", "Authoritative Ground Truth")
        source_type = source_metadata.get("source_type", "AUTHORITATIVE_REGISTRY")
        raw_tier_str = source_metadata.get("tier", LabelTier.TIER_A_AUTHORITATIVE_GT.value)
        default_tier = LabelTier(raw_tier_str)

        records: list[ExternalReferenceRecord] = []
        for item in data.get("records", []):
            obs_at_raw = item.get("observed_at") or item.get("observation_date")
            if isinstance(obs_at_raw, str):
                if len(obs_at_raw) == 10:
                    obs_at = datetime.strptime(obs_at_raw, "%Y-%m-%d").replace(tzinfo=UTC)
                else:
                    obs_at = datetime.fromisoformat(obs_at_raw.replace("Z", "+00:00"))
            elif isinstance(obs_at_raw, datetime):
                obs_at = obs_at_raw
            else:
                raise ValueError(f"Invalid observation timestamp in record: {item}")

            rec_tier_str = item.get("tier", default_tier.value)
            rec_tier = LabelTier(rec_tier_str)

            rec = ExternalReferenceRecord(
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                source_record_id=str(item["source_record_id"]),
                observed_at=obs_at,
                geometry=Coordinate(
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                ),
                claim_class=str(item.get("classification") or item.get("claim_class")),
                confidence=float(item.get("confidence", 1.0)),
                tier=rec_tier,
                source_snapshot_hash=file_hash,
                metadata=item.get("metadata", {}),
            )
            records.append(rec)

        # Deterministic sorting
        records.sort(key=lambda r: (r.source_id, r.source_record_id, r.observed_at))
        return records, file_hash

    @classmethod
    def match_events_to_ground_truth(
        cls,
        events: Sequence[Event],
        ground_truth_records: Sequence[ExternalReferenceRecord],
        max_distance_meters: float = 2000.0,
        max_temporal_delta_hours: float = 24.0,
    ) -> list[ReferenceEvidence]:
        """Match physical thermal events against external ground-truth records.

        Enforces strict matching tolerances (geodesic distance and UTC time delta).

        Args:
            events: Physical thermal events from RealThermalEventDataset.
            ground_truth_records: Validated external ground-truth records.
            max_distance_meters: Maximum geodesic match distance in meters.
            max_temporal_delta_hours: Maximum absolute temporal difference in hours.

        Returns:
            list[ReferenceEvidence]: Matched, canonical ReferenceEvidence items.
        """
        matched_evidence: list[ReferenceEvidence] = []
        max_delta_sec = max_temporal_delta_hours * 3600.0

        for ev in events:
            ev_lat = ev.centroid_geometry.latitude
            ev_lon = ev.centroid_geometry.longitude
            ev_time = ev.started_at

            for gt in ground_truth_records:
                # 1. Temporal matching
                gt_time = gt.observed_at
                time_delta_sec = abs((ev_time - gt_time).total_seconds())
                if time_delta_sec > max_delta_sec:
                    continue

                # 2. Geodesic spatial matching
                dist_m = haversine_distance_meters(
                    ev_lat,
                    ev_lon,
                    gt.geometry.latitude,
                    gt.geometry.longitude,
                )
                if dist_m > max_distance_meters:
                    continue

                # 3. Class mapping
                raw_class = gt.claim_class.lower()
                canonical_class: str
                if raw_class in ("non_industrial", "agricultural", "crop_residue", "stubble_burn", "wildfire"):
                    canonical_class = "non_industrial"
                elif raw_class in ("industrial", "refinery_flare", "power_plant", "steel_mill"):
                    canonical_class = "industrial"
                else:
                    canonical_class = raw_class

                # 4. Deterministic evidence ID
                raw_sig = (
                    f"{ev.event_id}:{gt.source_id}:{gt.source_record_id}:"
                    f"{canonical_class}:{gt.tier.value}"
                )
                ev_digest = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()
                evidence_id = f"ref_gt_{ev_digest[:20]}"

                prov_type = (
                    LabelProvenanceType.GROUND_TRUTH
                    if gt.tier == LabelTier.TIER_A_AUTHORITATIVE_GT
                    else LabelProvenanceType.REFERENCE_LABEL
                )

                evidence = ReferenceEvidence(
                    evidence_id=evidence_id,
                    source_name=gt.source_name,
                    source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
                    entity_id=ev.event_id,
                    geometry=Coordinate(
                        latitude=gt.geometry.latitude,
                        longitude=gt.geometry.longitude,
                    ),
                    observed_at=gt.observed_at,
                    claim_class=canonical_class,
                    confidence_score=gt.confidence,
                    tier=gt.tier,
                    provenance_type=prov_type,
                    evidence_payload={
                        "ground_truth_source_id": gt.source_id,
                        "ground_truth_source_name": gt.source_name,
                        "ground_truth_source_type": gt.source_type,
                        "source_record_id": gt.source_record_id,
                        "distance_meters": dist_m,
                        "temporal_delta_seconds": time_delta_sec,
                        "source_snapshot_hash": gt.source_snapshot_hash,
                        "raw_claim_class": gt.claim_class,
                        "metadata": gt.metadata,
                    },
                    notes=(
                        f"Matched to {gt.source_name} ({gt.source_record_id}) "
                        f"at {dist_m:.1f}m distance and {time_delta_sec/3600.0:.2f}h time delta."
                    ),
                )
                matched_evidence.append(evidence)

        # Deterministic sorting
        matched_evidence.sort(
            key=lambda e: (
                e.entity_id,
                e.tier.value,
                e.source_name,
                e.evidence_id,
            )
        )
        return matched_evidence
