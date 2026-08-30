"""Adversarial leakage tests ensuring temporal, label, and identifier safety."""

import math
from datetime import UTC, datetime, timedelta

from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from packages.schemas.event import Event
from packages.schemas.ml import (
    LeakageRisk,
    TargetDefinition,
    TargetType,
    TargetUnit,
)
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.leakage import LeakageAuditor
from services.ml.features.standard_set import (
    APPROVED_FEATURES,
    DISQUALIFIED_CANDIDATES,
)


def _create_detection(
    det_id: str,
    acq_time: datetime,
    frp: float = 20.0,
) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_20260101",
        geometry=Coordinate(latitude=22.48, longitude=70.06),
        acquired_at=acq_time,
        satellite="SNPP",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash=f"hash_{det_id}",
        frp_mw=frp,
        brightness_ti4_k=330.0,
        confidence="nominal",
        day_night=DayNight.DAY,
    )


def _create_event(
    event_id: str,
    det_ids: list[str],
    start_time: datetime,
    end_time: datetime,
) -> Event:
    return Event(
        event_id=event_id,
        detection_ids=det_ids,
        detection_count=len(det_ids),
        started_at=start_time,
        ended_at=end_time,
        centroid_geometry=Coordinate(latitude=22.48, longitude=70.06),
        formation_configuration_id="cfg_event_v1",
        formation_configuration_version="v1.0",
    )


class TestMLLeakageSafety:
    """Adversarial test suite proving leakage resistance in feature extraction."""

    def test_future_detection_leakage_is_strictly_blocked(self) -> None:
        """Detections occurring after prediction time T are completely ignored."""
        t_pred = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

        # 2 detections in the past
        d_past_1 = _create_detection("d_p1", t_pred - timedelta(hours=2), frp=10.0)
        d_past_2 = _create_detection("d_p2", t_pred - timedelta(hours=1), frp=20.0)

        # 2 detections in the future relative to t_pred
        d_future_1 = _create_detection("d_f1", t_pred + timedelta(hours=1), frp=500.0)
        d_future_2 = _create_detection("d_f2", t_pred + timedelta(hours=3), frp=1000.0)

        event = _create_event(
            "evt_leak_test",
            ["d_p1", "d_p2", "d_f1", "d_f2"],
            t_pred - timedelta(hours=2),
            t_pred + timedelta(hours=3),
        )

        extractor = FeatureExtractor()
        record = extractor.extract_features_for_event(
            event=event,
            member_detections=[d_past_1, d_past_2, d_future_1, d_future_2],
            as_of_time=t_pred,
        )

        # Count must be 2, NOT 4
        assert record.features["detection_count"] == 2

        frp_mean = float(record.features["frp_mean_mw"] or 0.0)
        frp_max = float(record.features["frp_max_mw"] or 0.0)
        dur_hrs = float(record.features["duration_hours"] or 0.0)

        # Mean FRP must be (10 + 20) / 2 = 15.0, NOT (10 + 20 + 500 + 1000) / 4 = 382.5
        assert math.isclose(frp_mean, 15.0)

        # Max FRP must be 20.0, NOT 1000.0
        assert math.isclose(frp_max, 20.0)

        # Duration must be 1.0 hour, NOT 5.0 hours
        assert math.isclose(dur_hrs, 1.0)

    def test_future_preceding_events_are_strictly_excluded(self) -> None:
        """Historical event counts only include events completed before T_prediction."""
        t_pred = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        d_current = _create_detection("d_curr", t_pred)
        event = _create_event("evt_curr", ["d_curr"], t_pred, t_pred)

        # Preceding event in the past (ended at T - 4h)
        e_past = _create_event(
            "evt_past",
            ["d_p"],
            t_pred - timedelta(hours=5),
            t_pred - timedelta(hours=4),
        )

        # Future event (ended at T + 2h)
        e_future = _create_event(
            "evt_future",
            ["d_f"],
            t_pred + timedelta(hours=1),
            t_pred + timedelta(hours=2),
        )

        extractor = FeatureExtractor()
        record = extractor.extract_features_for_event(
            event=event,
            member_detections=[d_current],
            as_of_time=t_pred,
            preceding_events=[e_past, e_future],
        )

        # Only 1 past event within 24h
        assert record.features["prior_event_count_24h"] == 1
        # Elapsed time is (12:00 - 08:00) = 4.0 hours
        elapsed = float(record.features["time_since_previous_event_hours"] or 0.0)
        assert math.isclose(elapsed, 4.0)

    def test_identifiers_are_excluded_from_model_features(self) -> None:
        """No raw IDs (event_id, source_id, facility_id) appear in features dict."""
        t_pred = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        d1 = _create_detection("d1", t_pred)
        event = _create_event("evt_sec_001", ["d1"], t_pred, t_pred)

        extractor = FeatureExtractor()
        record = extractor.extract_features_for_event(
            event=event,
            member_detections=[d1],
            as_of_time=t_pred,
        )

        disallowed_keys = {
            "event_id",
            "source_id",
            "detection_id",
            "facility_id",
            "raw_record_id",
            "raw_event_id",
            "raw_source_id",
            "raw_facility_id",
            "reference_class",
            "reference_label",
            "label_confidence",
        }

        feature_keys = set(record.features.keys())
        overlap = feature_keys & disallowed_keys
        assert len(overlap) == 0, (
            f"Disallowed identifier/label keys in features: {overlap}"
        )

    def test_disallowed_candidates_are_rejected_by_leakage_auditor(
        self,
    ) -> None:
        """LeakageAuditor flags reference labels and post-event features as unsafe."""
        auditor = LeakageAuditor()
        target = TargetDefinition(
            target_id="target_phenomenon_v1",
            name="Thermal Phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            unit_of_prediction=TargetUnit.EVENT,
            class_vocabulary=["flare", "wildfire", "industrial"],
            is_approved=True,
        )

        report = auditor.audit_feature_set(
            DISQUALIFIED_CANDIDATES, target_definition=target
        )
        assert report.is_safe is False
        assert report.violation_count >= len(DISQUALIFIED_CANDIDATES)

        # Verify specific violation types
        risk_types = {v.risk_type for v in report.violations}
        assert LeakageRisk.DIRECT_LEAKAGE in risk_types
        assert LeakageRisk.TEMPORAL_LEAKAGE in risk_types

    def test_approved_feature_set_is_100_percent_clean_in_leakage_audit(
        self,
    ) -> None:
        """All APPROVED_FEATURES pass the LeakageAuditor with zero violations."""
        auditor = LeakageAuditor()
        target = TargetDefinition(
            target_id="target_phenomenon_v1",
            name="Thermal Phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            unit_of_prediction=TargetUnit.EVENT,
            class_vocabulary=["flare", "wildfire", "industrial"],
            is_approved=True,
        )

        report = auditor.audit_feature_set(APPROVED_FEATURES, target_definition=target)
        assert report.is_safe is True
        assert report.violation_count == 0
        assert report.safe_count == len(APPROVED_FEATURES)
