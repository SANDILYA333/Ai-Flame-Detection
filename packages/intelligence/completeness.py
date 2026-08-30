"""Evidence completeness auditing across observation and context categories."""

from collections.abc import Sequence

from packages.schemas.context import ContextEvidence
from packages.schemas.enums import EvidenceAvailabilityState
from packages.schemas.event import Event
from packages.schemas.intelligence import (
    EvidenceCategoryState,
    EvidenceCompleteness,
)
from packages.schemas.source import PersistentSource


def evaluate_evidence_completeness(
    event: Event,
    source: PersistentSource | None = None,
    context_evidence: Sequence[ContextEvidence] | None = None,
) -> EvidenceCompleteness:
    """Audit the availability status across all expected evidence categories.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANT:
    Distinguishes missing/unavailable data (e.g. context provider offline) from
    evidence of absence (e.g. search conducted but no facility found in dataset).

    Args:
        event: Canonical Event domain object.
        source: Optional linked PersistentSource domain object.
        context_evidence: Optional sequence of associated ContextEvidence objects.

    Returns:
        EvidenceCompleteness: Detailed category breakdown and completeness ratio.
    """
    categories: list[EvidenceCategoryState] = []

    # 1. Observation category (FIRMS satellite detections)
    if event.detection_count >= 1:
        categories.append(
            EvidenceCategoryState(
                category="firms_detection",
                status=EvidenceAvailabilityState.AVAILABLE,
                details=f"{event.detection_count} canonical detections acquired.",
            )
        )
    else:
        categories.append(
            EvidenceCategoryState(
                category="firms_detection",
                status=EvidenceAvailabilityState.MISSING,
                details="Zero detections attached to event.",
            )
        )

    # 2. Persistence tracking category
    if source is not None:
        categories.append(
            EvidenceCategoryState(
                category="persistence_tracking",
                status=EvidenceAvailabilityState.AVAILABLE,
                details=(
                    f"Linked persistent source '{source.source_id}' with state "
                    f"'{source.persistence_state}' over "
                    f"{source.active_days_count} active days."
                ),
            )
        )
    else:
        categories.append(
            EvidenceCategoryState(
                category="persistence_tracking",
                status=EvidenceAvailabilityState.NOT_FOUND_IN_SOURCE,
                details="No longitudinal persistent source linked.",
            )
        )

    # 3. Contextual infrastructure category
    if context_evidence:
        # Check if any context evidence is AVAILABLE
        available_context = [
            c
            for c in context_evidence
            if c.availability_state == EvidenceAvailabilityState.AVAILABLE
        ]
        if available_context:
            categories.append(
                EvidenceCategoryState(
                    category="context_infrastructure",
                    status=EvidenceAvailabilityState.AVAILABLE,
                    details=(
                        f"{len(available_context)} nearby contextual features matched."
                    ),
                )
            )
        else:
            first_state = context_evidence[0].availability_state
            categories.append(
                EvidenceCategoryState(
                    category="context_infrastructure",
                    status=first_state,
                    details=f"Context evaluation status: '{first_state}'.",
                )
            )
    else:
        categories.append(
            EvidenceCategoryState(
                category="context_infrastructure",
                status=EvidenceAvailabilityState.NOT_FOUND_IN_SOURCE,
                details="No contextual evidence associated within search radius.",
            )
        )

    total_expected = len(categories)
    available_count = sum(
        1 for c in categories if c.status == EvidenceAvailabilityState.AVAILABLE
    )
    completeness_ratio = float(available_count) / float(total_expected)

    return EvidenceCompleteness(
        categories=categories,
        available_count=available_count,
        total_expected_count=total_expected,
        completeness_ratio=round(completeness_ratio, 4),
    )
