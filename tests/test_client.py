"""Tests for aioeltako_ip client using aioresponses and captured fixtures."""

import json
from pathlib import Path
import pytest
from aioresponses import aioresponses

from aioeltako_ip import (
    AuthenticationError,
    AutomationAddOn,
    AutomationRule,
    EltakoClient,
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
async def test_get_system_and_well_known(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    system_data = load_fixture("system")
    well_known_data = load_fixture("well_known")
    root_url = f"https://{test_host}:443"

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/system", payload=system_data)
        m.get(f"{root_url}/.well-known/eltako/devices", payload=well_known_data)
        m.post(f"{root_url}/identify", status=200, payload={"status": 200})

        async with EltakoClient(test_host, pop=test_pop) as client:
            info = await client.get_system()
            assert info.product_name == "ELTAKO-ESR64PF-IPM"
            assert info.serial_number == "ELTAKO-0000000000"
            assert info.software_version == "2.5.0"

            wk = await client.get_well_known()
            assert wk["api"]["version"] == "0.4.0"

            assert await client.identify() is True


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

            relay_dev = next(
                d
                for d in devices
                if d.product_guid == "4893e06b-448c-40d5-b426-42e2e6b73656"
            )
            assert relay_dev.display_name == "ELTAKO-ESR64PF-IPM"
            assert relay_dev.get_function_value("relay") == "on"

            contact_dev = next(
                d
                for d in devices
                if d.product_guid == "791a7c28-22e3-4fab-8ecc-0084e15396c5"
            )
            assert contact_dev.display_name == "window"
            assert contact_dev.get_info_value("contact") == "opened"
            assert contact_dev.get_info_value("connectionStatus") == "online"


@pytest.mark.asyncio
async def test_set_relay_dimmer_cover_and_settings(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    guid = "11111111-1111-1111-1111-111111111111"

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.put(f"{test_base_url}/devices/{guid}/functions/relay", status=202)
        m.put(f"{test_base_url}/devices/{guid}/functions/targetBrightness", status=200)
        m.put(f"{test_base_url}/devices/{guid}/functions/targetPosition", status=200)
        m.put(f"{test_base_url}/devices/{guid}/functions/targetTilt", status=200)
        m.put(f"{test_base_url}/devices/{guid}/settings/edgeMode", status=200)

        async with EltakoClient(test_host, pop=test_pop) as client:
            assert await client.set_relay(guid, False) is True
            assert await client.set_brightness(guid, 75) is True
            assert await client.set_cover_position(guid, 40) is True
            assert await client.set_cover_tilt(guid, 20) is True
            assert (
                await client.set_setting(
                    guid, "edgeMode", "trailingEdge", char_type="enumeration"
                )
                is True
            )


@pytest.mark.asyncio
async def test_rename_device_round_trip(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    devices_data = load_fixture("devices")
    guid = devices_data[0]["deviceGuid"]

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/devices/{guid}", payload=devices_data[0])
        m.put(f"{test_base_url}/devices/{guid}", status=200)

        async with EltakoClient(test_host, pop=test_pop) as client:
            assert await client.rename_device(guid, "Hallway Relay") is True


@pytest.mark.asyncio
async def test_enocean_devices_status_scan_and_legacypair(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    status_data = load_fixture("enocean_status")
    enocean_devices_data = load_fixture("enocean_devices")
    legacypair_status = load_fixture("legacypair_status")
    legacypair_supported = load_fixture("legacypair_supported")

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/services/enocean/status", payload=status_data)
        m.get(
            f"{test_base_url}/services/enocean/devices", payload=enocean_devices_data
        )
        m.get(
            f"{test_base_url}/services/enocean/scan",
            payload=[
                {
                    "eurId": 16909060,
                    "productGuid": "791a7c28-22e3-4fab-8ecc-0084e15396c5",
                    "signalStrength": -58,
                }
            ],
        )
        m.delete(
            f"{test_base_url}/services/enocean/devices/44444444-4444-4444-4444-444444444444",
            status=204,
        )
        m.get(
            f"{test_base_url}/services/enocean/legacypair/status",
            payload=legacypair_status,
        )
        m.get(
            f"{test_base_url}/services/enocean/legacypair/info/supported-devices",
            payload=legacypair_supported,
        )

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

            scan_items = await client.get_enocean_scan_results()
            assert len(scan_items) == 1
            assert scan_items[0].eur_id == 16909060

            assert (
                await client.delete_enocean_device(
                    "44444444-4444-4444-4444-444444444444"
                )
                is True
            )

            lp_status = await client.get_enocean_legacy_pair_status()
            assert lp_status.status == "confirmationMissing"
            assert lp_status.taught_in is False

            supported = await client.get_enocean_legacy_pair_supported_devices()
            assert "7358f66f-5d44-4781-a4eb-bd6857e8e39e" in supported


@pytest.mark.asyncio
async def test_matter_devices_and_reset(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    matter_devices_data = load_fixture("matter_devices")

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/services/matter/devices", payload=matter_devices_data)
        m.post(f"{test_base_url}/services/matter/reset", status=200, payload={})

        async with EltakoClient(test_host, pop=test_pop) as client:
            matter_devs = await client.get_matter_devices()
            assert len(matter_devs) == 3
            assert any(
                d.product_guid == "791a7c28-22e3-4fab-8ecc-0084e15396c5"
                for d in matter_devs
            )
            assert await client.reset_matter_service() is True


@pytest.mark.asyncio
async def test_update_and_firmware_endpoints(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    update_cfg_data = load_fixture("update_config")
    firmware_data = load_fixture("update_firmware")

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(f"{test_base_url}/update/config", payload=update_cfg_data)
        m.put(f"{test_base_url}/update/config", status=200)
        m.get(f"{test_base_url}/update/firmware", payload=firmware_data)
        m.put(f"{test_base_url}/update/firmware/bin", status=200)

        async with EltakoClient(test_host, pop=test_pop) as client:
            cfg = await client.get_update_config()
            assert cfg.update_server_uri == "update.eltako.com"
            assert cfg.auto_update is False
            assert cfg.update_schedule == "12h"

            assert await client.set_update_config(auto_update=True) is True

            fw = await client.get_firmware_update_info()
            assert fw.current_version == "2.5.0"
            assert fw.desired_version == "0.0.0"

            assert await client.upload_firmware_binary(b"\x00\x01\x02\x03") is True


@pytest.mark.asyncio
async def test_automations_endpoints(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    automations_data = load_fixture("automations")
    auto_guid = automations_data[0]["configuration"]["automationGuid"]

    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(
            f"{test_base_url}/services/eltako/automations", payload=automations_data
        )
        m.put(
            f"{test_base_url}/services/eltako/automations/{auto_guid}",
            status=200,
        )
        m.delete(
            f"{test_base_url}/services/eltako/automations/{auto_guid}",
            status=204,
        )

        async with EltakoClient(test_host, pop=test_pop) as client:
            rules = await client.get_automations()
            assert len(rules) == 1
            rule = rules[0]
            assert rule.logic == "buttonImpulseSwitch"
            assert rule.off_timer_ms == 10000

            assert (
                await client.set_automation_logic(
                    rule, logic="buttonSwitch", off_timer_ms=5000
                )
                is True
            )
            assert await client.delete_automation(auto_guid) is True
