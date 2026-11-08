"""Select platform for Eltako Series 62/64 IP settings, repeater, update schedule, and input modes."""

from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from aioeltako_ip import AutomationRule

from .const import (
    DEFAULT_SETTING_ENUMS,
    ENOCEAN_ORIENTATION_OPTIONS,
    REPEATER_LEVEL_OFF,
    REPEATER_OPTIONS,
    UPDATE_SCHEDULE_12H,
    UPDATE_SCHEDULE_OPTIONS,
    WIRED_INPUT_LOGIC_OPTIONS,
)
from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoDeviceEntity, EltakoGatewayEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)

SETTING_SELECT_LABELS: dict[str, str] = {
    "edgeMode": "Dimming Edge Mode",
    "dimCurve": "Dimming Curve",
    "runtimeMode": "Calibration Runtime Mode",
    "movementDirection": "Movement Direction",
    "enableTilt": "Slat Tilt Control",
    "thermostatOperationMode": "Thermostat Operation Mode",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako select entities."""
    coordinator = get_coordinator(hass, entry)

    entities: list[SelectEntity] = [
        EltakoRepeaterSelect(coordinator),
        EltakoUpdateScheduleSelect(coordinator),
    ]

    # Phase 1 & 6: Device hardware enumeration settings (/devices/{guid}/settings)
    for device in coordinator.data.devices.values():
        prod_spec = coordinator.data.products.get(device.product_guid)
        for setting in device.settings:
            if (
                setting.type == "enumeration"
                or setting.identifier in DEFAULT_SETTING_ENUMS
            ):
                options: list[str] = []
                if prod_spec:
                    c_spec = prod_spec.get_characteristic_spec(setting.identifier)
                    if c_spec and c_spec.enumerations:
                        options = list(c_spec.enumerations)
                if not options:
                    options = list(DEFAULT_SETTING_ENUMS.get(setting.identifier, []))
                if setting.value is not None and str(setting.value) not in options:
                    options.append(str(setting.value))
                if options:
                    entities.append(
                        EltakoDeviceSettingSelect(
                            coordinator,
                            device.device_guid,
                            setting.identifier,
                            options,
                        )
                    )

    # Phase 1 & 5: On-device automation logic mode for wired inputs (Taster vs Kippschalter)
    for rule in coordinator.data.automations:
        if rule.automation_guid and rule.input_device_guid:
            entities.append(
                EltakoWiredInputModeSelect(
                    coordinator,
                    device_guid=rule.input_device_guid,
                    automation_guid=rule.automation_guid,
                )
            )

    # Phase 2: Per-device EnOcean orientation configuration
    for eo_dev in coordinator.data.enocean_devices.values():
        dev = coordinator.data.devices.get(eo_dev.device_guid)
        has_buttons = dev is not None and any(
            f.identifier.startswith("buttonChannel") for f in dev.functions
        )
        if "orientation" in eo_dev.config or eo_dev.orientation or has_buttons:
            entities.append(
                EltakoEnOceanOrientationSelect(
                    coordinator,
                    device_guid=eo_dev.device_guid or eo_dev.service_device_guid,
                    service_device_guid=eo_dev.service_device_guid,
                )
            )

    async_add_entities(entities)


class EltakoRepeaterSelect(EltakoGatewayEntity, SelectEntity):
    """EnOcean repeater level control (off, 1-level, 2-level)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = REPEATER_OPTIONS
    _attr_translation_key = "repeater_level"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_repeater_level"
        self._attr_name = "EnOcean Repeater Level"

    @property
    def current_option(self) -> str:
        """Return the current repeater level."""
        return self.coordinator.data.enocean_config.get(
            "repeaterLevel", REPEATER_LEVEL_OFF
        )

    async def async_select_option(self, option: str) -> None:
        """Set the repeater level."""
        await self._async_execute(
            self.coordinator.client.set_enocean_repeater(repeater_level=option)
        )


class EltakoUpdateScheduleSelect(EltakoGatewayEntity, SelectEntity):
    """Firmware update check schedule selector (6h, 12h, 24h) (Phase 4)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = UPDATE_SCHEDULE_OPTIONS
    _attr_icon = "mdi:clock-outline"
    _attr_translation_key = "update_schedule"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.system_info.serial_number}_update_schedule"
        )
        self._attr_name = "Update Check Schedule"

    @property
    def current_option(self) -> str:
        """Return the active update schedule."""
        sched = self.coordinator.data.update_config.update_schedule
        if sched in UPDATE_SCHEDULE_OPTIONS:
            return sched
        return UPDATE_SCHEDULE_12H

    async def async_select_option(self, option: str) -> None:
        """Update the firmware check schedule."""
        await self._async_execute(
            self.coordinator.client.set_update_config(update_schedule=option)
        )


class EltakoWiredInputModeSelect(EltakoDeviceEntity, SelectEntity):
    """Select entity to switch wired input behavior between Impulse (Taster) and Switch (Kippschalter)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:DipSwitch"
    _attr_translation_key = "wired_input_mode"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        automation_guid: str = "input",
    ) -> None:
        super().__init__(coordinator, device_guid)
        self._automation_guid = automation_guid
        self._attr_unique_id = f"{device_guid}_{automation_guid}_input_mode"
        self._attr_name = "Wired Input Mode"

    @property
    def _rule(self) -> Optional[AutomationRule]:
        for rule in self.coordinator.data.automations:
            if rule.automation_guid == self._automation_guid:
                return rule
        return self.coordinator.data.get_automation_for_input(
            self._device_guid, self._automation_guid
        )

    @property
    def options(self) -> list[str]:
        """Return available logic modes."""
        opts = list(WIRED_INPUT_LOGIC_OPTIONS)
        curr = self.current_option
        if curr and curr not in opts:
            opts.append(curr)
        return opts

    @property
    def current_option(self) -> str | None:
        """Return the current automation logic for this input."""
        rule = self._rule
        return rule.logic if rule else None

    async def async_select_option(self, option: str) -> None:
        """Update on-device automation logic mode."""
        target_rule = self._rule
        if target_rule is None:
            return
        await self._async_execute(
            self.coordinator.client.set_automation_logic(target_rule, logic=option)
        )


