"""Comprehensive unit tests for Planck / Dozier Sub-Pixel Pyrometry."""

import math
import pytest
from packages.physics.pyrometry import DozierPyrometrySolver, PlanckPyrometryResult


def test_planck_radiance_physical_validity():
    """Verify Planck radiance calculation conforms to standard blackbody physics."""
    # At 3.74 um (MWIR) and 1000 K
    rad_mwir = DozierPyrometrySolver.planck_radiance(3.74, 1000.0)
    assert rad_mwir > 0.0
    assert math.isfinite(rad_mwir)

    # Temperature = 0 or negative -> 0.0
    assert DozierPyrometrySolver.planck_radiance(3.74, 0.0) == 0.0
    assert DozierPyrometrySolver.planck_radiance(3.74, -100.0) == 0.0


def test_dozier_inversion_converged_synthetic_flare():
    """Verify dual-band inversion for a compact high-temp flare signature."""
    # Synthetic hotspot: T_flame = 1200 K, fractional area p = 0.0003 (~42 m^2)
    # Background = 295 K
    # Forward model gives elevated MWIR (e.g. 335 K) and slightly elevated LWIR (296 K)
    res = DozierPyrometrySolver.solve(
        bright_mwir_k=335.0,
        bright_lwir_k=296.0,
        background_temp_k=295.0,
    )

    assert res.is_valid is True
    assert res.convergence_status == "CONVERGED"
    assert 450.0 <= res.emitter_temp_k <= 2200.0
    assert res.emitter_area_m2 > 0.0
    assert 0.0 < res.fractional_area_p <= 1.0
    assert math.isfinite(res.radiance_residual)
    assert res.radiance_residual < 0.1
    assert res.phenomenon_tag in [
        "HIGH_TEMP_COMPACT_FLARE_STACK",
        "INTERMEDIATE_COMBUSTION_SOURCE",
    ]


def test_dozier_inversion_safe_failure_invalid_inputs():
    """Verify solver safely fails on negative, NaN, non-finite, or cold inputs."""
    # NaN input
    res_nan = DozierPyrometrySolver.solve(float("nan"), 295.0)
    assert res_nan.is_valid is False
    assert res_nan.convergence_status == "INVALID_NON_FINITE_INPUT"

    # Negative input
    res_neg = DozierPyrometrySolver.solve(-300.0, 295.0)
    assert res_neg.is_valid is False

    # MWIR <= LWIR (no elevated hotspot)
    res_no_hotspot = DozierPyrometrySolver.solve(290.0, 295.0, background_temp_k=295.0)
    assert res_no_hotspot.is_valid is False
    assert res_no_hotspot.convergence_status == "NO_ELEVATED_HOTSPOT"
    assert res_no_hotspot.emitter_area_m2 == 0.0


def test_phenomenon_tagging():
    """Verify physical tagging rules for various fire/flare regimes."""
    # High temp compact flare
    tag1 = DozierPyrometrySolver.classify_phenomenon(
        emitter_temp_k=1300.0,
        emitter_area_m2=25.0,
        fractional_area_p=0.0002,
        residual_loss=0.001,
        is_converged=True,
    )
    assert tag1 == "HIGH_TEMP_COMPACT_FLARE_STACK"

    # Large area surface fire
    tag2 = DozierPyrometrySolver.classify_phenomenon(
        emitter_temp_k=750.0,
        emitter_area_m2=1200.0,
        fractional_area_p=0.01,
        residual_loss=0.005,
        is_converged=True,
    )
    assert tag2 == "LARGE_AREA_INDUSTRIAL_OR_SURFACE_FIRE"

    # Glint / false alarm / non-converged
    tag3 = DozierPyrometrySolver.classify_phenomenon(
        emitter_temp_k=320.0,
        emitter_area_m2=10.0,
        fractional_area_p=0.001,
        residual_loss=0.8,
        is_converged=False,
    )
    assert tag3 == "SUSPECTED_SOLAR_GLINT_OR_FALSE_ALARM"
