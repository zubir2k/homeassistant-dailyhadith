"""Tests for the translation options (AI Task / Assist and OpenAI-compatible)."""
from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.daily_hadith import translator as tr
from custom_components.daily_hadith.const import (
    API_ENDPOINT_HADITH_RANDOM,
    DOMAIN,
    FALLBACK_URL,
    ISSUE_TRANSLATOR_NEEDED,
    STORAGE_KEY,
)
from custom_components.daily_hadith.translator import (
    TranslationAuthError,
    TranslationError,
)

from .test_init import OPENAI_MS, PAYLOAD, _other

PATCH = "custom_components.daily_hadith.coordinator.async_translate"
FLOW_PATCH = "custom_components.daily_hadith.config_flow.async_translate"
OLLAMA = {"base_url": "http://ollama.local:11434/v1", "model": "llama3.1"}


def _feed_with_ms() -> str:
    p = json.loads(json.dumps(PAYLOAD))
    p["hadith"].append({"lang": "ms", "chapterTitle": "Tajuk", "body": "<p>Teks BM</p>"})
    return json.dumps(p)


@pytest.fixture(autouse=True)
async def tz(hass: HomeAssistant):
    await hass.config.async_set_time_zone("Asia/Kuala_Lumpur")


async def _setup(hass, data=None, options=None):
    entry = MockConfigEntry(domain=DOMAIN, data=data or {}, options=options or {})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def test_ai_language_in_normal_mode(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH, side_effect=["Teks Indonesia", "Judul"]) as mock:
        await _setup(hass, options={"language": "id", "translator": "openai", **OLLAMA})
    a = hass.states.get("sensor.daily_hadith").attributes
    assert a["translation"] == "Teks Indonesia"
    assert a["title_translation"] == "Judul"
    assert a["translation_language"] == "id"
    assert a["translation_source"] == "openai"
    assert a["malay"] == ""
    assert mock.call_count == 2
    assert mock.call_args_list[0].args[3] == "id"


async def test_malay_uses_ai_in_normal_mode(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH, side_effect=["Teks BM Diterjemah", "Tajuk BM"]) as mock:
        await _setup(hass, options={"language": "ms", "translator": "openai", **OLLAMA})
    a = hass.states.get("sensor.daily_hadith").attributes
    assert a["translation"] == "Teks BM Diterjemah"
    assert a["malay"] == "Teks BM Diterjemah"
    assert a["translation_source"] == "openai"
    assert mock.call_count == 2


async def test_english_means_no_translation(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH) as mock:
        await _setup(hass, options={"language": "en-GB", "translator": "none"})
    a = hass.states.get("sensor.daily_hadith").attributes
    assert a["translation"] == ""
    assert a["translation_language"] == "en-GB"
    mock.assert_not_called()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_TRANSLATOR_NEEDED) is None


async def test_api_mode_without_translator_raises_issue(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("9"))
    with patch(PATCH) as mock:
        entry = await _setup(hass, {CONF_API_KEY: "k"})
    a = hass.states.get("sensor.daily_hadith").attributes
    assert a["malay"] == ""
    assert a["translation"] == ""
    mock.assert_not_called()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_TRANSLATOR_NEEDED)

    # Adding a translator clears the issue and translates the cached hadith.
    with patch(PATCH, return_value="Terjemahan") as mock:
        hass.config_entries.async_update_entry(
            entry, options={"language": "ms", "translator": "openai", **OLLAMA}
        )
        await hass.async_block_till_done(wait_background_tasks=True)
    assert mock.call_count == 2
    assert aioclient_mock.call_count == 1  # no new hadith fetched
    assert hass.states.get("sensor.daily_hadith").attributes["malay"] == "Terjemahan"
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_TRANSLATOR_NEEDED) is None


async def test_translation_cached_across_reload(hass: HomeAssistant, aioclient_mock, hass_storage) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH, return_value="Çeviri") as mock:
        entry = await _setup(hass, options={"language": "tr", "translator": "openai", **OLLAMA})
        assert mock.call_count == 2
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert mock.call_count == 2
    stored = hass_storage[STORAGE_KEY]["data"]["data"][0]["translation"]
    assert stored["lang"] == "tr"
    assert stored["text"] == "Çeviri"


async def test_failed_translation_retries(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH, side_effect=TranslationError("model loading")):
        await _setup(hass, options={"language": "id", "translator": "openai", **OLLAMA})
    assert hass.states.get("sensor.daily_hadith").attributes["translation"] == ""
    with patch(PATCH, return_value="Teks") as mock:
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=16))
        await hass.async_block_till_done(wait_background_tasks=True)
    assert mock.call_count == 2
    assert hass.states.get("sensor.daily_hadith").attributes["translation"] == "Teks"


