"""ML model training workflows, dataset manifest generation, and split integrity."""

from services.ml.training.dataset import DatasetBuilder, DuplicateRecordViolation
from services.ml.training.gate import RealTrainingGateEvaluation, RealTrainingGateEvaluator
from services.ml.training.pipeline import MLTrainingPipeline
from services.ml.training.real_trainer import (
    CANONICAL_REAL_MODELS,
    RealMLTrainer,
    RealModelTrainingResult,
    RealTrainingSuiteResult,
)
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)

__all__ = [
    "CANONICAL_REAL_MODELS",
    "DatasetBuilder",
    "DuplicateRecordViolation",
    "MLTrainingPipeline",
    "RealMLTrainer",
    "RealModelTrainingResult",
    "RealTrainingGateEvaluation",
    "RealTrainingGateEvaluator",
    "RealTrainingSuiteResult",
    "SplitAssignmentService",
    "SplitIntegrityValidator",
]
