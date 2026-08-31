"""FastAPI route handlers for production ML runtime inference."""

from fastapi import APIRouter, HTTPException, status

from services.api.schemas.inference import (
    BatchPredictionRequestBody,
    BatchPredictionResponseBody,
    PredictionRequestBody,
    PredictionResponseBody,
)
from services.ml.inference.production_runtime import (
    ProductionMLRuntimeService,
)

router = APIRouter(prefix="/inference", tags=["inference"])


@router.post(
    "/predict",
    response_model=PredictionResponseBody,
    operation_id="predict_features",
    summary="Execute production ML inference on a feature vector",
    description=(
        "Executes leak-free point-in-time prediction using the policy-authorized "
        "production model and calibrated abstention threshold. "
        "Supports HIGH_PRECISION, HIGH_RECALL, and SELECTIVE operating modes."
    ),
)
def predict_features(
    request: PredictionRequestBody,
) -> PredictionResponseBody:
    """Execute single-sample ML prediction under authorized production policy."""
    try:
        res = ProductionMLRuntimeService.predict_features(
            features=request.features,
            entity_id=request.entity_id,
            mode=request.operating_mode,
        )
        return PredictionResponseBody(
            entity_id=res.entity_id,
            operating_mode=res.operating_mode,
            model_name=res.model_name,
            model_version=res.model_version,
            feature_schema_version=res.feature_schema_version,
            predicted_class=res.predicted_class,
            assigned_class=res.assigned_class,
            confidence=res.confidence,
            threshold=res.threshold,
            class_probabilities=res.class_probabilities,
            is_abstained=res.is_abstained,
            review_required=res.review_required,
            abstention_reason=res.abstention_reason,
            feature_count=res.feature_count,
            inference_timestamp=res.inference_timestamp,
            latency_ms=res.latency_ms,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Production model artifact is unavailable.",
        ) from err


@router.post(
    "/predict-batch",
    response_model=BatchPredictionResponseBody,
    operation_id="predict_batch_features",
    summary="Execute batch production ML inference",
    description=(
        "Executes high-throughput batch prediction over multiple feature vectors."
    ),
)
def predict_batch_features(
    request: BatchPredictionRequestBody,
) -> BatchPredictionResponseBody:
    """Execute batch ML prediction under authorized production policy."""
    try:
        results = ProductionMLRuntimeService.predict_batch(
            items=request.items,
            entity_ids=request.entity_ids,
            mode=request.operating_mode,
        )
        predictions = [
            PredictionResponseBody(
                entity_id=res.entity_id,
                operating_mode=res.operating_mode,
                model_name=res.model_name,
                model_version=res.model_version,
                feature_schema_version=res.feature_schema_version,
                predicted_class=res.predicted_class,
                assigned_class=res.assigned_class,
                confidence=res.confidence,
                threshold=res.threshold,
                class_probabilities=res.class_probabilities,
                is_abstained=res.is_abstained,
                review_required=res.review_required,
                abstention_reason=res.abstention_reason,
                feature_count=res.feature_count,
                inference_timestamp=res.inference_timestamp,
                latency_ms=res.latency_ms,
            )
            for res in results
        ]
        abstained_count = sum(1 for p in predictions if p.is_abstained)
        return BatchPredictionResponseBody(
            predictions=predictions,
            total_count=len(predictions),
            abstained_count=abstained_count,
            operating_mode=request.operating_mode,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Production model artifact is unavailable.",
        ) from err
