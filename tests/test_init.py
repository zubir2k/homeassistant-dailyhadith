"""Tests for Daily Hadith."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.daily_hadith.const import (
    API_ENDPOINT_HADITH_RANDOM,
    DOMAIN,
    FALLBACK_URL,
    STORAGE_KEY,
)
from custom_components.daily_hadith.sensor import clean_text

PAYLOAD = json.loads((Path(__file__).parents[1] / "dailyhadith.json").read_text())


def _other(num: str) -> dict:
    p = json.loads(json.dumps(PAYLOAD))
    p["hadithNumber"] = num
    return p


@pytest.fixture(autouse=True)
def mock_translate():
    """Never reach the real translation worker; return a fixed Malay string."""
    with patch(
        "custom_components.daily_hadith.coordinator.DailyHadithCoordinator._async_translate",
        return_value="Terjemahan Melayu",
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
async def tz(hass: HomeAssistant):
    await hass.config.async_set_time_zone("Asia/Kuala_Lumpur")


async def _setup(hass, data=None):
    entry = MockConfigEntry(domain=DOMAIN, data=data or {}, title="Daily Hadith")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_fallback_setup(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(PAYLOAD))
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    st = hass.states.get("sensor.daily_hadith")
    assert st.state == dt_util.now().date().isoformat()
    assert st.attributes["hadith_number"] == "1437"
    assert st.attributes["collection"] == "Riyadussalihin"
    assert st.attributes["url"] == "https://sunnah.com/riyadussalihin:1437"
    assert st.attributes["source"] == "github_fallback"
    assert "<" not in st.attributes["text"]
    assert er.async_get(hass).async_get("sensor.daily_hadith").unique_id == "daily_hadith_hadith"


async def test_api_used_then_falls_back(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("9"))
    await _setup(hass, {CONF_API_KEY: "k"})
    st = hass.states.get("sensor.daily_hadith")
    assert st.attributes["hadith_number"] == "9"
    assert st.attributes["source"] == "sunnah_api"
    assert aioclient_mock.mock_calls[0][3]["x-api-key"] == "k"


async def test_api_error_uses_fallback(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, status=500)
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(PAYLOAD))
    await _setup(hass, {CONF_API_KEY: "k"})
    assert hass.states.get("sensor.daily_hadith").attributes["source"] == "github_fallback"


async def test_not_ready_when_everything_fails(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, status=503)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_cache_used_and_stale_cache_refreshed(hass: HomeAssistant, aioclient_mock, hass_storage) -> None:
    today = dt_util.now().date().isoformat()
    hass_storage[STORAGE_KEY] = {"version": 1, "key": STORAGE_KEY, "data": {"data": [
        {"hadithNumber": "5", "collection": "bukhari", "fetch_date": today, "malayText": ""}]}}
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(PAYLOAD))
    await _setup(hass)
    assert hass.states.get("sensor.daily_hadith").attributes["hadith_number"] == "5"
    assert aioclient_mock.call_count == 0


async def test_stale_cache_refreshed(hass: HomeAssistant, aioclient_mock, hass_storage) -> None:
    hass_storage[STORAGE_KEY] = {"version": 1, "key": STORAGE_KEY, "data": {"data": [
        {"hadithNumber": "5", "collection": "bukhari", "fetch_date": "2020-01-01"}]}}
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(PAYLOAD))
    await _setup(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("sensor.daily_hadith").attributes["hadith_number"] == "1437"


async def test_midnight_refresh_and_no_timer_leak(
    hass: HomeAssistant, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-11-01 23:00:00+08:00")
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("1"))
    entry = await _setup(hass, {CONF_API_KEY: "k"})
    # Reload twice: old code stacked a new midnight timer each time.
    for _ in range(2):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    calls = aioclient_mock.call_count
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("2"))
    freezer.move_to("2026-11-02 00:00:31+08:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert calls == 1
    assert aioclient_mock.call_count == 1
    st = hass.states.get("sensor.daily_hadith")
    assert st.state == "2026-11-02"
    assert st.attributes["hadith_number"] == "2"


async def test_reload_service_forces_fetch(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("1"))
    await _setup(hass, {CONF_API_KEY: "k"})
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("2"))
    await hass.services.async_call(DOMAIN, "reload", blocking=True)
    assert hass.states.get("sensor.daily_hadith").attributes["hadith_number"] == "2"


async def test_unload_keeps_cache_remove_deletes(hass: HomeAssistant, aioclient_mock, hass_storage) -> None:
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(PAYLOAD))
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert STORAGE_KEY in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert STORAGE_KEY not in hass_storage


async def test_config_flow_no_key(hass: HomeAssistant) -> None:
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert r["type"] is FlowResultType.FORM
    with patch("custom_components.daily_hadith.async_setup_entry", return_value=True):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {})
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["data"] == {}


@pytest.mark.parametrize(("status", "error"), [(401, "invalid_api_key"), (500, "cannot_connect")])
async def test_config_flow_bad_key(hass: HomeAssistant, aioclient_mock, status, error) -> None:
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, status=status)
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {CONF_API_KEY: "bad"})
    assert r["errors"] == {"base": error}


async def test_single_instance(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert r["type"] is FlowResultType.ABORT
    assert r["reason"] == "single_instance_allowed"


async def test_reconfigure_adds_key(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(PAYLOAD))
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("7"))
    entry = await _setup(hass)
    r = await entry.start_reconfigure_flow(hass)
    assert r["step_id"] == "reconfigure"
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {CONF_API_KEY: " good "})
    assert r["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_API_KEY: "good"}


def test_clean_text() -> None:
    assert clean_text("<p>a<br/>b<BR>c <b>[x]</b></p><p>d</p>") == "a\nb\nc [x]\n\nd"
    assert clean_text(None) == ""


async def test_malay_from_fallback_feed(hass: HomeAssistant, aioclient_mock, mock_translate) -> None:
    payload = json.loads(json.dumps(PAYLOAD))
    payload["hadith"].append({"lang": "ms", "chapterTitle": "Tajuk", "body": "<p>Teks BM</p>"})
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(payload))
    await _setup(hass)
    attrs = hass.states.get("sensor.daily_hadith").attributes
    assert attrs["malay"] == "Teks BM"
    assert attrs["title_ms"] == "Tajuk"
    mock_translate.assert_not_called()


async def test_malay_translated_for_api(hass: HomeAssistant, aioclient_mock, mock_translate) -> None:
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("9"))
    await _setup(hass, {CONF_API_KEY: "k"})
    attrs = hass.states.get("sensor.daily_hadith").attributes
    assert attrs["malay"] == "Terjemahan Melayu"
    assert attrs["title_ms"] == "Terjemahan Melayu"
    assert mock_translate.call_count == 2


async def test_translation_failure_not_fatal(hass: HomeAssistant, aioclient_mock, mock_translate) -> None:
    mock_translate.return_value = ""
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("9"))
    await _setup(hass, {CONF_API_KEY: "k"})
    attrs = hass.states.get("sensor.daily_hadith").attributes
    assert attrs["hadith_number"] == "9"
    assert attrs["malay"] == ""


async def test_old_cache_without_malay_refetched(hass: HomeAssistant, aioclient_mock, hass_storage) -> None:
    today = dt_util.now().date().isoformat()
    hass_storage[STORAGE_KEY] = {"version": 1, "key": STORAGE_KEY, "data": {"data": [
        {"hadithNumber": "5", "collection": "bukhari", "fetch_date": today}]}}
    aioclient_mock.get(FALLBACK_URL, text=json.dumps(PAYLOAD))
    await _setup(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert aioclient_mock.call_count == 1
