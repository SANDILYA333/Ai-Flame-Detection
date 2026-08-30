"""Real-Data Contextual Enrichment & Reference Label Adjudication (ML-012).

Orchestrates:
1. Geospatial context enrichment across external providers.
2. Reference evidence synthesis with explicit quality tiering.
3. Deterministic label adjudication under strict missingness rules.
4. Point-in-time temporal integrity preventing future context leakage.
"""

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.context.service import enrich_with_context
from packages.events.pipeline import (
    _audit_no_secrets,
    get_default_calibrated_scientific_config,
)
from packages.schemas.common import Coordinate
from packages.schemas.context import ContextEvidence
from packages.schemas.enums import ContextType, SourceRole
from packages.schemas.event import (
    Event,
    RealEnrichedEventDataset,
    RealThermalEventDataset,
)
from packages.schemas.ml import (
    LabelConflictPolicy,
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    ReferenceEvidence,
)
from services.ml.labels.constructor import LabelConstructor

INDUSTRIAL_CONTEXT_TYPES = {
    ContextType.INDUSTRIAL,
    ContextType.OIL_GAS,
    ContextType.POWER,
    ContextType.MINING,
}

NON_INDUSTRIAL_CONTEXT_TYPES = {
    ContextType.AGRICULTURAL,
    ContextType.FOREST_VEGETATION,
}


