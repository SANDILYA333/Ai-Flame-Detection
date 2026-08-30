"""Dataset split extractor and anti-leakage feature selector for Phase 4 ML.

Extracts clean, strictly partitioned feature matrices (X_train, y_train, X_val, y_val,
X_test, y_test) from SupervisedDataset containers while enforcing anti-leakage filters:
- Strips identifiers (event_id, source_id, detection_id, facility_id).
- Consumes only approved model input features (is_model_input=True).
- Preserves showcase isolation (DATASET-003).
"""

from typing import Any

from packages.schemas.ml import (
    DatasetRowStatus,
    FeatureDefinition,
    LabeledFeatureRecord,
    SplitPartition,
    SupervisedDataset,
)

# Explicit identifier and metadata columns that MUST NEVER be passed as model inputs
PROHIBITED_METADATA_COLUMNS: frozenset[str] = frozenset(
    {
        "entity_id",
        "event_id",
        "source_id",
        "detection_id",
        "facility_id",
        "record_id",
        "id",
        "target",
        "target_id",
        "label",
        "label_value",
        "label_tier",
        "label_source",
        "label_confidence",
        "label_reason",
        "provenance",
        "split_partition",
        "split_key",
        "row_status",
        "exclusion_reason",
        "as_of_time",
        "acquisition_time",
        "timestamp",
        "started_at",
        "ended_at",
        "created_at",
    }
)


class DatasetSplitExtractor:
    """Extracts leakage-safe feature matrices from SupervisedDataset."""

    @classmethod
    def extract_split_matrices(
        cls,
        dataset: SupervisedDataset,
        target_id: str,
        feature_names: list[str] | None = None,
        include_unknown_train: bool = False,
        include_unknown_eval: bool = False,
    ) -> tuple[
        list[dict[str, Any]],
        list[str],
        list[str],
        list[dict[str, Any]],
        list[str],
        list[str],
        list[dict[str, Any]],
        list[str],
        list[str],
    ]:
        """Extract partitioned feature dictionaries, target vectors, and entity IDs.

        Args:
            dataset: SupervisedDataset container.
            target_id: Target specification identifier.
            feature_names: Optional explicit list of feature names to select.
            include_unknown_train: Whether to include 'unknown' label in training.
            include_unknown_eval: Whether to include 'unknown' label in evaluation.

        Returns:
            Tuple of:
            (X_train, y_train, ids_train,
             X_val, y_val, ids_val,
             X_test, y_test, ids_test)
        """
        # Determine allowed feature set
        allowed_features = cls._determine_feature_names(
            dataset.feature_definitions, feature_names
        )

        x_train: list[dict[str, Any]] = []
        y_train: list[str] = []
        ids_train: list[str] = []

        x_val: list[dict[str, Any]] = []
        y_val: list[str] = []
        ids_val: list[str] = []

        x_test: list[dict[str, Any]] = []
        y_test: list[str] = []
        ids_test: list[str] = []

        for record in dataset.records:
            # 1. Skip showcase-isolated records from benchmark partitions
            if (
                record.split_partition == SplitPartition.SHOWCASE_ISOLATION
                or record.row_status == DatasetRowStatus.SHOWCASE_ISOLATED
            ):
                continue

            # 2. Extract label for this target
            label_dec = record.labels.get(target_id)
            if label_dec is None:
                continue

            target_class = label_dec.assigned_class

            # 3. Clean feature dictionary (strictly approved features)
            clean_feats = cls._extract_record_features(record, allowed_features)

            # 4. Partition assignment
            if record.split_partition == SplitPartition.TRAIN:
                if record.row_status == DatasetRowStatus.EXCLUDED:
                    continue
                if target_class == "unknown" and not include_unknown_train:
                    continue
                x_train.append(clean_feats)
                y_train.append(target_class)
                ids_train.append(record.entity_id)

            elif record.split_partition == SplitPartition.VALIDATION:
                if target_class == "unknown" and not include_unknown_eval:
                    continue
                x_val.append(clean_feats)
                y_val.append(target_class)
                ids_val.append(record.entity_id)

            elif record.split_partition == SplitPartition.TEST:
                if target_class == "unknown" and not include_unknown_eval:
                    continue
                x_test.append(clean_feats)
                y_test.append(target_class)
                ids_test.append(record.entity_id)

        return (
            x_train,
            y_train,
            ids_train,
            x_val,
            y_val,
            ids_val,
            x_test,
            y_test,
            ids_test,
        )

    @classmethod
    def _extract_record_features(
        cls,
        record: LabeledFeatureRecord,
        allowed_feature_names: list[str],
    ) -> dict[str, Any]:
        """Extract clean feature dict from record, stripping prohibited columns."""
        raw_feats = record.feature_record.features
        clean: dict[str, Any] = {}

        for fname in allowed_feature_names:
            if fname in PROHIBITED_METADATA_COLUMNS:
                continue
            clean[fname] = raw_feats.get(fname)

        return clean

    @classmethod
    def _determine_feature_names(
        cls,
        definitions: list[FeatureDefinition] | None,
        explicit_features: list[str] | None,
    ) -> list[str]:
        """Resolve ordered list of model input feature names."""
        if explicit_features:
            return [
                f for f in explicit_features if f not in PROHIBITED_METADATA_COLUMNS
            ]

        if definitions:
            return [
                d.feature_name
                for d in definitions
                if d.is_model_input
                and d.feature_name not in PROHIBITED_METADATA_COLUMNS
            ]

        # Fallback to standard feature catalog approved model inputs
        from services.ml.features.standard_set import APPROVED_FEATURES

        return [
            d.feature_name
            for d in APPROVED_FEATURES
            if d.is_model_input and d.feature_name not in PROHIBITED_METADATA_COLUMNS
        ]
