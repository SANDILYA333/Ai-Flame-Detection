"""ML feature extraction, registration, dataset building, and leakage validation."""

from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.leakage import (
    LeakageAuditor,
    LeakageAuditReport,
    LeakageViolation,
)
from services.ml.features.registry import FeatureRegistry
from services.ml.features.reporting import (
    generate_dataset_quality_report,
    generate_feature_catalog_json,
    generate_feature_catalog_markdown,
)
from services.ml.features.standard_set import (
    APPROVED_FEATURES,
    DISQUALIFIED_CANDIDATES,
    STANDARD_FEATURE_VERSION,
    get_standard_feature_registry,
)

__all__ = [
    "APPROVED_FEATURES",
    "DISQUALIFIED_CANDIDATES",
    "STANDARD_FEATURE_VERSION",
    "FeatureDatasetBuilder",
    "FeatureExtractor",
    "FeatureRegistry",
    "LeakageAuditReport",
    "LeakageAuditor",
    "LeakageViolation",
    "generate_dataset_quality_report",
    "generate_feature_catalog_json",
    "generate_feature_catalog_markdown",
    "get_standard_feature_registry",
]
