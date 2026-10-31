"""Config flow for the Daily Hadith integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import API_ENDPOINT_HADITH_RANDOM, API_TIMEOUT, DOMAIN

_LOGGER = logging.getLogger(__name__)

TITLE = "Daily Hadith"


def _schema(default: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_API_KEY, description={"suggested_value": default}
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        }
    )


class DailyHadithConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daily Hadith."""

    VERSION = 1

    async def _validate(self, user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        """Return (data to store, errors). An empty key means use the fallback feed."""
        key = (user_input.get(CONF_API_KEY) or "").strip()
        if not key:
            return {}, {}
        error = await self._test_api_key(key)
        if error:
            return {}, {"base": error}
        return {CONF_API_KEY: key}, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Also enforced by "single_config_entry" in manifest.json.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._validate(user_input)
            if not errors:
                return self.async_create_entry(title=TITLE, data=data)

        return self.async_show_form(
            step_id="user", data_schema=_schema(), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add, change or remove the Sunnah.com API key."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(entry.data.get(CONF_API_KEY, "")),
            errors=errors,
        )

    async def _test_api_key(self, api_key: str) -> str | None:
        """Return an error key, or None when the API key works."""
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with session.get(
                    API_ENDPOINT_HADITH_RANDOM, headers={"x-api-key": api_key}
                ) as response:
                    if response.status in (401, 403):
                        return "invalid_api_key"
                    if response.status != 200:
                        return "cannot_connect"
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.debug("API key validation failed: %s", err)
            return "cannot_connect"
        return None
