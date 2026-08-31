#!/usr/bin/env python3
"""DATA-002 Ground-Truth Ingestion and Validation Engine.

Scans, validates, normalizes, and cryptographically digests all authoritative
ground-truth reference registries and facility infrastructure catalogs across:
- data/real/reference/industrial/
- data/real/reference/agricultural/
- data/real/reference/wildfire/
- data/real/reference/facilities/
- fixtures/reference/

Ensures strict provenance preservation, schema validation, and zero credential leakage.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from packages.context.ground_truth import GroundTruthIngestionService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest, validate, and audit real ground-truth reference datasets."
    )
    parser.add_argument(
        "--ref-dir",
        type=str,
        default="data/real/reference",
        help="Root path for ground-truth reference data.",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=str,
        default="fixtures/reference",
        help="Fixtures reference directory.",
    )
    args = parser.parse_args()

    ref_dir = Path(args.ref_dir)
    fixtures_dir = Path(args.fixtures_dir)

    print("=" * 70)
    print("SIH26162 — AUTHORITATIVE GROUND-TRUTH INGESTION ENGINE")
    print("=" * 70)
    print(f"Reference Directory: {ref_dir.resolve()}")
    print(f"Fixtures Directory:  {fixtures_dir.resolve()}")

    target_dirs = [d for d in [ref_dir, fixtures_dir] if d.exists()]
    if not target_dirs:
        print(f"ERROR: Neither {ref_dir} nor {fixtures_dir} exists.", file=sys.stderr)
        return 1

    # 1. Ingest Ground Truth Reference Records
    records, file_hashes = GroundTruthIngestionService.discover_and_load_catalog(target_dirs)
    print(f"\nDiscovered {len(file_hashes)} reference file(s) across catalog directories.")
    print(f"Successfully loaded and validated {len(records)} external reference record(s).\n")

    for fpath, fhash in sorted(file_hashes.items()):
        print(f"  - [{fhash[:12]}...] {fpath}")

    # 2. Ingest Facility Context Features
    facilities_dir = ref_dir / "facilities"
    facilities, fac_hashes = GroundTruthIngestionService.load_facility_context_features(
        facilities_dir if facilities_dir.exists() else ref_dir
    )
    print(f"\nLoaded {len(facilities)} verified industrial facility infrastructure feature(s).")

    # 3. Categorical Distributions
    by_country: dict[str, int] = Counter()
    by_region: dict[str, int] = Counter()
    by_regime: dict[str, int] = Counter()
    by_tier: dict[str, int] = Counter()
    by_source: dict[str, int] = Counter()
    by_class: dict[str, int] = Counter()

    for r in records:
        by_country[r.country] += 1
        by_region[r.region] += 1
        by_regime[r.fire_regime] += 1
        by_tier[r.tier.value] += 1
        by_source[r.source_name] += 1
        by_class[r.claim_class] += 1

    print("\n--- Distribution by Country ---")
    for k, v in sorted(by_country.items()):
        print(f"  {k:30s}: {v:4d}")

    print("\n--- Distribution by Fire Regime ---")
    for k, v in sorted(by_regime.items()):
        print(f"  {k:30s}: {v:4d}")

    print("\n--- Distribution by Claim Class ---")
    for k, v in sorted(by_class.items()):
        print(f"  {k:30s}: {v:4d}")

    print("\n--- Distribution by Source Tier ---")
    for k, v in sorted(by_tier.items()):
        print(f"  {k:30s}: {v:4d}")

    print("\n--- Verified Industrial Facilities ---")
    for fac in facilities:
        print(f"  - [{fac.feature_id}] {fac.facility_name or 'N/A'} ({fac.context_type.value}) @ ({fac.geometry.latitude:.4f}, {fac.geometry.longitude:.4f})")

    print("\n" + "=" * 70)
    print("STATUS: GROUND-TRUTH INGESTION & AUDIT SUCCESSFUL")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
