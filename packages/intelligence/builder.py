"""Builder and deterministic ID generator for IntelligenceResult models."""

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from packages.config.scientific import ScientificConfig
from packages.schemas.context import ContextEvidence
from packages.schemas.enums import (
    AttributionStrength,
    ContextType,
    PersistenceState,
    PhenomenonType,
)
from packages.schemas.event import Event
from packages.schemas.intelligence import (
    EvidenceCompleteness,
    IntelligenceResult,
    UncertaintyMetric,
)
from packages.schemas.source import PersistentSource


def generate_deterministic_intelligence_id(
    event_id: str,
    source_id: str | None,
    context_ids: Sequence[str],
    config_fingerprint: str,
) -> str:
    """Generate a deterministic, content-addressable intelligence result identifier.

    The ID is derived from the SHA-256 digest of the scientific configuration
    fingerprint, event ID, source ID, and sorted context evidence IDs.

    Args:
        event_id: Canonical Event identifier.
        source_id: Optional PersistentSource identifier.
        context_ids: Sequence of associated ContextEvidence identifiers.
        config_fingerprint: SHA-256 fingerprint of the scientific configuration.

    Returns:
        str: Canonical intelligence identifier (e.g. 'int_a1b2c3d4e5f60718293a4b5c').
    """
    sorted_ctx = sorted(c.strip() for c in context_ids if c and c.strip())
    src_part = source_id.strip() if source_id else "none"
    raw_key = f"{config_fingerprint}:int:{event_id.strip()}:{src_part}:" + ",".join(
        sorted_ctx
    )
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"int_{digest[:24]}"


def build_intelligence_result(
    event: Event,
    source: PersistentSource | None,
    context_evidence: Sequence[ContextEvidence] | None,
    phenomenon: PhenomenonType,
    context_type: ContextType,
    persistence_state: PersistenceState,
    attribution_strength: AttributionStrength,
    uncertainty: UncertaintyMetric,
    completeness: EvidenceCompleteness,
    config: ScientificConfig,
    pipeline_run_id: str | None = None,
    model_version: str | None = "v1.0-rules-engine",
    notes: str | None = None,
    created_at: datetime | None = None,
) -> IntelligenceResult:
    """Construct a canonical IntelligenceResult domain model from evaluated dimensions.

    Args:
        event: Evaluated canonical Event.
        source: Optional linked PersistentSource.
        context_evidence: Optional sequence of associated ContextEvidence objects.
        phenomenon: Classified physical phenomenon.
        context_type: Classified site environment.
        persistence_state: Observed temporal persistence state.
        attribution_strength: Classified attribution strength to context.
        uncertainty: Evaluated uncertainty and abstention metrics.
        completeness: Evaluated evidence completeness.
        config: Authoritative ScientificConfig instance.
        pipeline_run_id: Optional pipeline execution run ID.
        model_version: Inference model or rules engine version string.
        notes: Optional explanatory notes.
        created_at: Optional UTC creation timestamp (defaults to current UTC).

    Returns:
        IntelligenceResult: Canonical validated IntelligenceResult domain model.
    """
    ctx_ids = [c.context_id for c in context_evidence] if context_evidence else []
    src_id = source.source_id if source else None
    config_fingerprint = config.compute_fingerprint()

    intelligence_id = generate_deterministic_intelligence_id(
        event_id=event.event_id,
        source_id=src_id,
        context_ids=ctx_ids,
        config_fingerprint=config_fingerprint,
    )

    return IntelligenceResult(
        intelligence_id=intelligence_id,
        event_id=event.event_id,
        source_id=src_id,
        phenomenon=phenomenon,
        context=context_type,
        persistence=persistence_state,
        attribution=attribution_strength,
        uncertainty=uncertainty,
        evidence_completeness=completeness,
        created_at=created_at or datetime.now(UTC),
        pipeline_run_id=pipeline_run_id,
        model_version=model_version,
        configuration_version=config.version,
        notes=notes,
    )
