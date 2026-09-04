"""Planck / Dozier dual-band radiance inversion and thermal pyrometry (PHYS-001).

Implements the physical inversion for estimating sub-pixel fire/flame temperature
and sub-pixel active fire area from dual-band thermal infrared observations
(VIIRS I4 3.74 um / I5 11.45 um or MODIS B21/B22 and B31/B32) using the Dozier (1981)
sub-pixel mixture model:

    L_obs(lambda) = p * B(lambda, T_flame) + (1 - p) * B(lambda, T_bg)

where:
    p = A_flame / A_pixel (fractional sub-pixel area)
    B(lambda, T) = C1 / (lambda^5 * (exp(C2 / (lambda * T)) - 1))
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanckPyrometryResult:
    """Telemetry package from Dozier dual-band radiance inversion."""

    emitter_temp_k: float
    emitter_area_m2: float
    fractional_area_p: float
    background_temp_k: float
    mwir_radiance_observed: float
    lwir_radiance_observed: float
    mwir_radiance_model: float
    lwir_radiance_model: float
    radiance_residual: float
    is_valid: bool
    convergence_status: str
    phenomenon_tag: str
    pixel_area_m2: float = 140625.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize pyrometry telemetry to JSON-compatible dictionary."""
        return {
            "emitter_temp_k": round(self.emitter_temp_k, 1),
            "emitter_area_m2": round(self.emitter_area_m2, 2),
            "fractional_area_p": round(self.fractional_area_p, 8),
            "background_temp_k": round(self.background_temp_k, 1),
            "mwir_radiance_observed": round(self.mwir_radiance_observed, 4),
            "lwir_radiance_observed": round(self.lwir_radiance_observed, 4),
            "mwir_radiance_model": round(self.mwir_radiance_model, 4),
            "lwir_radiance_model": round(self.lwir_radiance_model, 4),
            "radiance_residual": round(self.radiance_residual, 6),
            "is_valid": self.is_valid,
            "convergence_status": self.convergence_status,
            "phenomenon_tag": self.phenomenon_tag,
            "pixel_area_m2": round(self.pixel_area_m2, 1),
        }


