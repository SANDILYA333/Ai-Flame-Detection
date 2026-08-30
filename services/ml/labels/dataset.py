"""Supervised dataset assembly and leakage-safe splitting service for Phase 4 ML.

Merges ML-002 FeatureDatasets with ML-003 LabelDecisions, executes deterministic
group-aware, spatial, or temporal holdout splitting, audits split integrity, and
materializes content-addressable SupervisedDataset containers.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

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
from services.ml.labels.targets import get_standard_target_registry
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)


class SupervisedDatasetBuilder:
    """Builder assembling supervised feature-label datasets with leakage-safe splits."""

    def __init__(
        self,
        targets: dict[str, TargetDefinition] | None = None,
    ) -> None:
        self.targets = targets or get_standard_target_registry()

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

            raw_split_records.append(
                {
                    "entity_id": eid,
                    "event_id": feat_rec.event_id or eid,
                    "source_id": feat_rec.source_id,
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
        elif split_strategy == SplitStrategy.TEMPORAL_HOLDOUT:
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
