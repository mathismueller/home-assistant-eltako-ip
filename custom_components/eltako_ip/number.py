"""Number platform for Eltako Series 62/64 IP."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from aioeltako_ip import AutomationRule

from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoDeviceEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)

# Metadata fallback for numeric settings when /products is not loaded
NUMERIC_SETTING_META: dict[str, dict[str, Any]] = {
    "minimumBrightness": {
        "name": "Minimum Brightness",
        "min": 1.0,
        "max": 45.0,
        "step": 1.0,
        "unit": PERCENTAGE,
    },
    "maximumBrightness": {
        "name": "Maximum Brightness",
        "min": 55.0,
        "max": 100.0,
        "step": 1.0,
        "unit": PERCENTAGE,
    },
    "runtime": {
        "name": "Shutter Runtime",
        "min": 1.0,
        "max": 300.0,
        "step": 1.0,
        "unit": UnitOfTime.SECONDS,
    },
    "offset": {
        "name": "Start Delay Offset",
        "min": 0.0,
        "max": 10.0,
        "step": 0.1,
        "unit": UnitOfTime.SECONDS,
    },
    "tiltRuntime": {
        "name": "Slat Tilt Runtime",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
        "unit": UnitOfTime.SECONDS,
    },
    "temperatureOffset": {
        "name": "Temperature Offset",
        "min": -5.0,
        "max": 5.0,
        "step": 0.1,
        "unit": UnitOfTemperature.CELSIUS,
    },
    "humidityOffset": {
        "name": "Humidity Offset",
        "min": -10.0,
        "max": 10.0,
        "step": 1.0,
        "unit": PERCENTAGE,
    },
    "minimumHeatTargetTemperature": {
        "name": "Minimum Target Temperature",
        "min": 5.0,
        "max": 20.0,
        "step": 0.5,
        "unit": UnitOfTemperature.CELSIUS,
    },
    "maximumHeatTargetTemperature": {
        "name": "Maximum Target Temperature",
        "min": 20.0,
        "max": 35.0,
        "step": 0.5,
        "unit": UnitOfTemperature.CELSIUS,
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako number entities."""
    coordinator = get_coordinator(hass, entry)
    entities: list[NumberEntity] = []

    # 1. Dynamic numeric device settings (dimmer min/max brightness, shutter runtime, etc.)
    for device in coordinator.data.devices.values():
        for setting in device.settings:
            if setting.type == "number" or setting.identifier in NUMERIC_SETTING_META:
                entities.append(
                    EltakoDeviceSettingNumber(
                        coordinator,
                        device.device_guid,
                        setting.identifier,
                    )
                )

    # 2. On-device automation off-timer numbers (e.g. wired input -> relay offTimer in seconds)
    for rule in coordinator.data.automations:
        if rule.input_device_guid in coordinator.data.devices:
            entities.append(
                EltakoAutomationOffTimerNumber(
                    coordinator,
                    rule.input_device_guid,
                    rule.automation_guid,
                    rule.input_characteristic_identifier,
                )
            )

    async_add_entities(entities)


class EltakoDeviceSettingNumber(EltakoDeviceEntity, NumberEntity):
    """Numeric configuration setting for an Eltako device (dimmer, cover, thermostat)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        setting_identifier: str,
    ) -> None:
        """Initialize the device setting number entity."""
        super().__init__(coordinator, device_guid)
        self._setting_identifier = setting_identifier
        self._attr_unique_id = f"{device_guid}_setting_{setting_identifier}"
        self._attr_translation_key = f"setting_{setting_identifier}"

        meta = NUMERIC_SETTING_META.get(setting_identifier, {})
        self._attr_name = meta.get("name", setting_identifier)
        self._attr_native_min_value = float(meta.get("min", 0.0))
        self._attr_native_max_value = float(meta.get("max", 100.0))
        self._attr_native_step = float(meta.get("step", 1.0))
        if "unit" in meta:
            self._attr_native_unit_of_measurement = meta["unit"]

        # Refine limits from /products specification if available
        dev = self._device
        if dev:
            spec = coordinator.data.products.get(dev.product_guid)
            if spec:
                for s_spec in spec.settings:
                    if s_spec.identifier == setting_identifier:
                        if s_spec.minimum is not None:
                            self._attr_native_min_value = float(s_spec.minimum)
                        if s_spec.maximum is not None:
                            self._attr_native_max_value = float(s_spec.maximum)
                        break

    @property
    def native_value(self) -> Optional[float]:
        """Return the current numeric setting value."""
        dev = self._device
        if not dev:
            return None
        val = dev.get_setting_value(self._setting_identifier)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the numeric setting on the device."""
        # Preserve integer representation when step is an integer
        send_val: float | int = (
            int(round(value)) if self._attr_native_step >= 1.0 else value
        )
        await self._async_execute(
            self.coordinator.client.set_setting(
                self._device_guid,
                self._setting_identifier,
                send_val,
                char_type="number",
            )
        )


class EltakoAutomationOffTimerNumber(EltakoDeviceEntity, NumberEntity):
    """Configures the hardware off-timer (in seconds) for an on-device automation rule."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0.0
    _attr_native_max_value = 36000.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_translation_key = "automation_off_timer"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        input_device_guid: str,
        automation_guid: str,
        input_identifier: str = "input",
    ) -> None:
        """Initialize the automation off-timer number entity."""
        super().__init__(coordinator, input_device_guid)
        self._automation_guid = automation_guid
        self._input_identifier = input_identifier
        self._attr_unique_id = f"{input_device_guid}_{automation_guid}_off_timer"
        if input_identifier == "input":
            self._attr_name = "Wired Input Off-Timer"
        else:
            self._attr_name = f"Wired Input ({input_identifier}) Off-Timer"

    @property
    def _rule(self) -> Optional[AutomationRule]:
        for rule in self.coordinator.data.automations:
            if rule.automation_guid == self._automation_guid:
                return rule
        return self.coordinator.data.get_automation_for_input(
            self._device_guid, self._input_identifier
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator is available and the active logic supports offTimer."""
        if not super().available:
            return False
        rule = self._rule
        if not rule:
            return False
        return rule.logic != "buttonSwitch"

    @property
    def native_value(self) -> Optional[float]:
        """Return the current off-timer in seconds (0 if disabled)."""
        rule = self._rule
        if not rule:
            return None
        if rule.off_timer_ms is None or rule.off_timer_ms <= 0:
            return 0.0
        return round(rule.off_timer_ms / 1000.0, 2)

    async def async_set_native_value(self, value: float) -> None:
        """Update the off-timer (in seconds) on the on-device automation rule."""
        rule = self._rule
        if not rule:
            return
        if rule.logic == "buttonSwitch" and value > 0:
            raise HomeAssistantError(
                "Off-timer is not supported when Wired Input Mode is set to buttonSwitch."
            )
        ms_val = int(round(value * 1000)) if value > 0 else 0
        await self._async_execute(
            self.coordinator.client.set_automation_logic(
                rule,
                logic=rule.logic,
                off_timer_ms=ms_val,
            )
        )
