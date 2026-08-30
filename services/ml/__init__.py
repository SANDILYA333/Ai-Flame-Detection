"""Machine learning service package for SIH26162.

Provides Phase 4 ML readiness assessment, evaluation harness, feature registries,
dataset manifest generation, split integrity validation, label construction,
model training pipelines, and baseline classifiers.
"""

from services.ml.calibration.abstention import AbstentionDecisionEngine
from services.ml.calibration.contract import CalibrationManager
from services.ml.evaluation.ablation import FeatureAblationService
from services.ml.evaluation.generalization import GeneralizationBenchmarkService
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
from services.ml.labels.constructor import LabelConstructor
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.labels.targets import (
    STANDARD_TARGET_SET_VERSION,
    STANDARD_TARGETS,
    TARGET_INDUSTRIAL_SEGREGATION,
    TARGET_PERSISTENT_COMBUSTION,
    TARGET_THERMAL_PHENOMENON,
    get_standard_target_registry,
)
from services.ml.models.base import BaseMLModel
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.registry import ModelRegistry
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.extractor import (
    PROHIBITED_METADATA_COLUMNS,
    DatasetSplitExtractor,
)
from services.ml.preprocessing.transformer import FeaturePreprocessor
from services.ml.readiness import MLReadinessAuditor
from services.ml.training.dataset import DatasetBuilder, DuplicateRecordViolation
from services.ml.training.pipeline import MLTrainingPipeline
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)

__all__ = [
    "APPROVED_FEATURES",
    "DISQUALIFIED_CANDIDATES",
    "PROHIBITED_METADATA_COLUMNS",
    "STANDARD_FEATURE_VERSION",
    "STANDARD_TARGETS",
    "STANDARD_TARGET_SET_VERSION",
    "TARGET_INDUSTRIAL_SEGREGATION",
    "TARGET_PERSISTENT_COMBUSTION",
    "TARGET_THERMAL_PHENOMENON",
    "AbstentionDecisionEngine",
    "BaseMLModel",
    "CalibrationManager",
    "DatasetBuilder",
    "DatasetSplitExtractor",
    "DecisionTreeClassifier",
    "DeterministicContextualClassifier",
    "DuplicateRecordViolation",
    "EvaluationHarness",
    "FeatureAblationService",
    "FeatureDatasetBuilder",
    "FeatureExtractor",
    "FeaturePreprocessor",
    "FeatureRegistry",
    "GeneralizationBenchmarkService",
    "LabelConstructor",
    "LeakageAuditReport",
    "LeakageAuditor",
    "LeakageViolation",
    "LogisticRegressionClassifier",
    "MLReadinessAuditor",
    "MLTrainingPipeline",
    "MajorityClassClassifier",
    "ModelRegistry",
    "RandomForestClassifier",
    "SplitAssignmentService",
    "SplitIntegrityValidator",
    "SupervisedDatasetBuilder",
    "get_standard_feature_registry",
    "get_standard_target_registry",
]
