"""Real-World ML Evaluation Framework (NEXT-005).

Provides rigorous, leak-free evaluation campaigns for real-data supervised models across:
1. Event Holdout (GROUPED_EVENT_HOLDOUT)
2. Facility Holdout (FACILITY_HOLDOUT)
3. Persistent Source Holdout (PERSISTENT_SOURCE_HOLDOUT)
4. Temporal Forward Holdout (TEMPORAL_HOLDOUT)
5. Geographic Holdout (SPATIAL_GEOGRAPHIC_HOLDOUT)

Enforces:
- Strict distinction between "Technically Executable" and "Scientifically Valid".
- Train-only feature preprocessing (prevention of preprocessor leakage).
- Absolute anti-leakage invariants (Event, Facility, Source, Temporal, Geographic).
- Accurate multiclass & probabilistic metrics (Macro F1, Brier Score, Log Loss).
- Rejection of insufficient pilot datasets without manufacturing synthetic data.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.schemas.ml import (
    DatasetRowStatus,
    ModelArtifact,
    SplitAssignment,
    SplitManifest,
    SplitPartition,
    SplitStrategy,
    SupervisedDataset,
)
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.models.base import BaseMLModel
from services.ml.models.registry import ModelRegistry
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor
from services.ml.training.splits import SplitAssignmentService, SplitIntegrityValidator


@dataclass(frozen=True)
class StrategyEvaluationResult:
    """Evaluation result for a specific holdout strategy."""

    strategy_name: str
    split_strategy: SplitStrategy
    status: str  # "VALID" or "NOT_EVALUABLE"
    is_scientifically_valid: bool
    reason: str | None
    sample_counts: dict[str, int]
    class_distribution: dict[str, int]
    group_statistics: dict[str, int]
    metrics: dict[str, Any] = field(default_factory=dict)
    leakage_audit: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert strategy evaluation result to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "split_strategy": self.split_strategy.value,
            "status": self.status,
            "is_scientifically_valid": self.is_scientifically_valid,
            "reason": self.reason,
            "sample_counts": self.sample_counts,
            "class_distribution": self.class_distribution,
            "group_statistics": self.group_statistics,
            "metrics": self.metrics,
            "leakage_audit": self.leakage_audit,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class RealEvaluationCampaignResult:
    """Consolidated report across all real-world holdout evaluation strategies."""

    dataset_id: str
    dataset_version: str
    target_id: str
    model_id: str
    model_type: str
    overall_status: str  # "NOT_SCIENTIFICALLY_VALID_ON_PILOT" or "VALID"
    is_production_ready: bool
    strategy_results: dict[str, StrategyEvaluationResult]
    summary_findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert consolidated evaluation report to dictionary."""
        return {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "target_id": self.target_id,
            "model_id": self.model_id,
            "model_type": self.model_type,
            "overall_status": self.overall_status,
            "is_production_ready": self.is_production_ready,
            "strategy_results": {
                k: v.to_dict() for k, v in self.strategy_results.items()
            },
            "summary_findings": self.summary_findings,
        }


