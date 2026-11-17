"""Fixtures for Daily Hadith tests."""
import sys
from unittest.mock import patch

if sys.platform == "win32":
    try:
        import pytest_socket
        def _win_disable_socket(allow_unix_socket=False):
            pass
        pytest_socket.disable_socket = _win_disable_socket
    except ImportError:
        pass

try:
    import pycares

    if hasattr(pycares, "_shutdown_manager"):
        pycares._shutdown_manager.start()
except Exception:
    pass

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    if sys.platform == "win32":
        try:
            import pytest_socket
            pytest_socket.enable_socket()
        except ImportError:
            pass
    yield
    if sys.platform == "win32":
        try:
            import pytest_socket
            pytest_socket.enable_socket()
        except ImportError:
            pass


import aiohttp


@pytest.fixture(autouse=True)
def no_aiodns():
    """Mocked sessions still build a connector; keep aiodns from leaving a pycares thread."""
    with patch("aiohttp.connector.DefaultResolver", aiohttp.ThreadedResolver):
        yield


@pytest.fixture(autouse=True)
def no_http_server():
    """The card needs the http and frontend components; don't open a real port."""
    with patch("homeassistant.components.http.HomeAssistantHTTP.start"):
        yield
