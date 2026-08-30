"""Unit, adversarial, and determinism tests for DATA-002 FIRMS Canonical Parser."""

import random
from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.data.firms import (
    compute_canonical_detection_id,
    compute_firms_raw_hash,
    normalize_day_night,
    normalize_instrument,
    normalize_satellite_name,
    parse_firms_csv,
    parse_firms_csv_with_report,
    parse_firms_timestamp,
)
from packages.errors import ContractViolationError
from packages.schemas.enums import DayNight

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "firms"


class TestFirmsTimestampParsing:
    """Validate acquisition date and time parsing into explicit UTC datetimes."""

    def test_valid_iso_date_and_4digit_time(self) -> None:
        """Parses YYYY-MM-DD and HHMM correctly into UTC."""
        dt = parse_firms_timestamp("2026-08-01", "0830")
        assert dt == datetime(2026, 8, 1, 8, 30, 0, tzinfo=UTC)
        assert dt.tzinfo == UTC

    def test_valid_3digit_time_padding(self) -> None:
        """Pads 3-digit times (e.g. '430' -> '04:30:00 UTC')."""
        dt = parse_firms_timestamp("2026-08-01", "430")
        assert dt == datetime(2026, 8, 1, 4, 30, 0, tzinfo=UTC)

    def test_valid_colon_separated_time(self) -> None:
        """Handles HH:MM format."""
        dt = parse_firms_timestamp("2026-08-01", "14:25")
        assert dt == datetime(2026, 8, 1, 14, 25, 0, tzinfo=UTC)

    @pytest.mark.parametrize(
        ("date_str", "time_str"),
        [
            ("2026-99-99", "0830"),
            ("2026-02-30", "1200"),
            ("invalid", "0830"),
            ("2026-08-01", "2599"),
            ("2026-08-01", "1260"),
            ("2026-08-01", "invalid"),
        ],
    )
    def test_invalid_timestamps_raise_value_error(
        self, date_str: str, time_str: str
    ) -> None:
        """Malformed or invalid calendar dates/times raise ValueError."""
        with pytest.raises(ValueError):
            parse_firms_timestamp(date_str, time_str)


class TestFirmsNormalizationHelpers:
    """Validate satellite, instrument, and day/night normalization."""

    def test_normalize_satellite_names(self) -> None:
        """Normalizes vendor satellite shorthand codes."""
        assert normalize_satellite_name("N") == "Suomi-NPP"
        assert normalize_satellite_name("SNPP") == "Suomi-NPP"
        assert normalize_satellite_name("1") == "NOAA-20"
        assert normalize_satellite_name("N20") == "NOAA-20"
        assert normalize_satellite_name("2") == "NOAA-21"
        assert normalize_satellite_name("T") == "Terra"
        assert normalize_satellite_name("A") == "Aqua"
        assert normalize_satellite_name("NOAA-20") == "NOAA-20"

    def test_normalize_instrument_inference(self) -> None:
        """Infers instrument from normalized satellite if missing."""
        assert normalize_instrument("VIIRS", "NOAA-20") == "VIIRS"
        assert normalize_instrument("MODIS", "Terra") == "MODIS"
        assert normalize_instrument(None, "NOAA-20") == "VIIRS"
        assert normalize_instrument(None, "Terra") == "MODIS"
        assert normalize_instrument(None, "UnknownSat") == "UNKNOWN_SENSOR"

    def test_normalize_day_night(self) -> None:
        """Maps daynight strings to DayNight enum."""
        assert normalize_day_night("D") == DayNight.DAY
        assert normalize_day_night("Day") == DayNight.DAY
        assert normalize_day_night("N") == DayNight.NIGHT
        assert normalize_day_night("Night") == DayNight.NIGHT
        assert normalize_day_night(None) is None
        assert normalize_day_night("") is None


class TestFirmsCsvParsingFixtures:
    """Validate parsing across real-world FIRMS CSV product fixtures."""

    def test_parse_viirs_snpp_valid(self) -> None:
        """Parses valid VIIRS Suomi-NPP fixture."""
        csv_path = FIXTURES_DIR / "viirs_snpp_valid.csv"
        detections = parse_firms_csv(
            csv_input=csv_path,
            source_snapshot_id="SNAP-TEST-001",
            product_type="nrt",
            product_version="v2.0",
        )
        assert len(detections) == 3

        d0 = detections[0]
        assert d0.source == "firms"
        assert d0.source_snapshot_id == "SNAP-TEST-001"
        assert d0.satellite == "Suomi-NPP"
        assert d0.instrument == "VIIRS"
        assert d0.geometry.latitude == 22.4502
        assert d0.geometry.longitude == 70.0512
        assert d0.acquired_at == datetime(2026, 8, 1, 8, 30, 0, tzinfo=UTC)
        assert d0.frp_mw == 28.5
        assert d0.brightness_ti4_k == 352.4
        assert d0.brightness_ti5_k == 296.2
        assert d0.confidence == "nominal"
        assert d0.day_night == DayNight.DAY
        assert d0.detection_id.startswith("det_")
        assert len(d0.raw_hash) == 64

    def test_parse_viirs_noaa20_valid(self) -> None:
        """Parses valid VIIRS NOAA-20 fixture."""
        csv_path = FIXTURES_DIR / "viirs_noaa20_valid.csv"
        detections = parse_firms_csv(
            csv_input=csv_path,
            source_snapshot_id="SNAP-TEST-002",
        )
        assert len(detections) == 2
        assert detections[0].satellite == "NOAA-20"
        assert detections[1].satellite == "NOAA-20"

    def test_parse_modis_valid_with_aliases(self) -> None:
        """Parses MODIS fixture mapping brightness and bright_t31 aliases."""
        csv_path = FIXTURES_DIR / "modis_valid.csv"
        detections = parse_firms_csv(
            csv_input=csv_path,
            source_snapshot_id="SNAP-TEST-003",
        )
        assert len(detections) == 2
        d_terra = detections[0]
        assert d_terra.satellite == "Terra"
        assert d_terra.instrument == "MODIS"
        assert d_terra.brightness_ti4_k == 325.6
        assert d_terra.brightness_ti5_k == 295.0
        assert d_terra.confidence == "85"

    def test_parse_extra_columns_allowed(self) -> None:
        """Extra provider columns are accepted without error."""
        csv_path = FIXTURES_DIR / "extra_columns.csv"
        detections = parse_firms_csv(
            csv_input=csv_path,
            source_snapshot_id="SNAP-TEST-EXTRA",
        )
        assert len(detections) == 1
        assert detections[0].satellite == "Suomi-NPP"

    def test_parse_empty_fixture_returns_empty_list(self) -> None:
        """Empty fixture with headers returns empty list."""
        csv_path = FIXTURES_DIR / "empty.csv"
        detections = parse_firms_csv(
            csv_input=csv_path,
            source_snapshot_id="SNAP-TEST-EMPTY",
        )
        assert detections == []

    def test_missing_optional_fields_preserves_none(self) -> None:
        """Missing optional fields (FRP, confidence) remain None, not 0.0."""
        csv_text = (
            "latitude,longitude,acq_date,acq_time,satellite\n"
            "22.4500,70.0500,2026-08-01,1200,NOAA-20\n"
        )
        detections = parse_firms_csv(
            csv_input=csv_text,
            source_snapshot_id="SNAP-TEST-OPT",
        )
        assert len(detections) == 1
        d = detections[0]
        assert d.frp_mw is None
        assert d.confidence is None
        assert d.brightness_ti4_k is None
        assert d.brightness_ti5_k is None
        assert d.day_night is None


