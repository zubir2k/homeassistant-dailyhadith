"""Config flow for the Daily Hadith integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    API_ENDPOINT_HADITH_RANDOM,
    API_TIMEOUT,
    CONF_AI_TASK_ENTITY,
    CONF_BASE_URL,
    CONF_LANGUAGE,
    CONF_MODEL,
    CONF_TRANSLATOR,
    DEFAULT_LANGUAGE,
    DOMAIN,
    TRANSLATOR_AI_TASK,
    TRANSLATOR_NONE,
    TRANSLATOR_OPENAI,
    TRANSLATORS,
)
from .translator import (
    NO_TRANSLATION,
    TranslationAuthError,
    TranslationError,
    async_translate,
    base_language,
    language_options,
)

_LOGGER = logging.getLogger(__name__)

TITLE = "Daily Hadith"
TEST_TEXT = "Peace be upon you."


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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DailyHadithOptionsFlow:
        """Return the translation options flow."""
        return DailyHadithOptionsFlow()

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


class DailyHadithOptionsFlow(OptionsFlow):
    """Choose the translation language and the AI that translates."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._choice: dict[str, Any] = {}

    def _needs_ai(self, language: str) -> bool:
        """Return True when this language can only come from an AI translator."""
        return base_language(language) not in NO_TRANSLATION

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the language and the translator."""
        options = self.config_entry.options
        errors: dict[str, str] = {}
        if user_input is not None:
            language = user_input[CONF_LANGUAGE].strip()
            translator = user_input[CONF_TRANSLATOR]
            if translator == TRANSLATOR_NONE and self._needs_ai(language):
                errors["base"] = "translator_required"
            else:
                self._choice = {CONF_LANGUAGE: language, CONF_TRANSLATOR: translator}
                if translator == TRANSLATOR_AI_TASK:
                    return await self.async_step_ai_task()
                if translator == TRANSLATOR_OPENAI:
                    return await self.async_step_openai()
                return self.async_create_entry(data=self._choice)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LANGUAGE,
                    default=options.get(CONF_LANGUAGE) or DEFAULT_LANGUAGE,
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=language_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                        sort=False,
                    )
                ),
                vol.Required(
                    CONF_TRANSLATOR,
                    default=options.get(CONF_TRANSLATOR, TRANSLATOR_NONE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=TRANSLATORS,
                        translation_key=CONF_TRANSLATOR,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def _test(self, options: dict[str, Any]) -> str | None:
        """Translate a short sentence; return an error key or None."""
        try:
            await async_translate(self.hass, options, TEST_TEXT, options[CONF_LANGUAGE])
        except TranslationAuthError:
            return "invalid_auth"
        except TranslationError as err:
            _LOGGER.warning("Test translation failed: %s", err)
            return "translation_failed"
        return None

    async def async_step_ai_task(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the AI Task or Assist conversation entity (empty = default)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options = {**self._choice}
            if entity := user_input.get(CONF_AI_TASK_ENTITY):
                options[CONF_AI_TASK_ENTITY] = entity
            has_ai_svc = self.hass.services.has_service("ai_task", "generate_data")
            has_conv_svc = self.hass.services.has_service("conversation", "process")
            if not has_ai_svc and not has_conv_svc:
                errors["base"] = "ai_task_unavailable"
            elif (
                base_language(options[CONF_LANGUAGE]) not in NO_TRANSLATION
                and (error := await self._test(options))
            ):
                errors["base"] = error
            if not errors:
                return self.async_create_entry(data=options)

        current = self.config_entry.options.get(CONF_AI_TASK_ENTITY)
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AI_TASK_ENTITY, description={"suggested_value": current}
                ): EntitySelector(
                    EntitySelectorConfig(domain=["ai_task", "conversation"])
                ),
            }
        )
        return self.async_show_form(step_id="ai_task", data_schema=schema, errors=errors)

    async def async_step_openai(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up an OpenAI-compatible API (OpenAI, Ollama, OpenRouter, Workers AI...)."""
        errors: dict[str, str] = {}
        current = self.config_entry.options
        if user_input is not None:
            options = {
                **self._choice,
                CONF_BASE_URL: user_input[CONF_BASE_URL].strip(),
                CONF_MODEL: user_input[CONF_MODEL].strip(),
            }
            if key := (user_input.get(CONF_API_KEY) or "").strip():
                options[CONF_API_KEY] = key
            if not options[CONF_BASE_URL].startswith(("http://", "https://")):
                errors[CONF_BASE_URL] = "invalid_url"
            elif base_language(options[CONF_LANGUAGE]) not in NO_TRANSLATION and (
                error := await self._test(options)
            ):
                errors["base"] = error
            if not errors:
                return self.async_create_entry(data=options)
            current = {**current, **user_input}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BASE_URL,
                    description={"suggested_value": current.get(CONF_BASE_URL)},
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                vol.Optional(
                    CONF_API_KEY,
                    description={"suggested_value": current.get(CONF_API_KEY)},
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
                vol.Required(
                    CONF_MODEL,
                    description={"suggested_value": current.get(CONF_MODEL)},
                ): TextSelector(),
            }
        )
        return self.async_show_form(step_id="openai", data_schema=schema, errors=errors)
