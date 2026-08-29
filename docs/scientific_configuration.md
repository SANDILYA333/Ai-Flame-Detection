# Scientific Configuration Contract (BE-004)

The platform provides a centralized, strongly-typed, and immutable scientific configuration contract defined in `packages/config/scientific.py`.

---

## 1. Architectural Scope & Operational Separation

| Domain | Contract | Package Location | Ownership |
| :--- | :--- | :--- | :--- |
| **Operational Configuration** | `Settings` | `packages/config/settings.py` | Environment modes, network ports, database credentials, pool sizes |
| **Scientific Configuration** | `ScientificConfig` | `packages/config/scientific.py` | Spatial/temporal clustering, persistence spans, attribution radii, confidence cutoffs |

Operational configuration is loaded from environment variables (`.env`). Scientific configuration represents versioned, calibrated experimental contracts and does **not** read from environment secrets.

---

## 2. The Zero-Invented-Defaults Principle

In strict accordance with scientific integrity rules:
- **No arbitrary scientific thresholds are hardcoded.**
- All numerical parameters default to `None` to represent an **explicit incomplete / uncalibrated state**.
- Algorithms and pipeline stages verify completeness via `config.validate_completeness()`. If uncalibrated parameters exist, execution is halted with a `MissingConfigurationError` (from `packages.errors`).

---

## 3. Scientific Parameters & Physical Units

| Parameter | Type | Unit | Validation Constraint | Description |
| :--- | :--- | :--- | :--- | :--- |
| `spatial_cluster_radius_meters` | `float \| None` | meters ($m$) | $> 0$ | Spatial clustering radius for grouping detections into events |
| `temporal_window_hours` | `float \| None` | hours ($h$) | $> 0$ | Temporal window for grouping continuous detection episodes |
| `persistence_threshold_days` | `float \| None` | days ($d$) | $> 0$ | Minimum observation span to classify a persistent source |
| `persistence_min_observations` | `int \| None` | count | $\ge 1$ | Minimum distinct detection count required for persistence |
| `attribution_radius_meters` | `float \| None` | meters ($m$) | $> 0$ | Spatial search radius around centroid for industrial infrastructure |
| `attribution_confidence_threshold`| `float \| None` | probability | $[0.0, 1.0]$ | Minimum posterior confidence for definitive attribution |
| `minimum_event_confidence` | `float \| None` | probability | $[0.0, 1.0]$ | Minimum confidence score for confirmed thermal event |
| `abstention_confidence_threshold` | `float \| None` | probability | $[0.0, 1.0]$ | Confidence cutoff below which the system must abstain |

---

## 4. Provenance & Fingerprinting

Every `ScientificConfig` instance can compute a deterministic SHA-256 fingerprint from its canonical JSON representation:
```python
from packages.config import ScientificConfig

config = ScientificConfig(
    version="v1.0.0",
    spatial_cluster_radius_meters=1500.0,
    temporal_window_hours=24.0,
    persistence_threshold_days=30.0,
    persistence_min_observations=5,
    attribution_radius_meters=2000.0,
    attribution_confidence_threshold=0.85,
    minimum_event_confidence=0.70,
    abstention_confidence_threshold=0.50,
)

fingerprint = config.compute_fingerprint()
# Example: 4a3f12... (SHA-256 hex digest)
```

Derived scientific outputs (events, persistent sources, intelligence records) attach this fingerprint to ensure complete experimental reproducibility.