async def test_title_failure_keeps_body(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH, side_effect=["Teks", TranslationError("x")]):
        await _setup(hass, options={"language": "id", "translator": "openai", **OLLAMA})
    a = hass.states.get("sensor.daily_hadith").attributes
    assert a["translation"] == "Teks"
    assert a["title_translation"] == ""


# --- options flow --------------------------------------------------------------
async def _options(hass, data=None):
    entry = MockConfigEntry(domain=DOMAIN, data=data or {})
    entry.add_to_hass(hass)
    with patch("custom_components.daily_hadith.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(entry.entry_id)
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["step_id"] == "init"
    return entry, r


async def test_options_none_with_english(hass: HomeAssistant) -> None:
    entry, r = await _options(hass)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"language": "en", "translator": "none"}
    )
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"language": "en", "translator": "none"}


@pytest.mark.parametrize(
    ("data", "language", "error"),
    [
        ({}, "id", "translator_required"),
        ({}, "ms", "translator_required"),
        ({CONF_API_KEY: "k"}, "ms", "translator_required"),
    ],
)
async def test_options_need_translator(hass: HomeAssistant, data, language, error) -> None:
    _, r = await _options(hass, data)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"language": language, "translator": "none"}
    )
    assert r["errors"] == {"base": error}


async def test_options_openai(hass: HomeAssistant) -> None:
    entry, r = await _options(hass)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"language": "id", "translator": "openai"}
    )
    assert r["step_id"] == "openai"
    r2 = await hass.config_entries.options.async_configure(
        r["flow_id"], {"base_url": "ollama.local", "model": "m"}
    )
    assert r2["errors"] == {"base_url": "invalid_url"}
    with patch(FLOW_PATCH, side_effect=TranslationAuthError("401")):
        r2 = await hass.config_entries.options.async_configure(
            r["flow_id"], {**OLLAMA, CONF_API_KEY: "bad"}
        )
    assert r2["errors"] == {"base": "invalid_auth"}
    with patch(FLOW_PATCH, side_effect=TranslationError("down")):
        r2 = await hass.config_entries.options.async_configure(r["flow_id"], OLLAMA)
    assert r2["errors"] == {"base": "translation_failed"}
    with patch(FLOW_PATCH, return_value="Damai"):
        r2 = await hass.config_entries.options.async_configure(
            r["flow_id"], {**OLLAMA, CONF_API_KEY: " sk "}
        )
    assert r2["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "language": "id", "translator": "openai", **OLLAMA, CONF_API_KEY: "sk",
    }


async def test_options_ai_task(hass: HomeAssistant) -> None:
    entry, r = await _options(hass)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"language": "fr", "translator": "ai_task"}
    )
    assert r["step_id"] == "ai_task"
    r2 = await hass.config_entries.options.async_configure(r["flow_id"], {})
    assert r2["errors"] == {"base": "ai_task_unavailable"}

    hass.services.async_register(
        "ai_task", "generate_data", AsyncMock(return_value={"data": "Paix"}),
        supports_response=SupportsResponse.ONLY,
    )
    r2 = await hass.config_entries.options.async_configure(
        r["flow_id"], {"ai_task_entity": "ai_task.ollama"}
    )
    assert r2["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "language": "fr", "translator": "ai_task", "ai_task_entity": "ai_task.ollama",
    }


# --- translator backends -------------------------------------------------------
async def test_openai_backend(hass: HomeAssistant, aioclient_mock) -> None:
    url = "http://ollama.local:11434/v1/chat/completions"
    aioclient_mock.post(url, json={"choices": [{"message": {"content": "<think>hmm</think>\n Selamat "}}]})
    opts = {"translator": "openai", **OLLAMA, CONF_API_KEY: "sk"}
    assert await tr.async_translate(hass, opts, "Peace", "ms") == "Selamat"
    _, _, body, headers = aioclient_mock.mock_calls[0]
    assert headers["Authorization"] == "Bearer sk"
    assert body["model"] == "llama3.1"
    assert "Malay (ms)" in body["messages"][0]["content"]

    aioclient_mock.clear_requests()
    aioclient_mock.post(url, status=401)
    with pytest.raises(TranslationAuthError):
        await tr.async_translate(hass, opts, "Peace", "ms")
    aioclient_mock.clear_requests()
    aioclient_mock.post(url, json={"oops": 1})
    with pytest.raises(TranslationError):
        await tr.async_translate(hass, opts, "Peace", "ms")


