"""Platform for Daily Hadith sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN
import re

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daily Hadith sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DailyHadithSensor(coordinator)])

class DailyHadithSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Daily Hadith sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_hadith"
        self._attr_name = "Daily Hadith"
        self._attr_icon = "mdi:book-open-page-variant"

    def _clean_text(self, text: str) -> str:
        """Remove HTML tags and unnecessary formatting."""
        if not text:
            return ""
        # Convert paragraphs and line breaks
        text = text.replace("<br/>", "\n").replace("<br>", "\n")
        text = text.replace("<p>", "").replace("</p>", "\n\n")
        # Remove all remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Remove leading bullets/dashes
        return text.strip()

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return "No data"
        hadith_data = self.coordinator.data.get("data", [{}])[0]
        return hadith_data.get("fetch_date", "Unknown")

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return {}
        hadith_data = self.coordinator.data.get("data", [{}])[0]

        english_text = self._clean_text(hadith_data.get("text", ""))
        arabic_text = self._clean_text(hadith_data.get("arabicText", ""))
        collection = hadith_data.get("collection", "").title()

        return {
            "title": hadith_data.get("chapterTitle", ""),
            "text": english_text,
            "arabic": arabic_text,
            "collection": collection,
            "chapter": hadith_data.get("chapter", ""),
            "hadith_number": hadith_data.get("hadithNumber", ""),
            "book_number": hadith_data.get("bookNumber", ""),
            "reference": f"{collection} #{hadith_data.get('hadithNumber', '')}",
        }
