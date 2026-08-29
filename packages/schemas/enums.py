"""Canonical domain enumerations for SIH26162.

These enums represent the orthogonal domain ontology and status taxonomies.
Provisional v1 taxonomies are explicitly documented as subject to refinement.
"""

from enum import StrEnum


class PhenomenonType(StrEnum):
    """Provisional v1 phenomenon ontology.

    Represents the observed or inferred physical thermal anomaly phenomenon.
    This taxonomy is provisional and orthogonal to context, persistence,
    and attribution.
    """

    FIRE = "fire"
    FLARE = "flare"
    INDUSTRIAL_THERMAL_SOURCE = "industrial_thermal_source"
    AGRICULTURAL_BURN = "agricultural_burn"
    VEGETATION_WILDFIRE = "vegetation_wildfire"
    OTHER_THERMAL_ANOMALY = "other_thermal_anomaly"
    UNKNOWN = "unknown"


class ContextType(StrEnum):
    """Contextual classification of the surrounding land-use or infrastructure.

    Context provides evidence about the site, but does NOT represent the
    phenomenon label. A nearby industrial facility does not prove an
    industrial fire.
    """

    INDUSTRIAL = "industrial"
    OIL_GAS = "oil_gas"
    POWER = "power"
    MINING = "mining"
    AGRICULTURAL = "agricultural"
    FOREST_VEGETATION = "forest_vegetation"
    URBAN = "urban"
    OTHER = "other"
    UNKNOWN = "unknown"


class PersistenceState(StrEnum):
    """Observed temporal persistence state of a thermal source or cluster.

    Persistence is an observed temporal characteristic, not proof of
    facility type or causation.
    """

    TRANSIENT = "transient"
    RECURRING = "recurring"
    PERSISTENT = "persistent"
    INSUFFICIENT_HISTORY = "insufficient_history"


class AttributionStrength(StrEnum):
    """Strength of attribution linking an event to a contextual facility.

    Represents attribution confidence, NOT fire severity, model probability,
    or certainty of causation.
    """

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNKNOWN = "unknown"


class EvidenceAvailabilityState(StrEnum):
    """Explicit availability state of evidence sources.

    Distinguishes missing/unavailable data from evidence of absence.
    """

    AVAILABLE = "available"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    NOT_FOUND_IN_SOURCE = "not_found_in_source"
    UNKNOWN = "unknown"


class DayNight(StrEnum):
    """Day or night observation flag."""

    DAY = "D"
    NIGHT = "N"
    UNKNOWN = "unknown"


class SourceRole(StrEnum):
    """Canonical semantic roles for data sources within SIH26162.

    Explicitly defines how each registered source contributes to data
    provenance, intelligence formation, or validation.
    """

    OBSERVATION = "OBSERVATION"
    REFERENCE = "REFERENCE"
    CONTEXT = "CONTEXT"
    VALIDATION = "VALIDATION"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    DERIVED = "DERIVED"
    GROUND_TRUTH_CANDIDATE = "GROUND_TRUTH_CANDIDATE"
    GROUND_TRUTH_EVIDENCE = "GROUND_TRUTH_EVIDENCE"
    OPTIONAL = "OPTIONAL"
    DEMO_ONLY = "DEMO_ONLY"
