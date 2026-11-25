"""Constants for the Daily Hadith integration."""

from __future__ import annotations

from typing import Final

from dailyhadith import (
    API_BASE_URL,
    API_ENDPOINT_RANDOM as API_ENDPOINT_HADITH_RANDOM,
    DEFAULT_FALLBACK_URL as FALLBACK_URL,
    DEFAULT_TIMEOUT as API_TIMEOUT,
    SOURCE_API,
    SOURCE_FALLBACK,
)

DOMAIN: Final = "daily_hadith"
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "daily_hadith.data"

# Translation (options flow)
CONF_LANGUAGE: Final = "language"
CONF_TRANSLATOR: Final = "translator"
CONF_AI_TASK_ENTITY: Final = "ai_task_entity"
CONF_BASE_URL: Final = "base_url"
CONF_MODEL: Final = "model"

TRANSLATOR_NONE: Final = "none"
TRANSLATOR_AI_TASK: Final = "ai_task"
TRANSLATOR_OPENAI: Final = "openai"
TRANSLATORS: Final = [TRANSLATOR_NONE, TRANSLATOR_AI_TASK, TRANSLATOR_OPENAI]

# Malay comes free from the shared feed, so it stays the default language.
DEFAULT_LANGUAGE: Final = "ms"
TRANSLATION_TIMEOUT: Final = 90  # seconds per request (local models can be slow)

ISSUE_TRANSLATOR_NEEDED: Final = "translator_needed"

SUNNAH_URL: Final = "https://sunnah.com"

SERVICE_RELOAD: Final = "reload"
SERVICE_REFRESH: Final = "refresh"



# Where a translation came from (translation_source attribute)
TR_SOURCE_FEED: Final = "feed"

# State of the diagnostic translation sensor
TR_STATUS_NOT_NEEDED: Final = "not_needed"
TR_STATUS_TRANSLATING: Final = "translating"
TR_STATUS_TRANSLATED: Final = "translated"
TR_STATUS_FAILED: Final = "failed"
TR_STATUS_NEEDS_TRANSLATOR: Final = "needs_translator"
TR_STATUSES: Final = [
    TR_STATUS_NOT_NEEDED,
    TR_STATUS_TRANSLATING,
    TR_STATUS_TRANSLATED,
    TR_STATUS_FAILED,
    TR_STATUS_NEEDS_TRANSLATOR,
]
