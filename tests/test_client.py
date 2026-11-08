"""Tests for aioeltako_ip client using aioresponses and captured fixtures."""

import json
from pathlib import Path
import pytest
from aioresponses import aioresponses

from aioeltako_ip import (
    EltakoClient,
    AuthenticationError,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURES_DIR / f"{name}.json") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_login_success(test_base_url: str, test_host: str, test_pop: str):
    login_data = load_fixture("login")
    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)

        async with EltakoClient(test_host, pop=test_pop) as client:
            key = await client.login()
            assert key == login_data["apiKey"]
            assert client.api_key == login_data["apiKey"]


@pytest.mark.asyncio
async def test_login_invalid_pop(test_base_url: str, test_host: str):
    with aioresponses() as m:
        m.post(f"{test_base_url}/login", status=401, payload={"title": "Unauthorized"})

        async with EltakoClient(test_host, pop="invalid_pop_value") as client:
            with pytest.raises(AuthenticationError):
                await client.login()


@pytest.mark.asyncio
async def test_get_system(test_base_url: str, test_host: str, test_pop: str):
    login_data = load_fixture("login")
    system_data = load_fixture("system")

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/system", payload=system_data)

        async with EltakoClient(test_host, pop=test_pop) as client:
            info = await client.get_system()
            assert info.product_name == "ELTAKO-ESR64PF-IPM"
            assert info.serial_number == "ELTAKO-0000000000"
            assert info.software_version == "2.5.0"


@pytest.mark.asyncio
async def test_get_devices(test_base_url: str, test_host: str, test_pop: str):
    login_data = load_fixture("login")
    devices_data = load_fixture("devices")

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/devices", payload=devices_data)

        async with EltakoClient(test_host, pop=test_pop) as client:
            devices = await client.get_devices()
            assert len(devices) == 3

            relay_dev = next(d for d in devices if d.product_guid == "4893e06b-448c-40d5-b426-42e2e6b73656")
            assert relay_dev.display_name == "ELTAKO-ESR64PF-IPM"
            assert relay_dev.get_function_value("relay") == "on"

            contact_dev = next(d for d in devices if d.product_guid == "791a7c28-22e3-4fab-8ecc-0084e15396c5")
            assert contact_dev.display_name == "window"
            assert contact_dev.get_info_value("contact") == "opened"
            assert contact_dev.get_info_value("connectionStatus") == "online"


@pytest.mark.asyncio
async def test_set_relay(test_base_url: str, test_host: str, test_pop: str):
    login_data = load_fixture("login")
    guid = "11111111-1111-1111-1111-111111111111"

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.put(f"{test_base_url}/devices/{guid}/functions/relay", status=202)

        async with EltakoClient(test_host, pop=test_pop) as client:
            ok = await client.set_relay(guid, False)
            assert ok is True


@pytest.mark.asyncio
async def test_enocean_devices_and_status(test_base_url: str, test_host: str, test_pop: str):
    login_data = load_fixture("login")
    status_data = load_fixture("enocean_status")
    enocean_devices_data = load_fixture("enocean_devices")

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/services/enocean/status", payload=status_data)
        m.get(f"{test_base_url}/services/enocean/devices", payload=enocean_devices_data)

        async with EltakoClient(test_host, pop=test_pop) as client:
            status = await client.get_enocean_status()
            assert status.health == "ok"
            assert status.max_eur_ids == 128
            assert status.free_eur_ids == 127

            eo_devices = await client.get_enocean_devices()
            assert len(eo_devices) == 1
            sensor = eo_devices[0]
            assert sensor.eur_id == 16909060
            assert sensor.signal_strength == -60


@pytest.mark.asyncio
async def test_matter_devices(test_base_url: str, test_host: str, test_pop: str):
    login_data = load_fixture("login")
    matter_devices_data = load_fixture("matter_devices")

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/services/matter/devices", payload=matter_devices_data)

        async with EltakoClient(test_host, pop=test_pop) as client:
            matter_devs = await client.get_matter_devices()
            assert len(matter_devs) == 3
            assert any(d.product_guid == "791a7c28-22e3-4fab-8ecc-0084e15396c5" for d in matter_devs)
