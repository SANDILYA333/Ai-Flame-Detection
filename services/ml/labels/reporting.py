"""Reporting and diagnostic summary utilities for Phase 4 ML labels and datasets.

Generates human-readable Markdown summaries and machine-readable JSON diagnostics
for target specifications, label distributions, quality tiers, exclusions, and splits.
"""

from typing import Any

from packages.schemas.ml import SupervisedDataset, TargetDefinition
from services.ml.labels.targets import get_standard_target_registry


def generate_target_catalog_markdown(
    targets: dict[str, TargetDefinition] | None = None,
) -> str:
    """Generate a GitHub Flavored Markdown table of all registered ML targets."""
    target_dict = targets or get_standard_target_registry()

    header = "| Target ID | Name | Type | Unit | Classes | Approved |"
    separator = "| :--- | :--- | :--- | :--- | :--- | :--- |"
    lines = [
        "# SIH26162 Phase 4 — Target Specifications",
        "",
        header,
        separator,
    ]

    for t in target_dict.values():
        classes_str = ", ".join(f"`{c}`" for c in t.class_vocabulary)
        app_str = "✓ Yes" if t.is_approved else "✗ Open"
        lines.append(
            f"| `{t.target_id}` | {t.name} | {t.target_type.value} | "
            f"{t.unit_of_prediction.value} | {classes_str} | **{app_str}** |"
        )

    return "\n".join(lines)


def generate_target_catalog_json(
    targets: dict[str, TargetDefinition] | None = None,
) -> dict[str, Any]:
    """Generate a machine-readable JSON dictionary of target specifications."""
    target_dict = targets or get_standard_target_registry()

    catalog: list[dict[str, Any]] = []
    for t in target_dict.values():
        catalog.append(
            {
                "target_id": t.target_id,
                "name": t.name,
                "target_type": t.target_type.value,
                "unit_of_prediction": t.unit_of_prediction.value,
                "class_vocabulary": t.class_vocabulary,
                "positive_definition": t.positive_definition,
                "negative_definition": t.negative_definition,
                "unknown_definition": t.unknown_definition,
                "is_approved": t.is_approved,
                "unresolved_reason": t.unresolved_reason,
            }
        )

    return {
        "total_targets": len(catalog),
        "targets": catalog,
    }


def generate_supervised_dataset_report(
    dataset: SupervisedDataset,
) -> dict[str, Any]:
    """Generate a complete diagnostic quality summary for a SupervisedDataset."""
    manifest = dataset.manifest
    split_m = dataset.split_manifest
    stats = dataset.summary_statistics

    return {
        "dataset_id": manifest.dataset_id,
        "dataset_version": manifest.dataset_version,
        "target_id": manifest.target_id,
        "feature_set_version": manifest.feature_set_version,
        "label_set_version": manifest.label_set_version,
        "sha256_hash": manifest.sha256_hash,
        "record_counts": {
            "total": len(dataset.records),
            "train": split_m.train_count,
            "validation": split_m.validation_count,
            "test": split_m.test_count,
            "showcase_isolated": split_m.showcase_count,
            "excluded": split_m.excluded_count,
        },
        "split_strategy": split_m.split_strategy.value,
        "class_distributions": stats.get("class_distribution_by_target", {}),
        "tier_distributions": stats.get("tier_distribution_by_target", {}),
        "exclusion_breakdown": stats.get("exclusion_breakdown", {}),
    }
