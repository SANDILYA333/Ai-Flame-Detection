"""FastAPI route handlers for production ML runtime inference and FIRMS integration."""

from fastapi import APIRouter, HTTPException, status

from services.api.schemas.inference import (
    BatchPredictionRequestBody,
    BatchPredictionResponseBody,
    FirmsCsvPredictionRequestBody,
    FirmsCsvPredictionResponseBody,
    FirmsMLPredictionResponseBody,
    PredictionRequestBody,
    PredictionResponseBody,
)
from services.ml.inference.production_runtime import (
    ProductionMLRuntimeService,
)
from services.ml.integration.firms_pipeline import (
    FirmsProductionMLIntegrationService,
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


@router.post(
    "/evaluate-firms-csv",
    response_model=FirmsCsvPredictionResponseBody,
    operation_id="evaluate_firms_csv",
    summary="Evaluate raw NASA FIRMS CSV end-to-end",
    description=(
        "Ingests raw NASA FIRMS CSV rows, derives physical thermal events, "
        "extracts 30 canonical feat_v1.0.0 features point-in-time, and "
        "executes policy-governed production ML inference."
    ),
)
def evaluate_firms_csv(
    request: FirmsCsvPredictionRequestBody,
) -> FirmsCsvPredictionResponseBody:
    """Execute end-to-end evaluation of raw NASA FIRMS CSV data."""
    try:
        results = FirmsProductionMLIntegrationService.evaluate_firms_csv(
            csv_content=request.csv_content,
            mode=request.operating_mode,
        )
        response_items = [
            FirmsMLPredictionResponseBody(
                event_id=r.event_id,
                source=r.source,
                event_timestamp=r.event_timestamp,
                centroid_latitude=r.centroid_latitude,
                centroid_longitude=r.centroid_longitude,
                detection_count=r.detection_count,
                max_frp_mw=r.max_frp_mw,
                operating_mode=r.operating_mode,
                feature_schema_version=r.feature_schema_version,
                feature_count=r.feature_count,
                model_name=r.model_name,
                model_version=r.model_version,
                predicted_class=r.predicted_class,
                assigned_class=r.assigned_class,
                confidence=r.confidence,
                threshold=r.threshold,
                class_probabilities=r.class_probabilities,
                is_abstained=r.is_abstained,
                review_required=r.review_required,
                abstention_reason=r.abstention_reason,
                feature_extraction_latency_ms=r.feature_extraction_latency_ms,
                inference_latency_ms=r.inference_latency_ms,
                total_latency_ms=r.total_latency_ms,
            )
            for r in results
        ]
        abstained_count = sum(1 for r in response_items if r.is_abstained)
        return FirmsCsvPredictionResponseBody(
            results=response_items,
            total_events=len(response_items),
            abstained_events=abstained_count,
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
