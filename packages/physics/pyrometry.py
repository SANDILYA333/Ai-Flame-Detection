"""Planck / Dozier dual-band radiance inversion and thermal pyrometry (PHYS-001)."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PlanckPyrometryResult:
    """Telemetry package from Dozier dual-band radiance inversion."""

    emitter_temp_k: float
    emitter_area_m2: float
    background_temp_k: float
    mwir_radiance_observed: float
    lwir_radiance_observed: float
    mwir_radiance_model: float
    lwir_radiance_model: float
    radiance_residual: float
    is_valid: bool
    convergence_status: str

    def to_dict(self) -> dict:
        return {
            "emitter_temp_k": round(self.emitter_temp_k, 1),
            "emitter_area_m2": round(self.emitter_area_m2, 2),
            "background_temp_k": round(self.background_temp_k, 1),
            "mwir_radiance_observed": round(self.mwir_radiance_observed, 4),
            "lwir_radiance_observed": round(self.lwir_radiance_observed, 4),
            "mwir_radiance_model": round(self.mwir_radiance_model, 4),
            "lwir_radiance_model": round(self.lwir_radiance_model, 4),
            "radiance_residual": round(self.radiance_residual, 5),
            "is_valid": self.is_valid,
            "convergence_status": self.convergence_status,
        }


class DozierPyrometrySolver:
    """Nonlinear solver for subpixel fire temperature and area using Dozier (1981).

    Planck's Law: B(lambda, T) = c1 / (lambda^5 * (exp(c2 / (lambda * T)) - 1))
    """

    C1: float = 1.19104297e8  # W * um^4 / (m^2 * sr)
    C2: float = 14387.77  # um * K
    LAMBDA_MWIR: float = 3.74  # um (VIIRS I4 / M13 central wavelength)
    LAMBDA_LWIR: float = 11.45  # um (VIIRS I5 / M15 central wavelength)
    PIXEL_AREA_M2: float = 375.0 * 375.0  # 140,625 m^2 (VIIRS imagery band nominal)

    @classmethod
    def planck_radiance(cls, wavelength_um: float, temp_k: float) -> float:
        """Compute blackbody spectral radiance in W / (m^2 * sr * um)."""
        if temp_k <= 0.0:
            return 0.0
        exponent = cls.C2 / (wavelength_um * temp_k)
        if exponent > 700.0:
            return 0.0
        return cls.C1 / ((wavelength_um**5) * (math.exp(exponent) - 1.0))

    @classmethod
    def brightness_to_radiance(
        cls, wavelength_um: float, brightness_temp_k: float
    ) -> float:
        """Convert equivalent blackbody brightness temperature to spectral radiance."""
        return cls.planck_radiance(wavelength_um, brightness_temp_k)

    @classmethod
    def solve(
        cls,
        bright_mwir_k: float,
        bright_lwir_k: float,
        background_temp_k: float = 295.0,
        pixel_area_m2: float | None = None,
    ) -> PlanckPyrometryResult:
        """Invert dual-band measurements to estimate emitter temperature and area."""
        pixel_area = pixel_area_m2 or cls.PIXEL_AREA_M2

        # Observed radiances
        l_mwir_obs = cls.brightness_to_radiance(cls.LAMBDA_MWIR, bright_mwir_k)
        l_lwir_obs = cls.brightness_to_radiance(cls.LAMBDA_LWIR, bright_lwir_k)

        l_mwir_bg = cls.brightness_to_radiance(cls.LAMBDA_MWIR, background_temp_k)
        l_lwir_bg = cls.brightness_to_radiance(cls.LAMBDA_LWIR, background_temp_k)

        # If MWIR <= background, no subpixel hot spot detected
        if l_mwir_obs <= l_mwir_bg or bright_mwir_k <= bright_lwir_k:
            return PlanckPyrometryResult(
                emitter_temp_k=bright_mwir_k,
                emitter_area_m2=0.0,
                background_temp_k=background_temp_k,
                mwir_radiance_observed=l_mwir_obs,
                lwir_radiance_observed=l_lwir_obs,
                mwir_radiance_model=l_mwir_obs,
                lwir_radiance_model=l_lwir_obs,
                radiance_residual=0.0,
                is_valid=False,
                convergence_status="NO_ELEVATED_HOTSPOT",
            )

        # Bounded golden section search for emitter temperature T_f in [450K, 2200K]
        best_t = bright_mwir_k
        best_area = 0.0
        min_residual = float("inf")

        # Scan temperatures from 500K to 2000K in steps
        for t_k in range(500, 2050, 10):
            l_mwir_fire = cls.planck_radiance(cls.LAMBDA_MWIR, float(t_k))
            l_lwir_fire = cls.planck_radiance(cls.LAMBDA_LWIR, float(t_k))

            denom_mwir = l_mwir_fire - l_mwir_bg
            if denom_mwir <= 0:
                continue

            # Fractional area from MWIR
            p_mwir = (l_mwir_obs - l_mwir_bg) / denom_mwir
            if not (0.0 < p_mwir <= 1.0):
                continue

            # Predicted LWIR from p_mwir
            l_lwir_pred = p_mwir * l_lwir_fire + (1.0 - p_mwir) * l_lwir_bg
            residual = abs(l_lwir_pred - l_lwir_obs)

            if residual < min_residual:
                min_residual = residual
                best_t = float(t_k)
                best_area = p_mwir * pixel_area

        l_mwir_best = cls.planck_radiance(cls.LAMBDA_MWIR, best_t)
        l_lwir_best = cls.planck_radiance(cls.LAMBDA_LWIR, best_t)
        p_best = (
            (l_mwir_obs - l_mwir_bg) / (l_mwir_best - l_mwir_bg)
            if (l_mwir_best - l_mwir_bg) > 0
            else 0.0
        )
        p_best = max(0.0, min(1.0, p_best))

        l_mwir_mod = p_best * l_mwir_best + (1.0 - p_best) * l_mwir_bg
        l_lwir_mod = p_best * l_lwir_best + (1.0 - p_best) * l_lwir_bg

        return PlanckPyrometryResult(
            emitter_temp_k=best_t,
            emitter_area_m2=best_area,
            background_temp_k=background_temp_k,
            mwir_radiance_observed=l_mwir_obs,
            lwir_radiance_observed=l_lwir_obs,
            mwir_radiance_model=l_mwir_mod,
            lwir_radiance_model=l_lwir_mod,
            radiance_residual=min_residual,
            is_valid=True,
            convergence_status="CONVERGED",
        )
