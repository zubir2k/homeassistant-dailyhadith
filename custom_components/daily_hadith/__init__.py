"""The Daily Hadith integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .card_registration import async_register_card, async_unregister_card
from .const import DOMAIN, SERVICE_RELOAD, STORAGE_KEY, STORAGE_VERSION
from .coordinator import DailyHadithConfigEntry, DailyHadithCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's actions once, independent of config entries."""

    async def handle_reload(call: ServiceCall) -> None:
        """Fetch a new hadith for every loaded entry."""
        _LOGGER.info("Manual hadith refresh requested")
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.state is ConfigEntryState.LOADED:
                await entry.runtime_data.async_force_refresh()

    hass.services.async_register(DOMAIN, SERVICE_RELOAD, handle_reload)
    # Serve the bundled Daily Hadith card and add it to the dashboard resources.
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DailyHadithConfigEntry) -> bool:
    """Set up Daily Hadith from a config entry."""
    # Re-sync the card resource: removing the integration deletes it, and
    # async_setup does not run again when it is added back without a restart.
    await async_register_card(hass)

    coordinator = DailyHadithCoordinator(hass, entry)

    has_cache = await coordinator.async_load_cached()
    if not has_cache:
        # Nothing cached yet: setup must succeed with real data or retry later.
        await coordinator.async_config_entry_first_refresh()
    elif not coordinator.is_current():
        # Cached hadith is from an earlier day (HA was off at midnight):
        # show it now, replace it in the background.
        entry.async_create_background_task(
            hass, coordinator.async_refresh(), "daily_hadith_catch_up"
        )

    if not coordinator.data:
        raise ConfigEntryNotReady("No hadith available yet")

    entry.runtime_data = coordinator

    @callback
    def _midnight(_now: datetime) -> None:
        """Fetch the new day's hadith just after local midnight."""
        entry.async_create_background_task(
            hass, coordinator.async_refresh(), "daily_hadith_midnight"
        )

    # Uses HA's configured time zone and is cancelled on unload/reload.
    entry.async_on_unload(
        async_track_time_change(hass, _midnight, hour=0, minute=0, second=30)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DailyHadithConfigEntry) -> bool:
    """Unload a config entry. The cache is kept so a reload doesn't refetch."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: DailyHadithConfigEntry) -> None:
    """Delete the cached hadith and the card resource when the integration is removed."""
    await async_unregister_card(hass)
    await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()
