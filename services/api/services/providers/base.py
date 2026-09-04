"""Abstract base notification provider contract."""

from abc import ABC, abstractmethod

from packages.schemas.responders import (
    ChannelResult,
    NotificationChannel,
    NotificationMode,
)


class BaseNotificationProvider(ABC):
    """Abstract interface defining delivery provider operations."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for the messaging provider."""
        ...

    @property
    @abstractmethod
    def supported_channels(self) -> set[NotificationChannel]:
        """Set of notification channels supported by this provider."""
        ...

    @abstractmethod
    def send(
        self,
        *,
        channel: NotificationChannel,
        recipient: str,
        message: str,
        mode: NotificationMode = NotificationMode.SIMULATED,
        correlation_id: str | None = None,
    ) -> ChannelResult:
        """Dispatch a notification message to the recipient over the specified channel."""
        ...
