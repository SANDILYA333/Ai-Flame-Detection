"""Machine learning service package for SIH26162.

Provides Phase 4 ML readiness assessment, evaluation harness, feature registries,
dataset manifest generation, split integrity validation, and calibration contracts.
"""

from services.ml.calibration.abstention import AbstentionDecisionEngine
from services.ml.calibration.contract import CalibrationManager
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.leakage import (
    LeakageAuditor,
    LeakageAuditReport,
    LeakageViolation,
)
from services.ml.features.registry import FeatureRegistry
from services.ml.features.standard_set import (
    APPROVED_FEATURES,
    DISQUALIFIED_CANDIDATES,
    STANDARD_FEATURE_VERSION,
    get_standard_feature_registry,
)
from services.ml.readiness import MLReadinessAuditor
from services.ml.training.dataset import DatasetBuilder, DuplicateRecordViolation
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)

__all__ = [
    "APPROVED_FEATURES",
    "DISQUALIFIED_CANDIDATES",
    "STANDARD_FEATURE_VERSION",
    "AbstentionDecisionEngine",
    "CalibrationManager",
    "DatasetBuilder",
    "DuplicateRecordViolation",
    "EvaluationHarness",
    "FeatureDatasetBuilder",
    "FeatureExtractor",
    "FeatureRegistry",
    "LeakageAuditReport",
    "LeakageAuditor",
    "LeakageViolation",
    "MLReadinessAuditor",
    "SplitAssignmentService",
    "SplitIntegrityValidator",
    "get_standard_feature_registry",
]