class RealContextLabelingService:
    """Service orchestrating real-data contextual enrichment and label adjudication."""

    @classmethod
    def load_context_features_from_fixture(
        cls,
        fixture_path: Path | str,
    ) -> tuple[list[ContextFeature], dict[str, str]]:
        """Load external context features from a deterministic JSON fixture snapshot.

        Returns:
            tuple[list[ContextFeature], dict[str, str]]:
                List of validated ContextFeature objects and mapping of
                provider -> raw SHA256 hash.
        """
        path = Path(fixture_path)
        if not path.exists():
            raise FileNotFoundError(f"Context fixture not found at {path}")

        raw_bytes = path.read_bytes()
        raw_hash = hashlib.sha256(raw_bytes).hexdigest()

        data = json.loads(raw_bytes.decode("utf-8"))
        _audit_no_secrets(data)

        raw_features = data.get("features", [])
        features = [ContextFeature.model_validate(f) for f in raw_features]

        # Map provider to snapshot hash
        snapshot_id = data.get("snapshot_metadata", {}).get("snapshot_id", path.stem)
        hashes = {snapshot_id: raw_hash}

        return features, hashes

    @classmethod
    def synthesize_reference_evidence(
        cls,
        events: Sequence[Event],
        context_by_event: dict[str, list[ContextEvidence]] | Sequence[ContextEvidence],
        config: ScientificConfig,
    ) -> list[ReferenceEvidence]:
        """Synthesize auditable ReferenceEvidence from matched ContextEvidence."""
        radius_meters = config.attribution_radius_meters or 1500.0

        # Handle both dict and sequence of ContextEvidence
        evidence_dict: dict[str, list[ContextEvidence]]
        if isinstance(context_by_event, dict):
            evidence_dict = context_by_event
        else:
            # Fallback for sequence: match by proximity to event centroid
            evidence_dict = {}
            for ev in events:
                evidence_dict[ev.event_id] = [
                    c
                    for c in context_by_event
                    if c.distance_to_event_meters is not None
                ]

        reference_items: list[ReferenceEvidence] = []

        for ev in events:
            ev_context = evidence_dict.get(ev.event_id, [])
            for ctx in ev_context:
                dist = (
                    ctx.distance_to_event_meters
                    if ctx.distance_to_event_meters is not None
                    else 999999.0
                )
                if dist > radius_meters:
                    continue

                claim_class: str | None = None
                tier = LabelTier.TIER_C_PROXY_WEAK
                confidence = 0.75

                if ctx.context_type in INDUSTRIAL_CONTEXT_TYPES:
                    claim_class = "industrial"
                    if dist <= 500.0 or (
                        ctx.bounding_box is not None
                        and ctx.bounding_box.min_latitude
                        <= ev.centroid_geometry.latitude
                        <= ctx.bounding_box.max_latitude
                        and ctx.bounding_box.min_longitude
                        <= ev.centroid_geometry.longitude
                        <= ctx.bounding_box.max_longitude
                    ):
                        tier = LabelTier.TIER_B_STRONG_EVIDENCE
                        confidence = 0.90
                    else:
                        tier = LabelTier.TIER_C_PROXY_WEAK
                        confidence = 0.75

                elif ctx.context_type in NON_INDUSTRIAL_CONTEXT_TYPES:
                    claim_class = "non_industrial"
                    tier = LabelTier.TIER_C_PROXY_WEAK
                    confidence = 0.75

                if claim_class is not None:
                    # Create deterministic evidence ID
                    raw_sig = (
                        f"{ev.event_id}:{ctx.context_id}:{claim_class}:{tier.value}"
                    )
                    ev_digest = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()
                    evidence_id = f"ref_ev_{ev_digest[:20]}"

                    reference_items.append(
                        ReferenceEvidence(
                            evidence_id=evidence_id,
                            source_name=ctx.source_type.upper(),
                            source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
                            entity_id=ev.event_id,
                            geometry=Coordinate(
                                latitude=ctx.geometry.latitude,
                                longitude=ctx.geometry.longitude,
                            ),
                            observed_at=ev.started_at,
                            claim_class=claim_class,
                            confidence_score=confidence,
                            tier=tier,
                            provenance_type=LabelProvenanceType.REFERENCE_LABEL,
                            evidence_payload={
                                "contributing_context_id": ctx.context_id,
                                "facility_name": ctx.facility_name or "",
                                "external_facility_id": ctx.external_facility_id or "",
                                "distance_meters": dist,
                                "context_type": ctx.context_type.value,
                                "source_provider": ctx.source_type,
                            },
                            notes=(
                                f"Spatial match to "
                                f"{ctx.facility_name or ctx.context_type.value} "
                                f"at {dist:.1f}m distance."
                            ),
                        )
                    )

        # Sort deterministically
        reference_items.sort(
            key=lambda r: (
                r.entity_id,
                r.source_name,
                r.tier.value,
                r.evidence_id,
            )
        )
        return reference_items

    @classmethod
    def adjudicate_labels(
        cls,
        events: Sequence[Event],
        reference_evidence: Sequence[ReferenceEvidence],
        target_ids: Sequence[str] | None = None,
        conflict_policy: LabelConflictPolicy = LabelConflictPolicy.TIER_PRECEDENCE,
        as_of_time: datetime | None = None,
    ) -> list[LabelDecision]:
        """Adjudicate formal LabelDecisions for events across prediction targets."""
        constructor = LabelConstructor(default_conflict_policy=conflict_policy)
        active_targets = (
            list(target_ids) if target_ids else ["target_industrial_segregation"]
        )

        decisions: list[LabelDecision] = []
        for ev in events:
            for target_id in active_targets:
                decision = constructor.construct_label(
                    target_id=target_id,
                    entity_id=ev.event_id,
                    evidence_items=reference_evidence,
                    conflict_policy=conflict_policy,
                    as_of_time=as_of_time,
                )
                decisions.append(decision)

        # Sort deterministically
        decisions.sort(
            key=lambda d: (
                d.target_id,
                d.entity_id,
                d.decision_id,
            )
        )
        return decisions

    @classmethod
    def enrich_and_adjudicate_dataset(
        cls,
        event_dataset: RealThermalEventDataset,
        candidate_features: Sequence[ContextFeature],
        snapshot_hashes: dict[str, str] | None = None,
        config: ScientificConfig | None = None,
        data_status: str = "OFFLINE_FIXTURE",
        dataset_id: str = "ds_real_enriched_v1.0.0",
        dataset_version: str = "v1.0.0",
    ) -> RealEnrichedEventDataset:
        """Execute complete contextual enrichment and label adjudication pipeline."""
        now = datetime.now(UTC)
        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        # 1. Enrich events with external geospatial context
        all_context_evidence: list[ContextEvidence] = []
        context_by_event: dict[str, list[ContextEvidence]] = {}
        for ev in event_dataset.events:
            ctx_items = enrich_with_context(
                target_id=ev.event_id,
                target_coord=ev.centroid_geometry,
                target_time=ev.started_at,
                candidate_features=candidate_features,
                config=active_config,
            )
            all_context_evidence.extend(ctx_items)
            context_by_event[ev.event_id] = ctx_items

        # Sort context evidence deterministically
        all_context_evidence.sort(
            key=lambda c: (
                c.source_type,
                c.context_id,
                c.distance_to_event_meters or 0.0,
            )
        )

        # 2. Synthesize Reference Evidence
        reference_evidence = cls.synthesize_reference_evidence(
            events=event_dataset.events,
            context_by_event=context_by_event,
            config=active_config,
        )

        # 3. Adjudicate Reference Labels
        labels = cls.adjudicate_labels(
            events=event_dataset.events,
            reference_evidence=reference_evidence,
            target_ids=["target_industrial_segregation"],
            conflict_policy=LabelConflictPolicy.TIER_PRECEDENCE,
            as_of_time=now,
        )

        # 4. Construct dataset container
        temp_dataset = RealEnrichedEventDataset(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            source_detection_dataset_id=event_dataset.detection_dataset_id,
            source_detection_dataset_hash=event_dataset.detection_dataset_hash,
            source_event_dataset_id=event_dataset.dataset_id,
            source_event_dataset_hash=event_dataset.canonical_dataset_hash,
            study_area_id=event_dataset.study_area_id,
            study_area_name=event_dataset.study_area_name,
            bounding_box=event_dataset.bounding_box,
            events=event_dataset.events,
            persistent_sources=event_dataset.persistent_sources,
            context_evidence=all_context_evidence,
            reference_evidence=reference_evidence,
            reference_labels=labels,
            context_snapshot_hashes=snapshot_hashes or {},
            config_fingerprint=active_config.compute_fingerprint(),
            canonical_dataset_hash="0" * 64,
            data_status=data_status,
            created_at=now,
        )

        canonical_hash = temp_dataset.compute_canonical_hash()
        final_dataset = temp_dataset.model_copy(
            update={"canonical_dataset_hash": canonical_hash}
        )

        # 5. Audit against secrets
        _audit_no_secrets(final_dataset.model_dump(mode="json"))

        return final_dataset

    @classmethod
    def enrich_and_adjudicate_point_in_time(
        cls,
        event_dataset: RealThermalEventDataset,
        as_of_time: datetime,
        candidate_features: Sequence[ContextFeature],
        config: ScientificConfig | None = None,
    ) -> RealEnrichedEventDataset:
        """Enrich and adjudicate events as of a cutoff timestamp (anti-leakage).

        - Events starting after as_of_time are excluded.
        - Context features valid in the future (valid_from > as_of) are excluded.
        """
        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        # Strict point-in-time event filtering
        valid_events = [e for e in event_dataset.events if e.started_at <= as_of_time]

        # Strict point-in-time context filtering
        valid_features = [
            f
            for f in candidate_features
            if (f.valid_from is None or f.valid_from <= as_of_time)
            and (f.valid_to is None or f.valid_to >= as_of_time)
        ]

        filtered_event_ds = event_dataset.model_copy(
            update={
                "events": valid_events,
                "event_count": len(valid_events),
            }
        )

        return cls.enrich_and_adjudicate_dataset(
            event_dataset=filtered_event_ds,
            candidate_features=valid_features,
            config=active_config,
            data_status="OFFLINE_FIXTURE",
            dataset_id=f"pit_enriched_{as_of_time.isoformat()}",
        )

    @classmethod
    def save_dataset(
        cls,
        dataset: RealEnrichedEventDataset,
        output_dir: Path | str,
    ) -> Path:
        """Save canonical enriched event dataset to filesystem with secret auditing."""
        dir_path = Path(output_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        data = dataset.model_dump(mode="json")
        _audit_no_secrets(data)

        out_file = dir_path / f"{dataset.dataset_id}.json"
        json_str = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
        out_file.write_text(json_str, encoding="utf-8")
        return out_file

    @classmethod
    def load_dataset(
        cls,
        file_path: Path | str,
    ) -> RealEnrichedEventDataset:
        """Load and verify canonical enriched event dataset from filesystem."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Enriched event dataset not found at {path}")

        json_str = path.read_text(encoding="utf-8")
        data = json.loads(json_str)
        _audit_no_secrets(data)

        dataset = RealEnrichedEventDataset.model_validate(data)

        # Verify canonical hash integrity
        computed_hash = dataset.compute_canonical_hash()
        if dataset.canonical_dataset_hash != computed_hash:
            raise ValueError(
                f"Enriched event dataset hash mismatch: "
                f"stored={dataset.canonical_dataset_hash}, "
                f"computed={computed_hash}."
            )

        return dataset
