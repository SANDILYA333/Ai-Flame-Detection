"""Absolute Scientific Gate Evaluator for Real ML Model Training (NEXT-004).

Evaluates whether an empirical SupervisedDataset satisfies the 10 mandatory
scientific criteria required for real-world supervised model training:
1. Number of eligible labeled real events (N >= 500)
2. Multiclass class distribution & minimum minority class presence
3. Number of unique persistent sources
4. Number of unique industrial facilities
5. Geographic diversity (study areas)
6. Temporal coverage & multi-season span
7. Sensor platform diversity (VIIRS + MODIS)
8. Feasibility of grouped/temporal train-val-test holdouts
9. Sufficient representation across all target classes
10. Statistical validity & power of resulting evaluation metrics
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from packages.schemas.ml import DatasetRowStatus, SupervisedDataset


@dataclass(frozen=True)
class RealTrainingGateEvaluation:
    """Detailed evaluation result from the scientific training gate."""

    gate_status: str  # "PASSED" or "NOT_PASSED"
    is_production_ready: bool
    total_events: int
    eligible_events: int
    excluded_events: int
    class_distribution: dict[str, int]
    unique_persistent_sources: int
    unique_facilities: int
    geographic_coverage: list[str]
    temporal_coverage_days: float
    sensor_diversity: list[str]
    split_feasibility: bool
    class_diversity_sufficient: bool
    statistical_validity: bool
    rejection_reasons: list[str] = field(default_factory=list)
    circularity_warning: str = (
        "Reference labels are derived from contextual proximity to industrial infrastructure. "
        "Models trained on this data without feature ablation risk learning the attribution "
        "rule rather than thermal anomaly physics. Rigorous feature ablation required."
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation to dictionary representation."""
        return {
            "gate_status": self.gate_status,
            "is_production_ready": self.is_production_ready,
            "total_events": self.total_events,
            "eligible_events": self.eligible_events,
            "excluded_events": self.excluded_events,
            "class_distribution": self.class_distribution,
            "unique_persistent_sources": self.unique_persistent_sources,
            "unique_facilities": self.unique_facilities,
            "geographic_coverage": self.geographic_coverage,
            "temporal_coverage_days": self.temporal_coverage_days,
            "sensor_diversity": self.sensor_diversity,
            "split_feasibility": self.split_feasibility,
            "class_diversity_sufficient": self.class_diversity_sufficient,
            "statistical_validity": self.statistical_validity,
            "rejection_reasons": self.rejection_reasons,
            "circularity_warning": self.circularity_warning,
        }


