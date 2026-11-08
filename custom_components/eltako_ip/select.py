"""Select platform for Eltako Series 62/64 IP EnOcean repeater settings."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    REPEATER_LEVEL_OFF,
    REPEATER_OPTIONS,
)
from .coordinator import EltakoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako select entities."""
    coordinator: EltakoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([EltakoRepeaterSelect(coordinator)])


class EltakoRepeaterSelect(CoordinatorEntity[EltakoDataUpdateCoordinator], SelectEntity):
    """EnOcean repeater level control (off, 1-level, 2-level)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = REPEATER_OPTIONS

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_repeater_level"
        self._attr_name = "EnOcean Repeater Level"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.system_info.serial_number)},
            name=self.coordinator.system_info.product_name,
            manufacturer="Eltako",
            model=self.coordinator.system_info.product_name,
            sw_version=self.coordinator.system_info.software_version,
            hw_version=self.coordinator.system_info.hardware_version,
        )

    @property
    def current_option(self) -> str:
        """Return the current repeater level."""
        return self.coordinator.data.enocean_config.get("repeaterLevel", REPEATER_LEVEL_OFF)

    async def async_select_option(self, option: str) -> None:
        """Set the repeater level."""
        await self.coordinator.client.set_enocean_repeater(repeater_level=option)
        await self.coordinator.async_request_refresh()
