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

from packages.context.models import ContextFeature
from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.common import BaseDomainModel, Coordinate, UtcDatetime
from packages.schemas.enums import ContextType, SourceRole
from packages.schemas.event import Event
from packages.schemas.ml import (
    LabelProvenanceType,
    LabelTier,
    ReferenceEvidence,
)

SENSITIVE_KEY_PATTERNS = (
    "map_key",
    "token",
    "secret",
    "password",
    "api_key",
    "credential",
    "private_key",
    "authorization",
)


def _audit_no_secrets(obj: Any, path: str = "") -> None:
    """Recursively verify no credentials exist in ground truth records."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = str(k).lower()
            for pattern in SENSITIVE_KEY_PATTERNS:
                if pattern in k_lower:
                    raise ValueError(
                        f"Prohibited sensitive key '{k}' found at path '{path}.{k}'"
                    )
            _audit_no_secrets(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _audit_no_secrets(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        lower_str = obj.lower()
        if "bearer " in lower_str or "firms_map_key" in lower_str:
            raise ValueError(
                f"Prohibited credential token detected in value at '{path}'"
            )


def _parse_timestamp(val: Any) -> datetime:
    """Parse various timestamp representations into UTC datetime."""
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=UTC)
    if isinstance(val, str):
        cleaned = val.strip().replace("Z", "+00:00")
        if len(cleaned) == 10 and cleaned.count("-") == 2:
            return datetime.strptime(cleaned, "%Y-%m-%d").replace(tzinfo=UTC)
        return datetime.fromisoformat(cleaned)
    raise ValueError(f"Cannot parse timestamp value: {val}")


class ExternalReferenceRecord(BaseDomainModel):
    """Canonical representation of an external ground-truth observation record."""

    source_id: str
    source_name: str
    source_type: str  # e.g. "AUTHORITATIVE_REGISTRY", "AGRICULTURAL_SURVEY", "GOVERNMENT_MONITORING"
    source_record_id: str
    observed_at: UtcDatetime
    geometry: Coordinate
    claim_class: str  # "industrial", "non_industrial", "crop_residue", "wildfire", "bushfire", etc.
    confidence: float
    country: str = "India"
    region: str = "N/A"
    fire_regime: str = "agricultural"  # "industrial", "agricultural", "forest_natural", "grassland_savanna", "other_natural"
    tier: LabelTier = LabelTier.TIER_A_AUTHORITATIVE
    source_snapshot_hash: str
    metadata: dict[str, Any] = {}


class GroundTruthIngestionService:
    """Service ingesting authoritative reference datasets and matching them to physical events."""

    @classmethod
    def load_ground_truth_from_json(
        cls,
        json_path: Path | str,
    ) -> tuple[list[ExternalReferenceRecord], str]:
        """Load external ground truth records from a structured JSON snapshot file."""
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
        raw_tier_str = source_metadata.get("tier", LabelTier.TIER_A_AUTHORITATIVE.value)
        default_tier = LabelTier(raw_tier_str)

        records: list[ExternalReferenceRecord] = []
        for item in data.get("records", []):
            obs_at_raw = item.get("observed_at") or item.get("observation_date")
            obs_at = _parse_timestamp(obs_at_raw)

            rec_tier_str = item.get("tier", default_tier.value)
            rec_tier = LabelTier(rec_tier_str)
            item_meta = item.get("metadata", {})

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
                country=str(item.get("country", item_meta.get("country", "India"))),
                region=str(item.get("region", item_meta.get("region", item_meta.get("district", "N/A")))),
                fire_regime=str(item.get("fire_regime", item_meta.get("fire_regime", "agricultural"))),
                tier=rec_tier,
                source_snapshot_hash=file_hash,
                metadata=item_meta,
            )
            records.append(rec)

        records.sort(key=lambda r: (r.source_id, r.source_record_id, r.observed_at))
        return records, file_hash

    @classmethod
    def load_ground_truth_from_csv(
        cls,
        csv_path: Path | str,
        source_id: str | None = None,
        source_name: str | None = None,
        default_tier: LabelTier = LabelTier.TIER_A_AUTHORITATIVE,
    ) -> tuple[list[ExternalReferenceRecord], str]:
        """Load external ground truth records from a CSV file."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground truth CSV file not found: {path}")

        raw_bytes = path.read_bytes()
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(text.splitlines())
        if not reader.fieldnames:
            return [], file_hash

        resolved_source_id = source_id or path.stem
        resolved_source_name = source_name or f"Ground Truth CSV ({path.stem})"

        records: list[ExternalReferenceRecord] = []
        for idx, row in enumerate(reader):
            cleaned = {k.strip().lower(): v.strip() for k, v in row.items() if k and v is not None}
            if "latitude" not in cleaned or "longitude" not in cleaned:
                continue

            rec_id = cleaned.get("source_record_id") or cleaned.get("id") or f"row_{idx:05d}"
            obs_raw = cleaned.get("observed_at") or cleaned.get("acq_date") or cleaned.get("date") or "2026-08-01"
            obs_at = _parse_timestamp(obs_raw)

            tier_str = cleaned.get("tier", default_tier.value)
            tier = LabelTier(tier_str) if tier_str in [t.value for t in LabelTier] else default_tier
            claim_cls = cleaned.get("claim_class") or cleaned.get("classification") or cleaned.get("regime") or "non_industrial"
            conf = float(cleaned.get("confidence", 1.0))
            country = cleaned.get("country", "India")
            region = cleaned.get("region", "N/A")
            regime = cleaned.get("fire_regime") or cleaned.get("regime") or "agricultural"

            rec = ExternalReferenceRecord(
                source_id=resolved_source_id,
                source_name=resolved_source_name,
                source_type="CSV_REGISTRY",
                source_record_id=str(rec_id),
                observed_at=obs_at,
                geometry=Coordinate(
                    latitude=float(cleaned["latitude"]),
                    longitude=float(cleaned["longitude"]),
                ),
                claim_class=claim_cls,
                confidence=conf,
                country=country,
                region=region,
                fire_regime=regime,
                tier=tier,
                source_snapshot_hash=file_hash,
                metadata=cleaned,
            )
            records.append(rec)

        records.sort(key=lambda r: (r.source_id, r.source_record_id, r.observed_at))
        return records, file_hash

    @classmethod
    def load_ground_truth_from_geojson(
        cls,
        geojson_path: Path | str,
        source_id: str | None = None,
        source_name: str | None = None,
        default_tier: LabelTier = LabelTier.TIER_A_AUTHORITATIVE,
    ) -> tuple[list[ExternalReferenceRecord], str]:
        """Load external ground truth records from a GeoJSON FeatureCollection."""
        path = Path(geojson_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground truth GeoJSON file not found: {path}")

        raw_bytes = path.read_bytes()
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        data = json.loads(raw_bytes.decode("utf-8"))
        _audit_no_secrets(data)

        resolved_source_id = source_id or data.get("source_metadata", {}).get("source_id", path.stem)
        resolved_source_name = source_name or data.get("source_metadata", {}).get("source_name", f"GeoJSON Reference ({path.stem})")

        records: list[ExternalReferenceRecord] = []
        features = data.get("features", [])
        for idx, feat in enumerate(features):
            geom = feat.get("geometry", {})
            props = feat.get("properties", {})
            geom_type = geom.get("type", "Point")
            coords = geom.get("coordinates", [0.0, 0.0])

            lat: float
            lon: float
            if geom_type == "Point":
                lon, lat = float(coords[0]), float(coords[1])
            elif geom_type in ("Polygon", "MultiPolygon"):
                # Centroid approximation
                poly_coords = coords[0] if geom_type == "Polygon" else coords[0][0]
                lons = [c[0] for c in poly_coords]
                lats = [c[1] for c in poly_coords]
                lon, lat = sum(lons) / len(lons), sum(lats) / len(lats)
            else:
                continue

            rec_id = props.get("source_record_id") or feat.get("id") or f"feat_{idx:05d}"
            obs_raw = props.get("observed_at") or props.get("observation_date") or props.get("date") or "2026-08-01"
            obs_at = _parse_timestamp(obs_raw)

            tier_str = props.get("tier", default_tier.value)
            tier = LabelTier(tier_str) if tier_str in [t.value for t in LabelTier] else default_tier
            claim_cls = props.get("claim_class") or props.get("classification") or "non_industrial"
            conf = float(props.get("confidence", 1.0))
            country = props.get("country", "India")
            region = props.get("region", "N/A")
            regime = props.get("fire_regime") or props.get("regime") or "agricultural"

            rec = ExternalReferenceRecord(
                source_id=resolved_source_id,
                source_name=resolved_source_name,
                source_type="GEOJSON_REGISTRY",
                source_record_id=str(rec_id),
                observed_at=obs_at,
                geometry=Coordinate(latitude=lat, longitude=lon),
                claim_class=claim_cls,
                confidence=conf,
                country=country,
                region=region,
                fire_regime=regime,
                tier=tier,
                source_snapshot_hash=file_hash,
                metadata=props,
            )
            records.append(rec)

        records.sort(key=lambda r: (r.source_id, r.source_record_id, r.observed_at))
        return records, file_hash

    @classmethod
    def load_ground_truth_auto(
        cls,
        path: Path | str,
    ) -> tuple[list[ExternalReferenceRecord], str]:
        """Automatically detect file format and load ground truth records."""
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix in (".geojson",):
            return cls.load_ground_truth_from_geojson(p)
        if suffix in (".csv",):
            return cls.load_ground_truth_from_csv(p)
        return cls.load_ground_truth_from_json(p)

    @classmethod
    def discover_and_load_catalog(
        cls,
        catalog_dirs: Sequence[Path | str] | Path | str,
    ) -> tuple[list[ExternalReferenceRecord], dict[str, str]]:
        """Recursively discover and load all ground truth files across directory paths."""
        dirs = [Path(catalog_dirs)] if isinstance(catalog_dirs, (str, Path)) else [Path(d) for d in catalog_dirs]
        all_records: list[ExternalReferenceRecord] = []
        file_hashes: dict[str, str] = {}
        seen_keys: set[tuple[str, str]] = set()

        for base_dir in dirs:
            if not base_dir.exists():
                continue
            for path in sorted(base_dir.glob("**/*")):
                if path.is_file() and path.suffix.lower() in (".json", ".geojson", ".csv") and "manifest" not in path.stem:
                    try:
                        records, f_hash = cls.load_ground_truth_auto(path)
                        file_hashes[str(path)] = f_hash
                        for r in records:
                            key = (r.source_id, r.source_record_id)
                            if key not in seen_keys:
                                seen_keys.add(key)
                                all_records.append(r)
                    except Exception as e:
                        continue

        all_records.sort(key=lambda r: (r.source_id, r.source_record_id, r.observed_at))
        return all_records, file_hashes

    @classmethod
    def load_facility_context_features(
        cls,
        facility_path_or_dir: Path | str,
    ) -> tuple[list[ContextFeature], dict[str, str]]:
        """Load industrial facility infrastructure context features with cryptographic hashing."""
        base_path = Path(facility_path_or_dir)
        features: list[ContextFeature] = []
        file_hashes: dict[str, str] = {}

        paths = [base_path] if base_path.is_file() else sorted(base_path.glob("**/*.json"))

        for p in paths:
            if not p.exists() or "manifest" in p.stem:
                continue
            raw_bytes = p.read_bytes()
            f_hash = hashlib.sha256(raw_bytes).hexdigest()
            file_hashes[str(p)] = f_hash
            try:
                data = json.loads(raw_bytes.decode("utf-8"))
                _audit_no_secrets(data)
                raw_features = data.get("features", [])
                for f in raw_features:
                    feat = ContextFeature(
                        feature_id=f["feature_id"],
                        provider=f.get("provider", "facility_registry"),
                        dataset_name=f.get("dataset_name", p.stem),
                        dataset_version=f.get("dataset_version", "v1.0.0"),
                        context_type=ContextType(f["context_type"]),
                        geometry=Coordinate(
                            latitude=float(f["latitude"]),
                            longitude=float(f["longitude"]),
                        ),
                        facility_name=f.get("facility_name", f.get("name")),
                        raw_metadata={str(k): str(v) for k, v in f.get("metadata", {}).items()},
                    )
                    features.append(feat)
            except Exception:
                continue

        return features, file_hashes

    @classmethod
    def match_events_to_ground_truth(
        cls,
        events: Sequence[Event],
        ground_truth_records: Sequence[ExternalReferenceRecord],
        max_distance_meters: float = 2000.0,
        max_temporal_delta_hours: float = 24.0,
    ) -> list[ReferenceEvidence]:
        """Deterministically match physical events to external ground truth records."""
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

                # 3. Class mapping across industrial and non-industrial regimes
                raw_class = gt.claim_class.lower()
                canonical_class: str
                if raw_class in (
                    "non_industrial",
                    "agricultural",
                    "crop_residue",
                    "stubble_burn",
                    "wildfire",
                    "forest_fire",
                    "bushfire",
                    "grassland",
                    "savanna",
                    "natural_fire",
                ):
                    canonical_class = "non_industrial"
                elif raw_class in (
                    "industrial",
                    "refinery_flare",
                    "refinery",
                    "power_plant",
                    "steel_mill",
                    "smelter",
                    "gas_oil_separation_plant",
                    "chemical_plant",
                    "flaring",
                    "coal_mining",
                    "petrochemical",
                ):
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
                    if gt.tier == LabelTier.TIER_A_AUTHORITATIVE
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

        matched_evidence.sort(
            key=lambda e: (
                e.entity_id,
                e.tier.value,
                e.source_name,
                e.evidence_id,
            )
        )
        return matched_evidence