class TestFirmsParserFailuresAndReporting:
    """Validate strict failure handling and structured batch reporting."""

    def test_missing_required_headers_raises_contract_violation(self) -> None:
        """CSV missing required columns raises ContractViolationError."""
        csv_path = FIXTURES_DIR / "missing_required.csv"
        with pytest.raises(ContractViolationError) as exc_info:
            parse_firms_csv(
                csv_input=csv_path,
                source_snapshot_id="SNAP-TEST-FAIL",
            )
        assert "missing required headers" in str(exc_info.value)

    def test_empty_snapshot_id_raises_contract_violation(self) -> None:
        """Empty source_snapshot_id is strictly rejected."""
        with pytest.raises(ContractViolationError) as exc_info:
            parse_firms_csv(
                csv_input="latitude,longitude,acq_date,acq_time,satellite\n",
                source_snapshot_id="",
            )
        assert "source_snapshot_id cannot be empty" in str(exc_info.value)

    def test_malformed_coordinates_strict_raises(self) -> None:
        """Malformed coordinates in strict mode raise ContractViolationError."""
        csv_path = FIXTURES_DIR / "malformed_coordinates.csv"
        with pytest.raises(ContractViolationError) as exc_info:
            parse_firms_csv(
                csv_input=csv_path,
                source_snapshot_id="SNAP-TEST-FAIL",
                strict=True,
            )
        assert "Malformed FIRMS record at row 1" in str(exc_info.value)

    def test_parse_with_report_collects_errors_without_dropping(self) -> None:
        """Report mode collects valid detections and structured row errors."""
        csv_path = FIXTURES_DIR / "malformed_coordinates.csv"
        report = parse_firms_csv_with_report(
            csv_input=csv_path,
            source_snapshot_id="SNAP-TEST-REPORT",
        )
        assert report.source_snapshot_id == "SNAP-TEST-REPORT"
        assert report.total_rows == 3
        assert report.valid_count == 0
        assert report.error_count == 3
        assert len(report.row_errors) == 3
        assert report.row_errors[0].row_index == 0


class TestFirmsDeterminismAndHashing:
    """Validate content-addressable ID and permutation invariance."""

    def test_hashing_and_id_determinism(self) -> None:
        """Same raw row produces identical hash and ID across runs."""
        raw_dict = {
            "latitude": 22.4502,
            "longitude": 70.0512,
            "acq_date": "2026-08-01",
            "acq_time": "0830",
            "satellite": "N",
        }
        h1 = compute_firms_raw_hash(raw_dict)
        h2 = compute_firms_raw_hash(raw_dict)
        assert h1 == h2
        assert len(h1) == 64

        id1 = compute_canonical_detection_id("SNAP-001", h1)
        id2 = compute_canonical_detection_id("SNAP-001", h2)
        assert id1 == id2
        assert id1.startswith("det_")

    def test_permutation_invariance_20_trials(self) -> None:
        """20 random orderings of input rows produce identical sorted output."""
        csv_path = FIXTURES_DIR / "viirs_snpp_valid.csv"
        with open(csv_path, encoding="utf-8") as f:
            lines = f.readlines()

        header = lines[0]
        data_rows = lines[1:]

        baseline = parse_firms_csv(
            csv_input="".join(lines),
            source_snapshot_id="SNAP-PERM-TEST",
        )
        baseline_ids = [d.detection_id for d in baseline]

        rng = random.Random(42)
        for _trial in range(20):
            shuffled_rows = list(data_rows)
            rng.shuffle(shuffled_rows)
            shuffled_csv = header + "".join(shuffled_rows)

            shuffled_result = parse_firms_csv(
                csv_input=shuffled_csv,
                source_snapshot_id="SNAP-PERM-TEST",
            )
            shuffled_ids = [d.detection_id for d in shuffled_result]
            assert shuffled_ids == baseline_ids
