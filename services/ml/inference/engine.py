"""Canonical ML Inference Runtime Engine for Phase 4 (ML-009).

Executes point-in-time model inference with strict feature contract validation,
preprocessor transformation, and uncertainty/abstention auditing.
"""

import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from packages.schemas.common import UtcDatetime
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.event import Event
from packages.schemas.ml import (
    AbstentionContract,
    FeatureRecord,
    InferencePredictionResult,
    ModelArtifact,
)
from packages.schemas.source import PersistentSource
from services.ml.calibration.abstention import AbstentionDecisionEngine
from services.ml.features.extractor import FeatureExtractor
from services.ml.models.registry import ModelRegistry

if TYPE_CHECKING:
    from services.ml.models.base import BaseMLModel
    from services.ml.preprocessing.transformer import FeaturePreprocessor


class MLInferenceEngine:
    """Inference engine executing predictions from frozen model artifacts."""

    def __init__(
        self,
        artifact: ModelArtifact,
        abstention_contract: AbstentionContract | None = None,
        feature_extractor: FeatureExtractor | None = None,
    ) -> None:
        """Initialize inference engine from a validated ModelArtifact.

        Args:
            artifact: Serialized ModelArtifact container.
            abstention_contract: Optional configuration for abstention.
            feature_extractor: Optional feature extraction service.
        """
        ModelRegistry.verify_artifact_integrity(artifact)
        self.artifact: ModelArtifact = artifact
        self.preprocessor: FeaturePreprocessor
        self.model: BaseMLModel

        self.preprocessor, self.model = ModelRegistry.reconstruct_pipeline(artifact)
        self.abstention_contract: AbstentionContract | None = abstention_contract
        self.feature_extractor: FeatureExtractor = (
            feature_extractor or FeatureExtractor()
        )

        # Expected raw feature names from preprocessor
        self.expected_feature_names: list[str] = list(self.preprocessor.feature_names)
        self.output_column_names: list[str] = list(
            self.preprocessor.output_column_names
        )
        self.class_vocabulary: list[str] = list(artifact.class_vocabulary)

    def validate_feature_schema(self, features: dict[str, Any]) -> None:
        """Validate feature input dictionary against frozen preprocessor contract.

        Raises:
            ValueError: If required features are missing or dictionary is empty.
        """
        if not features:
            raise ValueError("Input feature dictionary cannot be empty.")

        missing = [f for f in self.expected_feature_names if f not in features]
        if missing:
            msg = f"{len(missing)} required feature(s) missing: {missing[:5]}"
            if len(missing) > 5:
                msg += "..."
            raise ValueError(f"Feature schema mismatch: {msg}.")

    def predict_features(
        self,
        features: dict[str, Any],
        entity_id: str = "entity_inference",
        as_of_time: UtcDatetime | None = None,
        abstention_contract: AbstentionContract | None = None,
    ) -> InferencePredictionResult:
        """Execute single-entity inference from a raw feature dictionary.

        Args:
            features: Dictionary of engineered feature name to value.
            entity_id: Optional identifier of the sample entity.
            as_of_time: Optional prediction cutoff timestamp.
            abstention_contract: Optional runtime override for abstention criteria.

        Returns:
            InferencePredictionResult with class, probabilities, and confidence.
        """
        t_start = time.perf_counter()
        now = as_of_time or datetime.now(UTC)

        # 1. Validate Feature Contract
        self.validate_feature_schema(features)

        # 2. Transform Features via Frozen Preprocessor
        is_raw = (
            self.artifact.metadata.model_type == "DeterministicContextualClassifier"
        )
        if is_raw:
            preds = self.model.predict([features])
            probs_list = self.model.predict_proba([features])
        else:
            vec = self.preprocessor.transform([features])
            preds = self.model.predict(vec)
            probs_list = self.model.predict_proba(vec)

        predicted_class = str(preds[0])
        prob_dict = dict(probs_list[0]) if probs_list else {}

        # 3. Calculate Confidence Score
        confidence = float(
            prob_dict.get(
                predicted_class, max(prob_dict.values()) if prob_dict else 1.0
            )
        )

        # 4. Check Abstention Criteria
        is_abstained = False
        abstention_reason = None
        contract = abstention_contract or self.abstention_contract
        if contract is not None:
            should_abs, abs_reason = AbstentionDecisionEngine.evaluate_abstention(
                confidence=confidence,
                uncertainty=1.0 - confidence,
                evidence_completeness_ratio=1.0,
                contract=contract,
            )
            is_abstained = bool(should_abs)
            if is_abstained:
                abstention_reason = abs_reason.value

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        return InferencePredictionResult(
            entity_id=entity_id,
            target_id=self.artifact.metadata.target_id,
            target_version=self.artifact.metadata.target_version,
            model_id=self.artifact.metadata.model_id,
            model_version=self.artifact.metadata.model_version,
            model_type=self.artifact.metadata.model_type,
            feature_set_version=self.artifact.metadata.feature_set_version,
            predicted_class=predicted_class,
            class_probabilities=prob_dict,
            confidence=confidence,
            is_abstained=is_abstained,
            abstention_reason=abstention_reason,
            feature_count=len(features),
            inference_timestamp=now,
            latency_ms=round(t_elapsed, 3),
        )

    def predict_record(
        self,
        record: FeatureRecord,
    ) -> InferencePredictionResult:
        """Execute inference from a canonical FeatureRecord."""
        return self.predict_features(
            features=record.features,
            entity_id=record.entity_id,
            as_of_time=record.as_of_time,
        )

    def predict_event(
        self,
        event: Event,
        member_detections: Sequence[Detection],
        as_of_time: UtcDatetime,
        preceding_events: Sequence[Event] | None = None,
        source: PersistentSource | None = None,
        context_evidence: Sequence[ContextEvidence] | None = None,
    ) -> InferencePredictionResult:
        """Extract point-in-time features for an event and execute inference."""
        feature_record = self.feature_extractor.extract_features_for_event(
            event=event,
            member_detections=member_detections,
            as_of_time=as_of_time,
            preceding_events=preceding_events,
            source=source,
            context_evidence=context_evidence,
        )
        return self.predict_record(feature_record)

    def predict_batch(
        self,
        feature_dicts: list[dict[str, Any]],
        entity_ids: list[str] | None = None,
    ) -> list[InferencePredictionResult]:
        """Execute batch inference over multiple feature dictionaries."""
        ids = entity_ids or [f"entity_{i:04d}" for i in range(len(feature_dicts))]
        results: list[InferencePredictionResult] = []

        for feat_dict, eid in zip(feature_dicts, ids, strict=False):
            results.append(self.predict_features(features=feat_dict, entity_id=eid))

        return results
