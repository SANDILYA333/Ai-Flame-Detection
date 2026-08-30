"""Label construction, target specifications, and supervised dataset building."""

from services.ml.labels.constructor import LabelConstructor
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.labels.reporting import (
    generate_supervised_dataset_report,
    generate_target_catalog_json,
    generate_target_catalog_markdown,
)
from services.ml.labels.targets import (
    STANDARD_TARGET_SET_VERSION,
    STANDARD_TARGETS,
    TARGET_INDUSTRIAL_SEGREGATION,
    TARGET_PERSISTENT_COMBUSTION,
    TARGET_THERMAL_PHENOMENON,
    get_standard_target_registry,
)

__all__ = [
    "STANDARD_TARGETS",
    "STANDARD_TARGET_SET_VERSION",
    "TARGET_INDUSTRIAL_SEGREGATION",
    "TARGET_PERSISTENT_COMBUSTION",
    "TARGET_THERMAL_PHENOMENON",
    "LabelConstructor",
    "SupervisedDatasetBuilder",
    "generate_supervised_dataset_report",
    "generate_target_catalog_json",
    "generate_target_catalog_markdown",
    "get_standard_target_registry",
]
