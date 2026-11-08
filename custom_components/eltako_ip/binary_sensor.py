"""Binary sensor platform for Eltako Series 62/64 IP."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoDeviceEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)

# Additional binary sensor characteristics from /products
BINARY_CHAR_META: dict[str, dict[str, Any]] = {
    "windowDoorContact": {
        "name": "Window/Door Contact",
        "device_class": BinarySensorDeviceClass.WINDOW,
        "on_values": {"opened", "open", True, 1},
    },
    "motionDetection": {
        "name": "Motion",
        "device_class": BinarySensorDeviceClass.MOTION,
        "on_values": {"detected", "motion", "on", True, 1},
    },
    "motionDetected": {
        "name": "Motion",
        "device_class": BinarySensorDeviceClass.MOTION,
        "on_values": {"detected", "motion", "on", True, 1},
    },
    "smokeDetection": {
        "name": "Smoke",
        "device_class": BinarySensorDeviceClass.SMOKE,
        "on_values": {"detected", "alarm", "on", True, 1},
    },
    "waterDetection": {
        "name": "Water Leak",
        "device_class": BinarySensorDeviceClass.MOISTURE,
        "on_values": {"detected", "wet", "alarm", "on", True, 1},
    },
    "rain": {
        "name": "Rain",
        "device_class": BinarySensorDeviceClass.MOISTURE,
        "on_values": {"detected", "raining", "on", True, 1},
    },
    "vibrationDetection": {
        "name": "Vibration",
        "device_class": BinarySensorDeviceClass.VIBRATION,
        "on_values": {"detected", "on", True, 1},
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako binary sensors dynamically from device characteristics."""
    coordinator = get_coordinator(hass, entry)
    entities: list[BinarySensorEntity] = []

    for device in coordinator.data.devices.values():
        # 1. Contact sensor (FTK / FFG7B / etc.)
        if (
            device.get_info_value("contact") is not None
            or device.get_function_value("contact") is not None
        ):
            entities.append(EltakoContactBinarySensor(coordinator, device.device_guid))

        # 2. Sensor connectivity status
        if device.get_info_value("connectionStatus") is not None:
            entities.append(
                EltakoConnectivityBinarySensor(coordinator, device.device_guid)
            )

        # 3. Physical wired input terminals (1-channel and 2-channel)
        if device.get_function_value("input") is not None:
            entities.append(
                EltakoWiredInputBinarySensor(coordinator, device.device_guid, "input")
            )
        for ch_id in ("inputChannel1", "inputChannel2", "inputBridged"):
            if device.get_function_value(ch_id) is not None:
                entities.append(
                    EltakoWiredInputBinarySensor(coordinator, device.device_guid, ch_id)
                )

        # 4. Additional binary characteristics in infos or functions
        seen_ids: set[str] = set()
        for char in (*device.infos, *device.functions):
            if char.identifier in BINARY_CHAR_META and char.identifier not in seen_ids:
                seen_ids.add(char.identifier)
                entities.append(
                    EltakoGenericBinarySensor(
                        coordinator, device.device_guid, char.identifier
                    )
                )

    async_add_entities(entities)


class EltakoContactBinarySensor(EltakoDeviceEntity, BinarySensorEntity):
    """Solar window/door contact sensor (FTK)."""

    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_translation_key = "contact"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        """Initialize the contact binary sensor."""
        super().__init__(coordinator, device_guid)
        self._attr_unique_id = f"{device_guid}_contact"
        self._attr_name = "Contact"

    @property
    def is_on(self) -> bool:
        """Return true if window/door is opened."""
        device = self._device
        if not device:
            return False
        val = device.get_info_value("contact")
        if val is None:
            val = device.get_function_value("contact")
        return val in ("opened", "open", "tilted", True)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return raw contact state (e.g. opened, tilted, closed)."""
        device = self._device
        if not device:
            return {}
        val = device.get_info_value("contact") or device.get_function_value("contact")
        return {"contact_position": val} if val is not None else {}


class EltakoConnectivityBinarySensor(EltakoDeviceEntity, BinarySensorEntity):
    """Sensor connection status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connection_status"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        """Initialize the connectivity binary sensor."""
        super().__init__(coordinator, device_guid)
        self._attr_unique_id = f"{device_guid}_connectivity"
        self._attr_name = "Connection Status"

    @property
    def is_on(self) -> bool:
        """Return true if sensor is online."""
        device = self._device
        if not device:
            return False
        return device.get_info_value("connectionStatus") == "online"


class EltakoWiredInputBinarySensor(EltakoDeviceEntity, BinarySensorEntity):
    """Physical wired input terminal on Series 64 actuator."""

    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_translation_key = "wired_input"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        identifier: str = "input",
    ) -> None:
        """Initialize the wired input binary sensor."""
        super().__init__(coordinator, device_guid)
        self._identifier = identifier
        self._attr_unique_id = f"{device_guid}_{identifier}"
        if identifier == "input":
            self._attr_name = "Wired Input"
        elif identifier == "inputChannel1":
            self._attr_name = "Wired Input 1"
        elif identifier == "inputChannel2":
            self._attr_name = "Wired Input 2"
        else:
            self._attr_name = f"Wired Input ({identifier})"

    @property
    def is_on(self) -> bool:
        """Return true if wired input is opened."""
        device = self._device
        if not device:
            return False
        return device.get_function_value(self._identifier) == "opened"


class EltakoGenericBinarySensor(EltakoDeviceEntity, BinarySensorEntity):
    """Generic characteristic-driven binary sensor for EnOcean / IP devices."""

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        identifier: str,
    ) -> None:
        """Initialize the generic binary sensor."""
        super().__init__(coordinator, device_guid)
        self._identifier = identifier
        meta = BINARY_CHAR_META.get(identifier, {})
        self._on_values = meta.get("on_values", {"opened", "on", True, 1})
        self._attr_unique_id = f"{device_guid}_{identifier}"
        self._attr_name = meta.get("name", identifier)
        self._attr_device_class = meta.get("device_class")
        self._attr_translation_key = f"binary_{identifier}"

    @property
    def is_on(self) -> bool:
        """Return true if the characteristic matches an active state."""
        device = self._device
        if not device:
            return False
        val = device.get_info_value(self._identifier)
        if val is None:
            val = device.get_function_value(self._identifier)
        return val in self._on_values
