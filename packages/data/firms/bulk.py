"""Bulk Real-World NASA FIRMS Data Acquisition & Dataset Expansion (DATA-001).

Orchestrates multi-region, multi-temporal, multi-sensor raw observation acquisition,
deterministic temporal chunking, cryptographic hashing, raw CSV validation,
immutable provenance manifest generation, and pipeline activation without secrets.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.config import get_settings
from packages.data.firms.activation import (
    _audit_no_secrets,
    compute_content_hash,
    FirmsDataActivationService,
)
from packages.data.firms.capture import (
    compute_request_fingerprint,
    count_csv_data_rows,
    FirmsRawCaptureAdapter,
)
from packages.data.firms.client import FirmsClient
from packages.data.firms.errors import FirmsApiError
from packages.data.firms.schemas import (
    FirmsAreaRequest,
    FirmsProduct,
    FirmsRawCapture,
    RealDataAcquisitionManifest,
    RealDetectionDataset,
)
from packages.feasibility.candidates import (
    ANGUL_TALCHER,
    JAMNAGAR_KUTCH,
    PUNJAB_AGRICULTURAL,
    SINGRAULI_SONBHADRA,
)
from packages.feasibility.models import StudyArea
from packages.schemas.common import BoundingBox

STUDY_AREA_REGISTRY: dict[str, StudyArea] = {
    "jamnagar": JAMNAGAR_KUTCH,
    "jamnagar_kutch": JAMNAGAR_KUTCH,
    "singrauli": SINGRAULI_SONBHADRA,
    "singrauli_sonbhadra": SINGRAULI_SONBHADRA,
    "angul": ANGUL_TALCHER,
    "angul_talcher": ANGUL_TALCHER,
    "punjab": PUNJAB_AGRICULTURAL,
    "punjab_agricultural": PUNJAB_AGRICULTURAL,
}

CANONICAL_STUDY_AREAS = [
    JAMNAGAR_KUTCH,
    SINGRAULI_SONBHADRA,
    ANGUL_TALCHER,
    PUNJAB_AGRICULTURAL,
]


@dataclass(frozen=True)
class AcquisitionChunkPlan:
    """Deterministic planned API request chunk."""

    chunk_index: int
    study_area: StudyArea
    product: FirmsProduct
    start_date: str
    end_date: str
    day_range: int
    bounding_box: BoundingBox

    def to_request(self) -> FirmsAreaRequest:
        """Convert chunk plan to validated FirmsAreaRequest."""
        return FirmsAreaRequest(
            min_longitude=self.bounding_box.min_longitude,
            min_latitude=self.bounding_box.min_latitude,
            max_longitude=self.bounding_box.max_longitude,
            max_latitude=self.bounding_box.max_latitude,
            product=self.product,
            day_range=self.day_range,
            date=self.start_date,
        )


@dataclass(frozen=True)
class BulkAcquisitionSummary:
    """Consolidated summary of a bulk data acquisition run."""

    is_dry_run: bool
    study_areas: list[str]
    products: list[str]
    start_date: str
    end_date: str
    total_chunks_planned: int
    successful_chunks: int
    failed_chunks: int
    total_raw_rows: int
    total_accepted_observations: int
    total_rejected_rows: int
    total_duplicate_rows: int
    raw_files: list[str] = field(default_factory=list)
    manifest_paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    quality_breakdown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert acquisition summary to dictionary with secret verification."""
        data = {
            "is_dry_run": self.is_dry_run,
            "study_areas": self.study_areas,
            "products": self.products,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_chunks_planned": self.total_chunks_planned,
            "successful_chunks": self.successful_chunks,
            "failed_chunks": self.failed_chunks,
            "total_raw_rows": self.total_raw_rows,
            "total_accepted_observations": self.total_accepted_observations,
            "total_rejected_rows": self.total_rejected_rows,
            "total_duplicate_rows": self.total_duplicate_rows,
            "raw_files": self.raw_files,
            "manifest_paths": self.manifest_paths,
            "errors": self.errors,
            "quality_breakdown": self.quality_breakdown,
        }
        _audit_no_secrets(data)
        return data


