# 🔬 Scientific Contracts & Mathematical Foundations

## 1. Planck Sub-Pixel Pyrometry (Dozier Dual-Band Inversion)

Satellite infrared sensors measure integrated radiance across an entire pixel footprint (e.g. $375\text{ m} \times 375\text{ m}$ for VIIRS I-bands). When a sub-pixel fire is present, the observed radiance is a weighted mixture of the background surface temperature and the active flaming area.

### Mathematical Formulation
Let:
* $\lambda_4 = 3.74\,\mu\text{m}$ (Medium-Wave Infrared - MWIR)
* $\lambda_5 = 11.45\,\mu\text{m}$ (Long-Wave Infrared - LWIR)
* $p = \frac{A_{\text{flame}}}{A_{\text{pixel}}}$ (Fractional area occupied by the fire)
* $T_{\text{bg}}$ = Background ambient temperature (typically $295\text{ K} - 305\text{ K}$)
* $T_{\text{flame}}$ = True flame combustion temperature ($\text{K}$)

Planck's Blackbody Spectral Radiance function $B(\lambda, T)$ is given by:

$$B(\lambda, T) = \frac{c_1}{\lambda^5 \left( \exp\left(\frac{c_2}{\lambda T}\right) - 1 \right)}$$

Where:
* $c_1 = 2 h c^2 = 1.191042 \times 10^8\,\text{W}\cdot\mu\text{m}^4\cdot\text{m}^{-2}\cdot\text{sr}^{-1}$
* $c_2 = \frac{h c}{k_B} = 1.438775 \times 10^4\,\mu\text{m}\cdot\text{K}$

The observed radiances $L_4$ and $L_5$ satisfy:

$$\begin{cases}
L(\lambda_4, T_4) = p \cdot B(\lambda_4, T_{\text{flame}}) + (1 - p) \cdot B(\lambda_4, T_{\text{bg}}) \\
L(\lambda_5, T_5) = p \cdot B(\lambda_5, T_{\text{flame}}) + (1 - p) \cdot B(\lambda_5, T_{\text{bg}})
\end{cases}$$

### Numerical Optimization Strategy
The non-linear system is solved using the **L-BFGS-B (Limited-memory Broyden–Fletcher–Goldfarb–Shanno with Bounds)** optimization algorithm:

$$\min_{T_{\text{flame}}, p} \left[ \left(\frac{L_{\text{obs}, 4} - L_{\text{model}, 4}}{L_{\text{obs}, 4}}\right)^2 + \left(\frac{L_{\text{obs}, 5} - L_{\text{model}, 5}}{L_{\text{obs}, 5}}\right)^2 \right]$$

Subject to:
* $450\text{ K} \le T_{\text{flame}} \le 2000\text{ K}$
* $10^{-7} \le p \le 1.0$

---

## 2. Quantitative Segregation Thresholds

| Source Type | True Flame Temp ($T_{\text{flame}}$) | Fire Area ($A_{\text{flame}}$) | FRP Recurrence (90 Days) | Action Decision |
| :--- | :---: | :---: | :---: | :--- |
| **Refinery Flare Stack** | $> 1,100\text{ K}$ | $< 50\text{ m}^2$ | $\ge 0.70$ (Continuous) | Routine (No Emergency) |
| **Industrial Blast / Pool Fire** | $700\text{ K} - 950\text{ K}$ | $> 1,000\text{ m}^2$ | $< 0.10$ (Sudden Surge) | **CRITICAL DISASTER** |
| **Forest Wildfire** | $600\text{ K} - 800\text{ K}$ | $> 100,000\text{ m}^2$ | Transient (Seasonal) | Natural Disaster |
| **Agricultural Stubble** | $600\text{ K} - 850\text{ K}$ | $10,000\text{ m}^2 - 100,000\text{ m}^2$ | Clustered in Cropland | Environmental Alert |
| **Coal Seam Smoldering** | $500\text{ K} - 750\text{ K}$ | $500\text{ m}^2 - 20,000\text{ m}^2$ | $> 0.85$ in Coalfields | Subsurface Hazard |
| **Solar Glint Rejection** | $< 350\text{ K}$ | Indeterminate | Single Flash | False Positive Discard |

---

## 3. Atmospheric Dispersion & Gaussian Plume Modeling

For industrial fires involving hazardous chemicals, toxic gas concentration $C(x, y, z)$ downwind is modeled according to the steady-state Gaussian plume formulation:

$$C(x, y, z) = \frac{Q}{2\pi u \sigma_y \sigma_z} \exp\left( -\frac{y^2}{2\sigma_y^2} \right) \left[ \exp\left( -\frac{(z - H)^2}{2\sigma_z^2} \right) + \exp\left( -\frac{(z + H)^2}{2\sigma_z^2} \right) \right]$$

Where:
* $Q$: Chemical emission rate ($\text{g/s}$), proportional to thermal FRP.
* $u$: Live $10\text{m}$ wind speed ($\text{m/s}$) from Open-Meteo.
* $\sigma_y, \sigma_z$: Pasquill-Gifford dispersion coefficients based on atmospheric stability class (default Class D - Neutral).
* $H$: Effective plume release height ($\text{m}$), adjusted for buoyant thermal rise ($\Delta H \propto \text{FRP}^{1/3}$).

### Evacuation Polygon Geometry
The GIS webapp dynamically projects the downwind danger wedge along the meteorological wind bearing ($\theta$):

$$\vec{r}_{\text{downwind}}(L) = (\text{lat}_0 + L \cos\theta, \text{lon}_0 + L \sin\theta)$$

The lateral spread is bounded by the standard ERG 2024 Initial Isolation Zone ($R_{\text{iso}} \approx 0.5\text{ km} - 1.0\text{ km}$) and Day/Night Downwind Evacuation Distance ($R_{\text{evac}} \approx 2.5\text{ km} - 5.0\text{ km}$).
