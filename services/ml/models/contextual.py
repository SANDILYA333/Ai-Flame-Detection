"""Deterministic contextual baseline classifier (B2 Baseline).

Applies explicit contextual distance thresholds and persistence rules from the
SIH26162 execution plan without complex machine learning.
"""

from typing import Any

from services.ml.models.base import BaseMLModel


class DeterministicContextualClassifier(BaseMLModel):
    """B2 Baseline applying deterministic contextual distance and persistence rules."""

    def __init__(
        self,
        proximity_threshold_m: float = 1000.0,
        random_seed: int = 42,
    ) -> None:
        super().__init__(
            model_name="DeterministicContextualClassifier", random_seed=random_seed
        )
        self.proximity_threshold_m: float = proximity_threshold_m
        self.target_type: str = "binary"  # "binary" or "multiclass"

    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
    ) -> "DeterministicContextualClassifier":
        """Record target vocabulary from training partition."""
        self.class_vocabulary = sorted(set(class_vocabulary or y_train))
        if "industrial" in self.class_vocabulary:
            self.target_type = "binary"
        else:
            self.target_type = "multiclass"

        self.is_fitted = True
        return self

    def predict(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[str]:
        """Predict class based on deterministic distance rules."""
        predictions: list[str] = []

        for row in x_data:
            if isinstance(row, dict):
                dist_ind = row.get("ctx_dist_osm_industrial_m")
                dist_og = row.get("ctx_dist_osm_oil_gas_m")
                dist_pwr = row.get("ctx_dist_osm_power_m")
                dist_wri = row.get("ctx_dist_wri_power_m")
                is_night = row.get("det_is_night")

                # Find closest industrial facility distance
                valid_dists = [
                    float(d)
                    for d in (dist_ind, dist_og, dist_pwr, dist_wri)
                    if d is not None and float(d) >= 0
                ]
                min_dist = min(valid_dists) if valid_dists else float("inf")

                is_near_facility = min_dist <= self.proximity_threshold_m

                if self.target_type == "binary":
                    pred = "industrial" if is_near_facility else "non_industrial"
                else:
                    # Multiclass phenomenon rule
                    if is_near_facility:
                        pred = "flare" if is_night else "industrial_thermal_source"
                    else:
                        pred = "vegetation_wildfire"

                predictions.append(pred)
            else:
                # Transformed float vector fallback
                predictions.append(
                    self.class_vocabulary[0] if self.class_vocabulary else "unknown"
                )

        return predictions

    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Return pseudo-probabilities based on deterministic classification."""
        preds = self.predict(x_data)
        probs: list[dict[str, float]] = []

        for p in preds:
            row_prob = dict.fromkeys(self.class_vocabulary, 0.0)
            if p in row_prob:
                row_prob[p] = 0.85
                other_count = len(self.class_vocabulary) - 1
                if other_count > 0:
                    rem = 0.15 / other_count
                    for c in self.class_vocabulary:
                        if c != p:
                            row_prob[c] = rem
            else:
                for c in self.class_vocabulary:
                    row_prob[c] = 1.0 / max(len(self.class_vocabulary), 1)
            probs.append(row_prob)

        return probs

    def get_parameters(self) -> dict[str, Any]:
        return {
            "proximity_threshold_m": self.proximity_threshold_m,
            "target_type": self.target_type,
            "class_vocabulary": self.class_vocabulary,
        }

    def set_parameters(self, params: dict[str, Any]) -> None:
        self.proximity_threshold_m = float(params.get("proximity_threshold_m", 1000.0))
        self.target_type = str(params.get("target_type", "binary"))
        self.class_vocabulary = list(params.get("class_vocabulary", []))
        self.is_fitted = True
