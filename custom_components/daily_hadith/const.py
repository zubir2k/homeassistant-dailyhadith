"""Constants for the Daily Hadith integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "daily_hadith"
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "daily_hadith.data"

# API configuration
API_BASE_URL: Final = "https://api.sunnah.com/v1"
API_ENDPOINT_HADITH_RANDOM: Final = f"{API_BASE_URL}/hadiths/random"
API_TIMEOUT: Final = 10  # seconds

# Hadith of the day published by zubir2k/dailyhadith-fetcher (no API key needed)
FALLBACK_URL: Final = (
    "https://raw.githubusercontent.com/zubir2k/dailyhadith-fetcher/"
    "refs/heads/main/dailyhadith.json"
)

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

SOURCE_API: Final = "sunnah_api"
SOURCE_FALLBACK: Final = "github_fallback"

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
