"""Config flow for Daily Hadith integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, API_ENDPOINT_HADITH_RANDOM, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daily Hadith."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Check if an instance already exists
        existing_entries = self._async_current_entries()
        if existing_entries:
            return self.async_abort(
                reason="single_instance_allowed",
                description_placeholders={
                    "title": existing_entries[0].title,
                },
            )
        errors = {}
           
        if user_input is not None:
            key = user_input.get(CONF_API_KEY)
            if key:
                valid = await self._test_api_key(key)
                if valid:
                    return self.async_create_entry(title="Daily Hadith", data=user_input)
                errors["base"] = "invalid_api_key"
            else:
                # No key provided, allow fallback
                return self.async_create_entry(title="Daily Hadith", data={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_API_KEY): str,
            }),
            errors=errors,
        )

    async def _test_api_key(self, api_key: str) -> bool:
        """Test if the API key is valid."""
        session = async_get_clientsession(self.hass)
        headers = {"x-api-key": api_key}

        try:
            async with session.get(
                API_ENDPOINT_HADITH_RANDOM,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as response:
                return response.status == 200
        except aiohttp.ClientError as err:
            _LOGGER.error("API key validation failed: %s", err)
            return False
