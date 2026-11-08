"""Button platform for Eltako Series 62/64 IP actions."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EltakoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako button entities."""
    coordinator: EltakoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([EltakoStartEnOceanScanButton(coordinator)])


class EltakoStartEnOceanScanButton(CoordinatorEntity[EltakoDataUpdateCoordinator], ButtonEntity):
    """Button to start EnOcean teach-in scanning."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mode_antenna"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_start_enocean_scan"
        self._attr_name = "Start EnOcean Pairing Scan"

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

    async def async_press(self) -> None:
        """Trigger EnOcean scan mode on the device."""
        await self.coordinator.client.start_enocean_scan()
        _LOGGER.info("EnOcean pairing scan mode initiated via button")
