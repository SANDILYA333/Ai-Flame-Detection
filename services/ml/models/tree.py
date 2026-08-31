"""Nonlinear Tree-Based ML Baseline Classifiers (B4 Tree Models).

Implements pure-Python, deterministic Decision Tree and Random Forest classifiers
with CART Gini impurity splitting, class-probability prediction, feature
importance (MDI), and lossless JSON-compatible parameter serialization for
ModelRegistry.
"""

import math
import random
from typing import Any

from services.ml.models.base import BaseMLModel


class _TreeNode:
    """Internal binary tree node for CART decision tree."""

    def __init__(
        self,
        feature_index: int | None = None,
        threshold: float | None = None,
        left: "_TreeNode | None" = None,
        right: "_TreeNode | None" = None,
        gain: float = 0.0,
        is_leaf: bool = False,
        class_probabilities: dict[str, float] | None = None,
        predicted_class: str | None = None,
        sample_count: int = 0,
    ) -> None:
        self.feature_index: int | None = feature_index
        self.threshold: float | None = threshold
        self.left: _TreeNode | None = left
        self.right: _TreeNode | None = right
        self.gain: float = gain
        self.is_leaf: bool = is_leaf
        self.class_probabilities: dict[str, float] = class_probabilities or {}
        self.predicted_class: str | None = predicted_class
        self.sample_count: int = sample_count

    def to_dict(self) -> dict[str, Any]:
        """Serialize tree node recursively to pure JSON-compatible dict."""
        return {
            "feature_index": self.feature_index,
            "threshold": self.threshold,
            "gain": self.gain,
            "is_leaf": self.is_leaf,
            "class_probabilities": self.class_probabilities,
            "predicted_class": self.predicted_class,
            "sample_count": self.sample_count,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "_TreeNode | None":
        """Deserialize tree node recursively from dict."""
        if data is None:
            return None
        node = cls(
            feature_index=data.get("feature_index"),
            threshold=data.get("threshold"),
            gain=float(data.get("gain", 0.0)),
            is_leaf=bool(data.get("is_leaf", False)),
            class_probabilities=data.get("class_probabilities", {}),
            predicted_class=data.get("predicted_class"),
            sample_count=int(data.get("sample_count", 0)),
        )
        node.left = cls.from_dict(data.get("left"))
        node.right = cls.from_dict(data.get("right"))
        return node


class DecisionTreeClassifier(BaseMLModel):
    """B4 Baseline: Multi-Class CART Decision Tree with Gini Impurity Splitting."""

    def __init__(
        self,
        max_depth: int = 5,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: float | int | str | None = None,
        random_seed: int = 42,
    ) -> None:
        super().__init__(model_name="DecisionTreeClassifier", random_seed=random_seed)
        self.max_depth: int = max_depth
        self.min_samples_split: int = max(2, min_samples_split)
        self.min_samples_leaf: int = max(1, min_samples_leaf)
        self.max_features: float | int | str | None = max_features

        self.root: _TreeNode | None = None
        self.n_features_: int = 0
        self.feature_importances_: list[float] = []

    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
    ) -> "DecisionTreeClassifier":
        """Fit decision tree on preprocessed numeric training matrix.

        Args:
            x_train: 2D float feature matrix [n_samples, n_features].
            y_train: Target class strings [n_samples].
            class_vocabulary: Optional class list.

        Returns:
            self: Fitted model.
        """
        if not x_train or not y_train:
            raise ValueError("x_train and y_train cannot be empty.")

        if isinstance(x_train[0], dict):
            raise TypeError(
                "DecisionTreeClassifier requires preprocessed 2D float matrix."
            )

        if len(x_train) != len(y_train):
            raise ValueError(
                f"Length mismatch: {len(x_train)} samples vs {len(y_train)} targets."
            )

        self.class_vocabulary = sorted(set(class_vocabulary or y_train))
        self.n_features_ = len(x_train[0])
        self.feature_importances_ = [0.0] * self.n_features_

        rng = random.Random(self.random_seed)
        sample_indices = list(range(len(x_train)))

        self.root = self._build_tree(
            x_train=x_train,
            y_train=y_train,
            indices=sample_indices,
            current_depth=0,
            rng=rng,
        )

        # Normalize MDI feature importances so sum = 1.0
        total_gain = sum(self.feature_importances_)
        if total_gain > 0:
            self.feature_importances_ = [
                g / total_gain for g in self.feature_importances_
            ]

        self.is_fitted = True
        return self

    def _build_tree(
        self,
        x_train: list[list[float]],
        y_train: list[str],
        indices: list[int],
        current_depth: int,
        rng: random.Random,
    ) -> _TreeNode:
        """Recursively build CART binary decision tree."""
        n_samples = len(indices)
        counts = self._class_counts(y_train, indices)
        leaf_probs = {
            cls_name: counts.get(cls_name, 0) / n_samples
            for cls_name in self.class_vocabulary
        }
        majority_cls = max(self.class_vocabulary, key=lambda c: counts.get(c, 0))

        # Check stopping criteria
        if (
            current_depth >= self.max_depth
            or n_samples < self.min_samples_split
            or len(counts) <= 1
        ):
            return _TreeNode(
                is_leaf=True,
                class_probabilities=leaf_probs,
                predicted_class=majority_cls,
                sample_count=n_samples,
            )

        # Find best split across eligible features
        best_gain = 0.0
        best_feat: int | None = None
        best_thresh: float | None = None
        best_left_idx: list[int] = []
        best_right_idx: list[int] = []

        current_gini = self._gini_impurity(counts, n_samples)
        eligible_features = self._select_candidate_features(rng)

        for feat_idx in eligible_features:
            values = sorted({x_train[i][feat_idx] for i in indices})
            if len(values) <= 1:
                continue

            for r in range(len(values) - 1):
                thresh = (values[r] + values[r + 1]) / 2.0
                left_idx = [i for i in indices if x_train[i][feat_idx] <= thresh]
                right_idx = [i for i in indices if x_train[i][feat_idx] > thresh]

                if (
                    len(left_idx) < self.min_samples_leaf
                    or len(right_idx) < self.min_samples_leaf
                ):
                    continue

                left_counts = self._class_counts(y_train, left_idx)
                right_counts = self._class_counts(y_train, right_idx)

                left_gini = self._gini_impurity(left_counts, len(left_idx))
                right_gini = self._gini_impurity(right_counts, len(right_idx))

                split_gini = (len(left_idx) / n_samples) * left_gini + (
                    len(right_idx) / n_samples
                ) * right_gini
                gain = current_gini - split_gini

                if gain > best_gain:
                    best_gain = gain
                    best_feat = feat_idx
                    best_thresh = thresh
                    best_left_idx = left_idx
                    best_right_idx = right_idx

        # If no valid split provides positive gain
        if best_feat is None or best_thresh is None or best_gain <= 1e-9:
            return _TreeNode(
                is_leaf=True,
                class_probabilities=leaf_probs,
                predicted_class=majority_cls,
                sample_count=n_samples,
            )

        # Accumulate weighted impurity reduction
        weighted_gain = best_gain * (n_samples / len(x_train))
        self.feature_importances_[best_feat] += weighted_gain

        left_child = self._build_tree(
            x_train=x_train,
            y_train=y_train,
            indices=best_left_idx,
            current_depth=current_depth + 1,
            rng=rng,
        )
        right_child = self._build_tree(
            x_train=x_train,
            y_train=y_train,
            indices=best_right_idx,
            current_depth=current_depth + 1,
            rng=rng,
        )

        return _TreeNode(
            feature_index=best_feat,
            threshold=best_thresh,
            left=left_child,
            right=right_child,
            gain=weighted_gain,
            is_leaf=False,
            class_probabilities=leaf_probs,
            predicted_class=majority_cls,
            sample_count=n_samples,
        )

    def _select_candidate_features(self, rng: random.Random) -> list[int]:
        """Select feature subset if max_features is configured."""
        all_feats = list(range(self.n_features_))
        if self.max_features is None:
            return all_feats

        n_sub: int
        if isinstance(self.max_features, int):
            n_sub = min(self.n_features_, max(1, self.max_features))
        elif isinstance(self.max_features, float):
            n_sub = min(
                self.n_features_, max(1, int(self.n_features_ * self.max_features))
            )
        elif self.max_features == "sqrt":
            n_sub = max(1, int(math.sqrt(self.n_features_)))
        elif self.max_features == "log2":
            n_sub = max(1, int(math.log2(self.n_features_)))
        else:
            return all_feats

        return rng.sample(all_feats, n_sub)

    @staticmethod
    def _class_counts(y_train: list[str], indices: list[int]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for idx in indices:
            cls_name = y_train[idx]
            counts[cls_name] = counts.get(cls_name, 0) + 1
        return counts

    @staticmethod
    def _gini_impurity(counts: dict[str, int], total_samples: int) -> float:
        if total_samples == 0:
            return 0.0
        sum_sq = sum((c / total_samples) ** 2 for c in counts.values())
        return 1.0 - sum_sq

    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Compute class probabilities for input sample matrix."""
        if not self.is_fitted or self.root is None:
            raise ValueError(
                "DecisionTreeClassifier must be fitted before predict_proba."
            )

        if not x_data:
            return []

        if isinstance(x_data[0], dict):
            raise TypeError("Expected preprocessed 2D float matrix.")

        if len(x_data[0]) != self.n_features_:
            raise ValueError(
                f"Feature dimension mismatch: expected {self.n_features_} "
                f"features, got {len(x_data[0])}."
            )

        results: list[dict[str, float]] = []
        for row in x_data:
            leaf = self._traverse_to_leaf(self.root, row)
            results.append(dict(leaf.class_probabilities))

        return results

    def predict(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[str]:
        """Predict class labels for given samples."""
        probs = self.predict_proba(x_data)
        predictions: list[str] = []

        for p_dict in probs:
            best_cls = max(self.class_vocabulary, key=lambda k: p_dict.get(k, 0.0))
            predictions.append(best_cls)

        return predictions

    def _traverse_to_leaf(self, node: _TreeNode, sample: list[float]) -> _TreeNode:
        """Traverse decision tree down to leaf node."""
        if node.is_leaf or node.feature_index is None or node.threshold is None:
            return node

        if sample[node.feature_index] <= node.threshold:
            if node.left is not None:
                return self._traverse_to_leaf(node.left, sample)
        else:
            if node.right is not None:
                return self._traverse_to_leaf(node.right, sample)

        return node

    def get_feature_importances(
        self, feature_names: list[str] | None = None
    ) -> dict[str, float]:
        """Return Mean Decrease in Impurity (Gini importance) dictionary."""
        if not self.is_fitted or not self.feature_importances_:
            return {}

        names = feature_names or [f"f_{i}" for i in range(self.n_features_)]
        importances: dict[str, float] = {}
        for j in range(min(self.n_features_, len(names))):
            importances[names[j]] = float(self.feature_importances_[j])

        return importances

    def get_parameters(self) -> dict[str, Any]:
        """Return tree hyperparameters and structure for serialization."""
        return {
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "min_samples_leaf": self.min_samples_leaf,
            "max_features": self.max_features,
            "random_seed": self.random_seed,
            "n_features": self.n_features_,
            "class_vocabulary": self.class_vocabulary,
            "feature_importances": self.feature_importances_,
            "tree_structure": self.root.to_dict() if self.root else None,
        }

    def set_parameters(self, params: dict[str, Any]) -> None:
        """Restore tree parameters and structure from serialized dict."""
        self.max_depth = int(params.get("max_depth", 5))
        self.min_samples_split = int(params.get("min_samples_split", 2))
        self.min_samples_leaf = int(params.get("min_samples_leaf", 1))
        self.max_features = params.get("max_features")
        self.random_seed = int(params.get("random_seed", 42))
        self.n_features_ = int(params.get("n_features", 0))
        self.class_vocabulary = list(params.get("class_vocabulary", []))
        self.feature_importances_ = list(params.get("feature_importances", []))
        self.root = _TreeNode.from_dict(params.get("tree_structure"))
        self.is_fitted = self.root is not None


class RandomForestClassifier(BaseMLModel):
    """B4 Ensemble: Bootstrap Aggregated Random Forest of Decision Trees."""

    def __init__(
        self,
        n_estimators: int = 10,
        max_depth: int = 5,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: float | int | str | None = "sqrt",
        random_seed: int = 42,
    ) -> None:
        super().__init__(model_name="RandomForestClassifier", random_seed=random_seed)
        self.n_estimators: int = max(1, n_estimators)
        self.max_depth: int = max_depth
        self.min_samples_split: int = max(2, min_samples_split)
        self.min_samples_leaf: int = max(1, min_samples_leaf)
        self.max_features: float | int | str | None = max_features

        self.trees: list[DecisionTreeClassifier] = []
        self.n_features_: int = 0
        self.feature_importances_: list[float] = []

    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
    ) -> "RandomForestClassifier":
        """Fit ensemble of trees using bootstrap sampling."""
        if not x_train or not y_train:
            raise ValueError("x_train and y_train cannot be empty.")

        if isinstance(x_train[0], dict):
            raise TypeError("Expected preprocessed 2D float matrix.")

        self.class_vocabulary = sorted(set(class_vocabulary or y_train))
        self.n_features_ = len(x_train[0])
        n_samples = len(x_train)

        self.trees = []
        importances_sum = [0.0] * self.n_features_

        for i in range(self.n_estimators):
            tree_seed = self.random_seed + i * 1013
            rng = random.Random(tree_seed)

            # Bootstrap sampling with replacement
            bootstrap_indices = [
                rng.randint(0, n_samples - 1) for _ in range(n_samples)
            ]
            x_boot = [x_train[idx] for idx in bootstrap_indices]
            y_boot = [y_train[idx] for idx in bootstrap_indices]

            tree = DecisionTreeClassifier(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                min_samples_leaf=self.min_samples_leaf,
                max_features=self.max_features,
                random_seed=tree_seed,
            )
            tree.fit(x_boot, y_boot, class_vocabulary=self.class_vocabulary)
            self.trees.append(tree)

            for j in range(self.n_features_):
                importances_sum[j] += tree.feature_importances_[j]

        # Average feature importances across ensemble
        self.feature_importances_ = [imp / self.n_estimators for imp in importances_sum]
        self.is_fitted = True
        return self

    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Average predicted class probability distributions across all trees."""
        if not self.is_fitted or not self.trees:
            raise ValueError(
                "RandomForestClassifier must be fitted before predict_proba."
            )

        if not x_data:
            return []

        if isinstance(x_data[0], dict):
            raise TypeError("Expected preprocessed 2D float matrix.")

        if len(x_data[0]) != self.n_features_:
            raise ValueError(
                f"Feature dimension mismatch: expected {self.n_features_} "
                f"features, got {len(x_data[0])}."
            )

        n_samples = len(x_data)
        ensemble_probs: list[dict[str, float]] = [
            dict.fromkeys(self.class_vocabulary, 0.0) for _ in range(n_samples)
        ]

        for tree in self.trees:
            t_probs = tree.predict_proba(x_data)
            for idx in range(n_samples):
                for cls_name in self.class_vocabulary:
                    ensemble_probs[idx][cls_name] += (
                        t_probs[idx].get(cls_name, 0.0) / self.n_estimators
                    )

        # Normalize to ensure numerical precision adds up strictly to 1.0
        for p_row in ensemble_probs:
            total = sum(p_row.values())
            if total > 0:
                for k in p_row:
                    p_row[k] /= total

        return ensemble_probs

    def predict(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[str]:
        """Predict class labels by majority ensemble vote."""
        probs = self.predict_proba(x_data)
        predictions: list[str] = []

        for p_dict in probs:
            best_cls = max(self.class_vocabulary, key=lambda k: p_dict.get(k, 0.0))
            predictions.append(best_cls)

        return predictions

    def get_feature_importances(
        self, feature_names: list[str] | None = None
    ) -> dict[str, float]:
        """Return Mean Decrease in Impurity averaged across all ensemble trees."""
        if not self.is_fitted or not self.feature_importances_:
            return {}

        names = feature_names or [f"f_{i}" for i in range(self.n_features_)]
        importances: dict[str, float] = {}
        for j in range(min(self.n_features_, len(names))):
            importances[names[j]] = float(self.feature_importances_[j])

        return importances

    def get_parameters(self) -> dict[str, Any]:
        """Return random forest hyperparameters and serialized trees."""
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "min_samples_leaf": self.min_samples_leaf,
            "max_features": self.max_features,
            "random_seed": self.random_seed,
            "n_features": self.n_features_,
            "class_vocabulary": self.class_vocabulary,
            "feature_importances": self.feature_importances_,
            "trees": [t.get_parameters() for t in self.trees],
        }

    def set_parameters(self, params: dict[str, Any]) -> None:
        """Restore random forest from serialized dictionary."""
        self.n_estimators = int(params.get("n_estimators", 10))
        self.max_depth = int(params.get("max_depth", 5))
        self.min_samples_split = int(params.get("min_samples_split", 2))
        self.min_samples_leaf = int(params.get("min_samples_leaf", 1))
        self.max_features = params.get("max_features")
        self.random_seed = int(params.get("random_seed", 42))
        self.n_features_ = int(params.get("n_features", 0))
        self.class_vocabulary = list(params.get("class_vocabulary", []))
        self.feature_importances_ = list(params.get("feature_importances", []))

        self.trees = []
        for t_params in params.get("trees", []):
            tree = DecisionTreeClassifier()
            tree.set_parameters(t_params)
            self.trees.append(tree)

        self.is_fitted = len(self.trees) > 0
