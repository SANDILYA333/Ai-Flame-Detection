"""Leakage-safe feature preprocessing and deterministic transformation service.

Fits imputation medians, normalization scaling, and categorical one-hot encodings
STRICTLY on the training partition (TRAIN ONLY) to eliminate lookahead leakage.
"""

import math
from typing import Any


class FeaturePreprocessor:
    """Preprocessor fitted on training data to transform features to vectors."""

    def __init__(self) -> None:
        self.is_fitted: bool = False
        self.feature_names: list[str] = []
        self.numeric_features: list[str] = []
        self.categorical_features: list[str] = []
        self.boolean_features: list[str] = []

        # Fitted statistics (TRAIN only)
        self.numeric_medians: dict[str, float] = {}
        self.numeric_means: dict[str, float] = {}
        self.numeric_stds: dict[str, float] = {}
        self.category_maps: dict[str, list[str]] = {}

        # Vector output column names after encoding
        self.output_column_names: list[str] = []

    def fit(
        self,
        x_train: list[dict[str, Any]],
        feature_names: list[str] | None = None,
    ) -> "FeaturePreprocessor":
        """Fit preprocessing statistics strictly on training data.

        Args:
            x_train: Training feature records.
            feature_names: Optional ordered list of feature names to consider.

        Returns:
            self: Fitted preprocessor.
        """
        if not x_train:
            raise ValueError("Cannot fit FeaturePreprocessor on empty x_train.")

        # Determine feature names
        if feature_names:
            self.feature_names = list(feature_names)
        else:
            all_keys: set[str] = set()
            for r in x_train:
                all_keys.update(r.keys())
            self.feature_names = sorted(all_keys)

        self.numeric_features = []
        self.categorical_features = []
        self.boolean_features = []

        # 1. Identify types from training data
        for fname in self.feature_names:
            vals = [r.get(fname) for r in x_train if r.get(fname) is not None]
            if not vals:
                # Default to numeric if empty
                self.numeric_features.append(fname)
                continue

            first_val = vals[0]
            if isinstance(first_val, bool):
                self.boolean_features.append(fname)
            elif isinstance(first_val, (int, float)):
                self.numeric_features.append(fname)
            else:
                self.categorical_features.append(fname)

        # 2. Fit Numeric Statistics (Medians, Means, Stds) on TRAIN
        self.numeric_medians = {}
        self.numeric_means = {}
        self.numeric_stds = {}

        for fname in self.numeric_features:
            num_vals: list[float] = []
            for r in x_train:
                v = r.get(fname)
                if (
                    v is not None
                    and isinstance(v, (int, float))
                    and not isinstance(v, bool)
                ):
                    num_vals.append(float(v))

            if num_vals:
                num_vals.sort()
                mid = len(num_vals) // 2
                med: float = (
                    num_vals[mid]
                    if len(num_vals) % 2 != 0
                    else (num_vals[mid - 1] + num_vals[mid]) / 2.0
                )
                mean_val: float = float(sum(num_vals) / len(num_vals))
                var_val: float = float(
                    sum((x - mean_val) ** 2 for x in num_vals) / max(len(num_vals), 1)
                )
                std_val: float = math.sqrt(var_val) if var_val > 1e-9 else 1.0

                self.numeric_medians[fname] = med
                self.numeric_means[fname] = mean_val
                self.numeric_stds[fname] = std_val
            else:
                self.numeric_medians[fname] = 0.0
                self.numeric_means[fname] = 0.0
                self.numeric_stds[fname] = 1.0

        # 3. Fit Categorical Categories on TRAIN
        self.category_maps = {}
        for fname in self.categorical_features:
            cat_set = {str(r[fname]) for r in x_train if r.get(fname) is not None}
            self.category_maps[fname] = sorted(cat_set)

        # 4. Construct output column names
        self.output_column_names = []
        for fname in self.numeric_features:
            self.output_column_names.append(f"num_{fname}")
        for fname in self.boolean_features:
            self.output_column_names.append(f"bool_{fname}")
        for fname in self.categorical_features:
            for cat in self.category_maps[fname]:
                self.output_column_names.append(f"cat_{fname}_{cat}")

        self.is_fitted = True
        return self

    def transform(self, x_data: list[dict[str, Any]]) -> list[list[float]]:
        """Transform feature records into normalized dense float matrices.

        Args:
            x_data: Feature records (from TRAIN, VALIDATION, or TEST).

        Returns:
            2D float matrix of transformed feature vectors.
        """
        if not self.is_fitted:
            raise ValueError(
                "FeaturePreprocessor must be fitted on TRAIN before transform."
            )

        matrix: list[list[float]] = []

        for row in x_data:
            vec: list[float] = []

            # 1. Numeric features (Impute median, standardize)
            for fname in self.numeric_features:
                val = row.get(fname)
                if val is None or not isinstance(val, (int, float)):
                    val = self.numeric_medians.get(fname, 0.0)
                else:
                    val = float(val)

                # Standardize using TRAIN mean & std
                mean_val = self.numeric_means.get(fname, 0.0)
                std_val = self.numeric_stds.get(fname, 1.0)
                norm_val = (val - mean_val) / std_val if std_val > 1e-9 else 0.0
                vec.append(norm_val)

            # 2. Boolean features
            for fname in self.boolean_features:
                bval = row.get(fname)
                if bval is None:
                    vec.append(0.0)
                else:
                    vec.append(1.0 if bool(bval) else 0.0)

            # 3. Categorical one-hot features
            for fname in self.categorical_features:
                row_cat = str(row.get(fname)) if row.get(fname) is not None else None
                for known_cat in self.category_maps.get(fname, []):
                    if row_cat is not None and row_cat == known_cat:
                        vec.append(1.0)
                    else:
                        vec.append(0.0)

            matrix.append(vec)

        return matrix

    def fit_transform(
        self,
        x_train: list[dict[str, Any]],
        feature_names: list[str] | None = None,
    ) -> list[list[float]]:
        """Fit on training data and return transformed matrix."""
        return self.fit(x_train, feature_names=feature_names).transform(x_train)

    def to_dict(self) -> dict[str, Any]:
        """Serialize preprocessor state to dictionary."""
        return {
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names,
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "boolean_features": self.boolean_features,
            "numeric_medians": self.numeric_medians,
            "numeric_means": self.numeric_means,
            "numeric_stds": self.numeric_stds,
            "category_maps": self.category_maps,
            "output_column_names": self.output_column_names,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeaturePreprocessor":
        """Deserialize preprocessor from state dictionary."""
        inst = cls()
        inst.is_fitted = bool(data.get("is_fitted", False))
        inst.feature_names = list(data.get("feature_names", []))
        inst.numeric_features = list(data.get("numeric_features", []))
        inst.categorical_features = list(data.get("categorical_features", []))
        inst.boolean_features = list(data.get("boolean_features", []))
        inst.numeric_medians = dict(data.get("numeric_medians", {}))
        inst.numeric_means = dict(data.get("numeric_means", {}))
        inst.numeric_stds = dict(data.get("numeric_stds", {}))
        inst.category_maps = {
            k: list(v) for k, v in data.get("category_maps", {}).items()
        }
        inst.output_column_names = list(data.get("output_column_names", []))
        return inst
