"""Sensor platform for the Daily Hadith integration."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_MODEL,
    CONF_TRANSLATOR,
    DOMAIN,
    SUNNAH_URL,
    TR_STATUSES,
    TRANSLATOR_AI_TASK,
    TRANSLATOR_NONE,
    TRANSLATOR_OPENAI,
)
from .coordinator import DailyHadithConfigEntry, DailyHadithCoordinator
from .translator import base_language, clean_text

__all__ = ["clean_text"]

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DailyHadithConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Daily Hadith sensor."""
    coordinator = entry.runtime_data
    async_add_entities(
        [DailyHadithSensor(coordinator), DailyHadithTranslationSensor(coordinator)]
    )


def _device_info(coordinator: DailyHadithCoordinator) -> DeviceInfo:
    """Return the shared service device."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name="Daily Hadith",
        manufacturer="Sunnah.com",
        model="Hadith of the day",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=SUNNAH_URL,
    )


class DailyHadithSensor(CoordinatorEntity[DailyHadithCoordinator], SensorEntity):
    """The main sensor holding today's hadith in Arabic, English and a translation."""

    _attr_has_entity_name = True
    _attr_name = None  # entity takes the device name -> sensor.daily_hadith
    _attr_translation_key = "hadith"
    _attr_device_class = SensorDeviceClass.DATE
    # The hadith text can be long; keep it out of the recorder database.
    _unrecorded_attributes = frozenset({"text", "arabic", "malay", "translation"})

    def __init__(self, coordinator: DailyHadithCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        # Unchanged from 1.0.x so existing entity IDs and automations keep working.
        self._attr_unique_id = f"{DOMAIN}_hadith"
        self._attr_device_info = _device_info(coordinator)

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Keep sensor available as long as cached data exists, even if a background
        refresh failed.
        """
        return super().available or bool(self.coordinator.data)

    @property
    def native_value(self) -> date | None:
        """Return today's date when a hadith was loaded."""
        if not self.coordinator.data:
            return None
        h = self.coordinator.hadith
        if raw := h.get("fetch_date"):
            return date.fromisoformat(raw)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the hadith text, translations and metadata."""
        h = self.coordinator.hadith
        slug = h.get("collection", "")
        collection = slug.title()
        number = h.get("hadithNumber", "")
        tr = h.get("translation") or {}
        tr_text = clean_text(tr.get("text"))
        tr_lang = tr.get("lang") if tr_text else None
        language = self.coordinator.language
        current = bool(tr_text) and tr_lang == language
        is_ms = current and base_language(tr_lang) == "ms"
        malay = tr_text if is_ms else ""
        title_ms = tr.get("title", "") if is_ms else ""
        return {
            "title": h.get("chapterTitle", ""),
            "title_ms": title_ms,
            "text": clean_text(h.get("text")),
            "arabic": clean_text(h.get("arabicText")),
            "malay": malay,
            "translation": tr_text if current else "",
            "title_translation": tr.get("title", "") if current else "",
            "translation_language": language,
            "translation_source": tr.get("source", "") if current else "",
            "collection": collection,
            "chapter": h.get("chapter", ""),
            "hadith_number": number,
            "book": h.get("bookNumber", ""),
            "book_number": h.get("bookNumber", ""),
            "reference": f"{collection} #{number}",
            "url": f"{SUNNAH_URL}/{slug}:{number}" if slug and number else SUNNAH_URL,
            "source": h.get("source", ""),
        }


class DailyHadithTranslationSensor(
    CoordinatorEntity[DailyHadithCoordinator], SensorEntity
):
    """Diagnostic: where the translation stands and why it failed, if it did."""

    _attr_has_entity_name = True
    _attr_translation_key = "translation"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = TR_STATUSES
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DailyHadithCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_translation"
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> str:
        """Return the translation status."""
        return self.coordinator.translation_status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the details needed to troubleshoot a translation."""
        c = self.coordinator
        options = c.config_entry.options
        translator = options.get(CONF_TRANSLATOR) or TRANSLATOR_NONE
        backend = ""
        if translator == TRANSLATOR_AI_TASK:
            backend = options.get(CONF_AI_TASK_ENTITY) or "default"
        elif translator == TRANSLATOR_OPENAI:
            backend = options.get(CONF_MODEL, "")
        return {
            "language": c.language,
            "translator": translator,
            "backend": backend,
            "hadith_number": c.hadith.get("hadithNumber", ""),
            "last_attempt": c.translation_attempt,
            "last_success": c.translation_success,
            "duration_seconds": c.translation_seconds,
            "next_retry": c.translation_retry_at,
            "error": c.translation_error,
        }
