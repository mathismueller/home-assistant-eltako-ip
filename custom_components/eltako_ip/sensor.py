"""Sensor platform for Eltako Series 62/64 IP."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRODUCT_FTK_CONTACT
from .coordinator import EltakoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako sensors."""
    coordinator: EltakoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        EltakoFreeEurIdsSensor(coordinator),
    ]

    # Signal strength (RSSI) sensor for each paired EnOcean device
    for eo_dev in coordinator.data.enocean_devices.values():
        entities.append(EltakoEnOceanRssiSensor(coordinator, eo_dev.device_guid))

    async_add_entities(entities)


class EltakoEnOceanRssiSensor(CoordinatorEntity[EltakoDataUpdateCoordinator], SensorEntity):
    """EnOcean signal strength (RSSI) sensor."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EltakoDataUpdateCoordinator, device_guid: str) -> None:
        super().__init__(coordinator)
        self._device_guid = device_guid
        self._attr_unique_id = f"{device_guid}_rssi"
        self._attr_name = "Signal Strength"

    @property
    def device_info(self) -> DeviceInfo:
        device = self.coordinator.data.devices.get(self._device_guid)
        name = device.display_name if device else "Eltako Sensor"
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_guid)},
            name=name,
            manufacturer="Eltako",
            via_device=(DOMAIN, self.coordinator.system_info.serial_number),
        )

    @property
    def native_value(self) -> int | None:
        """Return the current RSSI in dBm."""
        eo_dev = self.coordinator.data.enocean_devices.get(self._device_guid)
        if eo_dev and eo_dev.signal_strength is not None:
            return eo_dev.signal_strength
        return None


class EltakoFreeEurIdsSensor(CoordinatorEntity[EltakoDataUpdateCoordinator], SensorEntity):
    """Available EnOcean radio address slots on the transceiver."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_free_eur_ids"
        self._attr_name = "EnOcean Free Slots"

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
    def native_value(self) -> int:
        """Return free EURID slots."""
        return self.coordinator.data.enocean_status.free_eur_ids

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra details."""
        status = self.coordinator.data.enocean_status
        return {
            "max_eur_ids": status.max_eur_ids,
            "health": status.health,
            "filter_state": status.hardware_filter_state,
        }