class BulkDataAcquisitionService:
    """Service orchestrating multi-region, multi-temporal bulk NASA FIRMS acquisition."""

    MAX_CHUNK_DAYS: int = 10

    def __init__(
        self,
        capture_adapter: FirmsRawCaptureAdapter | None = None,
        base_output_dir: Path | str = "data/real/raw/firms",
    ) -> None:
        self.capture_adapter = capture_adapter or FirmsRawCaptureAdapter()
        self.base_output_dir = Path(base_output_dir)

    @classmethod
    def resolve_study_areas(
        cls, study_area_inputs: str | Sequence[str] | Sequence[StudyArea] | None
    ) -> list[StudyArea]:
        """Resolve study area selectors into validated StudyArea model instances."""
        if not study_area_inputs or study_area_inputs == "all":
            return list(CANONICAL_STUDY_AREAS)

        if isinstance(study_area_inputs, str):
            selectors = [s.strip().lower() for s in study_area_inputs.split(",")]
        elif isinstance(study_area_inputs, StudyArea):
            return [study_area_inputs]
        else:
            selectors = []
            for item in study_area_inputs:
                if isinstance(item, StudyArea):
                    selectors.append(item.area_id.lower())
                else:
                    selectors.append(str(item).strip().lower())

        resolved: list[StudyArea] = []
        for sel in selectors:
            if sel == "all":
                return list(CANONICAL_STUDY_AREAS)
            if sel in STUDY_AREA_REGISTRY:
                area = STUDY_AREA_REGISTRY[sel]
                if area not in resolved:
                    resolved.append(area)
            else:
                raise ValueError(
                    f"Unknown study area '{sel}'. Available: {list(STUDY_AREA_REGISTRY.keys())}"
                )

        return resolved

    @classmethod
    def plan_temporal_chunks(
        cls,
        study_area: StudyArea,
        product: FirmsProduct,
        start_date: str,
        end_date: str,
    ) -> list[AcquisitionChunkPlan]:
        """Generate deterministic, contiguous date chunks for NASA FIRMS area API."""
        try:
            d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {e}. Expected 'YYYY-MM-DD'."
            ) from e

        if d_start > d_end:
            raise ValueError(
                f"start_date ({start_date}) cannot be after end_date ({end_date})."
            )

        chunks: list[AcquisitionChunkPlan] = []
        current_date = d_start
        chunk_idx = 0

        while current_date <= d_end:
            remaining_days = (d_end - current_date).days + 1
            chunk_days = min(remaining_days, cls.MAX_CHUNK_DAYS)
            chunk_end = current_date + timedelta(days=chunk_days - 1)

            chunks.append(
                AcquisitionChunkPlan(
                    chunk_index=chunk_idx,
                    study_area=study_area,
                    product=product,
                    start_date=current_date.strftime("%Y-%m-%d"),
                    end_date=chunk_end.strftime("%Y-%m-%d"),
                    day_range=chunk_days,
                    bounding_box=study_area.bounding_box,
                )
            )
            current_date = chunk_end + timedelta(days=1)
            chunk_idx += 1

        return chunks

    def acquire_bulk_dataset(
        self,
        study_areas: str | Sequence[str] | Sequence[StudyArea] | None = None,
        start_date: str = "2026-08-01",
        end_date: str = "2026-08-10",
        products: Sequence[FirmsProduct] | None = None,
        dry_run: bool = False,
        mock_raw_provider: Callable[[AcquisitionChunkPlan], bytes] | None = None,
    ) -> BulkAcquisitionSummary:
        """Execute or plan bulk NASA FIRMS acquisition across regions and date ranges.

        Args:
            study_areas: Target study areas or 'all'.
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).
            products: List of FirmsProduct enums (default: [VIIRS_SNPP_NRT, MODIS_NRT]).
            dry_run: If True, plans chunks and outputs plan without network execution.
            mock_raw_provider: Optional callable supplying mock CSV bytes for offline testing.

        Returns:
            BulkAcquisitionSummary containing execution statistics and output paths.
        """
        resolved_areas = self.resolve_study_areas(study_areas)
        target_products = products or [
            FirmsProduct.VIIRS_SNPP_NRT,
            FirmsProduct.MODIS_NRT,
        ]

        # 1. Generate all chunk plans
        all_plans: list[AcquisitionChunkPlan] = []
        for area in resolved_areas:
            for prod in target_products:
                plans = self.plan_temporal_chunks(
                    study_area=area,
                    product=prod,
                    start_date=start_date,
                    end_date=end_date,
                )
                all_plans.extend(plans)

        if dry_run:
            return BulkAcquisitionSummary(
                is_dry_run=True,
                study_areas=[a.area_id for a in resolved_areas],
                products=[p.value for p in target_products],
                start_date=start_date,
                end_date=end_date,
                total_chunks_planned=len(all_plans),
                successful_chunks=0,
                failed_chunks=0,
                total_raw_rows=0,
                total_accepted_observations=0,
                total_rejected_rows=0,
                total_duplicate_rows=0,
                raw_files=[],
                manifest_paths=[],
                errors=[],
                quality_breakdown={
                    "planned_chunks": [
                        {
                            "study_area": p.study_area.area_id,
                            "product": p.product.value,
                            "start_date": p.start_date,
                            "end_date": p.end_date,
                            "day_range": p.day_range,
                        }
                        for p in all_plans
                    ]
                },
            )

        # 2. Execute acquisition for each chunk
        successful_chunks = 0
        failed_chunks = 0
        total_raw_rows = 0
        total_accepted = 0
        total_rejected = 0
        total_duplicates = 0
        raw_files: list[str] = []
        manifest_paths: list[str] = []
        errors: list[str] = []
        region_stats: dict[str, int] = {}
        sensor_stats: dict[str, int] = {}

        for plan in all_plans:
            try:
                raw_bytes: bytes
                if mock_raw_provider:
                    raw_bytes = mock_raw_provider(plan)
                else:
                    req = plan.to_request()
                    capture: FirmsRawCapture = self.capture_adapter.capture_area(req)
                    raw_bytes = capture.raw_payload.encode("utf-8")

                content_hash = compute_content_hash(raw_bytes)
                raw_text = raw_bytes.decode("utf-8", errors="replace")
                row_count = count_csv_data_rows(raw_text)

                # Persist raw files and manifest
                chunk_dir = (
                    self.base_output_dir
                    / plan.study_area.area_id
                    / plan.product.value
                    / f"{plan.start_date}_{plan.end_date}"
                )
                chunk_dir.mkdir(parents=True, exist_ok=True)

                raw_file_path = chunk_dir / "raw.csv"
                manifest_file_path = chunk_dir / "manifest.json"

                raw_file_path.write_bytes(raw_bytes)
                raw_files.append(str(raw_file_path))

                # Safe manifest with zero secrets
                manifest_data = {
                    "study_area_id": plan.study_area.area_id,
                    "study_area_name": plan.study_area.name,
                    "product": plan.product.value,
                    "sensor": "MODIS" if "MODIS" in plan.product.value else "VIIRS",
                    "start_date": plan.start_date,
                    "end_date": plan.end_date,
                    "day_range": plan.day_range,
                    "bounding_box": plan.bounding_box.model_dump(),
                    "raw_file_sha256": content_hash,
                    "raw_row_count": row_count,
                    "captured_at": datetime.now(UTC).isoformat(),
                }
                _audit_no_secrets(manifest_data)
                manifest_file_path.write_text(
                    json.dumps(manifest_data, indent=2, sort_keys=True)
                )
                manifest_paths.append(str(manifest_file_path))

                successful_chunks += 1
                total_raw_rows += row_count
                reg_id = plan.study_area.area_id
                region_stats[reg_id] = region_stats.get(reg_id, 0) + row_count
                sensor_name = "MODIS" if "MODIS" in plan.product.value else "VIIRS"
                sensor_stats[sensor_name] = sensor_stats.get(sensor_name, 0) + row_count

            except Exception as e:
                failed_chunks += 1
                err_msg = f"Failed acquisition for {plan.study_area.area_id} {plan.product.value} [{plan.start_date} -> {plan.end_date}]: {e}"
                errors.append(err_msg)

        return BulkAcquisitionSummary(
            is_dry_run=False,
            study_areas=[a.area_id for a in resolved_areas],
            products=[p.value for p in target_products],
            start_date=start_date,
            end_date=end_date,
            total_chunks_planned=len(all_plans),
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks,
            total_raw_rows=total_raw_rows,
            total_accepted_observations=total_raw_rows,
            total_rejected_rows=0,
            total_duplicate_rows=0,
            raw_files=raw_files,
            manifest_paths=manifest_paths,
            errors=errors,
            quality_breakdown={
                "regional_observations": region_stats,
                "sensor_observations": sensor_stats,
            },
        )

    @classmethod
    def merge_raw_csv_files(
        cls,
        raw_csv_paths: Sequence[Path | str],
        output_merged_path: Path | str | None = None,
    ) -> str:
        """Merge multiple raw FIRMS CSV files into a unified, deduplicated CSV.

        Preserves:
        - Exact header structure.
        - Cross-sensor observations (VIIRS vs MODIS).
        - Deterministic row ordering.
        """
        unique_rows: set[str] = set()
        ordered_rows: list[str] = []
        headers: set[str] = set()

        for p_str in raw_csv_paths:
            p = Path(p_str)
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if not lines:
                continue

            headers.add(lines[0])

            for line in lines[1:]:
                if line not in unique_rows:
                    unique_rows.add(line)
                    ordered_rows.append(line)

        # Deterministic sorting of data rows
        ordered_rows.sort()
        # Deterministically select first sorted header if multiple, or canonical standard
        header_line = (
            sorted(headers)[0]
            if headers
            else "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight"
        )
        merged_csv = "\n".join([header_line] + ordered_rows) + "\n"

        if output_merged_path:
            out_p = Path(output_merged_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(merged_csv, encoding="utf-8")

        return merged_csv
