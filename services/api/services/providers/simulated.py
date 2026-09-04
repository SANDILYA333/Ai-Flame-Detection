"""Simulated notification provider for deterministic testing and zero-network execution."""

from datetime import UTC, datetime

from packages.schemas.responders import (
    ChannelDeliveryStatus,
    ChannelResult,
    NotificationChannel,
    NotificationMode,
)
from services.api.services.providers.base import BaseNotificationProvider


class SimulatedNotificationProvider(BaseNotificationProvider):
    """Zero-network simulation provider supporting all notification channels."""

    @property
    def provider_id(self) -> str:
        return "simulated"

    @property
    def supported_channels(self) -> set[NotificationChannel]:
        return {NotificationChannel.SMS, NotificationChannel.WHATSAPP}

    def send(
        self,
        *,
        channel: NotificationChannel,
        recipient: str,
        message: str,
        mode: NotificationMode = NotificationMode.SIMULATED,
        correlation_id: str | None = None,
    ) -> ChannelResult:
        now = datetime.now(UTC)
        now_str = now.strftime("%Y%m%d%H%M%S")
        masked = (
            f"{recipient[:3]}******{recipient[-4:]}"
            if len(recipient) >= 7
            else "****"
        )
        return ChannelResult(
            channel=channel,
            status=ChannelDeliveryStatus.SIMULATED,
            recipient=recipient,
            destination_masked=masked,
            message=f"{channel.value} alert simulated successfully for {recipient}.",
            provider=self.provider_id,
            provider_message_id=f"SIM-{channel.value}-{now_str}",
            correlation_id=correlation_id,
            submitted_at=now,
            delivered_at=now,
            retry_count=0,
        )
