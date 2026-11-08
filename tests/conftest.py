"""Pytest configuration and custom fixtures."""

import os
from typing import AsyncGenerator, Optional
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from aioeltako_ip import EltakoClient

# Compatibility patch for aioresponses on aiohttp >= 3.11/3.14 (stream_writer parameter)
try:
    import inspect
    from unittest.mock import Mock
    from aiohttp.client_reqrep import ClientResponse

    _orig_client_response_init = ClientResponse.__init__
    if "stream_writer" in inspect.signature(_orig_client_response_init).parameters:
        def _compat_client_response_init(self, *args, **kwargs):
            if "stream_writer" not in kwargs:
                kwargs["stream_writer"] = Mock()
            return _orig_client_response_init(self, *args, **kwargs)

        ClientResponse.__init__ = _compat_client_response_init
except Exception:
    pass

# Mock test environment constants (RFC 5737 TEST-NET-1)
TEST_HOST = "192.0.2.1"
TEST_PORT = 443
TEST_POP = "test_proof_of_possession"
TEST_BASE_URL = f"https://{TEST_HOST}:{TEST_PORT}/api/v0"

_CACHED_LIVE_API_KEY: Optional[str] = None


@pytest.fixture
def test_host() -> str:
    return TEST_HOST


@pytest.fixture
def test_port() -> int:
    return TEST_PORT


@pytest.fixture
def test_pop() -> str:
    return TEST_POP


@pytest.fixture
def test_base_url() -> str:
    return TEST_BASE_URL


@pytest_asyncio.fixture
async def mock_client() -> AsyncGenerator[EltakoClient, None]:
    """Provides a client instance configured for mock testing."""
    client = EltakoClient(host=TEST_HOST, pop=TEST_POP, port=TEST_PORT)
    yield client
    await client.close()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run live tests against physical hardware specified in .env",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "live: mark test to run against physical hardware"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="Pass --live to run tests against real hardware")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


@pytest_asyncio.fixture
async def live_client() -> AsyncGenerator[EltakoClient, None]:
    """Provides an authenticated client connected to real hardware defined in .env.

    Reuses a session-cached API key to avoid churning the 10-slot API key ring buffer.
    """
    global _CACHED_LIVE_API_KEY
    load_dotenv()
    host = os.getenv("ELTAKO_HOST")
    pop = os.getenv("ELTAKO_POP")
    port = int(os.getenv("ELTAKO_PORT", "443"))

    if not host or not pop:
        pytest.skip(".env file missing ELTAKO_HOST or ELTAKO_POP for live hardware testing")

    client = EltakoClient(host=host, pop=pop, port=port, api_key=_CACHED_LIVE_API_KEY)
    if not _CACHED_LIVE_API_KEY:
        _CACHED_LIVE_API_KEY = await client.login()
    yield client
    await client.close()
