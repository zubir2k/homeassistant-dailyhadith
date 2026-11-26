"""Data coordinator for the Daily Hadith integration."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from dailyhadith import DailyHadithClient, DailyHadithError

from .const import (
    API_TIMEOUT,
    CONF_LANGUAGE,
    CONF_TRANSLATOR,
    DEFAULT_LANGUAGE,
    DOMAIN,
    FALLBACK_URL,
    ISSUE_TRANSLATOR_NEEDED,
    STORAGE_KEY,
    STORAGE_VERSION,
    TR_STATUS_FAILED,
    TR_STATUS_NEEDS_TRANSLATOR,
    TR_STATUS_NOT_NEEDED,
    TR_STATUS_TRANSLATED,
    TR_STATUS_TRANSLATING,
)
from .translator import (
    NO_TRANSLATION,
    async_translate,
    base_language,
    clean_text,
    language_name,
    translator_ready,
)

_LOGGER = logging.getLogger(__name__)

TRANSLATION_RETRY = timedelta(minutes=15)

type DailyHadithConfigEntry = ConfigEntry[DailyHadithCoordinator]


def build_processed_data(source: dict[str, Any], origin: str) -> dict[str, Any]:
    """Standardize the Sunnah.com hadith payload for storage."""
    hadiths = source.get("hadith") or []
    english = next((h for h in hadiths if h.get("lang") == "en"), {})
    arabic = next((h for h in hadiths if h.get("lang") == "ar"), {})

    return {
        "collection": source.get("collection", ""),
        "bookNumber": source.get("bookNumber", ""),
        "chapterId": source.get("chapterId", ""),
        "hadithNumber": source.get("hadithNumber", ""),
        "text": english.get("body", ""),
        "arabicText": arabic.get("body", ""),
        "chapterTitle": english.get("chapterTitle", ""),
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
        self.client = DailyHadithClient(
            api_key=self.api_key,
            session=self._session,
            fallback_url=FALLBACK_URL,
            timeout=API_TIMEOUT,
        )
        self._force_next = False
        self._translating = False
        self._pending_translation = False
        self._retry_unsub: CALLBACK_TYPE | None = None
        # Shown by the diagnostic "Translation" sensor.
        self.translation_status: str = TR_STATUS_NOT_NEEDED
        self.translation_error: str | None = None
        self.translation_attempt: datetime | None = None
        self.translation_success: datetime | None = None
        self.translation_seconds: float | None = None
        self.translation_retry_at: datetime | None = None

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
        """Return True when the cached hadith belongs to today (HA time zone)."""
        h = self.hadith
        return h.get("fetch_date") == dt_util.now().date().isoformat()

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
            record = self.hadith
            self._apply_translation(record)
            self.async_schedule_translation(record)
            return self.data

        self.client.api_key = self.api_key
        today_iso = dt_util.now().date().isoformat()
        try:
            hadith = await self.client.async_get_hadith(fetch_date=today_iso)
            record = hadith.to_dict()
        except DailyHadithError as err:
            raise UpdateFailed(
                f"Could not fetch a hadith: {err}",
                translation_domain=DOMAIN,
                translation_key="cannot_fetch",
                translation_placeholders={"error": str(err)},
            ) from err

        self._apply_translation(record)
        data = {"data": [record]}
        await self.store.async_save(data)
        self.async_schedule_translation(record)
        return data

    async def _fetch_api(self) -> dict[str, Any]:
        """Fetch a random hadith from the Sunnah.com API."""
        hadith = await self.client.async_get_from_api(
            fetch_date=dt_util.now().date().isoformat()
        )
        return hadith.to_dict()

    async def _fetch_fallback(self) -> dict[str, Any]:
        """Fetch the hadith of the day from the GitHub fallback feed."""
        hadith = await self.client.async_get_from_fallback(
            fetch_date=dt_util.now().date().isoformat()
        )
        return hadith.to_dict()

    # --- translation --------------------------------------------------------
    @property
    def language(self) -> str:
        """Return the chosen translation language code."""
        return self.config_entry.options.get(CONF_LANGUAGE) or DEFAULT_LANGUAGE

    def _free_translation(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """Return the translation that needs no AI, or None when AI is needed."""
        lang = self.language
        base = base_language(lang)
        if base in NO_TRANSLATION:
            return {}
        return None

    def _needs_translation(self, record: dict[str, Any]) -> bool:
        """Return True when the record lacks a translation an AI must make."""
        if not record:
            return False
        if self._free_translation(record) is not None:
            return False
        current = record.get("translation") or {}
        return not (current.get("lang") == self.language and current.get("text"))

    @callback
    def _set_status(self, status: str, error: str | None = None) -> None:
        """Record the translation state and refresh the entities."""
        changed = (status, error) != (self.translation_status, self.translation_error)
        self.translation_status = status
        self.translation_error = error
        if changed:
            self.async_update_listeners()

    @callback
    def _update_issue(self, needed: bool) -> None:
        """Raise or clear the repair issue asking for a translator."""
        if needed:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_TRANSLATOR_NEEDED,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_TRANSLATOR_NEEDED,
                translation_placeholders={"language": language_name(self.language)},
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_TRANSLATOR_NEEDED)

    @callback
    def _apply_translation(self, record: dict[str, Any]) -> None:
        """Fill the record's translation now when no AI is needed."""
        free = self._free_translation(record)
        if free is not None:
            record["translation"] = free
            self._update_issue(False)
            self._set_status(TR_STATUS_NOT_NEEDED)
            return
        current = record.get("translation") or {}
        if current.get("lang") != self.language:
            record["translation"] = {}

    @callback
    def async_refresh_translation(self) -> None:
        """Re-check the cached hadith's translation (e.g. after options change)."""
        if record := self.hadith:
            self._apply_translation(record)
            self.async_schedule_translation(record)

    @callback
    def async_schedule_translation(self, record: dict[str, Any] | None = None) -> None:
        """Translate the hadith in the background if an AI translation is missing.

        The hadith is shown at once in English; the translation follows when the
        model answers, so a slow local model never delays the sensor.
        """
        record = record if record is not None else self.hadith
        if not self._needs_translation(record):
            self._update_issue(False)
            if self._free_translation(record) is not None:
                self._set_status(TR_STATUS_NOT_NEEDED)
            elif record.get("translation"):
                self._set_status(TR_STATUS_TRANSLATED)
            return
        if not translator_ready(self.hass, dict(self.config_entry.options)):
            self._update_issue(True)
            self._set_status(TR_STATUS_NEEDS_TRANSLATOR)
            return
        self._update_issue(False)
        if self._translating:
            # Another hadith is still being translated (e.g. the refresh button
            # was pressed mid-translation). Translate this one when it ends.
            self._pending_translation = True
            return
        self._translating = True
        self._pending_translation = False
        self.async_cancel_retry()
        self.translation_attempt = dt_util.now()
        self._set_status(TR_STATUS_TRANSLATING)
        self.config_entry.async_create_background_task(
            self.hass, self._async_translate_record(record), "daily_hadith_translate"
        )

    @callback
    def _schedule_retry(self) -> None:
        """Try the translation again later (e.g. the AI was still starting up)."""
        if self._retry_unsub:
            return

        @callback
        def _retry(_now: Any) -> None:
            self._retry_unsub = None
            self.async_refresh_translation()

        self._retry_unsub = async_call_later(self.hass, TRANSLATION_RETRY, _retry)
        self.translation_retry_at = dt_util.now() + TRANSLATION_RETRY

    @callback
    def async_cancel_retry(self) -> None:
        """Cancel a pending translation retry."""
        self.translation_retry_at = None
        if self._retry_unsub:
            self._retry_unsub()
            self._retry_unsub = None

    async def _async_translate_record(self, record: dict[str, Any]) -> None:
        """Translate the record's English text and title, then publish it."""
        lang = self.language
        options = dict(self.config_entry.options)
        started = time.monotonic()
        try:
            await self._async_do_translate(record, lang, options)
        finally:
            self._translating = False
            self.translation_seconds = round(time.monotonic() - started, 1)
            if self._pending_translation:
                self._pending_translation = False
                self.async_schedule_translation()

    async def _async_do_translate(
        self, record: dict[str, Any], lang: str, options: dict[str, Any]
    ) -> None:
        """Run the translation requests and store the result."""
        body, title = await asyncio.gather(
            async_translate(self.hass, options, clean_text(record.get("text")), lang),
            async_translate(self.hass, options, record.get("chapterTitle", ""), lang),
            return_exceptions=True,
        )
        if isinstance(body, BaseException):
            _LOGGER.warning(
                "Could not translate the hadith into %s (retrying in %s minutes): %s",
                lang,
                int(TRANSLATION_RETRY.total_seconds() // 60),
                body,
            )
            self._schedule_retry()
            self._set_status(TR_STATUS_FAILED, str(body) or type(body).__name__)
            return
        if isinstance(title, BaseException):
            _LOGGER.debug("Could not translate the chapter title: %s", title)
            title = ""
        if self.hadith is not record and (
            self.hadith.get("hadithNumber") != record.get("hadithNumber")
            or self.hadith.get("fetch_date") != record.get("fetch_date")
        ):
            # A newer hadith arrived meanwhile; the finally block translates it.
            self._pending_translation = True
            return
        record["translation"] = {
            "lang": lang,
            "text": body,
            "title": title,
            "source": options.get(CONF_TRANSLATOR, ""),
        }
        self.translation_success = dt_util.now()
        self.translation_status = TR_STATUS_TRANSLATED
        self.translation_error = None
        data = {"data": [record]}
        await self.store.async_save(data)
        self.async_set_updated_data(data)

    async def async_force_refresh(self) -> None:
        """Fetch a new hadith now, even if today's is cached."""
        self._force_next = True
        await self.async_refresh()
