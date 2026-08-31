"""NASA FIRMS Real-World Data Activation, Filtering, and Provenance Layer (ML-010).

Provides a deterministic pipeline converting raw/archived NASA FIRMS observations
into canonical Detection datasets with full provenance manifests, spatial/temporal
filtering, deduplication, and quality control auditing.
"""

import csv
import io
import json
from datetime import UTC, datetime
from datetime import time as dt_time
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from packages.data.firms.capture import compute_content_hash
from packages.data.firms.normalizer import normalize_raw_row_to_detection
from packages.data.firms.schemas import (
    FirmsRawCapture,
    RawFirmsCsvRow,
    RealDataAcquisitionManifest,
    RealDetectionDataset,
)
from packages.feasibility.models import StudyArea

if TYPE_CHECKING:
    from packages.schemas.detection import Detection

_REQUIRED_COLUMNS = {"latitude", "longitude", "acq_date", "acq_time", "satellite"}
SENSITIVE_KEY_PATTERNS = (
    "map_key",
    "token",
    "secret",
    "password",
    "api_key",
    "credential",
    "private_key",
    "authorization",
)


def _audit_no_secrets(obj: Any, path: str = "") -> None:
    """Recursively verify no credentials or map keys exist in metadata."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = str(k).lower()
            for pattern in SENSITIVE_KEY_PATTERNS:
                if pattern in k_lower:
                    raise ValueError(
                        f"Prohibited sensitive key '{k}' found at path '{path}.{k}'"
                    )
            _audit_no_secrets(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _audit_no_secrets(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        lower_str = obj.lower()
        if "bearer " in lower_str or "firms_map_key" in lower_str:
            raise ValueError(
                f"Prohibited credential token detected in value at '{path}'"
            )


class FirmsDataActivationService:
    """Service orchestrating raw NASA FIRMS data ingestion and provenance tracking."""

    @classmethod
    def activate_from_csv(
        cls,
        csv_input: str | bytes | Path | TextIO,
        study_area: StudyArea,
        requested_start_date: str,
        requested_end_date: str,
        source_product: str = "VIIRS_SNPP_NRT",
        sensor: str = "VIIRS",
        dataset_id: str = "ds_real_firms_v1.0.0",
        dataset_version: str = "v1.0.0",
        source_snapshot_id: str = "snap_real_firms_001",
    ) -> RealDetectionDataset:
        """Activate real FIRMS observations from CSV content with strict provenance."""
        now = datetime.now(UTC)

        # 1. Resolve raw content and compute raw file hash
        raw_bytes: bytes
        raw_text: str
        if isinstance(csv_input, bytes):
            raw_bytes = csv_input
            raw_text = csv_input.decode("utf-8", errors="replace")
        elif isinstance(csv_input, Path):
            raw_bytes = csv_input.read_bytes()
            raw_text = raw_bytes.decode("utf-8", errors="replace")
        elif isinstance(csv_input, str):
            raw_text = csv_input
            raw_bytes = csv_input.encode("utf-8")
        else:
            raw_text = csv_input.read()
            raw_bytes = raw_text.encode("utf-8")

        raw_file_hash = compute_content_hash(raw_bytes)

        # 2. Parse temporal filter boundaries (UTC)
        try:
            start_d = datetime.strptime(requested_start_date, "%Y-%m-%d").date()
            end_d = datetime.strptime(requested_end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}. Expected 'YYYY-MM-DD'.") from e

        start_dt = datetime.combine(start_d, dt_time.min, tzinfo=UTC)
        end_dt = datetime.combine(end_d, dt_time.max, tzinfo=UTC)

        # 3. Parse CSV rows
        stream = io.StringIO(raw_text)
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("CSV input is completely empty or missing header.")

        norm_headers = {h.strip().lower() for h in reader.fieldnames if h}
        missing_hdr = _REQUIRED_COLUMNS - norm_headers
        if missing_hdr:
            raise ValueError(
                f"Missing required FIRMS CSV columns: {sorted(missing_hdr)}"
            )

        raw_record_count = 0
        valid_rows = 0
        invalid_record_count = 0
        duplicate_record_count = 0
        spatial_excluded_count = 0
        temporal_excluded_count = 0

        canonical_detections: list[Detection] = []
        seen_signatures: set[tuple[str, str, str, float, float, str]] = set()

        bbox = study_area.bounding_box

        for _idx, row in enumerate(reader):
            raw_record_count += 1
            cleaned_row = {
                k.strip().lower(): (
                    v.strip() if v is not None and v.strip() != "" else None
                )
                for k, v in row.items()
                if k
            }

            try:
                validated_row = RawFirmsCsvRow.model_validate(cleaned_row)
                det = normalize_raw_row_to_detection(
                    row=validated_row,
                    raw_dict=cleaned_row,
                    source_snapshot_id=source_snapshot_id,
                    product_type="nrt"
                    if "nrt" in source_product.lower()
                    else "standard",
                    product_version="v2.0",
                )
                valid_rows += 1
            except Exception:
                invalid_record_count += 1
                continue

            # 4. Spatial Filtering (inside bounding box)
            lat = det.geometry.latitude
            lon = det.geometry.longitude
            if not (
                bbox.min_latitude <= lat <= bbox.max_latitude
                and bbox.min_longitude <= lon <= bbox.max_longitude
            ):
                spatial_excluded_count += 1
                continue

            # 5. Temporal Filtering (within requested window)
            if not (start_dt <= det.acquired_at <= end_dt):
                temporal_excluded_count += 1
                continue

            # 6. Deduplication (exact identical observation)
            sig = (
                det.source,
                det.instrument,
                det.acquired_at.isoformat(),
                round(lat, 5),
                round(lon, 5),
                det.satellite,
            )
            if sig in seen_signatures:
                duplicate_record_count += 1
                continue

            seen_signatures.add(sig)
            canonical_detections.append(det)

        # 7. Sort detections deterministically
        canonical_detections.sort(
            key=lambda d: (
                d.acquired_at.isoformat(),
                d.geometry.latitude,
                d.geometry.longitude,
                d.satellite,
                d.detection_id,
            )
        )

        # 8. Compute quality summary distributions
        actual_start: datetime | None = None
        actual_end: datetime | None = None
        if canonical_detections:
            actual_start = min(d.acquired_at for d in canonical_detections)
            actual_end = max(d.acquired_at for d in canonical_detections)

        missing_counts: dict[str, int] = {
            "frp_mw": sum(1 for d in canonical_detections if d.frp_mw is None),
            "brightness_ti4_k": sum(
                1 for d in canonical_detections if d.brightness_ti4_k is None
            ),
            "confidence": sum(1 for d in canonical_detections if d.confidence is None),
            "day_night": sum(1 for d in canonical_detections if d.day_night is None),
        }

        sensor_dist: dict[str, int] = {}
        sat_dist: dict[str, int] = {}
        dn_dist: dict[str, int] = {}

        for d in canonical_detections:
            sensor_dist[d.instrument] = sensor_dist.get(d.instrument, 0) + 1
            sat_dist[d.satellite] = sat_dist.get(d.satellite, 0) + 1
            dn_key = d.day_night.value if d.day_night else "unknown"
            dn_dist[dn_key] = dn_dist.get(dn_key, 0) + 1

        # 9. Compute dataset canonical hash
        temp_manifest = RealDataAcquisitionManifest(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            source_name="NASA_FIRMS",
            source_product=source_product,
            sensor=sensor,
            study_area_id=study_area.area_id,
            study_area_name=study_area.name,
            bounding_box=bbox,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            actual_coverage_start=actual_start,
            actual_coverage_end=actual_end,
            raw_record_count=raw_record_count,
            valid_record_count=valid_rows,
            invalid_record_count=invalid_record_count,
            duplicate_record_count=duplicate_record_count,
            spatial_excluded_count=spatial_excluded_count,
            temporal_excluded_count=temporal_excluded_count,
            canonical_record_count=len(canonical_detections),
            raw_file_hashes=[raw_file_hash],
            canonical_dataset_hash="0" * 64,  # temporary placeholder
            missingness_summary=missing_counts,
            sensor_distribution=sensor_dist,
            satellite_distribution=sat_dist,
            day_night_distribution=dn_dist,
            quality_control_passed=True,
            created_at=now,
        )

        dataset = RealDetectionDataset(
            manifest=temp_manifest,
            detections=canonical_detections,
        )
        canonical_hash = dataset.compute_canonical_hash()

        final_manifest = temp_manifest.model_copy(
            update={"canonical_dataset_hash": canonical_hash}
        )
        final_dataset = dataset.model_copy(update={"manifest": final_manifest})

        # 10. Audit against secrets
        _audit_no_secrets(final_dataset.model_dump(mode="json"))

        return final_dataset

    @classmethod
    def activate_from_raw_capture(
        cls,
        capture: FirmsRawCapture,
        study_area: StudyArea,
        requested_start_date: str,
        requested_end_date: str,
        sensor: str = "VIIRS",
        dataset_id: str = "ds_real_firms_v1.0.0",
        dataset_version: str = "v1.0.0",
    ) -> RealDetectionDataset:
        """Activate real observational dataset from a FirmsRawCapture snapshot."""
        return cls.activate_from_csv(
            csv_input=capture.raw_content,
            study_area=study_area,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            source_product=capture.product,
            sensor=sensor,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            source_snapshot_id=capture.source_snapshot_id,
        )

    @classmethod
    def save_dataset(
        cls,
        dataset: RealDetectionDataset,
        output_dir: Path | str,
    ) -> Path:
        """Save canonical observational dataset and manifest to directory."""
        dir_path = Path(output_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        data = dataset.model_dump(mode="json")
        _audit_no_secrets(data)

        out_file = dir_path / f"{dataset.manifest.dataset_id}.json"
        json_str = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
        out_file.write_text(json_str, encoding="utf-8")
        return out_file

    @classmethod
    def load_dataset(
        cls,
        file_path: Path | str,
    ) -> RealDetectionDataset:
        """Load and verify canonical observational dataset from filesystem."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Observational dataset not found at {path}")

        json_str = path.read_text(encoding="utf-8")
        data = json.loads(json_str)
        _audit_no_secrets(data)

        dataset = RealDetectionDataset.model_validate(data)

        # Verify canonical hash integrity
        computed_hash = dataset.compute_canonical_hash()
        if dataset.manifest.canonical_dataset_hash != computed_hash:
            raise ValueError(
                f"Observational dataset hash mismatch: "
                f"stored={dataset.manifest.canonical_dataset_hash}, "
                f"computed={computed_hash}."
            )

        return dataset
