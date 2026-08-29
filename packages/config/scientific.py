"""Canonical scientific configuration contract for SIH26162.

Provides a typed, versioned, and immutable scientific configuration contract
governing clustering, persistence, attribution, and confidence thresholds.
All scientific parameters default to None (explicit incomplete state) to prevent
unsupported scientific values from being invented.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from packages.errors import MissingConfigurationError

SCIENTIFIC_PARAMETER_FIELDS: frozenset[str] = frozenset(
    {
        "spatial_cluster_radius_meters",
        "temporal_window_hours",
        "persistence_threshold_days",
        "persistence_min_observations",
        "attribution_radius_meters",
        "attribution_confidence_threshold",
        "minimum_event_confidence",
        "abstention_confidence_threshold",
    }
)


class ScientificConfig(BaseModel):
    """Canonical contract for scientific algorithm parameters and thresholds.

    Defines explicit types and physical units. All thresholds default to None
    to represent an explicit incomplete/uncalibrated state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Contract Identification & Metadata
    version: str = Field(
        ...,
        min_length=1,
        description="Version or identifier of this scientific configuration contract.",
    )
    name: str = Field(
        default="default",
        description="Descriptive identifier for this configuration profile.",
    )
    description: str = Field(
        default="",
        description="Scientific justification, experimental notes, or calibration basis.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC creation timestamp for provenance tracking.",
    )

    # 1. Spatial Clustering Parameters
    spatial_cluster_radius_meters: float | None = Field(
        default=None,
        gt=0,
        description="Maximum distance in meters between detections to form a thermal event cluster.",
    )

    # 2. Temporal Clustering Parameters
    temporal_window_hours: float | None = Field(
        default=None,
        gt=0,
        description="Maximum time difference in hours between detections in the same event episode.",
    )

    # 3. Persistence Criteria
    persistence_threshold_days: float | None = Field(
        default=None,
        gt=0,
        description="Minimum temporal observation span in days to qualify as a persistent thermal source.",
    )
    persistence_min_observations: int | None = Field(
        default=None,
        ge=1,
        description="Minimum count of distinct satellite detections required for persistence.",
    )

    # 4. Attribution Parameters
    attribution_radius_meters: float | None = Field(
        default=None,
        gt=0,
        description="Spatial search radius in meters around event centroid for known infrastructure.",
    )
    attribution_confidence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score [0.0, 1.0] for confirmed infrastructure attribution.",
    )

    # 5. Decision & Abstention Thresholds
    minimum_event_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score [0.0, 1.0] for a confirmed thermal event.",
    )
    abstention_confidence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence cutoff [0.0, 1.0] below which the system must abstain from classifying.",
    )

    @property
    def is_complete(self) -> bool:
        """Return True if all required scientific parameters are populated."""
        return len(self.missing_parameters) == 0

    @property
    def missing_parameters(self) -> list[str]:
        """Return a sorted list of unset scientific parameter names."""
        return sorted(
            field
            for field in SCIENTIFIC_PARAMETER_FIELDS
            if getattr(self, field) is None
        )

    def validate_completeness(self) -> None:
        """Validate that all scientific parameters are set before algorithm execution.

        Raises:
            MissingConfigurationError: If any scientific parameter is unset (None).
        """
        missing = self.missing_parameters
        if missing:
            msg = (
                f"Scientific configuration '{self.version}' is incomplete. "
                f"Unset parameters: {', '.join(missing)}"
            )
            raise MissingConfigurationError(
                msg,
                details={
                    "version": self.version,
                    "missing_parameters": missing,
                },
            )

    def to_canonical_dict(self) -> dict[str, Any]:
        """Produce a deterministic, sorted dictionary representation of this configuration."""
        raw = self.model_dump()
        raw["created_at"] = self.created_at.isoformat()
        return {k: raw[k] for k in sorted(raw.keys())}

    def to_canonical_json(self) -> str:
        """Produce a deterministic canonical JSON string suitable for hashing."""
        return json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def compute_fingerprint(self) -> str:
        """Compute the SHA-256 hex digest of the canonical configuration JSON for provenance."""
        canonical_bytes = self.to_canonical_json().encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()
