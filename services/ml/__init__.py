"""Machine learning service package for SIH26162.

Provides Phase 4 ML readiness assessment, evaluation harness, feature registries,
dataset manifest generation, split integrity validation, and calibration contracts.
"""

from services.ml.calibration.abstention import AbstentionDecisionEngine
from services.ml.calibration.contract import CalibrationManager
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.features.leakage import (
    LeakageAuditor,
    LeakageAuditReport,
    LeakageViolation,
)
from services.ml.features.registry import FeatureRegistry
from services.ml.readiness import MLReadinessAuditor
from services.ml.training.dataset import DatasetBuilder, DuplicateRecordViolation
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)

__all__ = [
    "AbstentionDecisionEngine",
    "CalibrationManager",
    "DatasetBuilder",
    "DuplicateRecordViolation",
    "EvaluationHarness",
    "FeatureRegistry",
    "LeakageAuditReport",
    "LeakageAuditor",
    "LeakageViolation",
    "MLReadinessAuditor",
    "SplitAssignmentService",
    "SplitIntegrityValidator",
]
