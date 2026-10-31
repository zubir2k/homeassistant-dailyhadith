"""Sensor platform for the Daily Hadith integration."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SUNNAH_URL
from .coordinator import DailyHadithConfigEntry, DailyHadithCoordinator

PARALLEL_UPDATES = 0

_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def clean_text(text: str | None) -> str:
    """Turn Sunnah.com HTML into plain text with paragraph breaks."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = text.replace("<p>", "").replace("</p>", "\n\n")
    text = _TAG_RE.sub("", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return _MULTI_NL_RE.sub("\n\n", text).strip()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DailyHadithConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Daily Hadith sensor."""
    async_add_entities([DailyHadithSensor(entry.runtime_data)])


class DailyHadithSensor(CoordinatorEntity[DailyHadithCoordinator], SensorEntity):
    """Today's hadith. State is the date it was fetched; content is in attributes."""

    _attr_has_entity_name = True
    _attr_name = None  # entity takes the device name -> sensor.daily_hadith
    _attr_translation_key = "hadith"
    _attr_device_class = SensorDeviceClass.DATE
    # The hadith text can be long; keep it out of the recorder database.
    _unrecorded_attributes = frozenset({"text", "arabic", "malay"})

    def __init__(self, coordinator: DailyHadithCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        # Unchanged from 1.0.x so existing entity IDs and automations keep working.
        self._attr_unique_id = f"{DOMAIN}_hadith"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Daily Hadith",
            manufacturer="Sunnah.com",
            model="Hadith of the day",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=SUNNAH_URL,
        )

    @property
    def native_value(self) -> date | None:
        """Return the date the current hadith was fetched."""
        raw = self.coordinator.hadith.get("fetch_date")
        try:
            return date.fromisoformat(raw) if raw else None
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the hadith content."""
        h = self.coordinator.hadith
        if not h:
            return {}
        slug = h.get("collection", "")
        collection = slug.title()
        number = h.get("hadithNumber", "")
        return {
            "title": h.get("chapterTitle", ""),
            "title_ms": h.get("chapterTitleMs", ""),
            "text": clean_text(h.get("text")),
            "arabic": clean_text(h.get("arabicText")),
            "malay": clean_text(h.get("malayText")),
            "collection": collection,
            "chapter": h.get("chapter", ""),
            "hadith_number": number,
            "book_number": h.get("bookNumber", ""),
            "reference": f"{collection} #{number}",
            "url": f"{SUNNAH_URL}/{slug}:{number}" if slug and number else SUNNAH_URL,
            "source": h.get("source", ""),
        }
