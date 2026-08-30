"""Configuration package for SIH26162.

Provides operational Settings (BE-003) and scientific configuration contracts (BE-004).
"""

from packages.config.ml import (
    ML_PARAMETER_FIELDS,
    MLConfig,
)
from packages.config.scientific import (
    SCIENTIFIC_PARAMETER_FIELDS,
    ScientificConfig,
)
from packages.config.settings import (
    AppEnvironment,
    LogLevel,
    Settings,
    get_settings,
    get_test_settings,
)

__all__ = [
    "ML_PARAMETER_FIELDS",
    "SCIENTIFIC_PARAMETER_FIELDS",
    "AppEnvironment",
    "LogLevel",
    "MLConfig",
    "ScientificConfig",
    "Settings",
    "get_settings",
    "get_test_settings",
]
