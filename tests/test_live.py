"""Tests that execute directly against live physical hardware when --live is passed."""

import pytest
from aioeltako_ip import EltakoClient


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hardware_system_and_well_known(live_client: EltakoClient) -> None:
    """Verify live hardware connects and returns system info and well-known discovery."""
    sys_info = await live_client.get_system()
    assert sys_info.product_name
    assert sys_info.software_version
    assert sys_info.serial_number

    wk = await live_client.get_well_known()
    assert "api" in wk

    assert await live_client.identify() is True


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hardware_devices_and_products(live_client: EltakoClient) -> None:
    """Verify live devices and product specifications are discoverable."""
    devices = await live_client.get_devices()
    assert len(devices) > 0

    products = await live_client.get_products()
    assert len(products) > 0
    assert devices[0].product_guid in products


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hardware_enocean_and_legacypair(live_client: EltakoClient) -> None:
    """Verify EnOcean subsystem and legacy pairing info on live hardware."""
    status = await live_client.get_enocean_status()
    assert status.health == "ok"
    assert status.max_eur_ids > 0

    supported = await live_client.get_enocean_legacy_pair_supported_devices()
    assert len(supported) > 0

    lp_status = await live_client.get_enocean_legacy_pair_status()
    assert lp_status.status is not None


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hardware_matter_update_and_automations(
    live_client: EltakoClient,
) -> None:
    """Verify Matter service, OTA update config/firmware, and on-device automations on live hardware."""
    matter_service = await live_client.get_matter_service()
    assert isinstance(matter_service.devices, list)

    upd_cfg = await live_client.get_update_config()
    assert upd_cfg.update_server_uri

    fw_info = await live_client.get_firmware_update_info()
    assert fw_info.current_version

    automations = await live_client.get_automations()
    assert isinstance(automations, list)