async def test_ai_task_backend(hass: HomeAssistant) -> None:
    calls: list[ServiceCall] = []

    async def handler(call: ServiceCall):
        calls.append(call)
        return {"conversation_id": "x", "data": "Hola"}

    hass.services.async_register(
        "ai_task", "generate_data", handler, supports_response=SupportsResponse.ONLY
    )
    opts = {"translator": "ai_task", "ai_task_entity": "ai_task.gpt"}
    assert await tr.async_translate(hass, opts, "Hello", "es") == "Hola"
    assert calls[0].data["entity_id"] == "ai_task.gpt"
    assert "Spanish (es)" in calls[0].data["instructions"]


async def test_conversation_backend(hass: HomeAssistant) -> None:
    calls: list[ServiceCall] = []

    async def handler(call: ServiceCall):
        calls.append(call)
        return {"response": {"speech": {"plain": {"speech": "Terjemahan"}}, "response_type": "action_done"}}

    hass.services.async_register(
        "conversation", "process", handler, supports_response=SupportsResponse.ONLY
    )
    opts = {"translator": "ai_task", "ai_task_entity": "conversation.chatgpt"}
    assert await tr.async_translate(hass, opts, "Hello", "ms") == "Terjemahan"
    assert calls[0].data["agent_id"] == "conversation.chatgpt"


def test_helpers() -> None:
    assert tr.chat_url("https://api.openai.com/v1/") == "https://api.openai.com/v1/chat/completions"
    assert tr.chat_url("http://x/v1/chat/completions") == "http://x/v1/chat/completions"
    assert tr.chat_url("http://localhost:11434") == "http://localhost:11434/v1/chat/completions"
    assert tr.language_name("pt-BR") == "Brazilian Portuguese (pt-BR)"
    assert tr.language_name("xx") == "xx"
    assert tr.base_language("zh_Hant") == "zh"
    assert tr.clean_output('<text>"Salam"</text>') == "Salam"
    assert tr.clean_output('```markdown\nSalam\n```') == "Salam"


def test_language_options_include_malay() -> None:
    opts = tr.language_options()
    assert opts[0] == {"value": "ms", "label": "Bahasa Melayu (Malay)"}
    assert {"value": "id", "label": "Bahasa Indonesia (Indonesian)"} in opts
    assert {"value": "en", "label": "English"} in opts
    assert len({o["value"] for o in opts}) == len(opts)


DIAG = "sensor.daily_hadith_translation"


async def test_refresh_during_translation_translates_new_hadith(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Pressing refresh while a translation runs must not leave the new one blank."""
    import asyncio

    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("1"))
    gate = asyncio.Event()
    calls: list[str] = []

    async def slow(_hass, _opts, text, _lang):
        calls.append(text)
        if len(calls) <= 2:
            await gate.wait()
        return f"BM {len(calls)}"

    with patch(PATCH, side_effect=slow):
        entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "k"}, options=OPENAI_MS)
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(DIAG).state == "translating"

        aioclient_mock.clear_requests()
        aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("2"))
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert hass.states.get("sensor.daily_hadith").attributes["hadith_number"] == "2"

        gate.set()
        await hass.async_block_till_done(wait_background_tasks=True)

    assert len(calls) == 4  # the old hadith, then the new one
    a = hass.states.get("sensor.daily_hadith").attributes
    assert a["hadith_number"] == "2"
    assert a["translation"].startswith("BM")
    d = hass.states.get(DIAG)
    assert d.state == "translated"
    assert d.attributes["hadith_number"] == "2"


async def test_diagnostic_sensor_reports_failure(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH, side_effect=TranslationError("HTTP 504: gateway timeout")):
        await _setup(hass, options={"language": "id", "translator": "openai", **OLLAMA})
    d = hass.states.get(DIAG)
    assert d.state == "failed"
    assert d.attributes["error"] == "HTTP 504: gateway timeout"
    assert d.attributes["translator"] == "openai"
    assert d.attributes["backend"] == "llama3.1"
    assert d.attributes["next_retry"] is not None
    assert d.attributes["last_success"] is None


async def test_diagnostic_sensor_states(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FALLBACK_URL, text=_feed_with_ms())
    with patch(PATCH):
        await _setup(hass, options={"language": "en", "translator": "none"})
    assert hass.states.get(DIAG).state == "not_needed"


async def test_diagnostic_needs_translator(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(API_ENDPOINT_HADITH_RANDOM, json=_other("9"))
    await _setup(hass, {CONF_API_KEY: "k"})
    assert hass.states.get(DIAG).state == "needs_translator"
