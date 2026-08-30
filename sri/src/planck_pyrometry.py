"""
Planck & Dozier Sub-Pixel Thermal Pyrometry Engine (Scientific Version)
Solves the simultaneous Dozier equations using nonlinear least-squares optimization.
"""

import numpy as np
from scipy.optimize import minimize

C1 = 1.191042e8  # W * um^4 / (m^2 * sr)
C2 = 1.438775e4  # um * K

WAVELENGTH_MWIR = 3.74  # Band I4 (3.74 um)
WAVELENGTH_LWIR = 11.45 # Band I5 (11.45 um)

def planck_radiance(wavelength_um, temp_k):
    """Calculates spectral radiance for a given wavelength and temperature."""
    temp_k = max(temp_k, 100.0)
    exp_val = C2 / (wavelength_um * temp_k)
    exp_val = np.clip(exp_val, 1e-4, 50.0)
    return C1 / (wavelength_um**5 * (np.exp(exp_val) - 1.0))

def invert_dozier_subpixel(bt_mwir_k, bt_lwir_k, bg_temp_k=295.0, pixel_area_m2=140625.0):
    """
    Solves for True Fire Temperature (T_f) and Subpixel Fraction (p):
      L(MWIR, T_obs) = p * L(MWIR, T_f) + (1-p) * L(MWIR, T_bg)
      L(LWIR, T_obs) = p * L(LWIR, T_f) + (1-p) * L(LWIR, T_bg)
    """
    # Observed radiances
    l_mwir_obs = planck_radiance(WAVELENGTH_MWIR, bt_mwir_k)
    l_lwir_obs = planck_radiance(WAVELENGTH_LWIR, bt_lwir_k)
    
    l_mwir_bg = planck_radiance(WAVELENGTH_MWIR, bg_temp_k)
    l_lwir_bg = planck_radiance(WAVELENGTH_LWIR, bg_temp_k)
    
    # If MWIR is only slightly higher than LWIR, it is a low-temperature broad fire
    delta_t = bt_mwir_k - bt_lwir_k
    
    def loss(params):
        log_p, t_f = params
        p = 10**log_p
        
        l_mwir_pred = p * planck_radiance(WAVELENGTH_MWIR, t_f) + (1.0 - p) * l_mwir_bg
        l_lwir_pred = p * planck_radiance(WAVELENGTH_LWIR, t_f) + (1.0 - p) * l_lwir_bg
        
        err_mwir = (l_mwir_pred - l_mwir_obs) / l_mwir_obs
        err_lwir = (l_lwir_pred - l_lwir_obs) / l_lwir_obs
        
        return (err_mwir**2 + err_lwir**2)
    
    # Initial guess
    if delta_t > 40.0:  # Strong localized emitter (gas flare)
        x0 = [-4.0, 1500.0]
    else:  # Broad biomass fire
        x0 = [-1.5, 850.0]
        
    res = minimize(
        loss, 
        x0, 
        bounds=[(-7.0, 0.0), (500.0, 2200.0)],
        method='L-BFGS-B'
    )
    
    p_opt = 10**res.x[0]
    t_opt = float(res.x[1])
    area_opt = float(p_opt * pixel_area_m2)
    
    return round(t_opt, 1), round(area_opt, 2)

if __name__ == "__main__":
    t_f, a_f = invert_dozier_subpixel(bt_mwir_k=365.0, bt_lwir_k=305.0)
    print(f"Industrial Flare Example -> Temp: {t_f} K, Flame Area: {a_f} m^2")
    
    t_w, a_w = invert_dozier_subpixel(bt_mwir_k=325.0, bt_lwir_k=315.0)
    print(f"Biomass / Wildfire Example -> Temp: {t_w} K, Flame Area: {a_w} m^2")
