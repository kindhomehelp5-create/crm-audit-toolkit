"""CRM Audit Toolkit — integrations with external platforms."""

from .telegram_parser import TelegramParser
from .amocrm import AmoCRMClient

__all__ = [
    "TelegramParser",
    "AmoCRMClient",
]
