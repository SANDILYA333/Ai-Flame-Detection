"""Unit and integration tests for backend escalation engine (Phase 2)."""

import pytest
from fastapi.testclient import TestClient

from packages.config.settings import Settings
from packages.errors import ValidationError
from packages.schemas.responders import (
    EscalationState,
    ResponsePriority,
)
from services.api.app import create_app
from services.api.services.escalation import EscalationPolicyService
from services.api.services.events import EventQueryService


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_mandatory_boundary_94_00_percent() -> None:
    """TEST 1: confidence = 0.9400 -> NO_ESCALATION, automatic = False."""
    decision = EscalationPolicyService.evaluate_decision(
        event_id="EVT-TEST-001",
        confidence=0.9400,
        operational_priority=ResponsePriority.MEDIUM,
    )
    assert decision.escalation_state == EscalationState.NO_ESCALATION
    assert decision.automatic is False
    assert decision.medical_escalation is False
    assert "confidence_at_or_below_review_threshold" in decision.policy_drivers


def test_mandatory_boundary_94_01_percent() -> None:
    """TEST 2: confidence = 0.9401 -> ADMIN_REVIEW_REQUIRED, automatic = False."""
    decision = EscalationPolicyService.evaluate_decision(
        event_id="EVT-TEST-002",
        confidence=0.9401,
        operational_priority=ResponsePriority.HIGH,
    )
    assert decision.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED
    assert decision.automatic is False
    assert decision.medical_escalation is False
    assert "confidence_above_review_threshold" in decision.policy_drivers


def test_mandatory_boundary_98_00_percent() -> None:
    """TEST 3: confidence = 0.9800 -> ADMIN_REVIEW_REQUIRED, automatic = False."""
    decision = EscalationPolicyService.evaluate_decision(
        event_id="EVT-TEST-003",
        confidence=0.9800,
        operational_priority=ResponsePriority.HIGH,
    )
    assert decision.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED
    assert decision.automatic is False
    assert decision.medical_escalation is False
    assert "confidence_above_review_threshold" in decision.policy_drivers


def test_mandatory_boundary_98_01_percent() -> None:
    """TEST 4: confidence = 0.9801 -> AUTOMATIC_ESCALATION, automatic = True."""
    decision = EscalationPolicyService.evaluate_decision(
        event_id="EVT-TEST-004",
        confidence=0.9801,
        operational_priority=ResponsePriority.HIGH,
    )
    assert decision.escalation_state == EscalationState.AUTOMATIC_ESCALATION
    assert decision.automatic is True
    assert decision.medical_escalation is False
    assert "confidence_above_auto_threshold" in decision.policy_drivers


def test_critical_combinations_matrix() -> None:
    """Verify the full 6-case critical and confidence escalation combinations matrix."""
    # A. 94% + Non-Critical -> NO_ESCALATION, medical = False, auto = False
    dA = EscalationPolicyService.evaluate_decision(
        event_id="EVT-MAT-A",
        confidence=0.9400,
        operational_priority=ResponsePriority.MEDIUM,
    )
    assert dA.escalation_state == EscalationState.NO_ESCALATION
    assert dA.medical_escalation is False
    assert dA.automatic is False

    # B. 97% + Non-Critical -> ADMIN_REVIEW_REQUIRED, medical = False, auto = False
    dB = EscalationPolicyService.evaluate_decision(
        event_id="EVT-MAT-B",
        confidence=0.9700,
        operational_priority=ResponsePriority.HIGH,
    )
    assert dB.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED
    assert dB.medical_escalation is False
    assert dB.automatic is False

    # C. 97% + CRITICAL -> ADMIN_REVIEW_REQUIRED, medical = True, auto = False
    dC = EscalationPolicyService.evaluate_decision(
        event_id="EVT-MAT-C",
        confidence=0.9700,
        operational_priority=ResponsePriority.CRITICAL,
    )
    assert dC.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED
    assert dC.medical_escalation is True
    assert dC.automatic is False
    assert "operational_attention_critical" in dC.policy_drivers

    # D. 98% + CRITICAL -> ADMIN_REVIEW_REQUIRED, medical = True, auto = False
    dD = EscalationPolicyService.evaluate_decision(
        event_id="EVT-MAT-D",
        confidence=0.9800,
        operational_priority=ResponsePriority.CRITICAL,
    )
    assert dD.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED
    assert dD.medical_escalation is True
    assert dD.automatic is False

    # E. 98.01% + CRITICAL -> AUTOMATIC_ESCALATION, medical = True, auto = True
    dE = EscalationPolicyService.evaluate_decision(
        event_id="EVT-MAT-E",
        confidence=0.9801,
        operational_priority=ResponsePriority.CRITICAL,
    )
    assert dE.escalation_state == EscalationState.AUTOMATIC_ESCALATION
    assert dE.medical_escalation is True
    assert dE.automatic is True

    # F. 99% + Non-Critical -> AUTOMATIC_ESCALATION, medical = False, auto = True
    dF = EscalationPolicyService.evaluate_decision(
        event_id="EVT-MAT-F",
        confidence=0.9900,
        operational_priority=ResponsePriority.HIGH,
    )
    assert dF.escalation_state == EscalationState.AUTOMATIC_ESCALATION
    assert dF.medical_escalation is False
    assert dF.automatic is True


