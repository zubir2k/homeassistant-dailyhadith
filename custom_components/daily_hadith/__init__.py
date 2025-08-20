"""The Daily Hadith integration."""
from __future__ import annotations

from datetime import datetime, timedelta, time
import logging
import json

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_call_later

from .const import (
    DOMAIN,
    STORAGE_VERSION,
    STORAGE_KEY,
    API_ENDPOINT_HADITH_RANDOM,
    API_TIMEOUT,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


def get_next_midnight() -> timedelta:
    """Calculate time until next midnight."""
    now = datetime.now()
    midnight = datetime.combine(now.date() + timedelta(days=1), time(0, 0))
    return midnight - now


def build_processed_data(source: dict) -> dict:
    """Standardize and structure hadith data for storage."""
    english_hadith = next((h for h in source.get("hadith", []) if h.get("lang") == "en"), {})
    arabic_hadith = next((h for h in source.get("hadith", []) if h.get("lang") == "ar"), {})

    return {
        "collection": source.get("collection", ""),
        "bookNumber": source.get("bookNumber", ""),
        "chapterId": source.get("chapterId", ""),
        "hadithNumber": source.get("hadithNumber", ""),
        "text": english_hadith.get("body", "") if english_hadith else "",
        "arabicText": arabic_hadith.get("body", "") if arabic_hadith else "",
        "chapterTitle": english_hadith.get("chapterTitle", "") if english_hadith else "",
        "chapter": english_hadith.get("chapterNumber", "") if english_hadith else "",
        "fetch_date": datetime.now().strftime("%Y-%m-%d"),
    }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Daily Hadith from a config entry."""
    api_key = entry.data.get(CONF_API_KEY)
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_update_data() -> dict:
        """Fetch and process data from the Sunnah API or fallback to GitHub JSON."""
        session = async_get_clientsession(hass)

        try:
            async with async_timeout.timeout(API_TIMEOUT):
                if api_key:
                    headers = {"x-api-key": api_key}
                    async with session.get(API_ENDPOINT_HADITH_RANDOM, headers=headers) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"API error: {response.status}")
                        data = await response.json()
                        if not data or "hadith" not in data or not data["hadith"]:
                            raise UpdateFailed("Invalid data format from API")
                        processed_data = build_processed_data(data)
                else:
                    fallback_url = "https://raw.githubusercontent.com/zubir2k/dailyhadith-fetcher/refs/heads/main/dailyhadith.json"
                    _LOGGER.warning("Falling back to GitHub JSON data due to missing API key")
                    async with session.get(fallback_url) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"GitHub fallback error: {response.status}")
                        fallback_text = await response.text()
                        fallback_data = json.loads(fallback_text)
                        processed_data = build_processed_data(fallback_data)

                storage_data = {"data": [processed_data]}
                await store.async_save(storage_data)
                return storage_data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="daily_hadith",
        update_method=async_update_data,
        update_interval=timedelta(days=1),
    )

    stored_data = await store.async_load()
    if stored_data:
        coordinator.data = stored_data
    else:
        await coordinator.async_config_entry_first_refresh()

    @callback
    def schedule_midnight_update():
        delay = get_next_midnight().total_seconds()
        async_call_later(hass, delay, trigger_midnight_update)

    @callback
    def trigger_midnight_update(_):
        hass.async_create_task(coordinator.async_request_refresh())
        schedule_midnight_update()

    schedule_midnight_update()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "reload"):
        async def handle_reload_service(call):
            _LOGGER.info("Manual hadith refresh triggered via service call")
            for coordinator in hass.data.get(DOMAIN, {}).values():
                await coordinator.async_request_refresh()
    
        hass.services.async_register(DOMAIN, "reload", handle_reload_service)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        await store.async_remove()
    return unload_ok
