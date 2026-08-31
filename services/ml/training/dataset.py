"""Dataset manifest builder and duplicate observation auditor for Phase 4 ML.

Builds reproducible, content-addressable dataset manifests with deterministic
SHA-256 content hashing, duplicate detection, and showcase event isolation.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from packages.schemas.common import ProvenanceReference, UtcDatetime
from packages.schemas.ml import (
    DatasetManifest,
    SplitStrategy,
)


class DuplicateRecordViolation:
    """Duplicate observation finding."""

    def __init__(
        self,
        duplicate_type: str,
        entity_ids: list[str],
        reason: str,
    ) -> None:
        self.duplicate_type = duplicate_type
        self.entity_ids = entity_ids
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "duplicate_type": self.duplicate_type,
            "entity_ids": sorted(self.entity_ids),
            "reason": self.reason,
        }


class DatasetBuilder:
    """Builder generating reproducible ML dataset manifests."""

    @staticmethod
    def compute_records_hash(records: list[dict[str, Any]]) -> str:
        """Compute a deterministic SHA-256 hash of dataset records.

        Records are sorted deterministically by entity_id before canonical
        JSON serialization to guarantee identical hashes across environments.
        """
        canonical_records = []
        for r in records:
            clean_r = {}
            for k in sorted(r.keys()):
                v = r[k]
                if isinstance(v, datetime):
                    clean_r[k] = v.isoformat()
                else:
                    clean_r[k] = v
            canonical_records.append(clean_r)

        def sort_key(rec: dict[str, Any]) -> str:
            return str(rec.get("entity_id") or rec.get("id") or rec.get("event_id", ""))

        canonical_records.sort(key=sort_key)

        canonical_json = json.dumps(
            canonical_records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def audit_duplicates(
        cls, records: list[dict[str, Any]]
    ) -> list[DuplicateRecordViolation]:
        """Detect duplicate entity records, space-time collisions, or duplicates."""
        violations: list[DuplicateRecordViolation] = []

        seen_entities: dict[str, int] = {}
        seen_spacetime: dict[str, list[str]] = {}

        for rec in records:
            eid = str(rec.get("entity_id") or rec.get("id", ""))
            if eid:
                seen_entities[eid] = seen_entities.get(eid, 0) + 1

            lat = rec.get("latitude")
            lon = rec.get("longitude")
            acq_time = rec.get("acquisition_time") or rec.get("timestamp")
            if lat is not None and lon is not None and acq_time is not None:
                st_key = f"{float(lat):.5f}_{float(lon):.5f}_{acq_time!s}"
                if st_key not in seen_spacetime:
                    seen_spacetime[st_key] = []
                seen_spacetime[st_key].append(eid)

        # 1. Entity duplicates
        dup_eids = [eid for eid, count in seen_entities.items() if count > 1]
        if dup_eids:
            violations.append(
                DuplicateRecordViolation(
                    duplicate_type="DUPLICATE_ENTITY_ID",
                    entity_ids=dup_eids,
                    reason=(f"Found {len(dup_eids)} duplicate entity IDs in records."),
                )
            )

        # 2. Exact space-time collisions
        for st_key, eids in seen_spacetime.items():
            if len(eids) > 1:
                violations.append(
                    DuplicateRecordViolation(
                        duplicate_type="SPACETIME_COLLISION",
                        entity_ids=eids,
                        reason=(f"Identical space-time coordinate: {st_key}"),
                    )
                )

        return violations

    @classmethod
    def build_manifest(
        cls,
        dataset_id: str,
        dataset_version: str,
        target_id: str,
        feature_set_version: str,
        label_set_version: str,
        geographic_scope: str,
        temporal_start: UtcDatetime,
        temporal_end: UtcDatetime,
        split_strategy: SplitStrategy,
        records: list[dict[str, Any]],
        provenance: ProvenanceReference | None = None,
        isolated_showcase_ids: list[str] | None = None,
    ) -> DatasetManifest:
        """Build and validate a content-addressable dataset manifest.

        Showcase records (DATASET-003) are isolated from benchmark splits.
        """
        isolated_set = set(isolated_showcase_ids or [])

        benchmark_records = [
            r
            for r in records
            if str(r.get("entity_id") or r.get("id", "")) not in isolated_set
        ]

        content_hash = cls.compute_records_hash(benchmark_records)

        return DatasetManifest(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            target_id=target_id,
            feature_set_version=feature_set_version,
            label_set_version=label_set_version,
            geographic_scope=geographic_scope,
            temporal_start=temporal_start,
            temporal_end=temporal_end,
            split_strategy=split_strategy,
            record_count=len(benchmark_records),
            sha256_hash=content_hash,
            created_at=datetime.now(UTC),
            provenance=provenance,
        )
