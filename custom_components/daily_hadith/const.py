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

# Malay translation (English -> Malay) via the Cloudflare Worker
CF_WORKER_URL: Final = "https://hadith-translator.zubir-jamal.workers.dev"
TRANSLATION_TIMEOUT: Final = 30  # seconds per request

SUNNAH_URL: Final = "https://sunnah.com"

SERVICE_RELOAD: Final = "reload"

SOURCE_API: Final = "sunnah_api"
SOURCE_FALLBACK: Final = "github_fallback"
