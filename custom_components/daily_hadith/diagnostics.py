"""Diagnostics support for Daily Hadith."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import DailyHadithConfigEntry

TO_REDACT = {CONF_API_KEY, "api_key"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DailyHadithConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "coordinator": {
            "has_api_key": bool(coordinator.api_key),
            "is_current": coordinator.is_current(),
            "hadith": async_redact_data(dict(coordinator.hadith), TO_REDACT),
        },
    }
