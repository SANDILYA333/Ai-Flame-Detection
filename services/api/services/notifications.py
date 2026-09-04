"""Application service for multi-channel emergency notification dispatch, provider abstraction, and idempotency."""

from datetime import UTC, datetime
import re
from threading import Lock
from typing import ClassVar
import uuid

from packages.config.settings import Settings, get_settings
from packages.errors import ErrorCode, ValidationError
from packages.logging import get_logger
from packages.schemas.responders import (
    ChannelDeliveryStatus,
    ChannelResult,
    EscalationType,
    NotificationChannel,
    NotificationMode,
    ResponsePriority,
)
from services.api.services.providers.factory import NotificationProviderFactory
from services.api.services.providers.fast2sms import mask_phone_number

logger = get_logger("services.api.services.notifications")

# Strict E.164 and Indian mobile phone validation regex
_PHONE_REGEX = re.compile(r"^\+?[1-9]\d{6,14}$")
_CLEAN_PHONE_REGEX = re.compile(r"[\s\-\(\)]")


class NotificationService:
    """Service orchestrating SMS and WhatsApp emergency dispatch, provider routing, bounded retries, and idempotency."""

    _escalation_records: ClassVar[dict[str, datetime]] = {}
    _idempotency_cache: ClassVar[dict[str, ChannelResult]] = {}
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def generate_correlation_id(cls, event_id: str) -> str:
        """Generate a deterministic, unique correlation ID for tracing an alert across logs and providers."""
        short_uuid = uuid.uuid4().hex[:8]
        return f"CORR-{event_id}-{short_uuid}"

    @classmethod
    def make_idempotency_key(
        cls,
        event_id: str,
        responder_id: str,
        escalation_type: EscalationType,
        channel: NotificationChannel,
        trigger_source: str = "ADMIN_CONFIRMED",
        wind_sector: int | None = None,
    ) -> str:
        """Generate a deterministic logical idempotency key across all operational dimensions."""
        sector_str = f":wind_sec_{wind_sector}" if wind_sector is not None else ""
        return f"{event_id}:{responder_id}:{escalation_type.value}:{channel.value}:{trigger_source}{sector_str}"

    @classmethod
    def validate_and_normalize_phone(cls, phone: str | None) -> str:
        """Validate and format a phone number to standard E.164 format.

        Supports standard Indian numbers (10 digits starting with 6-9, with or without +91/0)
        as well as international E.164 compliant numbers.
        """
        if not phone or not phone.strip():
            raise ValidationError(
                "Recipient phone number is required for emergency dispatch.",
                code=ErrorCode.VALIDATION_ERROR,
            )

        cleaned = _CLEAN_PHONE_REGEX.sub("", phone.strip())

        # Handle Indian 10-digit without country code (e.g. 9876543210)
        if len(cleaned) == 10 and cleaned.isdigit() and cleaned[0] in "6789":
            cleaned = f"+91{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith("0") and cleaned[1] in "6789":
            cleaned = f"+91{cleaned[1:]}"
        elif not cleaned.startswith("+") and cleaned.isdigit():
            cleaned = f"+{cleaned}"

        if not _PHONE_REGEX.match(cleaned):
            raise ValidationError(
                f"Invalid phone number '{phone}'. Must be a valid Indian (+91) or E.164 international number.",
                code=ErrorCode.VALIDATION_ERROR,
            )

        return cleaned

    @classmethod
    def format_alert_message(
        cls,
        *,
        event_id: str,
        location: str,
        classification: str,
        confidence_percent: float,
        frp_mw: float,
        priority: ResponsePriority,
        is_critical: bool = False,
        mode: NotificationMode = NotificationMode.SIMULATED,
        wind_summary: str | None = None,
        hazard_reach_km: float | None = None,
        isolation_radius_m: float | None = 200.0,
    ) -> str:
        """Format scientific alert text adhering to Section 24 message template standards."""
        loc_str = location or "Spatial Anomaly Cluster"
        cls_str = classification or "UNCLASSIFIED"
        conf_str = f"{confidence_percent:.1f}"
        frp_str = f"{frp_mw:.1f}"

        mode_footer = (
            "\n\nThis is a simulated prototype notification."
            if mode == NotificationMode.SIMULATED
            else ""
        )

        wind_lines = ""
        if wind_summary:
            reach_str = f"\nPredicted Hazard Corridor: {hazard_reach_km:.1f} km" if hazard_reach_km else ""
            iso_str = f"\nModeled Isolation Zone: {isolation_radius_m:.0f} m" if isolation_radius_m else ""
            wind_lines = f"\nWind Conditions: {wind_summary}{reach_str}{iso_str}"

        if is_critical or priority == ResponsePriority.CRITICAL:
            return (
                "FLAME INTELLIGENCE — CRITICAL ALERT\n\n"
                "A thermal event has reached CRITICAL response priority.\n\n"
                f"Location: {loc_str}\n"
                f"Classification: {cls_str}\n"
                f"Model Confidence: {conf_str}%\n"
                f"Radiative Power (FRP): {frp_str} MW"
                f"{wind_lines}\n"
                f"Event ID: {event_id}\n\n"
                "Emergency response and medical preparedness are recommended."
                f"{mode_footer}"
            )

        return (
            "FLAME INTELLIGENCE ALERT\n\n"
            "A high-confidence thermal event has been detected by spaceborne sensors.\n\n"
            f"Location: {loc_str}\n"
            f"Classification: {cls_str}\n"
            f"Model Confidence: {conf_str}%\n"
            f"Radiative Power (FRP): {frp_str} MW"
            f"{wind_lines}\n"
            f"Event ID: {event_id}\n\n"
            "Emergency response assessment is recommended."
            f"{mode_footer}"
        )


    @classmethod
    def format_forest_proximity_message(
        cls,
        *,
        event_id: str,
        forest_name: str,
        distance_km: float,
        threat_level: str,
        inside_forest: bool = False,
        mode: NotificationMode = NotificationMode.SIMULATED,
    ) -> str:
        """Format operational forest proximity alert SMS/WhatsApp text."""
        mode_footer = (
            "\n\nThis is a simulated prototype notification."
            if mode == NotificationMode.SIMULATED
            else ""
        )
        if inside_forest or threat_level == "INSIDE_FOREST":
            return (
                "FOREST FIRE ALERT: CRITICAL\n\n"
                f"Thermal anomaly detected INSIDE monitored forest boundary: {forest_name}.\n"
                "Threat Level: FIRE INSIDE FOREST (0.0 km)\n"
                f"Event ID: {event_id}\n\n"
                "Immediate forest ranger deployment and containment recommended."
                f"{mode_footer}"
            )

        return (
            f"FOREST PROXIMITY ALERT: {threat_level}\n\n"
            f"Thermal anomaly detected {distance_km:.1f} km from {forest_name}.\n"
            f"Threat Level: {threat_level}\n"
            f"Event ID: {event_id}\n\n"
            "Immediate forest boundary monitoring recommended."
            f"{mode_footer}"
        )

    @classmethod
    def dispatch_multichannel(
        cls,
        *,
        event_id: str,
        recipient_phone: str,
        message_text: str,
        channels: list[NotificationChannel],
        mode: NotificationMode = NotificationMode.SIMULATED,
        responder_id: str = "responder-default",
        escalation_type: EscalationType = EscalationType.ADMIN_CONFIRMED,
        trigger_source: str = "ADMIN_CONFIRMED",
        wind_sector: int | None = None,
        correlation_id: str | None = None,
        settings: Settings | None = None,
    ) -> list[ChannelResult]:
        """Dispatch notifications across requested communication channels via provider abstractions."""
        cfg = settings or get_settings()
        results: list[ChannelResult] = []
        normalized_phone = cls.validate_and_normalize_phone(recipient_phone)
        masked_phone = mask_phone_number(normalized_phone)
        corr_id = correlation_id or cls.generate_correlation_id(event_id)

        for ch in channels:
            idem_key = cls.make_idempotency_key(
                event_id=event_id,
                responder_id=responder_id,
                escalation_type=escalation_type,
                channel=ch,
                trigger_source=trigger_source,
                wind_sector=wind_sector,
            )

            # Check fine-grained channel idempotency cache
            with cls._lock:
                if idem_key in cls._idempotency_cache:
                    cached = cls._idempotency_cache[idem_key]
                    logger.info(
                        f"Channel dispatch suppressed by idempotency cache for key: {idem_key}"
                    )
                    results.append(
                        ChannelResult(
                            channel=ch,
                            status=ChannelDeliveryStatus.DUPLICATE_SUPPRESSED,
                            recipient=normalized_phone,
                            destination_masked=masked_phone,
                            message=f"Duplicate notification dispatch suppressed for channel {ch.value}.",
                            provider=cached.provider or "idempotency_guard",
                            provider_message_id=cached.provider_message_id,
                            correlation_id=corr_id,
                            submitted_at=cached.submitted_at or datetime.now(UTC),
                            retry_count=0,
                        )
                    )
                    continue

            # Execute provider dispatch
            provider = NotificationProviderFactory.get_provider(ch, settings=cfg)
            result = provider.send(
                channel=ch,
                recipient=normalized_phone,
                message=message_text,
                mode=mode,
                correlation_id=corr_id,
            )

            # Ensure masked phone and correlation ID are set
            if not result.destination_masked:
                result = result.model_copy(update={"destination_masked": masked_phone})
            if not result.correlation_id:
                result = result.model_copy(update={"correlation_id": corr_id})

            # Cache successful dispatches
            if result.status in (
                ChannelDeliveryStatus.SENT,
                ChannelDeliveryStatus.PROVIDER_ACCEPTED,
                ChannelDeliveryStatus.SIMULATED,
            ):
                with cls._lock:
                    cls._idempotency_cache[idem_key] = result

            results.append(result)

        return results

    @classmethod
    def is_escalation_processed(
        cls,
        event_id: str,
        escalation_type: EscalationType,
    ) -> bool:
        """Check if an automatic escalation has already been executed for this event."""
        key = f"{event_id}:{escalation_type.value}"
        with cls._lock:
            return key in cls._escalation_records

    @classmethod
    def record_escalation(
        cls,
        event_id: str,
        escalation_type: EscalationType,
    ) -> bool:
        """Atomically mark an escalation as processed (returns True if freshly recorded, False if duplicate)."""
        key = f"{event_id}:{escalation_type.value}"
        with cls._lock:
            if key in cls._escalation_records:
                return False
            cls._escalation_records[key] = datetime.now(UTC)
            return True

    @classmethod
    def clear_escalation_records(cls) -> None:
        """Clear recorded escalations and idempotency cache (used for testing)."""
        with cls._lock:
            cls._escalation_records.clear()
            cls._idempotency_cache.clear()