def test_mumbai_high_target_case() -> None:
    """Verify Mumbai High Target Case: 97.0% confidence + CRITICAL priority."""
    decision = EscalationPolicyService.evaluate_decision(
        event_id="EVT-2026-0831-13",
        confidence=0.970,
        operational_priority=ResponsePriority.CRITICAL,
    )
    assert decision.event_id == "EVT-2026-0831-13"
    assert decision.confidence == 0.970
    assert decision.operational_priority == ResponsePriority.CRITICAL
    assert decision.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED
    assert decision.automatic is False
    assert decision.medical_escalation is True
    assert "confidence_above_review_threshold" in decision.policy_drivers
    assert "operational_attention_critical" in decision.policy_drivers


def test_invalid_and_missing_inputs_safety() -> None:
    """Verify invalid or missing inputs fail safely without automatic escalation."""
    # 1. Missing confidence (None)
    d_none = EscalationPolicyService.evaluate_decision(
        event_id="EVT-SAFE-01",
        confidence=None,
        operational_priority=ResponsePriority.MEDIUM,
    )
    assert d_none.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED
    assert d_none.automatic is False
    assert d_none.confidence is None
    assert "uncalibrated_or_missing_confidence" in d_none.policy_drivers

    # 2. Negative confidence (< 0)
    d_neg = EscalationPolicyService.evaluate_decision(
        event_id="EVT-SAFE-02",
        confidence=-0.15,
        operational_priority=ResponsePriority.HIGH,
    )
    assert d_neg.automatic is False
    assert d_neg.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED

    # 3. Excessive confidence (> 1.0)
    d_over = EscalationPolicyService.evaluate_decision(
        event_id="EVT-SAFE-03",
        confidence=1.5,
        operational_priority=ResponsePriority.HIGH,
    )
    assert d_over.automatic is False
    assert d_over.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED

    # 4. NaN / Inf confidence
    d_nan = EscalationPolicyService.evaluate_decision(
        event_id="EVT-SAFE-04",
        confidence=float("nan"),
        operational_priority=ResponsePriority.HIGH,
    )
    assert d_nan.automatic is False
    assert d_nan.escalation_state == EscalationState.ADMIN_REVIEW_REQUIRED

    # 5. Empty event_id raises ValidationError
    with pytest.raises(ValidationError):
        EscalationPolicyService.evaluate_decision(
            event_id="",
            confidence=0.95,
            operational_priority=ResponsePriority.HIGH,
        )


def test_evaluation_determinism() -> None:
    """Verify evaluation is 100% deterministic across repeated runs."""
    results = [
        EscalationPolicyService.evaluate_decision(
            event_id="EVT-DET-01",
            confidence=0.985,
            operational_priority=ResponsePriority.CRITICAL,
        )
        for _ in range(50)
    ]

    first = results[0]
    for r in results[1:]:
        assert r.event_id == first.event_id
        assert r.confidence == first.confidence
        assert r.escalation_state == first.escalation_state
        assert r.automatic == first.automatic
        assert r.medical_escalation == first.medical_escalation
        assert r.policy_drivers == first.policy_drivers


def test_threshold_configuration_validation() -> None:
    """Verify invalid threshold configuration is rejected."""
    invalid_settings = Settings(
        EMERGENCY_REVIEW_MIN_CONFIDENCE=0.98,
        EMERGENCY_AUTO_ESCALATION_MIN_CONFIDENCE=0.94,  # invalid: auto < review
    )
    with pytest.raises(ValidationError):
        EscalationPolicyService.evaluate_decision(
            event_id="EVT-CFG-ERR",
            confidence=0.95,
            operational_priority=ResponsePriority.HIGH,
            settings=invalid_settings,
        )


def test_api_get_escalation_decision(client: TestClient) -> None:
    """Test GET /events/{event_id}/escalation returns authoritative decision."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    response = client.get(f"/events/{event_id}/escalation")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == event_id
    assert "escalation_state" in data
    assert data["escalation_state"] in [
        "NO_ESCALATION",
        "ADMIN_REVIEW_REQUIRED",
        "AUTOMATIC_ESCALATION",
    ]
    assert "automatic" in data
    assert isinstance(data["automatic"], bool)
    assert "medical_escalation" in data
    assert isinstance(data["medical_escalation"], bool)
    assert "policy_drivers" in data
    assert len(data["policy_drivers"]) > 0


def test_api_get_escalation_nonexistent_event_returns_404(client: TestClient) -> None:
    """Test GET /events/{event_id}/escalation returns 404 for unknown event ID."""
    response = client.get("/events/NONEXISTENT-EVT-99999/escalation")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data or "message" in data or "detail" in data
