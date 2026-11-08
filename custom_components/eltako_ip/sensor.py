"""Sensor platform for Eltako Series 62/64 IP."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    LIGHT_LUX,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfRatio,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoDeviceEntity, EltakoGatewayEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)

# Metadata for dynamic telemetry characteristics from /products
SENSOR_CHAR_META: dict[str, dict[str, Any]] = {
    "power": {
        "name": "Power",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "powerChannel1": {
        "name": "Power Channel 1",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "powerChannel2": {
        "name": "Power Channel 2",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "powerMeter": {
        "name": "Power Meter",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "electricEnergyMeter": {
        "name": "Energy",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    "temperature": {
        "name": "Temperature",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
    },
    "humidity": {
        "name": "Humidity",
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
    },
    "illumination": {
        "name": "Illuminance",
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": LIGHT_LUX,
    },
    "co2": {
        "name": "Carbon Dioxide",
        "device_class": SensorDeviceClass.CO2,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfRatio.PARTS_PER_MILLION,
    },
    "tvoc": {
        "name": "Volatile Organic Compounds",
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfRatio.PARTS_PER_BILLION,
    },
    "batteryPercentageRemaining": {
        "name": "Battery",
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "category": EntityCategory.DIAGNOSTIC,
    },
    "batteryVoltage": {
        "name": "Battery Voltage",
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricPotential.VOLT,
        "category": EntityCategory.DIAGNOSTIC,
    },
    "supplyVoltage": {
        "name": "Supply Voltage",
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricPotential.VOLT,
        "category": EntityCategory.DIAGNOSTIC,
    },
    "windSpeed": {
        "name": "Wind Speed",
        "device_class": SensorDeviceClass.WIND_SPEED,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfSpeed.METERS_PER_SECOND,
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako sensors."""
    coordinator = get_coordinator(hass, entry)

    entities: list[SensorEntity] = [
        EltakoFreeEurIdsSensor(coordinator),
        EltakoAutomationsCountSensor(coordinator),
    ]
    if coordinator.data.matter_supported:
        entities.append(EltakoMatterBridgedCountSensor(coordinator))

    # Signal strength (RSSI) sensor for each paired EnOcean device
    for eo_dev in coordinator.data.enocean_devices.values():
        target_guid = eo_dev.device_guid or eo_dev.service_device_guid
        entities.append(EltakoEnOceanRssiSensor(coordinator, target_guid))

    # Dynamic characteristic sensors for power, energy, temperature, humidity, etc.
    for device in coordinator.data.devices.values():
        seen_ids: set[str] = set()
        for char in (*device.infos, *device.functions):
            if char.identifier in SENSOR_CHAR_META and char.identifier not in seen_ids:
                seen_ids.add(char.identifier)
                entities.append(
                    EltakoCharacteristicSensor(
                        coordinator, device.device_guid, char.identifier
                    )
                )

    async_add_entities(entities)


class EltakoEnOceanRssiSensor(EltakoDeviceEntity, SensorEntity):
    """EnOcean signal strength (RSSI) sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "signal_strength"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        """Initialize the RSSI sensor."""
        super().__init__(coordinator, device_guid)
        self._attr_unique_id = f"{device_guid}_rssi"
        self._attr_name = "Signal Strength"

    @property
    def native_value(self) -> Optional[int]:
        """Return the current RSSI in dBm."""
        eo_dev = self.coordinator.data.enocean_devices.get(self._device_guid)
        if eo_dev and eo_dev.signal_strength is not None:
            return eo_dev.signal_strength
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return EnOcean metadata for the device."""
        eo_dev = self.coordinator.data.enocean_devices.get(self._device_guid)
        if not eo_dev:
            return {}
        return {
            "service_device_guid": eo_dev.service_device_guid,
            "last_seen": eo_dev.last_seen,
            "bridge_direction": eo_dev.bridge_direction,
            "orientation": eo_dev.orientation,
        }


class EltakoFreeEurIdsSensor(EltakoGatewayEntity, SensorEntity):
    """Available EnOcean radio address slots on the transceiver."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "free_eur_ids"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        """Initialize the free EURIDs sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_free_eur_ids"
        self._attr_name = "EnOcean Free Slots"

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


class EltakoMatterBridgedCountSensor(EltakoGatewayEntity, SensorEntity):
    """Diagnostic sensor reporting the number of devices exposed to the Matter bridge."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:bridge"
    _attr_translation_key = "matter_bridged_devices"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        """Initialize the Matter bridged devices count sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_matter_devices"
        self._attr_name = "Matter Bridged Devices"

    @property
    def native_value(self) -> int:
        """Return the number of bridged Matter endpoints."""
        return len(self.coordinator.data.matter_devices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of bridged Matter endpoints."""
        endpoints = []
        for m_dev in self.coordinator.data.matter_devices:
            dev = (
                self.coordinator.data.devices.get(m_dev.device_guid)
                if m_dev.device_guid
                else None
            )
            endpoints.append(
                {
                    "service_device_guid": m_dev.service_device_guid,
                    "device_guid": m_dev.device_guid,
                    "product_guid": m_dev.product_guid,
                    "display_name": dev.display_name if dev else None,
                }
            )
        return {"endpoints": endpoints}


class EltakoAutomationsCountSensor(EltakoGatewayEntity, SensorEntity):
    """Diagnostic sensor reporting the number of active on-device hardware automations."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:script-text-outline"
    _attr_translation_key = "active_automations"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        """Initialize the active automations count sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_automations"
        self._attr_name = "On-Device Automations"

    @property
    def native_value(self) -> int:
        """Return the count of active on-device automations."""
        return sum(1 for r in self.coordinator.data.automations if r.active)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return summary of on-device automation rules."""
        return {
            "total_rules": len(self.coordinator.data.automations),
            "rules": [
                {
                    "automation_guid": r.automation_guid,
                    "active": r.active,
                    "logic": r.logic,
                    "input_device_guid": r.input_device_guid,
                    "input_characteristic": r.input_characteristic_identifier,
                    "output_device_guid": r.output_device_guid,
                    "output_characteristic": r.output_characteristic_identifier,
                    "off_timer_ms": r.off_timer_ms,
                }
                for r in self.coordinator.data.automations
            ],
        }


class EltakoCharacteristicSensor(EltakoDeviceEntity, SensorEntity):
    """Dynamic sensor for numeric device characteristics (power, energy, temperature, etc.)."""

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        identifier: str,
    ) -> None:
        """Initialize the characteristic sensor."""
        super().__init__(coordinator, device_guid)
        self._identifier = identifier
        meta = SENSOR_CHAR_META.get(identifier, {})
        self._attr_unique_id = f"{device_guid}_{identifier}"
        self._attr_name = meta.get("name", identifier)
        self._attr_device_class = meta.get("device_class")
        self._attr_state_class = meta.get("state_class")
        self._attr_native_unit_of_measurement = meta.get("unit")
        if "category" in meta:
            self._attr_entity_category = meta["category"]
        self._attr_translation_key = f"sensor_{identifier}"

    @property
    def native_value(self) -> Optional[float | int]:
        """Return the current value of the characteristic."""
        dev = self._device
        if not dev:
            return None
        val = dev.get_info_value(self._identifier)
        if val is None:
            val = dev.get_function_value(self._identifier)
        if val is None:
            return None
        try:
            num = float(val)
            return int(num) if num.is_integer() else num
        except (TypeError, ValueError):
            return None
