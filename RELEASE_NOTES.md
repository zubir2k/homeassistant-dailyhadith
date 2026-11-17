# Daily Hadith v1.3.0

## New
- **Translate into any language with your own AI**:
  - **Home Assistant AI Task / Assist**: use any AI agent configured in Home Assistant (ChatGPT, Claude, Google Gemini, Ollama, local LLMs).
  - **OpenAI-compatible API**: connect directly to OpenAI, Ollama, OpenRouter, Groq, LM Studio, Cloudflare Workers AI, etc.
  - Eliminates external third-party translator worker dependencies.
- **Both modes fully supported**:
  - **Without API key (Shared Feed)**: English and Arabic, plus free Malay without any AI setup required. Selecting any other language translates using your AI.
  - **With API key (Sunnah.com API)**: Random hadith with English and Arabic, translated into your chosen language (Malay, Indonesian, French, etc.) via your configured AI.
- **Lovelace Card v1.3.0**:
  - Dynamic language toggle (EN / your translated language code e.g. BM, ID, TR).
  - RTL support for Arabic, Urdu, Persian, and other RTL languages.
  - Optional small "AI translation" indicator note.
- **Diagnostics & Status Sensor**:
  - New diagnostic entity `sensor.daily_hadith_translation` reporting status (`not_needed`, `translating`, `translated`, `failed`, `needs_translator`) and timing/retry attributes.
  - Automatic non-blocking background translation so English is displayed immediately while translation runs.
  - Automatic 15-minute retry on temporary AI provider timeouts or network issues.

# Daily Hadith v1.2.0

## New
- **Daily Hadith card**, bundled with the integration and registered automatically (Lovelace resource in storage mode, script injection for YAML dashboards). The resource is removed when the integration is deleted.
  - Arabic in the bundled Amiri font (SIL OFL), right to left
  - EN / BM switch on the card, remembered per browser; BM is disabled on days without a Malay translation
  - Folds long hadith behind Show more / Selanjutnya
  - Sunnah.com reference chip with proper collection names (e.g. Riyad as-Salihin)
  - Copy and refresh (`daily_hadith.reload`) buttons
  - Follows the HA theme; visual editor; listed in the card picker; card labels in English and Malay
- Malay translation (`malay`, `title_ms` attributes): from the fallback feed, or via the hadith translator worker when an API key is set. A failed translation never blocks the hadith.
- Refreshed brand: the eSolat family frame around the Sunnah.com mark, with a dark-theme logo.
- README: card docs and removal instructions.

## Notes
- Manifest now depends on `http` and `frontend` (needed to serve the card).
- A cached hadith from 1.1.0 (no Malay) is refreshed once after upgrading.
- Includes everything from 1.1.0 (HA 2026.10/2026.11 load fix, coordinator, reconfigure flow, fallback feed).

## Daily Hadith v1.1.0: ready for Home Assistant 2026.11

### Fixes
- **Fails to load on current Home Assistant**: replaced `async_timeout` (no longer installed with HA) with `asyncio.timeout`.
- Midnight refresh now uses the Home Assistant time zone, not the host clock.
- After a restart, a cached hadith from an earlier day is replaced automatically.
- Reloading the integration no longer stacks extra midnight timers.
- Reloading no longer deletes the cached hadith (it's deleted only when the integration is removed).
- If the Sunnah.com API fails, the shared hadith of the day is used instead of the sensor going unavailable.

### New
- Reconfigure: add, change or remove your Sunnah.com API key without removing the integration.
- `url` and `source` attributes.
- Service device, icons, and English/Malay translations for the sensor, attributes and the `daily_hadith.reload` action.
- Text attributes excluded from the recorder.

### Under the hood
- `DataUpdateCoordinator` subclass with `entry.runtime_data`, `ConfigFlowResult`, `single_config_entry`, `integration_type: service`, action registered once in `async_setup`.
- Removed the unneeded `aiohttp` requirement.
- 15 tests added. hassfest passes against HA 2026.11.0b1.

### Compatibility
- `sensor.daily_hadith` keeps its unique ID, so entity IDs, dashboards and automations are unchanged.
- Minimum Home Assistant: 2024.11.0.
