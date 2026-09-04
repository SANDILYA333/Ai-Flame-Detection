"""Factory for resolving and instantiating notification providers based on system configuration."""

from packages.config.settings import Settings, get_settings
from packages.schemas.responders import NotificationChannel
from services.api.services.providers.base import BaseNotificationProvider
from services.api.services.providers.fast2sms import Fast2SMSProvider
from services.api.services.providers.richautomate import RichAutomateWhatsAppProvider
from services.api.services.providers.simulated import SimulatedNotificationProvider


class NotificationProviderFactory:
    """Factory resolving appropriate messaging providers according to settings."""

    @classmethod
    def get_provider(
        cls,
        channel: NotificationChannel,
        settings: Settings | None = None,
    ) -> BaseNotificationProvider:
        """Resolve the active provider for the given notification channel."""
        cfg = settings or get_settings()

        if cfg.NOTIFICATION_MODE.lower() == "simulation":
            if channel == NotificationChannel.SMS and cfg.SMS_PROVIDER.lower() == "fast2sms":
                return Fast2SMSProvider(cfg)
            if channel == NotificationChannel.WHATSAPP and cfg.WHATSAPP_PROVIDER.lower() == "richautomate":
                return RichAutomateWhatsAppProvider(cfg)
            return SimulatedNotificationProvider()

        if channel == NotificationChannel.SMS:
            if cfg.SMS_PROVIDER.lower() == "fast2sms":
                return Fast2SMSProvider(cfg)
            return SimulatedNotificationProvider()

        if channel == NotificationChannel.WHATSAPP:
            if cfg.WHATSAPP_PROVIDER.lower() == "richautomate":
                return RichAutomateWhatsAppProvider(cfg)
            return SimulatedNotificationProvider()

        return SimulatedNotificationProvider()
