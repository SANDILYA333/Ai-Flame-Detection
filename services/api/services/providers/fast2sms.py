"""Fast2SMS messaging provider abstraction for live and simulated SMS delivery with bounded retries and audit tracking."""

from datetime import UTC, datetime
import re
import time

import httpx

from packages.config.settings import Settings, get_settings
from packages.logging import get_logger
from packages.schemas.responders import (
    ChannelDeliveryStatus,
    ChannelResult,
    NotificationChannel,
    NotificationMode,
)
from services.api.services.providers.base import BaseNotificationProvider

logger = get_logger("services.api.services.providers.fast2sms")

_NON_DIGIT_REGEX = re.compile(r"\D")


def mask_phone_number(phone: str | None) -> str:
    """Mask phone number for safe logging and audit records (e.g. +91 ******1234)."""
    if not phone:
        return "N/A"
    clean = phone.strip()
    if len(clean) <= 5:
        return "****"
    if clean.startswith("+91") and len(clean) >= 10:
        return f"+91 ******{clean[-4:]}"
    if len(clean) >= 8:
        return f"{clean[:3]}******{clean[-4:]}"
    return f"{clean[:2]}***{clean[-2:]}"


class Fast2SMSProvider(BaseNotificationProvider):
    """Fast2SMS SMS gateway provider implementation with bounded retries and safe status mapping."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def provider_id(self) -> str:
        return "fast2sms"

    @property
    def supported_channels(self) -> set[NotificationChannel]:
        return {NotificationChannel.SMS}

    @staticmethod
    def _extract_10_digit_indian_number(phone: str) -> str:
        """Extract clean 10-digit mobile number for Fast2SMS payload."""
        digits = _NON_DIGIT_REGEX.sub("", phone)
        if len(digits) == 10:
            return digits
        if len(digits) == 12 and digits.startswith("91"):
            return digits[2:]
        if len(digits) == 11 and digits.startswith("0"):
            return digits[1:]
        return digits[-10:] if len(digits) >= 10 else digits

    def send(
        self,
        *,
        channel: NotificationChannel,
        recipient: str,
        message: str,
        mode: NotificationMode = NotificationMode.SIMULATED,
        correlation_id: str | None = None,
    ) -> ChannelResult:
        """Send SMS via Fast2SMS gateway or truth-preserving simulation with bounded retry logic."""
        masked_phone = mask_phone_number(recipient)
        now = datetime.now(UTC)
        now_str = now.strftime("%Y%m%d%H%M%S")

        if channel != NotificationChannel.SMS:
            return ChannelResult(
                channel=channel,
                status=ChannelDeliveryStatus.FAILED,
                recipient=recipient,
                destination_masked=masked_phone,
                message=f"Fast2SMS provider does not support channel {channel.value}.",
                provider=self.provider_id,
                correlation_id=correlation_id,
                submitted_at=now,
                error_details=f"Unsupported channel: {channel.value}",
            )

        # 1. Handle SIMULATED mode or unconfigured / disabled credentials
        has_api_key = bool(
            self._settings.FAST2SMS_API_KEY
            and self._settings.FAST2SMS_API_KEY.get_secret_value().strip()
        )
        is_enabled = self._settings.FAST2SMS_ENABLED

        if mode == NotificationMode.SIMULATED or not has_api_key or not is_enabled:
            sim_reason = (
                "Simulation mode explicitly selected"
                if mode == NotificationMode.SIMULATED
                else "Fast2SMS API key not configured or provider disabled"
            )
            logger.info(
                f"[Fast2SMS-Simulation] {sim_reason} for recipient {masked_phone} (Correlation={correlation_id})"
            )
            return ChannelResult(
                channel=NotificationChannel.SMS,
                status=ChannelDeliveryStatus.SIMULATED,
                recipient=recipient,
                destination_masked=masked_phone,
                message=f"SMS alert simulated successfully for {recipient}.",
                provider=self.provider_id,
                provider_message_id=f"F2S-SIM-{now_str}",
                correlation_id=correlation_id,
                submitted_at=now,
                delivered_at=now,
                retry_count=0,
            )

        # 2. Live Fast2SMS Gateway Dispatch with Bounded Retries
        api_key = self._settings.FAST2SMS_API_KEY.get_secret_value()  # type: ignore[union-attr]
        clean_number = self._extract_10_digit_indian_number(recipient)

        payload = {
            "route": "q",
            "message": message,
            "language": "english",
            "flash": 0,
            "numbers": clean_number,
        }

        headers = {
            "authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        timeout = self._settings.NOTIFICATION_TIMEOUT_SECONDS
        max_retries = self._settings.NOTIFICATION_MAX_RETRIES
        backoff_sec = self._settings.NOTIFICATION_RETRY_BACKOFF_SECONDS

        last_error_details = ""
        total_attempts = 0

        for attempt in range(max_retries + 1):
            total_attempts = attempt + 1
            submitted_ts = datetime.now(UTC)

            try:
                logger.info(
                    f"[Fast2SMS-Live] Dispatching live SMS (Attempt {total_attempts}/{max_retries + 1}) "
                    f"to {masked_phone} (Timeout={timeout}s, Correlation={correlation_id})"
                )
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        self._settings.FAST2SMS_BASE_URL,
                        json=payload,
                        headers=headers,
                    )

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception:
                        data = {}

                    if data.get("return") is True:
                        req_id = str(data.get("request_id") or f"F2S-{now_str}")
                        logger.info(
                            f"[Fast2SMS-Live] SMS successfully accepted by Fast2SMS "
                            f"(Request ID: {req_id}, Attempts: {total_attempts})"
                        )
                        return ChannelResult(
                            channel=NotificationChannel.SMS,
                            status=ChannelDeliveryStatus.SENT,
                            recipient=recipient,
                            destination_masked=masked_phone,
                            message=f"SMS alert dispatched successfully via Fast2SMS to {recipient}.",
                            provider=self.provider_id,
                            provider_message_id=req_id,
                            correlation_id=correlation_id,
                            submitted_at=submitted_ts,
                            retry_count=attempt,
                        )
                    else:
                        err_msgs = data.get("message")
                        err_str = (
                            ", ".join(err_msgs)
                            if isinstance(err_msgs, list)
                            else str(err_msgs or "Rejected by Fast2SMS")
                        )
                        logger.warning(
                            f"[Fast2SMS-Live] Gateway rejected SMS: {err_str} (Non-retryable)"
                        )
                        return ChannelResult(
                            channel=NotificationChannel.SMS,
                            status=ChannelDeliveryStatus.FAILED,
                            recipient=recipient,
                            destination_masked=masked_phone,
                            message=f"SMS delivery rejected by Fast2SMS: {err_str}",
                            provider=self.provider_id,
                            provider_message_id=None,
                            correlation_id=correlation_id,
                            submitted_at=submitted_ts,
                            retry_count=attempt,
                            error_details=f"Fast2SMS rejection: {err_str}",
                        )

                # HTTP 4xx (Non-retryable client / auth error)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    logger.error(
                        f"[Fast2SMS-Live] Client error HTTP {response.status_code} from Fast2SMS (Non-retryable)"
                    )
                    return ChannelResult(
                        channel=NotificationChannel.SMS,
                        status=ChannelDeliveryStatus.FAILED,
                        recipient=recipient,
                        destination_masked=masked_phone,
                        message="SMS delivery failed at Fast2SMS gateway (Authentication or Client Error).",
                        provider=self.provider_id,
                        correlation_id=correlation_id,
                        submitted_at=submitted_ts,
                        retry_count=attempt,
                        error_details=f"HTTP {response.status_code}: {response.text[:200]}",
                    )

                # HTTP 5xx or 429 Rate Limit (Retryable)
                last_error_details = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(
                    f"[Fast2SMS-Live] Retryable HTTP {response.status_code} received on attempt {total_attempts}"
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error_details = f"{type(exc).__name__}: {str(exc)}"
                logger.warning(
                    f"[Fast2SMS-Live] Transient network error on attempt {total_attempts}: {exc}"
                )
            except Exception as exc:
                last_error_details = f"Unexpected error: {str(exc)}"
                logger.error(f"[Fast2SMS-Live] Unexpected error on attempt {total_attempts}: {exc}")

            # Apply backoff before next attempt
            if attempt < max_retries:
                sleep_duration = backoff_sec * (2**attempt)
                logger.info(f"[Fast2SMS-Live] Backing off for {sleep_duration:.2f}s before retry")
                time.sleep(sleep_duration)

        # All retries exhausted
        logger.error(
            f"[Fast2SMS-Live] Dispatch failed after {total_attempts} attempts. Last error: {last_error_details}"
        )
        return ChannelResult(
            channel=NotificationChannel.SMS,
            status=ChannelDeliveryStatus.FAILED,
            recipient=recipient,
            destination_masked=masked_phone,
            message="SMS delivery failed after maximum retry attempts.",
            provider=self.provider_id,
            provider_message_id=None,
            correlation_id=correlation_id,
            submitted_at=now,
            retry_count=max_retries,
            error_details=last_error_details,
        )
