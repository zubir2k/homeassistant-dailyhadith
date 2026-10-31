"""Fixtures for Daily Hadith tests."""
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


@pytest.fixture(autouse=True)
def no_http_server():
    """The card needs the http and frontend components; don't open a real port."""
    with patch("homeassistant.components.http.HomeAssistantHTTP.start"):
        yield
