"""Unit tests for Home Assistant entities in custom_components/eltako_ip."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT

from aioeltako_ip import (
    Device,
    EnOceanDevice,
    EnOceanStatus,
    SystemInfo,
)
from custom_components.eltako_ip.switch import EltakoRelaySwitch
from custom_components.eltako_ip.binary_sensor import (
    EltakoContactBinarySensor,
    EltakoConnectivityBinarySensor,
    EltakoWiredInputBinarySensor,
)
from custom_components.eltako_ip.sensor import (
    EltakoEnOceanRssiSensor,
    EltakoFreeEurIdsSensor,
)
from custom_components.eltako_ip.select import EltakoRepeaterSelect
from custom_components.eltako_ip.button import EltakoStartEnOceanScanButton
from custom_components.eltako_ip.coordinator import EltakoData


@pytest.fixture
def mock_coordinator():
    """Build a mock EltakoDataUpdateCoordinator."""
    system = SystemInfo(
        software_version="2.5.0",
        hardware_version="1.0.0",
        product_name="ELTAKO-ESR64PF-IPM",
        product_type="ELTAKO-ESR64PF-IPM",
        product_guid="4893e06b-448c-40d5-b426-42e2e6b73656",
        serial_number="ELTAKO-0000000000",
    )

    relay_dev = Device(
        device_guid="11111111-1111-1111-1111-111111111111",
        product_guid="4893e06b-448c-40d5-b426-42e2e6b73656",
        display_name="ELTAKO-ESR64PF-IPM",
    )
    from aioeltako_ip.models import Characteristic
    relay_dev.functions = [Characteristic(identifier="relay", type="enumeration", value="on")]

    input_dev = Device(
        device_guid="22222222-2222-2222-2222-222222222222",
        product_guid="6f6d379f-4c6f-45ed-b881-671ed7ea8970",
        display_name="ELTAKO-Wired input",
    )
    input_dev.functions = [Characteristic(identifier="input", type="enumeration", value="opened")]

    contact_dev = Device(
        device_guid="33333333-3333-3333-3333-333333333333",
        product_guid="791a7c28-22e3-4fab-8ecc-0084e15396c5",
        display_name="window",
    )
    contact_dev.infos = [
        Characteristic(identifier="contact", type="enumeration", value="opened"),
        Characteristic(identifier="connectionStatus", type="enumeration", value="online"),
    ]

    eo_status = EnOceanStatus(
        health="ok",
        max_eur_ids=128,
        free_eur_ids=127,
        hardware_filter_state="enabled",
    )

    eo_dev = EnOceanDevice(
        service_device_guid="44444444-4444-4444-4444-444444444444",
        device_guid="33333333-3333-3333-3333-333333333333",
        product_guid="791a7c28-22e3-4fab-8ecc-0084e15396c5",
        eur_id=16909060,
        signal_strength=-60,
        last_seen="2026-11-08T12:00:00Z",
    )

    data = EltakoData(
        system=system,
        devices={
            relay_dev.device_guid: relay_dev,
            input_dev.device_guid: input_dev,
            contact_dev.device_guid: contact_dev,
        },
        enocean_status=eo_status,
        enocean_devices={contact_dev.device_guid: eo_dev},
        matter_devices=[],
        enocean_config={"repeaterLevel": "oneLevel", "repeaterMode": "on"},
    )

    coordinator = MagicMock()
    coordinator.data = data
    coordinator.system_info = system
    coordinator.client = MagicMock()
    coordinator.client.set_relay = AsyncMock(return_value=True)
    coordinator.client.set_enocean_repeater = AsyncMock()
    coordinator.client.start_enocean_scan = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_switch_entity(mock_coordinator):
    """Test ESR64PF relay switch entity."""
    switch = EltakoRelaySwitch(mock_coordinator, "11111111-1111-1111-1111-111111111111")
    assert switch.is_on is True
    assert switch.unique_id == "11111111-1111-1111-1111-111111111111_relay"
    assert switch.name == "Relay"
    assert switch.device_info["manufacturer"] == "Eltako"
    assert switch.device_info["model"] == "ELTAKO-ESR64PF-IPM"

    await switch.async_turn_off()
    mock_coordinator.client.set_relay.assert_called_with("11111111-1111-1111-1111-111111111111", False)

    await switch.async_turn_on()
    mock_coordinator.client.set_relay.assert_called_with("11111111-1111-1111-1111-111111111111", True)


def test_binary_sensors(mock_coordinator):
    """Test FTK solar contact sensor and wired input entities."""
    contact = EltakoContactBinarySensor(mock_coordinator, "33333333-3333-3333-3333-333333333333")
    assert contact.is_on is True
    assert contact.device_class == BinarySensorDeviceClass.WINDOW
    assert contact.unique_id == "33333333-3333-3333-3333-333333333333_contact"

    conn = EltakoConnectivityBinarySensor(mock_coordinator, "33333333-3333-3333-3333-333333333333")
    assert conn.is_on is True
    assert conn.device_class == BinarySensorDeviceClass.CONNECTIVITY

    wired_in = EltakoWiredInputBinarySensor(mock_coordinator, "22222222-2222-2222-2222-222222222222")
    assert wired_in.is_on is True
    assert wired_in.device_class == BinarySensorDeviceClass.OPENING


def test_diagnostic_sensors(mock_coordinator):
    """Test EnOcean RSSI and capacity slot sensors."""
    rssi = EltakoEnOceanRssiSensor(mock_coordinator, "33333333-3333-3333-3333-333333333333")
    assert rssi.native_value == -60
    assert rssi.device_class == SensorDeviceClass.SIGNAL_STRENGTH
    assert rssi.native_unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT

    free_slots = EltakoFreeEurIdsSensor(mock_coordinator)
    assert free_slots.native_value == 127
    assert free_slots.extra_state_attributes["max_eur_ids"] == 128
    assert free_slots.extra_state_attributes["health"] == "ok"


@pytest.mark.asyncio
async def test_repeater_select_and_button(mock_coordinator):
    """Test EnOcean repeater level selector and scan button."""
    repeater = EltakoRepeaterSelect(mock_coordinator)
    assert repeater.current_option == "oneLevel"
    await repeater.async_select_option("twoLevel")
    mock_coordinator.client.set_enocean_repeater.assert_called_with(repeater_level="twoLevel")

    button = EltakoStartEnOceanScanButton(mock_coordinator)
    await button.async_press()
    mock_coordinator.client.start_enocean_scan.assert_called_once()


@pytest.mark.asyncio
async def test_diagnostics(mock_coordinator):
    """Test diagnostics platform returns sanitized data with redacted secrets."""
    from custom_components.eltako_ip.diagnostics import async_get_config_entry_diagnostics
    from custom_components.eltako_ip.const import DOMAIN

    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "host": "192.0.2.1",
        "port": 443,
        "pop": "test_proof_of_possession",
    }
    entry.options = {"scan_interval": 10}

    hass = MagicMock()
    hass.data = {DOMAIN: {entry.entry_id: mock_coordinator}}

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry_data"]["pop"] == "**REDACTED**"
    assert diag["entry_data"]["host"] == "**REDACTED**"
    assert diag["system"]["product_name"] == "ELTAKO-ESR64PF-IPM"
    assert diag["system"]["serial_number"] == "**REDACTED**"
    assert len(diag["devices"]) == 3
    assert diag["enocean_devices"][0]["eur_id"] == "**REDACTED**"
