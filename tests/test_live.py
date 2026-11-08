"""Tests that execute directly against live physical hardware when --live is passed."""

import pytest
from aioeltako_ip import EltakoClient


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hardware_system(live_client: EltakoClient) -> None:
    """Verify live hardware connects and returns system info."""
    sys_info = await live_client.get_system()
    assert sys_info.product_name
    assert sys_info.software_version
    assert sys_info.serial_number


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hardware_devices(live_client: EltakoClient) -> None:
    """Verify live devices are discoverable."""
    devices = await live_client.get_devices()
    assert len(devices) > 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hardware_enocean(live_client: EltakoClient) -> None:
    """Verify EnOcean subsystem on live hardware."""
    status = await live_client.get_enocean_status()
    assert status.health == "ok"
    assert status.max_eur_ids > 0
