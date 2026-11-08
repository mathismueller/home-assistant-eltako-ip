"""Unit tests for Home Assistant entities across all 6 roadmap phases."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT

from aioeltako_ip import (
    AutomationAddOn,
    AutomationRule,
    Characteristic,
    Device,
    EnOceanDevice,
    EnOceanStatus,
    FirmwareUpdateInfo,
    MatterDevice,
    SystemInfo,
    UpdateConfig,
)
from custom_components.eltako_ip.binary_sensor import (
    EltakoConnectivityBinarySensor,
    EltakoContactBinarySensor,
    EltakoWiredInputBinarySensor,
)
from custom_components.eltako_ip.button import (
    EltakoIdentifyButton,
    EltakoUnpairEnOceanDeviceButton,
)
from custom_components.eltako_ip.coordinator import EltakoData
from custom_components.eltako_ip.cover import EltakoCover
from custom_components.eltako_ip.light import EltakoDimmerLight
from custom_components.eltako_ip.number import (
    EltakoAutomationOffTimerNumber,
    EltakoDeviceSettingNumber,
)
from custom_components.eltako_ip.select import (
    EltakoDeviceSettingSelect,
    EltakoEnOceanOrientationSelect,
    EltakoRepeaterSelect,
    EltakoUpdateScheduleSelect,
    EltakoWiredInputModeSelect,
)
from custom_components.eltako_ip.sensor import (
    EltakoAutomationsCountSensor,
    EltakoCharacteristicSensor,
    EltakoEnOceanRssiSensor,
    EltakoFreeEurIdsSensor,
    EltakoMatterBridgedCountSensor,
)
from custom_components.eltako_ip.switch import (
    EltakoAutoUpdateSwitch,
    EltakoMatterExposureSwitch,
    EltakoRelaySwitch,
)
from custom_components.eltako_ip.update import EltakoFirmwareUpdateEntity


@pytest.fixture
def mock_coordinator():
    """Build a mock EltakoDataUpdateCoordinator covering all 6 roadmap phases."""
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
        functions=[Characteristic(identifier="relay", type="enumeration", value="on")],
        infos=[Characteristic(identifier="power", type="number", value=42.5)],
    )

    input_dev = Device(
        device_guid="22222222-2222-2222-2222-222222222222",
        product_guid="6f6d379f-4c6f-45ed-b881-671ed7ea8970",
        display_name="ELTAKO-Wired input",
        functions=[
            Characteristic(identifier="input", type="enumeration", value="opened")
        ],
    )

    contact_dev = Device(
        device_guid="33333333-3333-3333-3333-333333333333",
        product_guid="791a7c28-22e3-4fab-8ecc-0084e15396c5",
        display_name="window",
        infos=[
            Characteristic(identifier="contact", type="enumeration", value="opened"),
            Characteristic(
                identifier="connectionStatus", type="enumeration", value="online"
            ),
        ],
    )

    dimmer_dev = Device(
        device_guid="55555555-5555-5555-5555-555555555555",
        product_guid="b7580625-4e9f-473b-afe4-29e0c073744a",
        display_name="Living Room Dimmer",
        functions=[
            Characteristic(identifier="targetBrightness", type="number", value=50),
            Characteristic(identifier="lastBrightness", type="number", value=80),
        ],
        infos=[
            Characteristic(identifier="currentBrightness", type="number", value=50),
        ],
        settings=[
            Characteristic(
                identifier="edgeMode", type="enumeration", value="trailingEdge"
            ),
            Characteristic(identifier="minimumBrightness", type="number", value=10),
        ],
    )

    cover_dev = Device(
        device_guid="66666666-6666-6666-6666-666666666666",
        product_guid="2b046bb5-6bcd-4d41-9c5c-01bac63ebc1d",
        display_name="Bedroom Blind",
        functions=[
            Characteristic(identifier="targetPosition", type="number", value=25),
            Characteristic(identifier="targetTilt", type="number", value=10),
        ],
        infos=[
            Characteristic(identifier="currentPosition", type="number", value=25),
            Characteristic(identifier="currentTilt", type="number", value=10),
        ],
        settings=[
            Characteristic(identifier="enableTilt", type="enumeration", value="enabled"),
            Characteristic(identifier="runtime", type="number", value=30),
        ],
    )

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
        orientation="clockwise90",
        last_seen="2026-11-08T12:00:00Z",
    )

    matter_dev = MatterDevice(
        service_device_guid="77777777-7777-7777-7777-777777777777",
        device_guid="11111111-1111-1111-1111-111111111111",
        product_guid="4893e06b-448c-40d5-b426-42e2e6b73656",
    )

    auto_rule = AutomationRule(
        automation_guid="88888888-8888-8888-8888-888888888888",
        active=True,
        input_device_guid="22222222-2222-2222-2222-222222222222",
        input_characteristic_identifier="input",
        output_device_guid="11111111-1111-1111-1111-111111111111",
        output_characteristic_identifier="relay",
        logic="buttonImpulseSwitch",
        addons=[AutomationAddOn(type="offTimer", time=10000)],
    )

    data = EltakoData(
        system=system,
        devices={
            relay_dev.device_guid: relay_dev,
            input_dev.device_guid: input_dev,
            contact_dev.device_guid: contact_dev,
            dimmer_dev.device_guid: dimmer_dev,
            cover_dev.device_guid: cover_dev,
        },
        enocean_status=eo_status,
        enocean_devices={contact_dev.device_guid: eo_dev},
        matter_devices=[matter_dev],
        enocean_config={"repeaterLevel": "oneLevel", "repeaterMode": "on"},
        update_config=UpdateConfig(
            update_server_uri="update.eltako.com",
            auto_update=False,
            update_schedule="12h",
        ),
        firmware_info=FirmwareUpdateInfo(
            current_version="2.5.0",
            desired_version="0.0.0",
            location="http://update.eltako.com:80",
            certificate="SECRET_CERT",
            thumbprint="SECRET_THUMBPRINT",
        ),
        automations=[auto_rule],
    )

    coordinator = MagicMock()
    coordinator.data = data
    coordinator.system_info = system
    coordinator.client = MagicMock()
    coordinator.client.set_relay = AsyncMock(return_value=True)
    coordinator.client.set_brightness = AsyncMock(return_value=True)
    coordinator.client.set_cover_position = AsyncMock(return_value=True)
    coordinator.client.set_cover_tilt = AsyncMock(return_value=True)
    coordinator.client.set_setting = AsyncMock(return_value=True)
    coordinator.client.set_enocean_repeater = AsyncMock()
    coordinator.client.set_enocean_device_config = AsyncMock(return_value=True)
    coordinator.client.start_enocean_scan = AsyncMock()
    coordinator.client.delete_enocean_device = AsyncMock(return_value=True)
    coordinator.client.delete_device = AsyncMock(return_value=True)
    coordinator.client.identify = AsyncMock(return_value=True)
    coordinator.client.expose_matter_device = AsyncMock(return_value={})
    coordinator.client.remove_matter_device = AsyncMock(return_value=True)
    coordinator.client.set_update_config = AsyncMock(return_value=True)
    coordinator.client.set_automation_logic = AsyncMock(return_value=True)
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_switch_entity(mock_coordinator):
    """Test ESR64PF relay switch entity."""
    switch = EltakoRelaySwitch(
        mock_coordinator, "11111111-1111-1111-1111-111111111111"
    )
    assert switch.is_on is True
    assert switch.unique_id == "11111111-1111-1111-1111-111111111111_relay"
    assert switch.name == "Relay"
    assert switch.device_info["manufacturer"] == "Eltako"
    assert switch.device_info["model"] == "ELTAKO-ESR64PF-IPM"

    await switch.async_turn_off()
    mock_coordinator.client.set_relay.assert_called_with(
        "11111111-1111-1111-1111-111111111111", False
    )

    await switch.async_turn_on()
    mock_coordinator.client.set_relay.assert_called_with(
        "11111111-1111-1111-1111-111111111111", True
    )


def test_binary_sensors(mock_coordinator):
    """Test FTK solar contact sensor and wired input entities."""
    contact = EltakoContactBinarySensor(
        mock_coordinator, "33333333-3333-3333-3333-333333333333"
    )
    assert contact.is_on is True
    assert contact.device_class == BinarySensorDeviceClass.WINDOW
    assert contact.unique_id == "33333333-3333-3333-3333-333333333333_contact"

    conn = EltakoConnectivityBinarySensor(
        mock_coordinator, "33333333-3333-3333-3333-333333333333"
    )
    assert conn.is_on is True
    assert conn.device_class == BinarySensorDeviceClass.CONNECTIVITY

    wired_in = EltakoWiredInputBinarySensor(
        mock_coordinator, "22222222-2222-2222-2222-222222222222"
    )
    assert wired_in.is_on is True
    assert wired_in.device_class == BinarySensorDeviceClass.OPENING
    assert wired_in.device_info["identifiers"] == {
        ("eltako_ip", "22222222-2222-2222-2222-222222222222")
    }
    assert wired_in.device_info["name"] == "ELTAKO-Wired input"
    assert wired_in.device_info["model"] == "Wired Input"
    assert wired_in.device_info["via_device"] == ("eltako_ip", "ELTAKO-0000000000")


def test_diagnostic_and_characteristic_sensors(mock_coordinator):
    """Test EnOcean RSSI, capacity slots, Matter bridged count, automations count, and power sensor."""
    rssi = EltakoEnOceanRssiSensor(
        mock_coordinator, "33333333-3333-3333-3333-333333333333"
    )
    assert rssi.native_value == -60
    assert rssi.device_class == SensorDeviceClass.SIGNAL_STRENGTH
    assert rssi.native_unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT

    free_slots = EltakoFreeEurIdsSensor(mock_coordinator)
    assert free_slots.native_value == 127
    assert free_slots.extra_state_attributes["max_eur_ids"] == 128
    assert free_slots.extra_state_attributes["health"] == "ok"

    matter_count = EltakoMatterBridgedCountSensor(mock_coordinator)
    assert matter_count.native_value == 1
    assert len(matter_count.extra_state_attributes["endpoints"]) == 1

    auto_count = EltakoAutomationsCountSensor(mock_coordinator)
    assert auto_count.native_value == 1
    assert auto_count.extra_state_attributes["total_rules"] == 1

    power_sensor = EltakoCharacteristicSensor(
        mock_coordinator, "11111111-1111-1111-1111-111111111111", "power"
    )
    assert power_sensor.native_value == 42.5


@pytest.mark.asyncio
async def test_repeater_select_and_buttons(mock_coordinator):
    """Test EnOcean repeater level selector, identify button, and unpair button."""
    repeater = EltakoRepeaterSelect(mock_coordinator)
    assert repeater.current_option == "oneLevel"
    await repeater.async_select_option("twoLevel")
    mock_coordinator.client.set_enocean_repeater.assert_called_with(
        repeater_level="twoLevel"
    )

    id_button = EltakoIdentifyButton(mock_coordinator)
    await id_button.async_press()
    mock_coordinator.client.identify.assert_called_once()

    from unittest.mock import patch
    from aioeltako_ip import DeviceNotFoundError

    unpair_button = EltakoUnpairEnOceanDeviceButton(
        mock_coordinator, "33333333-3333-3333-3333-333333333333"
    )
    unpair_button.hass = MagicMock()
    mock_dev_reg = MagicMock()
    mock_ha_dev = MagicMock()
    mock_ha_dev.id = "ha_device_id_3333"
    mock_dev_reg.async_get_device.side_effect = (
        lambda identifiers: mock_ha_dev
        if ("eltako_ip", "33333333-3333-3333-3333-333333333333") in identifiers
        else None
    )

    with patch("custom_components.eltako_ip.button.dr.async_get", return_value=mock_dev_reg):
        await unpair_button.async_press()
        mock_coordinator.client.delete_enocean_device.assert_called_with(
            "44444444-4444-4444-4444-444444444444"
        )
        mock_coordinator.client.delete_device.assert_called_with(
            "33333333-3333-3333-3333-333333333333"
        )
        mock_dev_reg.async_remove_device.assert_called_once_with("ha_device_id_3333")

        # Second press when already deleted on gateway (404) should not raise an error
        mock_coordinator.client.delete_enocean_device.side_effect = DeviceNotFoundError(
            "Endpoint or resource not found (404)"
        )
        await unpair_button.async_press()


@pytest.mark.asyncio
async def test_phase1_and_phase5_wired_input_mode_and_off_timer(mock_coordinator):
    """Test Wired Input Mode select (Taster vs Kippschalter) and Off-Timer number."""
    mode_select = EltakoWiredInputModeSelect(
        mock_coordinator, "22222222-2222-2222-2222-222222222222", "input"
    )
    assert mode_select.current_option == "buttonImpulseSwitch"
    await mode_select.async_select_option("buttonSwitch")
    mock_coordinator.client.set_automation_logic.assert_called_once()

    timer_num = EltakoAutomationOffTimerNumber(
        mock_coordinator,
        "22222222-2222-2222-2222-222222222222",
        "88888888-8888-8888-8888-888888888888",
        "input",
    )
    assert timer_num.native_value == 10.0
    await timer_num.async_set_native_value(25.0)
    mock_coordinator.client.set_automation_logic.assert_called_with(
        mock_coordinator.data.automations[0],
        logic="buttonImpulseSwitch",
        off_timer_ms=25000,
    )


@pytest.mark.asyncio
async def test_phase3_matter_exposure_switch(mock_coordinator):
    """Test per-device Matter Bridge Exposure switch."""
    relay_matter = EltakoMatterExposureSwitch(
        mock_coordinator, "11111111-1111-1111-1111-111111111111"
    )
    assert relay_matter.is_on is True
    await relay_matter.async_turn_off()
    mock_coordinator.client.remove_matter_device.assert_called_with(
        "77777777-7777-7777-7777-777777777777"
    )

    contact_matter = EltakoMatterExposureSwitch(
        mock_coordinator, "33333333-3333-3333-3333-333333333333"
    )
    assert contact_matter.is_on is False
    await contact_matter.async_turn_on()
    mock_coordinator.client.expose_matter_device.assert_called_with(
        product_guid="791a7c28-22e3-4fab-8ecc-0084e15396c5",
        device_guid="33333333-3333-3333-3333-333333333333",
    )


@pytest.mark.asyncio
async def test_phase4_firmware_update_entities(mock_coordinator):
    """Test Firmware Update entity, Auto-Update switch, and Update Schedule select."""
    fw_entity = EltakoFirmwareUpdateEntity(mock_coordinator)
    assert fw_entity.installed_version == "2.5.0"
    assert fw_entity.latest_version == "2.5.0"
    assert fw_entity.extra_state_attributes["update_server_uri"] == "update.eltako.com"

    auto_upd = EltakoAutoUpdateSwitch(mock_coordinator)
    assert auto_upd.is_on is False
    await auto_upd.async_turn_on()
    mock_coordinator.client.set_update_config.assert_called_with(auto_update=True)

    sched = EltakoUpdateScheduleSelect(mock_coordinator)
    assert sched.current_option == "12h"
    await sched.async_select_option("24h")
    mock_coordinator.client.set_update_config.assert_called_with(update_schedule="24h")


@pytest.mark.asyncio
async def test_phase6_dimmer_cover_and_settings(mock_coordinator):
    """Test Dimmer light, Cover blind, and dynamic device setting entities."""
    dimmer = EltakoDimmerLight(
        mock_coordinator, "55555555-5555-5555-5555-555555555555"
    )
    assert dimmer.is_on is True
    assert dimmer.brightness == 128
    await dimmer.async_turn_on(brightness=255)
    mock_coordinator.client.set_brightness.assert_called_with(
        "55555555-5555-5555-5555-555555555555", 100
    )
    await dimmer.async_turn_off()
    mock_coordinator.client.set_brightness.assert_called_with(
        "55555555-5555-5555-5555-555555555555", 0
    )

    cover = EltakoCover(
        mock_coordinator, "66666666-6666-6666-6666-666666666666"
    )
    assert cover.current_cover_position == 75
    assert cover.current_cover_tilt_position == 90
    assert cover.is_closed is False
    assert cover.supported_features & CoverEntityFeature.SET_TILT_POSITION
    await cover.async_close_cover()
    mock_coordinator.client.set_cover_position.assert_called_with(
        "66666666-6666-6666-6666-666666666666", 100
    )

    edge_select = EltakoDeviceSettingSelect(
        mock_coordinator,
        "55555555-5555-5555-5555-555555555555",
        "edgeMode",
        ["auto", "leadingEdge", "trailingEdge"],
    )
    assert edge_select.current_option == "trailingEdge"
    await edge_select.async_select_option("leadingEdge")
    mock_coordinator.client.set_setting.assert_called_with(
        "55555555-5555-5555-5555-555555555555",
        "edgeMode",
        "leadingEdge",
        char_type="enumeration",
    )

    min_br_num = EltakoDeviceSettingNumber(
        mock_coordinator,
        "55555555-5555-5555-5555-555555555555",
        "minimumBrightness",
    )
    assert min_br_num.native_value == 10.0
    await min_br_num.async_set_native_value(15.0)
    mock_coordinator.client.set_setting.assert_called_with(
        "55555555-5555-5555-5555-555555555555",
        "minimumBrightness",
        15,
        char_type="number",
    )

    orient_select = EltakoEnOceanOrientationSelect(
        mock_coordinator, "33333333-3333-3333-3333-333333333333"
    )
    assert orient_select.current_option == "clockwise90"
    await orient_select.async_select_option("clockwise180")
    mock_coordinator.client.set_enocean_device_config.assert_called_with(
        service_device_guid="44444444-4444-4444-4444-444444444444",
        orientation="clockwise180",
    )


@pytest.mark.asyncio
async def test_diagnostics(mock_coordinator):
    """Test diagnostics platform returns sanitized data with redacted secrets."""
    from custom_components.eltako_ip.const import DOMAIN
    from custom_components.eltako_ip.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.runtime_data = None
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
    assert len(diag["devices"]) == 5
    assert diag["enocean_devices"][0]["eur_id"] == "**REDACTED**"
    assert diag["firmware_info"]["certificate"] == "**REDACTED**"
    assert diag["firmware_info"]["thumbprint"] == "**REDACTED**"
    assert len(diag["automations"]) == 1


@pytest.mark.asyncio
async def test_zeroconf_autodiscovery_flow():
    """Test Zeroconf (_eltako._tcp.local.) autodiscovery step in EltakoConfigFlow."""
    from ipaddress import ip_address
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
    from custom_components.eltako_ip.config_flow import EltakoConfigFlow

    flow = EltakoConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()

    discovery_info = ZeroconfServiceInfo(
        ip_address=ip_address("192.0.2.1"),
        ip_addresses=[ip_address("192.0.2.1")],
        port=443,
        hostname="eltako-0000000000.local.",
        type="_eltako._tcp.local.",
        name="C8F5D6000000._eltako._tcp.local.",
        properties={
            "pn": "ELTAKO-ESR64PF-IPM",
            "sn": "0000000000",
            "md": "ESR64PF-IPM",
        },
    )

    result = await flow.async_step_zeroconf(discovery_info)
    assert result["type"] == "form"
    assert result["step_id"] == "discovery_confirm"
    flow.async_set_unique_id.assert_called_once_with("0000000000")
    assert flow.context["title_placeholders"]["name"] == "ELTAKO-ESR64PF-IPM (0000000000)"

    # Verify that if an existing entry uses a hostname, Zeroconf does not overwrite CONF_HOST with an IP
    existing_entry = MagicMock()
    existing_entry.unique_id = "0000000000"
    existing_entry.data = {"host": "eltako-0000000000.local", "port": 443}
    flow.hass.config_entries.async_entries.return_value = [existing_entry]

    updates = flow._build_discovery_host_updates("0000000000", "192.0.2.1", 443)
    assert updates == {"port": 443}


def test_matter_cross_integration_device_identifiers(mock_coordinator):
    """Test linking Eltako IP devices with Matter devices via shared Device Registry identifiers."""
    from unittest.mock import patch
    from custom_components.eltako_ip.coordinator import EltakoDataUpdateCoordinator

    # Attach the real methods from EltakoDataUpdateCoordinator onto mock_coordinator
    mock_coordinator.hass = MagicMock()
    mock_coordinator.get_matter_node_prefix = (
        lambda: EltakoDataUpdateCoordinator.get_matter_node_prefix(mock_coordinator)
    )
    mock_coordinator.get_device_identifiers = (
        lambda device_guid=None, *, is_gateway=False, data=None: (
            EltakoDataUpdateCoordinator.get_device_identifiers(
                mock_coordinator,
                device_guid,
                is_gateway=is_gateway,
                data=data,
            )
        )
    )

    # Simulate Matter bridge device and bridged endpoints in HA Device Registry
    mock_coordinator.data.matter_devices = [
        MatterDevice(
            service_device_guid="77777777-7777-7777-7777-777777777777",
            device_guid="11111111-1111-1111-1111-111111111111",
            product_guid="4893e06b-448c-40d5-b426-42e2e6b73656",
            endpoint_id=10,
        ),
        MatterDevice(
            service_device_guid="99999999-9999-9999-9999-999999999999",
            device_guid="33333333-3333-3333-3333-333333333333",
            product_guid="791a7c28-22e3-4fab-8ecc-0084e15396c5",
            endpoint_id=24,
        ),
    ]

    matter_bridge_entry = MagicMock()
    matter_bridge_entry.identifiers = {
        ("matter", "deviceid_142B913B69BC56B2-0000000000000017-MatterNodeDevice"),
        ("matter", "serial_ELTAKO-0000000000"),
    }
    mock_dev_reg = MagicMock()
    mock_dev_reg.async_get_devices.return_value = [matter_bridge_entry]

    with patch(
        "custom_components.eltako_ip.coordinator.dr.async_get",
        return_value=mock_dev_reg,
    ):
        gw_ids = mock_coordinator.get_device_identifiers(is_gateway=True)
        assert gw_ids == {
            ("eltako_ip", "ELTAKO-0000000000"),
            ("eltako_ip", "11111111-1111-1111-1111-111111111111"),
            ("matter", "serial_ELTAKO-0000000000"),
            ("matter", "deviceid_142B913B69BC56B2-0000000000000017-10"),
        }

        ftk_ids = mock_coordinator.get_device_identifiers(
            "33333333-3333-3333-3333-333333333333", is_gateway=False
        )
        assert ftk_ids == {
            ("eltako_ip", "33333333-3333-3333-3333-333333333333"),
            ("matter", "deviceid_142B913B69BC56B2-0000000000000017-24"),
        }


