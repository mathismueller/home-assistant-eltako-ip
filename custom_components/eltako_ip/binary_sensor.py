"""Binary sensor platform for Eltako Series 62/64 IP."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRODUCT_FTK_CONTACT, PRODUCT_WIRED_INPUT
from .coordinator import EltakoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako binary sensors."""
    coordinator: EltakoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    for device in coordinator.data.devices.values():
        # Solar contact sensor (FTK)
        if device.product_guid == PRODUCT_FTK_CONTACT:
            if device.get_info_value("contact") is not None:
                entities.append(EltakoContactBinarySensor(coordinator, device.device_guid))
            if device.get_info_value("connectionStatus") is not None:
                entities.append(EltakoConnectivityBinarySensor(coordinator, device.device_guid))

        # Physical wired switch/input
        elif device.product_guid == PRODUCT_WIRED_INPUT:
            if device.get_function_value("input") is not None:
                entities.append(EltakoWiredInputBinarySensor(coordinator, device.device_guid))

    async_add_entities(entities)


class EltakoContactBinarySensor(CoordinatorEntity[EltakoDataUpdateCoordinator], BinarySensorEntity):
    """Solar window/door contact sensor (FTK)."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def __init__(self, coordinator: EltakoDataUpdateCoordinator, device_guid: str) -> None:
        super().__init__(coordinator)
        self._device_guid = device_guid
        self._attr_unique_id = f"{device_guid}_contact"
        self._attr_name = "Contact"

    @property
    def device_info(self) -> DeviceInfo:
        device = self.coordinator.data.devices.get(self._device_guid)
        name = device.display_name if device else "Eltako FTK"
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_guid)},
            name=name,
            manufacturer="Eltako",
            model="FTK Solar Contact Sensor",
            via_device=(DOMAIN, self.coordinator.system_info.serial_number),
        )

    @property
    def is_on(self) -> bool:
        """Return true if window/door is opened."""
        device = self.coordinator.data.devices.get(self._device_guid)
        if not device:
            return False
        return device.get_info_value("contact") == "opened"


class EltakoConnectivityBinarySensor(CoordinatorEntity[EltakoDataUpdateCoordinator], BinarySensorEntity):
    """Sensor connection status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EltakoDataUpdateCoordinator, device_guid: str) -> None:
        super().__init__(coordinator)
        self._device_guid = device_guid
        self._attr_unique_id = f"{device_guid}_connectivity"
        self._attr_name = "Connection Status"

    @property
    def device_info(self) -> DeviceInfo:
        device = self.coordinator.data.devices.get(self._device_guid)
        name = device.display_name if device else "Eltako FTK"
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_guid)},
            name=name,
            manufacturer="Eltako",
            model="FTK Solar Contact Sensor",
            via_device=(DOMAIN, self.coordinator.system_info.serial_number),
        )

    @property
    def is_on(self) -> bool:
        """Return true if sensor is online."""
        device = self.coordinator.data.devices.get(self._device_guid)
        if not device:
            return False
        return device.get_info_value("connectionStatus") == "online"


class EltakoWiredInputBinarySensor(CoordinatorEntity[EltakoDataUpdateCoordinator], BinarySensorEntity):
    """Physical wired input terminal on Series 64 actuator."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator: EltakoDataUpdateCoordinator, device_guid: str) -> None:
        super().__init__(coordinator)
        self._device_guid = device_guid
        self._attr_unique_id = f"{device_guid}_input"
        self._attr_name = "Wired Input"

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
    def is_on(self) -> bool:
        """Return true if wired input is opened."""
        device = self.coordinator.data.devices.get(self._device_guid)
        if not device:
            return False
        return device.get_function_value("input") == "opened"
