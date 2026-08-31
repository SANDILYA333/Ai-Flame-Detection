"""Feature dataset builder and materialization service for SIH26162 Phase 4 ML.

Assembles, audits, and materializes reproducible, versioned, and content-addressable
FeatureDataset objects from upstream events and dependencies, enforcing showcase
isolation (DATASET-003) and deterministic content hashing.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from packages.schemas.common import ProvenanceReference, UtcDatetime
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.event import Event
from packages.schemas.ml import (
    DatasetManifest,
    FeatureDataset,
    FeatureDefinition,
    FeatureGroup,
    FeatureRecord,
    SplitStrategy,
)
from packages.schemas.source import PersistentSource
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.registry import FeatureRegistry
from services.ml.features.standard_set import (
    STANDARD_FEATURE_VERSION,
    get_standard_feature_registry,
)
from services.ml.training.dataset import DatasetBuilder


class FeatureDatasetBuilder:
    """Builder constructing validated, content-hashed FeatureDataset instances."""

    def __init__(self, registry: FeatureRegistry | None = None) -> None:
        self.registry = registry or get_standard_feature_registry()
        self.extractor = FeatureExtractor(registry=self.registry)

    def extract_and_build_dataset(
        self,
        dataset_id: str,
        dataset_version: str,
        target_id: str,
        geographic_scope: str,
        temporal_start: UtcDatetime,
        temporal_end: UtcDatetime,
        split_strategy: SplitStrategy,
        event_tuples: Sequence[
            tuple[
                Event,
                Sequence[Detection],
                datetime,
                Sequence[Event] | None,
                PersistentSource | None,
                Sequence[ContextEvidence] | None,
            ]
        ],
        feature_set_version: str = STANDARD_FEATURE_VERSION,
        label_set_version: str = "label_v1.0.0",
        allowed_feature_names: Sequence[str] | None = None,
        isolated_showcase_ids: Sequence[str] | None = None,
        provenance: ProvenanceReference | None = None,
    ) -> FeatureDataset:
        """Extract features for multiple events and assemble a FeatureDataset.

        Args:
            dataset_id: Canonical identifier for the dataset.
            dataset_version: Version string for this dataset build.
            target_id: Prediction target definition ID.
            geographic_scope: Geographic study area identifier or bbox string.
            temporal_start: Earliest observation boundary in UTC.
            temporal_end: Latest observation boundary in UTC.
            split_strategy: Evaluation partition strategy.
            event_tuples: Sequence of (event, detections, as_of_time, preceding_events,
                source, context_evidence) tuples.
            feature_set_version: Version identifier for feature definitions.
            label_set_version: Version identifier for reference labels.
            allowed_feature_names: Optional whitelist of feature names to extract.
            isolated_showcase_ids: List of entity IDs permanently isolated from splits.
            provenance: Lineage reference.

        Returns:
            FeatureDataset: Fully validated and content-hashed feature dataset.
        """
        records: list[FeatureRecord] = []
        for (
            event,
            detections,
            as_of_time,
            preceding,
            source,
            context,
        ) in event_tuples:
            rec = self.extractor.extract_features_for_event(
                event=event,
                member_detections=detections,
                as_of_time=as_of_time,
                preceding_events=preceding,
                source=source,
                context_evidence=context,
                allowed_feature_names=allowed_feature_names,
                provenance=provenance,
            )
            records.append(rec)

        return self.build_from_records(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            target_id=target_id,
            geographic_scope=geographic_scope,
            temporal_start=temporal_start,
            temporal_end=temporal_end,
            split_strategy=split_strategy,
            records=records,
            feature_set_version=feature_set_version,
            label_set_version=label_set_version,
            isolated_showcase_ids=isolated_showcase_ids,
            provenance=provenance,
        )

    def build_from_records(
        self,
        dataset_id: str,
        dataset_version: str,
        target_id: str,
        geographic_scope: str,
        temporal_start: UtcDatetime,
        temporal_end: UtcDatetime,
        split_strategy: SplitStrategy,
        records: Sequence[FeatureRecord],
        feature_set_version: str = STANDARD_FEATURE_VERSION,
        label_set_version: str = "label_v1.0.0",
        isolated_showcase_ids: Sequence[str] | None = None,
        provenance: ProvenanceReference | None = None,
    ) -> FeatureDataset:
        """Construct a FeatureDataset from pre-extracted FeatureRecord instances."""
        isolated_set = set(isolated_showcase_ids or [])

        # 1. Filter showcase records from benchmark records
        benchmark_records = [r for r in records if r.entity_id not in isolated_set]

        # 2. Sort deterministically by entity_id
        sorted_records = sorted(benchmark_records, key=lambda r: r.entity_id)

        # 3. Convert to dictionary representation for content hashing
        # and duplicate auditing
        raw_dict_records: list[dict[str, Any]] = []
        for r in sorted_records:
            entry = {
                "entity_id": r.entity_id,
                "prediction_unit": r.prediction_unit.value,
                "as_of_time": r.as_of_time.isoformat(),
                "event_id": r.event_id,
                "source_id": r.source_id,
                "features": r.features,
            }
            raw_dict_records.append(entry)

        # 4. Duplicate Record Auditing
        duplicate_violations = DatasetBuilder.audit_duplicates(raw_dict_records)
        if duplicate_violations:
            dup_details = [v.to_dict() for v in duplicate_violations]
            raise ValueError(
                f"Duplicate records detected in feature dataset: {dup_details}"
            )

        # 5. Deterministic Content Hashing
        content_hash = DatasetBuilder.compute_records_hash(raw_dict_records)

        # 6. Build Manifest
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            target_id=target_id,
            feature_set_version=feature_set_version,
            label_set_version=label_set_version,
            geographic_scope=geographic_scope,
            temporal_start=temporal_start,
            temporal_end=temporal_end,
            split_strategy=split_strategy,
            record_count=len(sorted_records),
            sha256_hash=content_hash,
            created_at=datetime.now(UTC),
            provenance=provenance,
        )

        # 7. Collect Feature Definitions and Groups
        feature_names: set[str] = set()
        for r in sorted_records:
            feature_names.update(r.features.keys())

        matched_definitions: list[FeatureDefinition] = []
        feature_groups: dict[str, list[str]] = {}

        for name in sorted(feature_names):
            try:
                defn = self.registry.get(name)
                matched_definitions.append(defn)
                group_name = defn.feature_group.value
                if group_name not in feature_groups:
                    feature_groups[group_name] = []
                feature_groups[group_name].append(name)
            except Exception:
                # Default group if unregistered
                group_name = FeatureGroup.THERMAL_CORE.value
                if group_name not in feature_groups:
                    feature_groups[group_name] = []
                feature_groups[group_name].append(name)

        # 8. Compute Summary Diagnostics
        summary_stats = self._compute_summary_statistics(
            sorted_records, list(feature_names)
        )

        return FeatureDataset(
            manifest=manifest,
            records=sorted_records,
            feature_definitions=matched_definitions,
            feature_groups=feature_groups,
            summary_statistics=summary_stats,
        )

    @staticmethod
    def _compute_summary_statistics(
        records: list[FeatureRecord],
        feature_names: list[str],
    ) -> dict[str, Any]:
        """Compute missingness rates and distribution summaries across records."""
        total_rows = len(records)
        missingness_by_feature: dict[str, dict[str, Any]] = {}

        for fname in sorted(feature_names):
            missing_count = sum(1 for r in records if r.features.get(fname) is None)
            present_count = total_rows - missing_count
            missing_pct = (
                float(missing_count / total_rows * 100.0) if total_rows > 0 else 0.0
            )

            missingness_by_feature[fname] = {
                "present_count": present_count,
                "missing_count": missing_count,
                "missing_percentage": round(missing_pct, 2),
            }

        return {
            "total_records": total_rows,
            "total_features": len(feature_names),
            "missingness_by_feature": missingness_by_feature,
        }