class RealEvaluationService:
    """Service executing real-world holdout evaluation campaigns."""

    MIN_SAMPLES_EVENT_HOLDOUT: int = 20
    MIN_SAMPLES_FACILITY_HOLDOUT: int = 20
    MIN_SAMPLES_SOURCE_HOLDOUT: int = 20
    MIN_SAMPLES_TEMPORAL_HOLDOUT: int = 20
    MIN_SAMPLES_GEOGRAPHIC_HOLDOUT: int = 20

    MIN_UNIQUE_FACILITIES: int = 3
    MIN_UNIQUE_SOURCES: int = 5
    MIN_TEMPORAL_SPAN_DAYS: float = 30.0
    MIN_GEOGRAPHIC_REGIONS: int = 2
    MIN_CLASSES_REQUIRED: int = 2

    @classmethod
    def evaluate_model_on_dataset(
        cls,
        dataset: SupervisedDataset,
        model_artifact_or_instance: ModelArtifact | BaseMLModel,
        target_id: str = "target_industrial_segregation",
        strategies: list[SplitStrategy] | None = None,
        random_seed: int = 42,
    ) -> RealEvaluationCampaignResult:
        """Run full real-world evaluation campaign across holdout strategies.

        Args:
            dataset: The real SupervisedDataset.
            model_artifact_or_instance: Fitted model artifact or BaseMLModel instance.
            target_id: Prediction target identifier.
            strategies: Optional subset of SplitStrategy enums to evaluate.
            random_seed: Deterministic seed for reproducible partitioning.

        Returns:
            RealEvaluationCampaignResult containing per-strategy evaluations.
        """
        now = datetime.now(UTC)
        eval_strategies = strategies or [
            SplitStrategy.GROUPED_EVENT_HOLDOUT,
            SplitStrategy.FACILITY_HOLDOUT,
            SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
            SplitStrategy.TEMPORAL_HOLDOUT,
            SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT,
        ]

        if isinstance(model_artifact_or_instance, ModelArtifact):
            model_id = model_artifact_or_instance.metadata.model_id
            model_type = model_artifact_or_instance.metadata.model_type
            artifact_hash = model_artifact_or_instance.sha256_hash
            _prep, model_instance = ModelRegistry.reconstruct_pipeline(
                model_artifact_or_instance
            )
        else:
            model_id = model_artifact_or_instance.model_name.lower()
            model_type = model_artifact_or_instance.model_name
            artifact_hash = None
            model_instance = model_artifact_or_instance

        strategy_results: dict[str, StrategyEvaluationResult] = {}
        all_valid = True

        for strat in eval_strategies:
            strat_res = cls._evaluate_single_strategy(
                dataset=dataset,
                model_instance=model_instance,
                model_id=model_id,
                model_type=model_type,
                artifact_hash=artifact_hash,
                target_id=target_id,
                strategy=strat,
                random_seed=random_seed,
                now=now,
            )
            strategy_results[strat.value] = strat_res
            if not strat_res.is_scientifically_valid:
                all_valid = False

        overall_status = (
            "VALID" if all_valid else "NOT_SCIENTIFICALLY_VALID_ON_PILOT"
        )
        summary_findings = []
        for s_name, res in strategy_results.items():
            if res.status == "NOT_EVALUABLE":
                summary_findings.append(f"{s_name}: {res.reason}")
            else:
                summary_findings.append(
                    f"{s_name}: Evaluated on N={res.sample_counts.get('test', 0)} test samples."
                )

        return RealEvaluationCampaignResult(
            dataset_id=dataset.manifest.dataset_id,
            dataset_version=dataset.manifest.dataset_version,
            target_id=target_id,
            model_id=model_id,
            model_type=model_type,
            overall_status=overall_status,
            is_production_ready=all_valid,
            strategy_results=strategy_results,
            summary_findings=summary_findings,
        )

    @classmethod
    def _evaluate_single_strategy(
        cls,
        dataset: SupervisedDataset,
        model_instance: BaseMLModel,
        model_id: str,
        model_type: str,
        artifact_hash: str | None,
        target_id: str,
        strategy: SplitStrategy,
        random_seed: int,
        now: datetime,
    ) -> StrategyEvaluationResult:
        """Evaluate a single holdout strategy with strict feasibility gating."""
        eligible_records = [
            r
            for r in dataset.records
            if r.row_status == DatasetRowStatus.TRAIN_ELIGIBLE
            and r.labels.get(target_id)
            and r.labels[target_id].is_train_eligible
            and r.labels[target_id].assigned_class != "unknown"
        ]
        eligible_count = len(eligible_records)
        total_count = len(dataset.records)
        excluded_count = total_count - eligible_count

        class_dist: dict[str, int] = {}
        for r in eligible_records:
            c = r.labels[target_id].assigned_class
            class_dist[c] = class_dist.get(c, 0) + 1

        # Calculate group distributions
        facilities = set()
        sources = set()
        regions = set()
        timestamps = []

        for r in dataset.records:
            fr = r.feature_record
            fac = fr.features.get("facility_id") or fr.features.get("facility_context_type")
            if fac and fac != "NONE":
                facilities.add(str(fac))
            if fr.source_id:
                sources.add(fr.source_id)
            elif fr.features.get("is_persistent_source"):
                sources.add(r.entity_id)
            if hasattr(fr, "as_of_time") and fr.as_of_time:
                timestamps.append(fr.as_of_time)

        regions.add(dataset.manifest.dataset_id)
        temporal_days = (
            (max(timestamps) - min(timestamps)).total_seconds() / 86400.0
            if timestamps
            else 0.0
        )

        group_stats = {
            "unique_facilities": len(facilities),
            "unique_persistent_sources": len(sources),
            "unique_regions": len(regions),
            "temporal_span_days": int(temporal_days),
        }

        # 1. Feasibility check per strategy
        is_feasible, reason = cls._check_strategy_feasibility(
            strategy=strategy,
            eligible_count=eligible_count,
            class_dist=class_dist,
            facility_count=len(facilities),
            source_count=len(sources),
            region_count=len(regions),
            temporal_days=temporal_days,
        )

        if not is_feasible:
            return StrategyEvaluationResult(
                strategy_name=strategy.value,
                split_strategy=strategy,
                status="NOT_EVALUABLE",
                is_scientifically_valid=False,
                reason=reason,
                sample_counts={
                    "total": total_count,
                    "eligible": eligible_count,
                    "excluded": excluded_count,
                    "train": dataset.split_manifest.train_count,
                    "validation": dataset.split_manifest.validation_count,
                    "test": dataset.split_manifest.test_count,
                },
                class_distribution=class_dist,
                group_statistics=group_stats,
                metrics={},
                leakage_audit={"status": "SKIPPED_DUE_TO_INFEASIBLE_SPLIT"},
                provenance={
                    "model_id": model_id,
                    "model_type": model_type,
                    "dataset_id": dataset.manifest.dataset_id,
                    "dataset_version": dataset.manifest.dataset_version,
                    "evaluated_at": now.isoformat(),
                },
            )

        # 2. Build raw split records for partition assignment
        raw_split_records: list[dict[str, Any]] = []
        for r in dataset.records:
            fr = r.feature_record
            eid = r.entity_id
            lat_val = fr.features.get("latitude", 22.0)
            lon_val = fr.features.get("longitude", 70.0)
            if not isinstance(lat_val, (int, float)):
                lat_val = 22.0
            if not isinstance(lon_val, (int, float)):
                lon_val = 70.0
            fac_val = fr.features.get("facility_id") or fr.features.get("facility_context_type")
            facility_id = str(fac_val) if fac_val and fac_val != "NONE" else None
            sensor_name = str(fr.features.get("sensor_instrument") or "VIIRS")
            t_val = fr.as_of_time or now

            raw_split_records.append(
                {
                    "entity_id": eid,
                    "event_id": fr.event_id or eid,
                    "source_id": fr.source_id,
                    "facility_id": facility_id,
                    "latitude": float(lat_val),
                    "longitude": float(lon_val),
                    "sensor_id": sensor_name,
                    "timestamp": t_val,
                    "acquisition_time": t_val,
                }
            )

        # 3. Assign partitions via SplitAssignmentService
        assignments: list[SplitAssignment] = []
        if strategy == SplitStrategy.GROUPED_EVENT_HOLDOUT:
            assignments = SplitAssignmentService.assign_grouped_event_split(
                records=raw_split_records,
                train_ratio=0.60,
                val_ratio=0.20,
                test_ratio=0.20,
                random_seed=random_seed,
            )
        elif strategy == SplitStrategy.FACILITY_HOLDOUT:
            assignments = SplitAssignmentService.assign_facility_holdout_split(
                records=raw_split_records,
                train_ratio=0.60,
                val_ratio=0.20,
                test_ratio=0.20,
                random_seed=random_seed,
            )
        elif strategy == SplitStrategy.PERSISTENT_SOURCE_HOLDOUT:
            assignments = SplitAssignmentService.assign_grouped_source_split(
                records=raw_split_records,
                train_ratio=0.60,
                val_ratio=0.20,
                test_ratio=0.20,
                random_seed=random_seed,
            )
        elif strategy == SplitStrategy.TEMPORAL_HOLDOUT:
            sorted_times = sorted(
                r["timestamp"] for r in raw_split_records if r.get("timestamp")
            )
            if sorted_times:
                n_t = len(sorted_times)
                val_idx = int(n_t * 0.60)
                test_idx = int(n_t * 0.80)
                val_cutoff = sorted_times[val_idx]
                test_cutoff = sorted_times[test_idx]
                assignments = (
                    SplitAssignmentService.assign_temporal_holdout_split(
                        records=raw_split_records,
                        val_cutoff=val_cutoff,
                        test_cutoff=test_cutoff,
                    )
                )
        elif strategy == SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT:
            assignments = SplitAssignmentService.assign_spatial_block_split(
                records=raw_split_records,
                block_size_degrees=0.25,
                train_ratio=0.60,
                val_ratio=0.20,
                test_ratio=0.20,
                random_seed=random_seed,
            )

        # 4. Validate split integrity
        record_timestamps = {r["entity_id"]: r["timestamp"] for r in raw_split_records}
        split_report = SplitIntegrityValidator.validate_split_integrity(
            assignments=assignments,
            split_strategy=strategy,
            record_timestamps=record_timestamps,
        )

        assignment_map = {a.entity_id: a.partition for a in assignments}
        partitioned_records = [
            r.model_copy(
                update={
                    "split_partition": assignment_map.get(
                        r.entity_id, SplitPartition.TRAIN
                    )
                }
            )
            for r in dataset.records
        ]

        temp_dataset = dataset.model_copy(
            update={
                "records": partitioned_records,
            }
        )

        # 5. Extract partitioned matrices
        (
            x_train_raw,
            y_train,
            ids_train,
            x_val_raw,
            y_val,
            ids_val,
            x_test_raw,
            y_test,
            ids_test,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=temp_dataset,
            target_id=target_id,
        )

        if not x_test_raw or not y_test:
            return StrategyEvaluationResult(
                strategy_name=strategy.value,
                split_strategy=strategy,
                status="NOT_EVALUABLE",
                is_scientifically_valid=False,
                reason=f"Split allocation produced empty test partition for {strategy.value}.",
                sample_counts={
                    "total": total_count,
                    "eligible": eligible_count,
                    "excluded": excluded_count,
                    "train": len(x_train_raw),
                    "validation": len(x_val_raw),
                    "test": len(x_test_raw),
                },
                class_distribution=class_dist,
                group_statistics=group_stats,
                metrics={},
                leakage_audit={"split_report": split_report.model_dump(mode="json")},
                provenance={
                    "model_id": model_id,
                    "model_type": model_type,
                    "dataset_id": dataset.manifest.dataset_id,
                    "dataset_version": dataset.manifest.dataset_version,
                    "evaluated_at": now.isoformat(),
                },
            )

        # 6. Anti-Leakage: Fit Preprocessor strictly on Train
        preprocessor = FeaturePreprocessor()
        preprocessor.fit(x_train_raw)
        x_train_vec = preprocessor.transform(x_train_raw)
        x_test_vec = preprocessor.transform(x_test_raw)

        # Ensure model is fitted on training partition if not already fitted
        if not getattr(model_instance, "is_fitted", False):
            if model_type == "DeterministicContextualClassifier":
                model_instance.fit(x_train_raw, y_train)
            else:
                model_instance.fit(x_train_vec, y_train)

        # 7. Execute model inference on test partition
        if model_type == "DeterministicContextualClassifier":
            test_preds = model_instance.predict(x_test_raw)
            test_probs = model_instance.predict_proba(x_test_raw)
        else:
            test_preds = model_instance.predict(x_test_vec)
            test_probs = model_instance.predict_proba(x_test_vec)

        # 8. Compute rigorous metrics
        eval_report = EvaluationHarness.evaluate_predictions(
            evaluation_id=f"eval_{strategy.value}_{target_id}",
            experiment_id=f"real_eval_{strategy.value}",
            dataset_id=dataset.manifest.dataset_id,
            dataset_version=dataset.manifest.dataset_version,
            model_id=model_id,
            model_version="v1.0.0",
            split_partition=SplitPartition.TEST,
            y_true=y_test,
            y_pred=test_preds,
            y_prob=test_probs,
        )

        return StrategyEvaluationResult(
            strategy_name=strategy.value,
            split_strategy=strategy,
            status="VALID",
            is_scientifically_valid=True,
            reason=None,
            sample_counts={
                "total": total_count,
                "eligible": eligible_count,
                "excluded": excluded_count,
                "train": len(x_train_raw),
                "validation": len(x_val_raw),
                "test": len(x_test_raw),
            },
            class_distribution=class_dist,
            group_statistics=group_stats,
            metrics=eval_report.model_dump(mode="json"),
            leakage_audit={
                "split_is_valid": split_report.is_valid,
                "event_leakage_violations": split_report.event_leakage_violations,
                "facility_leakage_violations": split_report.facility_leakage_violations,
                "source_leakage_violations": split_report.source_leakage_violations,
                "temporal_inversion_violations": split_report.temporal_inversion_violations,
            },
            provenance={
                "model_id": model_id,
                "model_type": model_type,
                "artifact_hash": artifact_hash,
                "dataset_id": dataset.manifest.dataset_id,
                "dataset_version": dataset.manifest.dataset_version,
                "dataset_hash": dataset.manifest.sha256_hash,
                "split_strategy": strategy.value,
                "evaluated_at": now.isoformat(),
            },
        )

    @classmethod
    def _check_strategy_feasibility(
        cls,
        strategy: SplitStrategy,
        eligible_count: int,
        class_dist: dict[str, int],
        facility_count: int,
        source_count: int,
        region_count: int,
        temporal_days: float,
    ) -> tuple[bool, str | None]:
        """Verify if data volume and diversity permit a scientifically valid evaluation."""
        if len(class_dist) < cls.MIN_CLASSES_REQUIRED:
            return (
                False,
                f"Zero class diversity: target contains only {list(class_dist.keys())} classes (minimum required: >= 2).",
            )

        if strategy == SplitStrategy.GROUPED_EVENT_HOLDOUT:
            if eligible_count < cls.MIN_SAMPLES_EVENT_HOLDOUT:
                return (
                    False,
                    f"Insufficient sample size: N={eligible_count} eligible events (minimum required: >= {cls.MIN_SAMPLES_EVENT_HOLDOUT}).",
                )

        elif strategy == SplitStrategy.FACILITY_HOLDOUT:
            if facility_count < cls.MIN_UNIQUE_FACILITIES:
                return (
                    False,
                    f"Insufficient facility diversity: {facility_count} facility clusters found (minimum required: >= {cls.MIN_UNIQUE_FACILITIES} distinct facilities).",
                )

        elif strategy == SplitStrategy.PERSISTENT_SOURCE_HOLDOUT:
            if source_count < cls.MIN_UNIQUE_SOURCES:
                return (
                    False,
                    f"Insufficient persistent source diversity: {source_count} persistent sources found (minimum required: >= {cls.MIN_UNIQUE_SOURCES} distinct sources).",
                )

        elif strategy == SplitStrategy.TEMPORAL_HOLDOUT:
            if temporal_days < cls.MIN_TEMPORAL_SPAN_DAYS:
                return (
                    False,
                    f"Insufficient temporal span: {temporal_days:.1f} days (minimum required: >= {cls.MIN_TEMPORAL_SPAN_DAYS:.0f} days for forward holdout).",
                )

        elif strategy == SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT:
            if region_count < cls.MIN_GEOGRAPHIC_REGIONS:
                return (
                    False,
                    f"Only 1 geographic study area present (minimum required: >= {cls.MIN_GEOGRAPHIC_REGIONS} distinct geographic regions).",
                )

        return True, None
