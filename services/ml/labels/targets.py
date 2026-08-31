"""Standard ML target definitions and class vocabularies for SIH26162 Phase 4.

Defines the approved prediction targets, class vocabularies, positive/negative
scientific definitions, and unknown/abstention semantics.
"""

from packages.schemas.ml import (
    TargetDefinition,
    TargetType,
    TargetUnit,
)

STANDARD_TARGET_SET_VERSION = "target_v1.0.0"

# ==============================================================================
# 1. APPROVED TARGET SPECIFICATIONS
# ==============================================================================

TARGET_THERMAL_PHENOMENON = TargetDefinition(
    target_id="target_thermal_phenomenon",
    name="Thermal Phenomenon Classification",
    target_type=TargetType.MULTICLASS_CLASSIFICATION,
    unit_of_prediction=TargetUnit.EVENT,
    class_vocabulary=[
        "flare",
        "industrial_thermal_source",
        "vegetation_wildfire",
        "agricultural_burn",
        "other_thermal_anomaly",
        "unknown",
    ],
    positive_definition=None,
    negative_definition=None,
    unknown_definition=(
        "Insufficient multi-source or authoritative evidence to resolve physical "
        "phenomenon class."
    ),
    is_approved=True,
    unresolved_reason=None,
)

TARGET_INDUSTRIAL_SEGREGATION = TargetDefinition(
    target_id="target_industrial_segregation",
    name="Industrial vs Non-Industrial Thermal Segregation",
    target_type=TargetType.BINARY_CLASSIFICATION,
    unit_of_prediction=TargetUnit.EVENT,
    class_vocabulary=[
        "industrial",
        "non_industrial",
        "unknown",
    ],
    positive_definition=(
        "Confirmed or probable industrial facility origin (refinery flare, "
        "petrochemical plant, power station, furnace, smelter, kiln)."
    ),
    negative_definition=(
        "Confirmed or probable non-industrial origin (vegetation wildfire, "
        "agricultural stubble burn, open bonfire)."
    ),
    unknown_definition=(
        "Ambiguous, missing, or conflicting contextual evidence regarding facility "
        "association."
    ),
    is_approved=True,
    unresolved_reason=None,
)

TARGET_PERSISTENT_COMBUSTION = TargetDefinition(
    target_id="target_persistent_combustion",
    name="Persistent Thermal Source Classification",
    target_type=TargetType.BINARY_CLASSIFICATION,
    unit_of_prediction=TargetUnit.EVENT,
    class_vocabulary=[
        "persistent_source",
        "transient_event",
        "unknown",
    ],
    positive_definition=(
        "Multi-day longitudinal thermal recurrence observed at a stationary "
        "physical location."
    ),
    negative_definition=(
        "Transient single-day thermal event without historical recurrence."
    ),
    unknown_definition=(
        "Insufficient historical observation span (< 7 calendar days)."
    ),
    is_approved=True,
    unresolved_reason=None,
)

STANDARD_TARGETS: list[TargetDefinition] = [
    TARGET_THERMAL_PHENOMENON,
    TARGET_INDUSTRIAL_SEGREGATION,
    TARGET_PERSISTENT_COMBUSTION,
]


def get_standard_target_registry() -> dict[str, TargetDefinition]:
    """Retrieve mapping of target_id to approved TargetDefinition."""
    return {t.target_id: t for t in STANDARD_TARGETS}
