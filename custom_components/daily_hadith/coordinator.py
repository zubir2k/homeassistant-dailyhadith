"""Data coordinator for the Daily Hadith integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_ENDPOINT_HADITH_RANDOM,
    API_TIMEOUT,
    CF_WORKER_URL,
    DOMAIN,
    FALLBACK_URL,
    SOURCE_API,
    SOURCE_FALLBACK,
    STORAGE_KEY,
    STORAGE_VERSION,
    TRANSLATION_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

type DailyHadithConfigEntry = ConfigEntry[DailyHadithCoordinator]


def build_processed_data(source: dict[str, Any], origin: str) -> dict[str, Any]:
    """Standardize the Sunnah.com hadith payload for storage."""
    hadiths = source.get("hadith") or []
    english = next((h for h in hadiths if h.get("lang") == "en"), {})
    arabic = next((h for h in hadiths if h.get("lang") == "ar"), {})
    malay = next((h for h in hadiths if h.get("lang") == "ms"), {})

    return {
        "collection": source.get("collection", ""),
        "bookNumber": source.get("bookNumber", ""),
        "chapterId": source.get("chapterId", ""),
        "hadithNumber": source.get("hadithNumber", ""),
        "text": english.get("body", ""),
        "arabicText": arabic.get("body", ""),
        "malayText": malay.get("body", ""),
        "chapterTitle": english.get("chapterTitle", ""),
        "chapterTitleMs": malay.get("chapterTitle", ""),
        "chapter": english.get("chapterNumber", ""),
        "fetch_date": dt_util.now().date().isoformat(),
        "source": origin,
    }


class DailyHadithCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch one hadith per day, cached in HA storage across restarts."""

    config_entry: DailyHadithConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DailyHadithConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            # Safety net only: the real refresh is pinned to local midnight.
            update_interval=timedelta(hours=6),
        )
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._session = async_get_clientsession(hass)
        self._force_next = False

    @property
    def api_key(self) -> str | None:
        """Return the configured Sunnah.com API key, if any."""
        return self.config_entry.data.get(CONF_API_KEY) or None

    @property
    def hadith(self) -> dict[str, Any]:
        """Return the current hadith record."""
        if not self.data:
            return {}
        items = self.data.get("data") or [{}]
        return items[0]

    def is_current(self) -> bool:
        """Return True when the cached hadith belongs to today (HA time zone).

        A record cached by an older version has no Malay keys at all; treat it
        as out of date so it is replaced once instead of staying untranslated.
        """
        h = self.hadith
        return (
            h.get("fetch_date") == dt_util.now().date().isoformat()
            and "malayText" in h
        )

    async def async_load_cached(self) -> bool:
        """Load the cached hadith from storage. Return True when one was found."""
        stored = await self.store.async_load()
        if stored and isinstance(stored, dict) and stored.get("data"):
            self.async_set_updated_data(stored)
            return True
        return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch a new hadith, unless today's is already cached."""
        force, self._force_next = self._force_next, False
        if not force and self.data and self.is_current():
            return self.data

        record: dict[str, Any] | None = None
        errors: list[str] = []

        if self.api_key:
            try:
                record = await self._fetch_api()
            except (TimeoutError, aiohttp.ClientError, UpdateFailed, ValueError) as err:
                errors.append(f"Sunnah.com API: {err}")
                _LOGGER.warning(
                    "Sunnah.com API failed (%s), using the daily fallback feed", err
                )

        if record is None:
            try:
                record = await self._fetch_fallback()
            except (TimeoutError, aiohttp.ClientError, UpdateFailed, ValueError) as err:
                errors.append(f"fallback feed: {err}")

        if record is None:
            raise UpdateFailed("Could not fetch a hadith: " + "; ".join(errors))

        data = {"data": [record]}
        await self.store.async_save(data)
        return data

    async def _fetch_api(self) -> dict[str, Any]:
        """Fetch a random hadith from the Sunnah.com API and add a Malay translation."""
        async with asyncio.timeout(API_TIMEOUT):
            async with self._session.get(
                API_ENDPOINT_HADITH_RANDOM, headers={"x-api-key": self.api_key or ""}
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(f"HTTP {response.status}")
                payload = await response.json()
        if not isinstance(payload, dict) or not payload.get("hadith"):
            raise UpdateFailed("unexpected response format")
        # Done outside the API timeout above: the translation has its own.
        await self._async_add_malay(payload)
        return build_processed_data(payload, SOURCE_API)

    async def _fetch_fallback(self) -> dict[str, Any]:
        """Fetch the hadith of the day from the GitHub fallback feed.

        The feed is produced by dailyhadith-fetcher and already contains the
        Malay entry, so no translation request is made from here.
        """
        async with asyncio.timeout(API_TIMEOUT):
            async with self._session.get(FALLBACK_URL) as response:
                if response.status != 200:
                    raise UpdateFailed(f"HTTP {response.status}")
                # raw.githubusercontent.com serves text/plain, so skip content-type check
                payload = await response.json(content_type=None)
        if not isinstance(payload, dict) or not payload.get("hadith"):
            raise UpdateFailed("unexpected response format")
        return build_processed_data(payload, SOURCE_FALLBACK)

    async def _async_translate(self, text: str) -> str:
        """Translate English text to Malay via the Cloudflare Worker."""
        if not text:
            return ""
        try:
            async with asyncio.timeout(TRANSLATION_TIMEOUT):
                async with self._session.post(
                    CF_WORKER_URL, json={"text": text, "targetLang": "ms"}
                ) as response:
                    if response.status != 200:
                        _LOGGER.warning("Translation worker returned HTTP %s", response.status)
                        return ""
                    result = await response.json()
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            _LOGGER.warning("Malay translation unavailable: %s", err)
            return ""
        if not isinstance(result, dict):
            return ""
        return str(result.get("translated") or "").strip()

    async def _async_add_malay(self, payload: dict[str, Any]) -> None:
        """Append a Malay ("ms") entry to the payload, translated from English.

        Failure is not fatal: the hadith is still shown, just without Malay.
        """
        hadiths = payload.get("hadith") or []
        if any(h.get("lang") == "ms" for h in hadiths):
            return
        english = next((h for h in hadiths if h.get("lang") == "en"), None)
        if not english:
            return

        # Body and chapter title are independent, so translate them together.
        body, title = await asyncio.gather(
            self._async_translate(english.get("body", "")),
            self._async_translate(english.get("chapterTitle", "")),
        )
        if not body:
            _LOGGER.warning("Malay translation came back empty, skipping it")
            return

        hadiths.append(
            {
                "lang": "ms",
                "chapterNumber": english.get("chapterNumber", ""),
                "chapterTitle": title,
                "body": f"<p>{body}</p>",
                "grades": [],
            }
        )

    async def async_force_refresh(self) -> None:
        """Fetch a new hadith now, even if today's is cached."""
        self._force_next = True
        await self.async_refresh()
