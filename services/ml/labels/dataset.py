"""Supervised dataset assembly and leakage-safe splitting service for Phase 4 ML.

Merges ML-002 FeatureDatasets with ML-003 LabelDecisions, executes deterministic
group-aware, spatial, or temporal holdout splitting, audits split integrity, and
materializes content-addressable SupervisedDataset containers.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from packages.schemas.common import ProvenanceReference
from packages.schemas.ml import (
    DatasetRowStatus,
    ExclusionReason,
    FeatureDataset,
    FeatureRecord,
    LabelDecision,
    LabeledFeatureRecord,
    LabelProvenanceType,
    LabelTier,
    SplitAssignment,
    SplitManifest,
    SplitPartition,
    SplitStrategy,
    SupervisedDataset,
    TargetDefinition,
)
from services.ml.features.standard_set import (
    STANDARD_FEATURE_VERSION,
    get_standard_feature_registry,
)
from services.ml.labels.targets import get_standard_target_registry
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from packages.data.firms.schemas import RealDetectionDataset
    from packages.schemas.context import ContextEvidence
    from packages.schemas.detection import Detection
    from packages.schemas.event import Event, RealEnrichedEventDataset
    from packages.schemas.source import PersistentSource


class SupervisedDatasetBuilder:
    """Builder assembling supervised feature-label datasets with leakage-safe splits."""

    def __init__(
        self,
        targets: dict[str, TargetDefinition] | None = None,
    ) -> None:
        self.targets = targets or get_standard_target_registry()

    def build_from_real_enriched_dataset(
        self,
        enriched_dataset: RealEnrichedEventDataset,
        detection_dataset: RealDetectionDataset,
        split_strategy: SplitStrategy = SplitStrategy.FACILITY_HOLDOUT,
        target_ids: Sequence[str] | None = None,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        dataset_id: str = "ds_real_supervised_v1.0.0",
        dataset_version: str = "v1.0.0",
        feature_set_version: str = STANDARD_FEATURE_VERSION,
        label_set_version: str = "label_v1.0.0",
        isolated_showcase_ids: Sequence[str] | None = None,
        provenance: ProvenanceReference | None = None,
    ) -> SupervisedDataset:
        """Assemble a SupervisedDataset directly from real enriched observations.

        Executes the canonical DATASET-002 bridge:
        RealEnrichedEventDataset + RealDetectionDataset
          -> FeatureDatasetBuilder (30 approved features as of T_pred)
          -> SupervisedDatasetBuilder (reference labels & leakage-safe splitting)
        """
        active_target_ids = (
            list(target_ids) if target_ids else ["target_industrial_segregation"]
        )

        # 1. Index member detections by detection_id
        detections_by_id = {d.detection_id: d for d in detection_dataset.detections}

        # 2. Map persistent sources by linked event IDs
        source_by_event_id: dict[str, PersistentSource] = {}
        for source in enriched_dataset.persistent_sources:
            for ev_id in source.linked_event_ids:
                source_by_event_id[ev_id] = source

        # 3. Map context evidence per event via reference_evidence and spatial verification
        context_id_to_event_id: dict[str, str] = {}
        for ref in enriched_dataset.reference_evidence:
            ctx_id = ref.evidence_payload.get("contributing_context_id")
            if ctx_id:
                context_id_to_event_id[ctx_id] = ref.entity_id

        context_by_event_id: dict[str, list[ContextEvidence]] = {}
        for c_item in enriched_dataset.context_evidence:
            matched_ev_id = context_id_to_event_id.get(c_item.context_id)
            if matched_ev_id:
                context_by_event_id.setdefault(matched_ev_id, []).append(c_item)

        # 4. Build event tuples for FeatureDatasetBuilder
        event_tuples: list[
            tuple[
                Event,
                Sequence[Detection],
                datetime,
                Sequence[Event] | None,
                PersistentSource | None,
                Sequence[ContextEvidence] | None,
            ]
        ] = []
        for ev in enriched_dataset.events:
            member_dets: list[Detection] = [
                detections_by_id[d_id]
                for d_id in ev.detection_ids
                if d_id in detections_by_id
            ]
            if not member_dets:
                continue

            as_of = ev.started_at
            preceding: list[Event] = [
                e
                for e in enriched_dataset.events
                if e.ended_at < ev.started_at and e.event_id != ev.event_id
            ]
            src = source_by_event_id.get(ev.event_id)
            ctx_items: Sequence[ContextEvidence] = context_by_event_id.get(
                ev.event_id, []
            )

            event_tuples.append((ev, member_dets, as_of, preceding, src, ctx_items))

        # 5. Extract features using FeatureDatasetBuilder (FEAT-001 / FEAT-003)
        from services.ml.features.builder import FeatureDatasetBuilder

        feature_builder = FeatureDatasetBuilder(
            registry=get_standard_feature_registry()
        )
        feature_dataset = feature_builder.extract_and_build_dataset(
            dataset_id=f"feat_{dataset_id}",
            dataset_version=dataset_version,
            target_id=active_target_ids[0],
            geographic_scope=enriched_dataset.study_area_id,
            temporal_start=(
                enriched_dataset.events[0].started_at
                if enriched_dataset.events
                else datetime.now(UTC)
            ),
            temporal_end=(
                enriched_dataset.events[-1].ended_at
                if enriched_dataset.events
                else datetime.now(UTC)
            ),
            split_strategy=split_strategy,
            event_tuples=event_tuples,
            feature_set_version=feature_set_version,
            label_set_version=label_set_version,
            isolated_showcase_ids=isolated_showcase_ids,
            provenance=provenance
            or ProvenanceReference(
                source=enriched_dataset.dataset_id,
                source_snapshot_id=enriched_dataset.dataset_version,
            ),
        )

        # 6. Index reference labels by target_id
        labels_by_target: dict[str, Sequence[LabelDecision]] = {}
        raw_labels_by_target: dict[str, list[LabelDecision]] = {}
        custom_exclusions: dict[str, ExclusionReason] = {}

        for lbl in enriched_dataset.reference_labels:
            if lbl.target_id in active_target_ids:
                raw_labels_by_target.setdefault(lbl.target_id, []).append(lbl)
                # Enforce Missing != Negative and train-eligibility
                if not lbl.is_train_eligible or lbl.assigned_class == "unknown":
                    custom_exclusions[lbl.entity_id] = (
                        ExclusionReason.CONFLICTING_LABEL_EVIDENCE
                        if lbl.has_conflicting_evidence
                        else ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE
                    )

        for tid, l_list in raw_labels_by_target.items():
            labels_by_target[tid] = l_list

        # 7. Assemble final SupervisedDataset
        return self.build_supervised_dataset(
            feature_dataset=feature_dataset,
            label_decisions_by_target=labels_by_target,
            split_strategy=split_strategy,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_seed=random_seed,
            isolated_showcase_ids=isolated_showcase_ids,
            custom_exclusions=custom_exclusions,
            provenance=provenance,
        )

    def build_supervised_dataset(
        self,
        feature_dataset: FeatureDataset,
        label_decisions_by_target: dict[str, Sequence[LabelDecision]],
        split_strategy: SplitStrategy = SplitStrategy.GROUPED_EVENT_HOLDOUT,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        isolated_showcase_ids: Sequence[str] | None = None,
        custom_exclusions: dict[str, ExclusionReason] | None = None,
        provenance: ProvenanceReference | None = None,
    ) -> SupervisedDataset:
        """Assemble a complete SupervisedDataset with leakage-safe partition splits.

        Args:
            feature_dataset: Source FeatureDataset with features and manifest.
            label_decisions_by_target: Target ID to sequence of LabelDecisions.
            split_strategy: Partitioning strategy.
            train_ratio: Proportion of data allocated to training.
            val_ratio: Proportion allocated to validation.
            test_ratio: Proportion allocated to test holdout.
            random_seed: Deterministic random seed for hashing.
            isolated_showcase_ids: Showcase entity IDs isolated from benchmark.
            custom_exclusions: Optional mapping of entity_id to ExclusionReason.
            provenance: Lineage reference.

        Returns:
            SupervisedDataset: Fully validated supervised dataset with SplitManifest.
        """
        now = datetime.now(UTC)
        showcase_set = set(isolated_showcase_ids or [])
        exclusion_map = dict(custom_exclusions or {})

        # Index label decisions by (target_id, entity_id)
        labels_by_target_and_entity: dict[str, dict[str, LabelDecision]] = {}
        for target_id, decisions in label_decisions_by_target.items():
            labels_by_target_and_entity[target_id] = {d.entity_id: d for d in decisions}

        # 1. Merge Features and Labels into raw records for splitting
        raw_split_records: list[dict[str, Any]] = []
        entity_feature_map: dict[str, FeatureRecord] = {}

        for feat_rec in feature_dataset.records:
            eid = feat_rec.entity_id
            entity_feature_map[eid] = feat_rec

            lat_raw = feat_rec.features.get("latitude")
            lon_raw = feat_rec.features.get("longitude")
            if isinstance(lat_raw, (int, float, str)) and isinstance(
                lon_raw, (int, float, str)
            ):
                lat_val = float(lat_raw)
                lon_val = float(lon_raw)
            elif feat_rec.event_id:
                # Derive deterministic geographic grid coordinates from event_id
                ev_hash = int(
                    hashlib.sha256(feat_rec.event_id.encode()).hexdigest()[:6], 16
                )
                lat_val = 20.0 + ((ev_hash % 20) * 0.25)
                lon_val = 68.0 + (((ev_hash >> 6) % 20) * 0.25)
            else:
                lat_val = 22.0
                lon_val = 70.0

            sensor_name = str(
                feat_rec.features.get("sensor_instrument")
                or feat_rec.features.get("satellite")
                or "VIIRS"
            )

            raw_split_records.append(
                {
                    "entity_id": eid,
                    "event_id": feat_rec.event_id or eid,
                    "source_id": feat_rec.source_id,
                    "facility_id": (
                        feat_rec.features.get("facility_context_type")
                        if feat_rec.features.get("facility_context_type") != "NONE"
                        else None
                    ),
                    "latitude": lat_val,
                    "longitude": lon_val,
                    "sensor_id": sensor_name,
                    "timestamp": feat_rec.as_of_time,
                    "acquisition_time": feat_rec.as_of_time,
                }
            )

        # 2. Assign Partitions via SplitAssignmentService
        assignments: list[SplitAssignment] = []
        if split_strategy == SplitStrategy.GROUPED_EVENT_HOLDOUT:
            assignments = SplitAssignmentService.assign_grouped_event_split(
                records=raw_split_records,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                random_seed=random_seed,
                isolated_showcase_ids=list(showcase_set),
            )
        elif split_strategy == SplitStrategy.PERSISTENT_SOURCE_HOLDOUT:
            assignments = SplitAssignmentService.assign_grouped_source_split(
                records=raw_split_records,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                random_seed=random_seed,
                isolated_showcase_ids=list(showcase_set),
            )
        elif split_strategy == SplitStrategy.FACILITY_HOLDOUT:
            assignments = SplitAssignmentService.assign_facility_holdout_split(
                records=raw_split_records,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                random_seed=random_seed,
                isolated_showcase_ids=list(showcase_set),
            )
        elif split_strategy == SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT:
            assignments = SplitAssignmentService.assign_spatial_block_split(
                records=raw_split_records,
                block_size_degrees=0.25,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                random_seed=random_seed,
                isolated_showcase_ids=list(showcase_set),
            )
        elif split_strategy == SplitStrategy.SOURCE_SENSOR_HOLDOUT:
            assignments = SplitAssignmentService.assign_source_sensor_split(
                records=raw_split_records,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                random_seed=random_seed,
                isolated_showcase_ids=list(showcase_set),
            )
        elif split_strategy == SplitStrategy.TEMPORAL_HOLDOUT:
            timestamps = [
                r["timestamp"]
                for r in raw_split_records
                if r.get("timestamp") and r["entity_id"] not in showcase_set
            ]
            if timestamps:
                t_min = min(timestamps)
                t_max = max(timestamps)
                span = t_max - t_min
                val_cutoff = t_min + (span * train_ratio)
                test_cutoff = t_min + (span * (train_ratio + val_ratio))
            else:
                t_start = feature_dataset.manifest.temporal_start
                t_end = feature_dataset.manifest.temporal_end
                span = t_end - t_start
                val_cutoff = t_start + (span * train_ratio)
                test_cutoff = t_start + (span * (train_ratio + val_ratio))

            assignments = SplitAssignmentService.assign_temporal_holdout_split(
                records=raw_split_records,
                val_cutoff=val_cutoff,
                test_cutoff=test_cutoff,
                isolated_showcase_ids=list(showcase_set),
            )
        else:
            # Default to grouped event holdout
            assignments = SplitAssignmentService.assign_grouped_event_split(
                records=raw_split_records,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                random_seed=random_seed,
                isolated_showcase_ids=list(showcase_set),
            )

        # 3. Validate Split Integrity
        record_timestamps = {
            str(r.get("entity_id") or r.get("id", "")): (
                r["timestamp"]
                if isinstance(r.get("timestamp"), datetime)
                else datetime.fromisoformat(str(r.get("timestamp")))
                if r.get("timestamp")
                else now
            )
            for r in raw_split_records
        }
        integrity_report = SplitIntegrityValidator.validate_split_integrity(
            assignments=assignments,
            split_strategy=split_strategy,
            record_timestamps=record_timestamps,
        )

        if not integrity_report.is_valid:
            raise ValueError(
                f"Split integrity validation failed: "
                f"event_violations={integrity_report.event_leakage_violations}, "
                f"source_violations={integrity_report.source_leakage_violations}"
            )

        # 4. Assemble LabeledFeatureRecord collection
        assignment_map = {a.entity_id: a for a in assignments}
        labeled_records: list[LabeledFeatureRecord] = []

        train_count = 0
        val_count = 0
        test_count = 0
        showcase_count = 0
        excluded_count = 0

        target_ids = list(label_decisions_by_target.keys()) or list(self.targets.keys())

        for feat_rec in feature_dataset.records:
            eid = feat_rec.entity_id
            assign = assignment_map.get(eid)
            partition = assign.partition if assign else SplitPartition.TRAIN

            # Build label dictionary for all targets
            record_labels: dict[str, LabelDecision] = {}
            has_unlabeled = False
            has_conflict = False

            for tid in target_ids:
                if (
                    tid in labels_by_target_and_entity
                    and eid in labels_by_target_and_entity[tid]
                ):
                    record_labels[tid] = labels_by_target_and_entity[tid][eid]
                    if record_labels[tid].has_conflicting_evidence:
                        has_conflict = True
                else:
                    # Missing label for target -> synthesize UNKNOWN
                    record_labels[tid] = LabelDecision(
                        decision_id=f"dec_{tid}_{eid}_unlabeled",
                        target_id=tid,
                        entity_id=eid,
                        assigned_class="unknown",
                        label_tier=LabelTier.UNKNOWN,
                        provenance_type=LabelProvenanceType.UNKNOWN,
                        confidence_score=0.0,
                        contributing_evidence_ids=[],
                        has_conflicting_evidence=False,
                        is_train_eligible=False,
                        is_eval_eligible=False,
                        exclusion_reason=ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE,
                        decision_timestamp=now,
                    )
                    has_unlabeled = True

            # Determine row status and exclusion
            row_exclusion: ExclusionReason | None = None
            if eid in showcase_set:
                row_status = DatasetRowStatus.SHOWCASE_ISOLATED
                row_exclusion = ExclusionReason.SHOWCASE_ISOLATION
                showcase_count += 1
            elif eid in exclusion_map:
                row_status = DatasetRowStatus.EXCLUDED
                row_exclusion = exclusion_map[eid]
                excluded_count += 1
            elif has_conflict:
                row_status = DatasetRowStatus.EXCLUDED
                row_exclusion = ExclusionReason.CONFLICTING_LABEL_EVIDENCE
                excluded_count += 1
            elif has_unlabeled and all(
                d.assigned_class == "unknown" for d in record_labels.values()
            ):
                row_status = DatasetRowStatus.UNLABELED
                row_exclusion = ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE
                excluded_count += 1
            elif partition == SplitPartition.TRAIN:
                row_status = DatasetRowStatus.TRAIN_ELIGIBLE
                train_count += 1
            elif partition == SplitPartition.VALIDATION:
                row_status = DatasetRowStatus.VALIDATION_ELIGIBLE
                val_count += 1
            elif partition == SplitPartition.TEST:
                row_status = DatasetRowStatus.TEST_ELIGIBLE
                test_count += 1
            else:
                row_status = DatasetRowStatus.EXCLUDED
                excluded_count += 1

            labeled_records.append(
                LabeledFeatureRecord(
                    entity_id=eid,
                    feature_record=feat_rec,
                    labels=record_labels,
                    split_partition=partition,
                    row_status=row_status,
                    exclusion_reason=row_exclusion,
                )
            )

        # 5. Build SplitManifest
        split_manifest = SplitManifest(
            split_id=f"split_{feature_dataset.manifest.dataset_id}_{split_strategy.value}",
            dataset_id=feature_dataset.manifest.dataset_id,
            dataset_version=feature_dataset.manifest.dataset_version,
            split_strategy=split_strategy,
            random_seed=random_seed,
            train_count=train_count,
            validation_count=val_count,
            test_count=test_count,
            showcase_count=showcase_count,
            excluded_count=excluded_count,
            assignments=assignments,
            integrity_report=integrity_report,
            created_at=now,
        )

        # 6. Compute Comprehensive Summary Statistics
        summary_stats = self._compute_dataset_summary(
            labeled_records=labeled_records,
            split_manifest=split_manifest,
            target_ids=target_ids,
        )

        # 7. Collect matched TargetDefinitions
        matched_targets = [
            self.targets[tid] for tid in target_ids if tid in self.targets
        ]

        return SupervisedDataset(
            manifest=feature_dataset.manifest,
            split_manifest=split_manifest,
            records=labeled_records,
            target_definitions=matched_targets,
            feature_definitions=feature_dataset.feature_definitions,
            summary_statistics=summary_stats,
        )

    @staticmethod
    def _compute_dataset_summary(
        labeled_records: list[LabeledFeatureRecord],
        split_manifest: SplitManifest,
        target_ids: list[str],
    ) -> dict[str, Any]:
        """Compute diagnostic counts across classes, tiers, exclusions, and splits."""
        total_rows = len(labeled_records)

        class_distribution_by_target: dict[str, dict[str, int]] = {}
        tier_distribution_by_target: dict[str, dict[str, int]] = {}

        for tid in target_ids:
            class_counts: dict[str, int] = {}
            tier_counts: dict[str, int] = {}
            for r in labeled_records:
                dec = r.labels.get(tid)
                if dec:
                    cls_name = dec.assigned_class
                    tier_name = dec.label_tier.value
                    class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                    tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1
            class_distribution_by_target[tid] = class_counts
            tier_distribution_by_target[tid] = tier_counts

        exclusion_breakdown: dict[str, int] = {}
        for r in labeled_records:
            if r.exclusion_reason:
                reason_name = r.exclusion_reason.value
                exclusion_breakdown[reason_name] = (
                    exclusion_breakdown.get(reason_name, 0) + 1
                )

        return {
            "total_records": total_rows,
            "train_count": split_manifest.train_count,
            "validation_count": split_manifest.validation_count,
            "test_count": split_manifest.test_count,
            "showcase_count": split_manifest.showcase_count,
            "excluded_count": split_manifest.excluded_count,
            "class_distribution_by_target": class_distribution_by_target,
            "tier_distribution_by_target": tier_distribution_by_target,
            "exclusion_breakdown": exclusion_breakdown,
            "split_strategy": split_manifest.split_strategy.value,
        }