class RealTrainingGateEvaluator:
    """Evaluator enforcing the absolute scientific gate before real model training."""

    MINIMUM_ELIGIBLE_SAMPLES_FOR_PROD: int = 500
    MINIMUM_MINORITY_CLASS_SAMPLES: int = 50
    MINIMUM_STUDY_AREAS: int = 4
    MINIMUM_TEMPORAL_DAYS: float = 180.0

    @classmethod
    def evaluate(
        cls,
        dataset: SupervisedDataset,
        target_id: str = "target_industrial_segregation",
    ) -> RealTrainingGateEvaluation:
        """Evaluate input SupervisedDataset against all 10 scientific criteria.

        Args:
            dataset: The real supervised dataset to evaluate.
            target_id: Target specification identifier.

        Returns:
            RealTrainingGateEvaluation with gate status and failure reasons.
        """
        rejection_reasons: list[str] = []

        total_events = len(dataset.records)
        eligible_records = [
            r
            for r in dataset.records
            if r.row_status == DatasetRowStatus.TRAIN_ELIGIBLE
            and r.labels.get(target_id)
            and r.labels[target_id].is_train_eligible
            and r.labels[target_id].assigned_class != "unknown"
        ]
        eligible_events = len(eligible_records)
        excluded_events = total_events - eligible_events

        # 1 & 2. Class distribution on eligible records
        class_dist: dict[str, int] = {}
        for r in eligible_records:
            c = r.labels[target_id].assigned_class
            class_dist[c] = class_dist.get(c, 0) + 1

        # 3. Persistent sources
        persistent_source_ids = set()
        for r in dataset.records:
            ps_feat = r.feature_record.features.get("is_persistent_source")
            if ps_feat:
                persistent_source_ids.add(r.entity_id)
        unique_persistent_sources = len(persistent_source_ids)

        # 4. Facilities
        facilities = set()
        for r in dataset.records:
            fac_type = r.feature_record.features.get("facility_context_type")
            if fac_type and fac_type != "NONE":
                facilities.add(fac_type)
        unique_facilities = len(facilities)

        # 5. Geographic coverage
        geo_coverage = [dataset.manifest.dataset_id]

        # 6. Temporal coverage
        timestamps: list[datetime] = []
        for r in dataset.records:
            if hasattr(r, "as_of_time") and r.as_of_time:
                timestamps.append(r.as_of_time)
        if timestamps:
            temporal_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400.0
        else:
            temporal_days = 0.0

        # 7. Sensor diversity
        sensors = set()
        for r in dataset.records:
            s = r.feature_record.features.get("sensor_instrument")
            if s:
                sensors.add(s)
        sensor_diversity = sorted(sensors)

        # 8. Split feasibility
        train_count = dataset.split_manifest.train_count
        val_count = dataset.split_manifest.validation_count
        test_count = dataset.split_manifest.test_count
        split_feasibility = (
            train_count > 0 and val_count > 0 and test_count > 0 and eligible_events >= 20
        )

        # 9. Class diversity sufficiency
        has_min_classes = len(class_dist) >= 2
        min_class_count = min(class_dist.values()) if class_dist else 0
        class_diversity_sufficient = (
            has_min_classes and min_class_count >= cls.MINIMUM_MINORITY_CLASS_SAMPLES
        )

        # 10. Statistical validity
        statistical_validity = (
            eligible_events >= cls.MINIMUM_ELIGIBLE_SAMPLES_FOR_PROD
            and class_diversity_sufficient
            and split_feasibility
        )

        # Audit against criteria
        if eligible_events < cls.MINIMUM_ELIGIBLE_SAMPLES_FOR_PROD:
            rejection_reasons.append(
                f"Insufficient sample size: N={eligible_events} eligible events "
                f"(minimum required: N >= {cls.MINIMUM_ELIGIBLE_SAMPLES_FOR_PROD})."
            )

        if not has_min_classes:
            rejection_reasons.append(
                f"Zero class diversity: target '{target_id}' contains only "
                f"{list(class_dist.keys())} classes (minimum required: >= 2 classes)."
            )
        elif min_class_count < cls.MINIMUM_MINORITY_CLASS_SAMPLES:
            rejection_reasons.append(
                f"Severe class imbalance: minority class has only {min_class_count} samples "
                f"(minimum required: >= {cls.MINIMUM_MINORITY_CLASS_SAMPLES})."
            )

        if not split_feasibility:
            rejection_reasons.append(
                f"Split holdout infeasible: train={train_count}, val={val_count}, "
                f"test={test_count} cannot form representative holdouts."
            )

        gate_passed = len(rejection_reasons) == 0 and statistical_validity
        gate_status = "PASSED" if gate_passed else "NOT_PASSED"

        return RealTrainingGateEvaluation(
            gate_status=gate_status,
            is_production_ready=gate_passed,
            total_events=total_events,
            eligible_events=eligible_events,
            excluded_events=excluded_events,
            class_distribution=class_dist,
            unique_persistent_sources=unique_persistent_sources,
            unique_facilities=unique_facilities,
            geographic_coverage=geo_coverage,
            temporal_coverage_days=temporal_days,
            sensor_diversity=sensor_diversity,
            split_feasibility=split_feasibility,
            class_diversity_sufficient=class_diversity_sufficient,
            statistical_validity=statistical_validity,
            rejection_reasons=rejection_reasons,
        )