class DozierPyrometrySolver:
    """Nonlinear solver for subpixel fire temperature and area using Dozier (1981).

    Planck's Law: B(lambda, T) = C1 / (lambda^5 * (exp(C2 / (lambda * T)) - 1))
    """

    C1: float = 1.19104297e8  # W * um^4 / (m^2 * sr)
    C2: float = 14387.77  # um * K
    LAMBDA_MWIR: float = 3.74  # um (VIIRS I4 central wavelength)
    LAMBDA_LWIR: float = 11.45  # um (VIIRS I5 central wavelength)
    PIXEL_AREA_M2: float = 375.0 * 375.0  # 140,625 m^2 (VIIRS nominal 375m)

    MIN_FLAME_TEMP_K: float = 450.0
    MAX_FLAME_TEMP_K: float = 2200.0
    MIN_LOG10_P: float = -7.0  # p >= 1e-7 (0.014 m^2 in 375m pixel)
    MAX_LOG10_P: float = 0.0  # p <= 1.0

    @classmethod
    def planck_radiance(cls, wavelength_um: float, temp_k: float) -> float:
        """Compute blackbody spectral radiance in W / (m^2 * sr * um)."""
        if temp_k <= 0.0 or not math.isfinite(temp_k):
            return 0.0
        exponent = cls.C2 / (wavelength_um * temp_k)
        if exponent > 700.0:
            return 0.0
        try:
            return cls.C1 / ((wavelength_um**5) * (math.expm1(exponent)))
        except OverflowError:
            return 0.0

    @classmethod
    def brightness_to_radiance(
        cls, wavelength_um: float, brightness_temp_k: float
    ) -> float:
        """Convert equivalent blackbody brightness temperature to spectral radiance."""
        return cls.planck_radiance(wavelength_um, brightness_temp_k)

    @classmethod
    def classify_phenomenon(
        cls,
        emitter_temp_k: float,
        emitter_area_m2: float,
        fractional_area_p: float,
        residual_loss: float,
        is_converged: bool,
    ) -> str:
        """Assign physical interpretation tag based on temperature and spatial footprint."""
        if not is_converged or emitter_temp_k < 400.0 or residual_loss > 0.5:
            return "SUSPECTED_SOLAR_GLINT_OR_FALSE_ALARM"

        if emitter_temp_k >= 1000.0 and emitter_area_m2 <= 150.0:
            return "HIGH_TEMP_COMPACT_FLARE_STACK"

        if emitter_area_m2 >= 500.0 or emitter_temp_k < 650.0:
            return "LARGE_AREA_INDUSTRIAL_OR_SURFACE_FIRE"

        return "INTERMEDIATE_COMBUSTION_SOURCE"

    @classmethod
    def solve(
        cls,
        bright_mwir_k: float,
        bright_lwir_k: float,
        background_temp_k: float = 295.0,
        pixel_area_m2: float | None = None,
    ) -> PlanckPyrometryResult:
        """Invert dual-band measurements to estimate emitter temperature and area.

        Uses relative radiance error loss optimization:
            Loss = ((L_model_mwir - L_obs_mwir) / L_obs_mwir)^2
                 + ((L_model_lwir - L_obs_lwir) / L_obs_lwir)^2

        Args:
            bright_mwir_k: Observed brightness temperature in MWIR band (Kelvin).
            bright_lwir_k: Observed brightness temperature in LWIR band (Kelvin).
            background_temp_k: Estimated ambient background temperature (Kelvin).
            pixel_area_m2: Ground footprint pixel area in m^2 (default 140,625 m^2).

        Returns:
            PlanckPyrometryResult with temperature, area, fractional p, and status.
        """
        pixel_area = pixel_area_m2 or cls.PIXEL_AREA_M2

        # 1. Input Sanity Checks
        if (
            not math.isfinite(bright_mwir_k)
            or not math.isfinite(bright_lwir_k)
            or not math.isfinite(background_temp_k)
            or bright_mwir_k <= 0.0
            or bright_lwir_k <= 0.0
            or background_temp_k <= 0.0
        ):
            return PlanckPyrometryResult(
                emitter_temp_k=0.0,
                emitter_area_m2=0.0,
                fractional_area_p=0.0,
                background_temp_k=background_temp_k,
                mwir_radiance_observed=0.0,
                lwir_radiance_observed=0.0,
                mwir_radiance_model=0.0,
                lwir_radiance_model=0.0,
                radiance_residual=float("inf"),
                is_valid=False,
                convergence_status="INVALID_NON_FINITE_INPUT",
                phenomenon_tag="SUSPECTED_SOLAR_GLINT_OR_FALSE_ALARM",
                pixel_area_m2=pixel_area,
            )

        # Observed radiances
        l_mwir_obs = cls.brightness_to_radiance(cls.LAMBDA_MWIR, bright_mwir_k)
        l_lwir_obs = cls.brightness_to_radiance(cls.LAMBDA_LWIR, bright_lwir_k)
        l_mwir_bg = cls.brightness_to_radiance(cls.LAMBDA_MWIR, background_temp_k)
        l_lwir_bg = cls.brightness_to_radiance(cls.LAMBDA_LWIR, background_temp_k)

        if l_mwir_obs <= 0.0 or l_lwir_obs <= 0.0:
            return PlanckPyrometryResult(
                emitter_temp_k=bright_mwir_k,
                emitter_area_m2=0.0,
                fractional_area_p=0.0,
                background_temp_k=background_temp_k,
                mwir_radiance_observed=l_mwir_obs,
                lwir_radiance_observed=l_lwir_obs,
                mwir_radiance_model=l_mwir_obs,
                lwir_radiance_model=l_lwir_obs,
                radiance_residual=0.0,
                is_valid=False,
                convergence_status="ZERO_RADIANCE",
                phenomenon_tag="SUSPECTED_SOLAR_GLINT_OR_FALSE_ALARM",
                pixel_area_m2=pixel_area,
            )

        # If MWIR <= background or MWIR <= LWIR, no elevated subpixel hotspot exists
        if l_mwir_obs <= l_mwir_bg or bright_mwir_k <= bright_lwir_k:
            return PlanckPyrometryResult(
                emitter_temp_k=bright_mwir_k,
                emitter_area_m2=0.0,
                fractional_area_p=0.0,
                background_temp_k=background_temp_k,
                mwir_radiance_observed=l_mwir_obs,
                lwir_radiance_observed=l_lwir_obs,
                mwir_radiance_model=l_mwir_obs,
                lwir_radiance_model=l_lwir_obs,
                radiance_residual=0.0,
                is_valid=False,
                convergence_status="NO_ELEVATED_HOTSPOT",
                phenomenon_tag="SUSPECTED_SOLAR_GLINT_OR_FALSE_ALARM",
                pixel_area_m2=pixel_area,
            )

        # 2. Bounded Dual-Band Parameter Search
        # Scan temperature T_f in [MIN_FLAME_TEMP_K, MAX_FLAME_TEMP_K]
        # and analytically solve for p_mwir, then evaluate relative radiance loss
        best_t = bright_mwir_k
        best_p = 0.0
        min_loss = float("inf")

        # Fine-grained multi-resolution temperature scan
        # Coarse step: 10 K
        t_start = int(max(cls.MIN_FLAME_TEMP_K, bright_mwir_k))
        t_end = int(cls.MAX_FLAME_TEMP_K)

        for t_k in range(t_start, t_end + 1, 5):
            t_flame = float(t_k)
            l_mwir_fire = cls.planck_radiance(cls.LAMBDA_MWIR, t_flame)
            l_lwir_fire = cls.planck_radiance(cls.LAMBDA_LWIR, t_flame)

            denom_mwir = l_mwir_fire - l_mwir_bg
            if denom_mwir <= 0.0:
                continue

            # Fractional area required to match MWIR
            p = (l_mwir_obs - l_mwir_bg) / denom_mwir
            if not (10**cls.MIN_LOG10_P <= p <= 1.0):
                continue

            # Forward model LWIR radiance
            l_lwir_pred = p * l_lwir_fire + (1.0 - p) * l_lwir_bg
            l_mwir_pred = p * l_mwir_fire + (1.0 - p) * l_mwir_bg

            # Relative radiance quadratic loss
            err_mwir = (l_mwir_pred - l_mwir_obs) / l_mwir_obs
            err_lwir = (l_lwir_pred - l_lwir_obs) / l_lwir_obs
            loss = (err_mwir**2) + (err_lwir**2)

            if loss < min_loss:
                min_loss = loss
                best_t = t_flame
                best_p = p

        # Refine around best_t with 0.5 K resolution
        t_refine_min = max(cls.MIN_FLAME_TEMP_K, best_t - 6.0)
        t_refine_max = min(cls.MAX_FLAME_TEMP_K, best_t + 6.0)
        t_curr = t_refine_min

        while t_curr <= t_refine_max:
            l_mwir_fire = cls.planck_radiance(cls.LAMBDA_MWIR, t_curr)
            l_lwir_fire = cls.planck_radiance(cls.LAMBDA_LWIR, t_curr)

            denom_mwir = l_mwir_fire - l_mwir_bg
            if denom_mwir > 0.0:
                p = (l_mwir_obs - l_mwir_bg) / denom_mwir
                if 10**cls.MIN_LOG10_P <= p <= 1.0:
                    l_lwir_pred = p * l_lwir_fire + (1.0 - p) * l_lwir_bg
                    l_mwir_pred = p * l_mwir_fire + (1.0 - p) * l_mwir_bg
                    err_mwir = (l_mwir_pred - l_mwir_obs) / l_mwir_obs
                    err_lwir = (l_lwir_pred - l_lwir_obs) / l_lwir_obs
                    loss = (err_mwir**2) + (err_lwir**2)

                    if loss < min_loss:
                        min_loss = loss
                        best_t = t_curr
                        best_p = p

            t_curr += 0.5

        # Final model outputs
        l_mwir_fire_final = cls.planck_radiance(cls.LAMBDA_MWIR, best_t)
        l_lwir_fire_final = cls.planck_radiance(cls.LAMBDA_LWIR, best_t)
        l_mwir_mod = best_p * l_mwir_fire_final + (1.0 - best_p) * l_mwir_bg
        l_lwir_mod = best_p * l_lwir_fire_final + (1.0 - best_p) * l_lwir_bg
        emitter_area = best_p * pixel_area

        is_converged = min_loss < 0.1 and best_p > 0.0

        phenomenon = cls.classify_phenomenon(
            emitter_temp_k=best_t,
            emitter_area_m2=emitter_area,
            fractional_area_p=best_p,
            residual_loss=min_loss,
            is_converged=is_converged,
        )

        return PlanckPyrometryResult(
            emitter_temp_k=best_t,
            emitter_area_m2=emitter_area,
            fractional_area_p=best_p,
            background_temp_k=background_temp_k,
            mwir_radiance_observed=l_mwir_obs,
            lwir_radiance_observed=l_lwir_obs,
            mwir_radiance_model=l_mwir_mod,
            lwir_radiance_model=l_lwir_mod,
            radiance_residual=min_loss,
            is_valid=is_converged,
            convergence_status="CONVERGED" if is_converged else "NON_CONVERGED",
            phenomenon_tag=phenomenon,
            pixel_area_m2=pixel_area,
        )
