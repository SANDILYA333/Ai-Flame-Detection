"""Production ML Runtime Integration & Inference Service (NEXT-009).

Bridges the authoritative NEXT-008 deployment policy with the point-in-time
inference engine to execute deterministic, calibrated, and leak-free ML predictions.

Enforces:
1. Production artifact verification (strictly rejects pilot/unverified artifacts).
2. Operating mode resolution (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).
3. Canonical feature schema enforcement (feat_v1.0.0).
4. First-class calibrated abstention with UNKNOWN != NON_INDUSTRIAL guarantee.
5. High-throughput in-memory engine caching and safe failure handling.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from packages.schemas.ml import (
    AbstentionReason,
)
from services.ml.deployment.policy import (
    OperatingModePolicy,
    ProductionDeploymentPolicyService,
    ProductionOperatingMode,
)
from services.ml.features.extractor import FeatureExtractor

if TYPE_CHECKING:
    from collections.abc import Sequence

    from packages.schemas.common import UtcDatetime
    from packages.schemas.context import ContextEvidence
    from packages.schemas.detection import Detection
    from packages.schemas.event import Event
    from packages.schemas.source import PersistentSource
    from services.ml.inference.engine import MLInferenceEngine


@dataclass(frozen=True)
class ProductionPredictionResponse:
    """Structured, auditable production ML prediction result."""

    entity_id: str
    operating_mode: str
    model_name: str
    model_version: str
    feature_schema_version: str
    predicted_class: str
    assigned_class: str
    confidence: float
    threshold: float
    class_probabilities: dict[str, float]
    is_abstained: bool
    review_required: bool
    abstention_reason: str | None
    feature_count: int
    inference_timestamp: datetime
    latency_ms: float


class ProductionMLRuntimeService:
    """Production runtime service executing policy-governed ML inference."""

    _engine_cache: ClassVar[
        dict[str, tuple[MLInferenceEngine, OperatingModePolicy]]
    ] = {}

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached inference engines (useful for test isolation)."""
        cls._engine_cache.clear()

    @classmethod
    def get_or_load_engine(
        cls,
        mode: ProductionOperatingMode | str = (
            ProductionOperatingMode.HIGH_PRECISION
        ),
    ) -> tuple[MLInferenceEngine, OperatingModePolicy]:
        """Resolve and cache authorized MLInferenceEngine for an operating mode.

        Args:
            mode: Target ProductionOperatingMode.

        Returns:
            Tuple of (MLInferenceEngine, OperatingModePolicy).

        Raises:
            ValueError: If mode is invalid or artifact fails safety audit.
            FileNotFoundError: If required production artifact is missing.
        """
        try:
            op_mode = (
                ProductionOperatingMode(mode)
                if isinstance(mode, str)
                else mode
            )
        except ValueError as err:
            valid_modes = [m.value for m in ProductionOperatingMode]
            raise ValueError(
                f"Invalid operating mode: '{mode}'. Must be one of: {valid_modes}"
            ) from err

        mode_key = op_mode.value
        if mode_key not in cls._engine_cache:
            engine, policy = (
                ProductionDeploymentPolicyService.resolve_production_model(
                    op_mode
                )
            )
            cls._engine_cache[mode_key] = (engine, policy)

        return cls._engine_cache[mode_key]

    @classmethod
    def validate_feature_payload(
        cls,
        features: dict[str, Any],
        engine: MLInferenceEngine,
    ) -> None:
        """Validate feature dictionary completeness against canonical contract.

        Args:
            features: Input dictionary mapping feature name to value.
            engine: Resolved MLInferenceEngine instance.

        Raises:
            ValueError: If features dict is empty, missing keys, or malformed.
        """
        if not isinstance(features, dict) or not features:
            raise ValueError("Input feature dictionary cannot be empty or non-dict.")

        expected = set(engine.expected_feature_names)
        missing = expected - set(features.keys())
        if missing:
            missing_preview = sorted(missing)[:5]
            suffix = "..." if len(missing) > 5 else ""
            raise ValueError(
                f"Feature schema mismatch: {len(missing)} required feature(s) "
                f"missing: {missing_preview}{suffix}."
            )

    @classmethod
    def predict_features(
        cls,
        features: dict[str, Any],
        entity_id: str = "entity_inference",
        mode: ProductionOperatingMode | str = (
            ProductionOperatingMode.HIGH_PRECISION
        ),
        as_of_time: UtcDatetime | None = None,
    ) -> ProductionPredictionResponse:
        """Execute single-sample production inference under authorized policy.

        Args:
            features: Dictionary of engineered features.
            entity_id: Identifier of the sample entity.
            mode: Selected ProductionOperatingMode.
            as_of_time: Optional prediction timestamp cutoff.

        Returns:
            Structured ProductionPredictionResponse.
        """
        t0 = time.perf_counter()
        now = as_of_time or datetime.now(UTC)

        engine, policy = cls.get_or_load_engine(mode)
        cls.validate_feature_payload(features, engine)

        # Execute raw model inference
        raw_res = engine.predict_features(
            features=features,
            entity_id=entity_id,
            as_of_time=now,
        )

        confidence = raw_res.confidence
        predicted_class = raw_res.predicted_class
        threshold = policy.confidence_threshold

        # Apply confidence policy and abstention logic
        if confidence >= threshold:
            assigned_class = predicted_class
            is_abstained = False
            review_required = False
            abstention_reason = None
        else:
            # INVARIANT: UNKNOWN != NON_INDUSTRIAL
            assigned_class = "unknown"
            is_abstained = True
            review_required = True
            abstention_reason = AbstentionReason.LOW_CONFIDENCE.value

        t_elapsed = (time.perf_counter() - t0) * 1000.0

        return ProductionPredictionResponse(
            entity_id=entity_id,
            operating_mode=policy.mode.value,
            model_name=engine.artifact.metadata.model_type,
            model_version=engine.artifact.metadata.model_version,
            feature_schema_version=engine.artifact.metadata.feature_set_version,
            predicted_class=predicted_class,
            assigned_class=assigned_class,
            confidence=round(confidence, 4),
            threshold=threshold,
            class_probabilities=raw_res.class_probabilities,
            is_abstained=is_abstained,
            review_required=review_required,
            abstention_reason=abstention_reason,
            feature_count=len(features),
            inference_timestamp=now,
            latency_ms=round(t_elapsed, 3),
        )

    @classmethod
    def predict_batch(
        cls,
        items: list[dict[str, Any]],
        entity_ids: list[str] | None = None,
        mode: ProductionOperatingMode | str = (
            ProductionOperatingMode.HIGH_PRECISION
        ),
    ) -> list[ProductionPredictionResponse]:
        """Execute high-throughput batch inference over multiple feature records.

        Args:
            items: List of feature dictionaries.
            entity_ids: Optional list of corresponding entity IDs.
            mode: Selected ProductionOperatingMode.

        Returns:
            List of ProductionPredictionResponse objects.
        """
        ids = entity_ids or [f"entity_{i:04d}" for i in range(len(items))]
        if len(items) != len(ids):
            msg = (
                f"Items count ({len(items)}) does not match "
                f"entity_ids count ({len(ids)})."
            )
            raise ValueError(msg)

        results: list[ProductionPredictionResponse] = []
        for feat_dict, eid in zip(items, ids, strict=False):
            results.append(
                cls.predict_features(
                    features=feat_dict,
                    entity_id=eid,
                    mode=mode,
                )
            )
        return results

    @classmethod
    def predict_event(
        cls,
        event: Event,
        member_detections: Sequence[Detection],
        as_of_time: UtcDatetime,
        mode: ProductionOperatingMode | str = (
            ProductionOperatingMode.HIGH_PRECISION
        ),
        preceding_events: Sequence[Event] | None = None,
        source: PersistentSource | None = None,
        context_evidence: Sequence[ContextEvidence] | None = None,
    ) -> ProductionPredictionResponse:
        """Extract canonical features for an event and execute production inference.

        Args:
            event: Canonical physical thermal event.
            member_detections: Associated satellite detections.
            as_of_time: Point-in-time calculation cutoff.
            mode: Selected ProductionOperatingMode.
            preceding_events: Preceding temporal event history.
            source: Linked persistent thermal source cluster.
            context_evidence: Spatial and infrastructure contextual evidence.

        Returns:
            ProductionPredictionResponse for the physical event.
        """
        extractor = FeatureExtractor()
        feature_record = extractor.extract_features_for_event(
            event=event,
            member_detections=member_detections,
            as_of_time=as_of_time,
            preceding_events=preceding_events,
            source=source,
            context_evidence=context_evidence,
        )

        return cls.predict_features(
            features=feature_record.features,
            entity_id=event.event_id,
            mode=mode,
            as_of_time=as_of_time,
        )
