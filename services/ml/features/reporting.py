"""Reporting and diagnostic summary utilities for Phase 4 ML features.

Generates human-readable Markdown tables and machine-readable JSON summaries
of feature manifests, eligibility statuses, missingness distributions, and
ablation groups.
"""

from typing import Any

from packages.schemas.ml import FeatureDataset
from services.ml.features.registry import FeatureRegistry
from services.ml.features.standard_set import get_standard_feature_registry


def generate_feature_catalog_markdown(
    registry: FeatureRegistry | None = None,
) -> str:
    """Generate a GitHub Flavored Markdown table of all registered features."""
    reg = registry or get_standard_feature_registry()
    features = reg.list_features()

    header = (
        "| Feature Name | Group | Source | Unit | "
        "Lag (s) | Missingness | Leakage Risk | Status |"
    )
    separator = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    lines = [
        "# SIH26162 Phase 4 — Feature Catalog",
        "",
        header,
        separator,
    ]

    for f in features:
        unit_str = f.physical_unit or "—"
        lag_str = f"{f.availability_lag_seconds:.1f}"
        lines.append(
            f"| `{f.feature_name}` | {f.feature_group.value} | {f.source_entity} "
            f"| {unit_str} | {lag_str} | {f.missingness_handling.value} "
            f"| {f.leakage_risk.value} | **{f.eligibility_status.value}** |"
        )

    return "\n".join(lines)


def generate_feature_catalog_json(
    registry: FeatureRegistry | None = None,
) -> dict[str, Any]:
    """Generate a machine-readable JSON dictionary of all registered features."""
    reg = registry or get_standard_feature_registry()
    features = reg.list_features()

    catalog: list[dict[str, Any]] = []
    for f in features:
        catalog.append(
            {
                "feature_name": f.feature_name,
                "feature_group": f.feature_group.value,
                "eligibility_status": f.eligibility_status.value,
                "source_entity": f.source_entity,
                "derivation_description": f.derivation_description,
                "physical_unit": f.physical_unit,
                "availability_lag_seconds": f.availability_lag_seconds,
                "missingness_handling": f.missingness_handling.value,
                "allowed_for_training": f.allowed_for_training,
                "is_model_input": f.is_model_input,
                "leakage_risk": f.leakage_risk.value,
                "leakage_justification": f.leakage_justification,
                "version": f.version,
            }
        )

    return {
        "total_features": len(catalog),
        "features": catalog,
    }


def generate_dataset_quality_report(
    dataset: FeatureDataset,
) -> dict[str, Any]:
    """Generate comprehensive quality diagnostics for a materialized FeatureDataset."""
    manifest = dataset.manifest
    stats = dataset.summary_statistics

    return {
        "dataset_id": manifest.dataset_id,
        "dataset_version": manifest.dataset_version,
        "target_id": manifest.target_id,
        "feature_set_version": manifest.feature_set_version,
        "record_count": manifest.record_count,
        "sha256_hash": manifest.sha256_hash,
        "temporal_span": {
            "start": manifest.temporal_start.isoformat(),
            "end": manifest.temporal_end.isoformat(),
        },
        "split_strategy": manifest.split_strategy.value,
        "feature_groups": dataset.feature_groups,
        "missingness_summary": stats.get("missingness_by_feature", {}),
    }
