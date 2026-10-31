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