class EltakoDeviceSettingSelect(EltakoDeviceEntity, SelectEntity):
    """Select entity for persistent hardware enumeration settings (/devices/{guid}/settings)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        identifier: str,
        options: list[str],
    ) -> None:
        super().__init__(coordinator, device_guid)
        self._identifier = identifier
        self._attr_options = options
        self._attr_unique_id = f"{device_guid}_setting_{identifier}"
        self._attr_name = SETTING_SELECT_LABELS.get(identifier, identifier)
        self._attr_translation_key = f"setting_{identifier}"

    @property
    def current_option(self) -> str | None:
        """Return the current setting value."""
        dev = self._device
        if not dev:
            return None
        val = dev.get_setting_value(self._identifier)
        return str(val) if val is not None else None

    async def async_select_option(self, option: str) -> None:
        """Update the setting on the device."""
        await self._async_execute(
            self.coordinator.client.set_setting(
                self._device_guid,
                self._identifier,
                option,
                char_type="enumeration",
            )
        )


class EltakoEnOceanOrientationSelect(EltakoDeviceEntity, SelectEntity):
    """Select entity to configure EnOcean rocker orientation (/services/enocean/devices/{guid}/config)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = ENOCEAN_ORIENTATION_OPTIONS
    _attr_icon = "mdi:rotate-right"
    _attr_translation_key = "enocean_orientation"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        service_device_guid: Optional[str] = None,
    ) -> None:
        super().__init__(coordinator, device_guid)
        if service_device_guid is None:
            eo_dev = coordinator.data.enocean_devices.get(device_guid)
            service_device_guid = eo_dev.service_device_guid if eo_dev else device_guid
        self._service_device_guid = service_device_guid
        self._attr_unique_id = f"{device_guid}_orientation"
        self._attr_name = "Orientation"

    @property
    def current_option(self) -> str:
        """Return current EnOcean orientation."""
        eo_dev = self.coordinator.data.enocean_devices.get(self._device_guid)
        if eo_dev:
            if eo_dev.orientation:
                return eo_dev.orientation
            if "orientation" in eo_dev.config:
                return str(eo_dev.config["orientation"])
        return "auto"

    async def async_select_option(self, option: str) -> None:
        """Set EnOcean rocker orientation."""
        await self._async_execute(
            self.coordinator.client.set_enocean_device_config(
                service_device_guid=self._service_device_guid,
                orientation=option,
            )
        )
