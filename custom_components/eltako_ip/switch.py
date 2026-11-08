"""Switch platform for Eltako Series 62/64 IP relay actuators."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRODUCT_ESR64PF_IPM
from .coordinator import EltakoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako switch entities."""
    coordinator: EltakoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = []

    for device in coordinator.data.devices.values():
        if device.product_guid == PRODUCT_ESR64PF_IPM and device.get_function_value("relay") is not None:
            entities.append(EltakoRelaySwitch(coordinator, device.device_guid))

    async_add_entities(entities)


class EltakoRelaySwitch(CoordinatorEntity[EltakoDataUpdateCoordinator], SwitchEntity):
    """Representation of an ESR64PF relay switch channel."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device_guid = device_guid
        self._attr_unique_id = f"{device_guid}_relay"
        self._attr_name = "Relay"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        device = self.coordinator.data.devices.get(self._device_guid)
        name = device.display_name if device else self.coordinator.system_info.product_name
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_guid)},
            name=name,
            manufacturer="Eltako",
            model=self.coordinator.system_info.product_name,
            sw_version=self.coordinator.system_info.software_version,
            hw_version=self.coordinator.system_info.hardware_version,
        )

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        device = self.coordinator.data.devices.get(self._device_guid)
        if not device:
            return False
        return device.get_function_value("relay") == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on."""
        await self.coordinator.client.set_relay(self._device_guid, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off."""
        await self.coordinator.client.set_relay(self._device_guid, False)
        await self.coordinator.async_request_refresh()
