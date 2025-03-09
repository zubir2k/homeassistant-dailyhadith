"""Constants for the Daily Hadith integration."""
DOMAIN = "daily_hadith"
STORAGE_VERSION = 1
STORAGE_KEY = "daily_hadith.data"

# API Configuration
API_BASE_URL = "https://api.sunnah.com/v1"
API_ENDPOINT_HADITH_RANDOM = f"{API_BASE_URL}/hadiths/random"
API_TIMEOUT = 10  # seconds