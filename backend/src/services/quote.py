"""Daily quote engine — dispatches to the configured locale."""

import importlib
import logging
from dataclasses import dataclass, field
from datetime import date
from types import ModuleType

logger = logging.getLogger(__name__)

_SUPPORTED_LANGUAGES = {"en", "nl"}
_LOCALE_PACKAGE = "src.services.quotes"


@dataclass
class QuoteContext:
    today: date
    weather_condition: str | None = None
    temperature: float | None = None
    language: str = field(default="en")


def get_quote(ctx: QuoteContext) -> str:
    """Return a daily quote for the given context and language."""
    locale = _load_locale(ctx.language)
    return (
        locale.holiday_quote(ctx.today)
        or locale.weather_quote(ctx.weather_condition, ctx.temperature, ctx.today)
        or locale.weekday_quote(ctx.today)
    )


def _load_locale(language: str) -> ModuleType:
    lang = language if language in _SUPPORTED_LANGUAGES else "en"
    if lang != language:
        logger.warning(f"Unsupported quote language '{language}', falling back to 'en'")
    return importlib.import_module(f"{_LOCALE_PACKAGE}.{lang}")
