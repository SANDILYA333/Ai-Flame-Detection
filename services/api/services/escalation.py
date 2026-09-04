"""Backend escalation policy engine for Emergency Response & Regulation (Phase 2)."""

import math
from datetime import UTC, datetime

from packages.config.settings import Settings, get_settings
from packages.errors import ErrorCode, NotFoundError, ValidationError
from packages.logging import get_logger
from packages.schemas.responders import (
    EscalationDecision,
    EscalationState,
    ResponsePriority,
)

logger = get_logger("services.api.services.escalation")


class EscalationPolicyService:
    """Deterministic backend-authoritative emergency escalation policy evaluator."""

    @classmethod
    def validate_threshold_configuration(cls, settings: Settings) -> None:
        """Validate that configured escalation thresholds are mathematically consistent.

        Rule: 0.0 <= review_threshold < auto_threshold <= 1.0
        """
        rev = settings.EMERGENCY_REVIEW_MIN_CONFIDENCE
        auto = settings.EMERGENCY_AUTO_ESCALATION_MIN_CONFIDENCE

        if not (0.0 <= rev < auto <= 1.0):
            raise ValidationError(
                f"Invalid escalation threshold configuration: review_min ({rev}) "
                f"must be strictly less than auto_min ({auto}) in [0.0, 1.0].",
                code=ErrorCode.VALIDATION_ERROR,
            )

    @classmethod
    def evaluate_decision(
        cls,
        *,
        event_id: str,
        confidence: float | None,
        operational_priority: ResponsePriority,
        settings: Settings | None = None,
    ) -> EscalationDecision:
        """Evaluate emergency escalation policy deterministically.

        Policy Invariants:
        1. confidence <= 0.94 -> NO_ESCALATION, automatic = False
        2. 0.94 < confidence <= 0.98 -> ADMIN_REVIEW_REQUIRED, automatic = False
        3. confidence > 0.98 -> AUTOMATIC_ESCALATION, automatic = True (if enabled)
        4. priority == CRITICAL -> medical_escalation = True
        5. Missing/invalid confidence -> safe fallback (ADMIN_REVIEW_REQUIRED)
        """
        if not event_id or not event_id.strip():
            raise ValidationError(
                "event_id is required for escalation policy evaluation.",
                code=ErrorCode.VALIDATION_ERROR,
            )

        cfg = settings or get_settings()
        cls.validate_threshold_configuration(cfg)

        review_threshold = cfg.EMERGENCY_REVIEW_MIN_CONFIDENCE
        auto_threshold = cfg.EMERGENCY_AUTO_ESCALATION_MIN_CONFIDENCE
        auto_enabled = cfg.EMERGENCY_AUTO_ESCALATION_ENABLED

        policy_drivers: list[str] = []

        # 1. Determine Medical Escalation (Independent Dimension)
        is_critical = operational_priority == ResponsePriority.CRITICAL
        medical_escalation = is_critical
        if is_critical:
            policy_drivers.append("operational_attention_critical")
        else:
            policy_drivers.append("operational_attention_standard")

        # 2. Validate & Evaluate Confidence Thresholds
        is_invalid_conf = (
            confidence is None
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or confidence < 0.0
            or confidence > 1.0
        )

        if is_invalid_conf:
            # Safe fallback: never auto-escalate on missing/invalid confidence
            policy_drivers.append("uncalibrated_or_missing_confidence")
            logger.warning(
                f"Event {event_id}: Missing/invalid confidence ({confidence}). "
                "Defaulting to safe ADMIN_REVIEW_REQUIRED."
            )
            return EscalationDecision(
                event_id=event_id,
                confidence=None,
                operational_priority=operational_priority,
                escalation_state=EscalationState.ADMIN_REVIEW_REQUIRED,
                automatic=False,
                medical_escalation=medical_escalation,
                policy_drivers=policy_drivers,
                evaluated_at=datetime.now(UTC),
                policy_version="v1.0.0",
            )

        conf_val = float(confidence)

        # 3. Exact Threshold Evaluation
        if conf_val <= review_threshold:
            escalation_state = EscalationState.NO_ESCALATION
            automatic = False
            policy_drivers.append("confidence_at_or_below_review_threshold")
        elif conf_val <= auto_threshold:
            escalation_state = EscalationState.ADMIN_REVIEW_REQUIRED
            automatic = False
            policy_drivers.append("confidence_above_review_threshold")
        else:
            if auto_enabled:
                escalation_state = EscalationState.AUTOMATIC_ESCALATION
                automatic = True
                policy_drivers.append("confidence_above_auto_threshold")
            else:
                escalation_state = EscalationState.ADMIN_REVIEW_REQUIRED
                automatic = False
                policy_drivers.append("auto_escalation_disabled_by_config")

        logger.info(
            f"Escalation evaluated for Event {event_id}: "
            f"State={escalation_state.value}, Auto={automatic}, "
            f"Medical={medical_escalation}, Conf={conf_val:.4f}, "
            f"Priority={operational_priority.value}"
        )

        return EscalationDecision(
            event_id=event_id,
            confidence=round(conf_val, 4),
            operational_priority=operational_priority,
            escalation_state=escalation_state,
            automatic=automatic,
            medical_escalation=medical_escalation,
            policy_drivers=policy_drivers,
            evaluated_at=datetime.now(UTC),
            policy_version="v1.0.0",
        )

    @classmethod
    def evaluate_event(
        cls,
        event_id: str,
        settings: Settings | None = None,
    ) -> EscalationDecision:
        """Resolve authoritative runtime event data and compute escalation decision."""
        from services.api.services.events import EventQueryService

        dataset = EventQueryService.get_canonical_enriched_dataset()
        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )
        if target_event is None:
            raise NotFoundError(
                message=f"Event '{event_id}' not found for escalation evaluation.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 1. Resolve Calibrated Confidence from authoritative intelligence
        label = next(
            (lbl for lbl in dataset.reference_labels if lbl.entity_id == event_id),
            None,
        )
        confidence: float | None = None
        if label and label.confidence_score is not None:
            confidence = float(label.confidence_score)
        else:
            try:
                intel = EventQueryService.get_event_intelligence(event_id)
                if intel.uncertainty.calibrated_confidence is not None:
                    confidence = float(intel.uncertainty.calibrated_confidence)
            except Exception:
                confidence = None

        # 2. Resolve Operational Priority / Attention
        classification = "UNKNOWN"
        if label and label.assigned_class:
            classification = label.assigned_class.strip().upper()
        elif getattr(target_event, "classification_state", None):
            classification = str(target_event.classification_state).strip().upper()

        max_frp = float(target_event.max_frp_mw or 0.0)

        is_abstained_or_unknown = classification == "UNKNOWN" or (
            label is not None
            and getattr(label, "label_tier", None)
            and label.label_tier.value == "TIER_C"
        )

        if is_abstained_or_unknown:
            priority = ResponsePriority.REVIEW_REQUIRED
        elif classification == "INDUSTRIAL":
            if max_frp > 50.0:
                priority = ResponsePriority.CRITICAL
            else:
                priority = ResponsePriority.HIGH
        else:
            priority = ResponsePriority.MEDIUM

        return cls.evaluate_decision(
            event_id=event_id,
            confidence=confidence,
            operational_priority=priority,
            settings=settings,
        )
