"""RichAutomate WhatsApp messaging provider abstraction with bounded retries and audit tracking."""

from datetime import UTC, datetime
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
from services.api.services.providers.fast2sms import mask_phone_number

logger = get_logger("services.api.services.providers.richautomate")


class RichAutomateWhatsAppProvider(BaseNotificationProvider):
    """RichAutomate WhatsApp gateway provider implementation with bounded retries and error classification."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def provider_id(self) -> str:
        return "richautomate"

    @property
    def supported_channels(self) -> set[NotificationChannel]:
        return {NotificationChannel.WHATSAPP}

    def send(
        self,
        *,
        channel: NotificationChannel,
        recipient: str,
        message: str,
        mode: NotificationMode = NotificationMode.SIMULATED,
        correlation_id: str | None = None,
    ) -> ChannelResult:
        """Send WhatsApp alert via RichAutomate gateway or truth-preserving simulation with bounded retry logic."""
        masked_phone = mask_phone_number(recipient)
        now = datetime.now(UTC)
        now_str = now.strftime("%Y%m%d%H%M%S")

        if channel != NotificationChannel.WHATSAPP:
            return ChannelResult(
                channel=channel,
                status=ChannelDeliveryStatus.FAILED,
                recipient=recipient,
                destination_masked=masked_phone,
                message=f"RichAutomate provider does not support channel {channel.value}.",
                provider=self.provider_id,
                correlation_id=correlation_id,
                submitted_at=now,
                error_details=f"Unsupported channel: {channel.value}",
            )

        # 1. Handle SIMULATED mode or unconfigured / disabled credentials
        has_api_key = bool(
            self._settings.RICHAUTOMATE_API_KEY
            and self._settings.RICHAUTOMATE_API_KEY.get_secret_value().strip()
        )
        is_enabled = self._settings.RICHAUTOMATE_ENABLED

        if mode == NotificationMode.SIMULATED or not has_api_key or not is_enabled:
            sim_reason = (
                "Simulation mode explicitly selected"
                if mode == NotificationMode.SIMULATED
                else "RichAutomate API key not configured or provider disabled"
            )
            logger.info(
                f"[RichAutomate-Simulation] {sim_reason} for recipient {masked_phone} (Correlation={correlation_id})"
            )
            return ChannelResult(
                channel=NotificationChannel.WHATSAPP,
                status=ChannelDeliveryStatus.SIMULATED,
                recipient=recipient,
                destination_masked=masked_phone,
                message=f"WhatsApp alert simulated successfully for {recipient}.",
                provider=self.provider_id,
                provider_message_id=f"RA-SIM-{now_str}",
                correlation_id=correlation_id,
                submitted_at=now,
                delivered_at=now,
                retry_count=0,
            )

        # 2. Live RichAutomate WhatsApp Gateway Dispatch with Bounded Retries
        api_key = self._settings.RICHAUTOMATE_API_KEY.get_secret_value()  # type: ignore[union-attr]
        base_url = self._settings.RICHAUTOMATE_BASE_URL.rstrip("/")
        endpoint_url = f"{base_url}/messages"

        payload = {
            "to": recipient,
            "type": "text",
            "text": {
                "body": message,
            },
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
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
                    f"[RichAutomate-Live] Dispatching live WhatsApp alert (Attempt {total_attempts}/{max_retries + 1}) "
                    f"to {masked_phone} (Timeout={timeout}s, Correlation={correlation_id})"
                )
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        endpoint_url,
                        json=payload,
                        headers=headers,
                    )

                if response.status_code in (200, 201, 202):
                    try:
                        data = response.json()
                    except Exception:
                        data = {}

                    msg_id = str(
                        data.get("id")
                        or data.get("message_id")
                        or (
                            data.get("messages", [{}])[0].get("id")
                            if isinstance(data.get("messages"), list)
                            and data.get("messages")
                            else None
                        )
                        or f"RA-{now_str}"
                    )
                    logger.info(
                        f"[RichAutomate-Live] WhatsApp alert accepted by RichAutomate "
                        f"(Message ID: {msg_id}, Attempts: {total_attempts})"
                    )
                    return ChannelResult(
                        channel=NotificationChannel.WHATSAPP,
                        status=ChannelDeliveryStatus.SENT,
                        recipient=recipient,
                        destination_masked=masked_phone,
                        message=f"WhatsApp alert dispatched successfully via RichAutomate to {recipient}.",
                        provider=self.provider_id,
                        provider_message_id=msg_id,
                        correlation_id=correlation_id,
                        submitted_at=submitted_ts,
                        retry_count=attempt,
                    )

                # HTTP 401 Unauthorized (Non-retryable)
                if response.status_code == 401:
                    logger.error(
                        f"[RichAutomate-Live] Authentication failure: Invalid API Key (Non-retryable)"
                    )
                    return ChannelResult(
                        channel=NotificationChannel.WHATSAPP,
                        status=ChannelDeliveryStatus.FAILED,
                        recipient=recipient,
                        destination_masked=masked_phone,
                        message="WhatsApp gateway authentication failed: Invalid API credentials.",
                        provider=self.provider_id,
                        correlation_id=correlation_id,
                        submitted_at=submitted_ts,
                        retry_count=attempt,
                        error_details="RichAutomate returned HTTP 401 Unauthorized",
                    )

                # Other HTTP 4xx Client Errors (Non-retryable)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    logger.error(
                        f"[RichAutomate-Live] Client error HTTP {response.status_code}: {response.text[:200]} (Non-retryable)"
                    )
                    return ChannelResult(
                        channel=NotificationChannel.WHATSAPP,
                        status=ChannelDeliveryStatus.FAILED,
                        recipient=recipient,
                        destination_masked=masked_phone,
                        message="WhatsApp delivery rejected at gateway.",
                        provider=self.provider_id,
                        correlation_id=correlation_id,
                        submitted_at=submitted_ts,
                        retry_count=attempt,
                        error_details=f"HTTP {response.status_code}: {response.text[:200]}",
                    )

                # HTTP 5xx or 429 Rate Limit (Retryable)
                last_error_details = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(
                    f"[RichAutomate-Live] Retryable HTTP {response.status_code} received on attempt {total_attempts}"
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error_details = f"{type(exc).__name__}: {str(exc)}"
                logger.warning(
                    f"[RichAutomate-Live] Transient network error on attempt {total_attempts}: {exc}"
                )
            except Exception as exc:
                last_error_details = f"Unexpected error: {str(exc)}"
                logger.error(
                    f"[RichAutomate-Live] Unexpected error on attempt {total_attempts}: {exc}"
                )

            # Apply backoff before next attempt
            if attempt < max_retries:
                sleep_duration = backoff_sec * (2**attempt)
                logger.info(
                    f"[RichAutomate-Live] Backing off for {sleep_duration:.2f}s before retry"
                )
                time.sleep(sleep_duration)

        # All retries exhausted
        logger.error(
            f"[RichAutomate-Live] Dispatch failed after {total_attempts} attempts. Last error: {last_error_details}"
        )
        return ChannelResult(
            channel=NotificationChannel.WHATSAPP,
            status=ChannelDeliveryStatus.FAILED,
            recipient=recipient,
            destination_masked=masked_phone,
            message="WhatsApp delivery failed after maximum retry attempts.",
            provider=self.provider_id,
            provider_message_id=None,
            correlation_id=correlation_id,
            submitted_at=now,
            retry_count=max_retries,
            error_details=last_error_details,
        )
