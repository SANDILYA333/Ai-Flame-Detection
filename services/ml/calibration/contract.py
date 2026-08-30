"""Probability calibration contract manager for Phase 4 ML.

Validates calibration fitting partitions (strictly preventing test set fitting)
and computes Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).
"""

from packages.schemas.ml import (
    CalibrationContract,
    CalibrationMethod,
    SplitPartition,
)


class CalibrationManager:
    """Manager validating calibration parameters and computing calibration errors."""

    @staticmethod
    def validate_fitting_partition(partition: SplitPartition) -> None:
        """Enforce: Calibration must NEVER fit on TEST partition."""
        if partition == SplitPartition.TEST:
            raise ValueError(
                "Calibration fitting on TEST partition is strictly prohibited."
            )

    @staticmethod
    def compute_calibration_error(
        y_true_binary: list[int],
        y_prob: list[float],
        n_bins: int = 10,
    ) -> tuple[float, float]:
        """Compute Expected Calibration Error and Maximum Calibration Error."""
        if not y_true_binary or not y_prob:
            return 0.0, 0.0

        n_samples = len(y_true_binary)
        bin_boundaries = [i / n_bins for i in range(n_bins + 1)]

        ece = 0.0
        mce = 0.0

        for b in range(n_bins):
            bin_lower = bin_boundaries[b]
            bin_upper = bin_boundaries[b + 1]

            bin_indices = [
                i
                for i, p in enumerate(y_prob)
                if (bin_lower <= p < bin_upper) or (b == n_bins - 1 and p == bin_upper)
            ]

            bin_size = len(bin_indices)
            if bin_size > 0:
                bin_acc = sum(y_true_binary[i] for i in bin_indices) / bin_size
                bin_conf = sum(y_prob[i] for i in bin_indices) / bin_size
                abs_err = abs(bin_acc - bin_conf)

                ece += (bin_size / n_samples) * abs_err
                if abs_err > mce:
                    mce = abs_err

        return float(ece), float(mce)

    @classmethod
    def create_contract(
        cls,
        calibration_id: str,
        method: CalibrationMethod,
        fitting_dataset_id: str,
        fitting_split_partition: SplitPartition,
        is_fitted: bool = False,
        expected_calibration_error: float | None = None,
        maximum_calibration_error: float | None = None,
        brier_score_before: float | None = None,
        brier_score_after: float | None = None,
    ) -> CalibrationContract:
        """Create and validate a CalibrationContract."""
        cls.validate_fitting_partition(fitting_split_partition)
        return CalibrationContract(
            calibration_id=calibration_id,
            method=method,
            fitting_dataset_id=fitting_dataset_id,
            fitting_split_partition=fitting_split_partition,
            is_fitted=is_fitted,
            expected_calibration_error=expected_calibration_error,
            maximum_calibration_error=maximum_calibration_error,
            brier_score_before=brier_score_before,
            brier_score_after=brier_score_after,
        )
