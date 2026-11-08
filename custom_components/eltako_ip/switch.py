"""Switch platform for Eltako Series 62/64 IP relay actuators, Matter exposure, and auto-update."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoDeviceEntity, EltakoGatewayEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)

RELAY_IDENTIFIERS: dict[str, str] = {
    "relay": "Relay",
    "relayChannel1": "Relay Channel 1",
    "relayChannel2": "Relay Channel 2",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako switch entities."""
    coordinator = get_coordinator(hass, entry)

    entities: list[SwitchEntity] = [
        EltakoAutoUpdateSwitch(coordinator),
    ]

    for device in coordinator.data.devices.values():
        for identifier, label in RELAY_IDENTIFIERS.items():
            if device.get_function_value(identifier) is not None:
                entities.append(
                    EltakoRelaySwitch(
                        coordinator,
                        device.device_guid,
                        identifier=identifier,
                        name=label,
                    )
                )

        # Phase 3: Matter bridge exposure toggle per device
        entities.append(EltakoMatterExposureSwitch(coordinator, device.device_guid))

    async_add_entities(entities)


class EltakoRelaySwitch(EltakoDeviceEntity, SwitchEntity):
    """Representation of an Eltako relay switch channel (ESR62/64, E2SR64, FSR61)."""

    _attr_translation_key = "relay"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
        identifier: str = "relay",
        name: str = "Relay",
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_guid)
        self._identifier = identifier
        self._attr_unique_id = f"{device_guid}_{identifier}"
        self._attr_name = name

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        device = self._device
        if not device:
            return False
        return device.get_function_value(self._identifier) == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on."""
        if self._identifier == "relay":
            coro = self.coordinator.client.set_relay(self._device_guid, True)
        else:
            coro = self.coordinator.client.set_relay(
                self._device_guid, True, identifier=self._identifier
            )
        await self._async_execute(coro)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off."""
        if self._identifier == "relay":
            coro = self.coordinator.client.set_relay(self._device_guid, False)
        else:
            coro = self.coordinator.client.set_relay(
                self._device_guid, False, identifier=self._identifier
            )
        await self._async_execute(coro)


class EltakoAutoUpdateSwitch(EltakoGatewayEntity, SwitchEntity):
    """Configuration switch to toggle background firmware auto-updates (Phase 4)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:update"
    _attr_translation_key = "auto_update"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_auto_update"
        self._attr_name = "Auto Update"

    @property
    def is_on(self) -> bool:
        """Return True if automatic firmware updates are enabled."""
        return self.coordinator.data.update_config.auto_update

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable automatic firmware updates."""
        await self._async_execute(
            self.coordinator.client.set_update_config(auto_update=True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable automatic firmware updates."""
        await self._async_execute(
            self.coordinator.client.set_update_config(auto_update=False)
        )


class EltakoMatterExposureSwitch(EltakoDeviceEntity, SwitchEntity):
    """Configuration switch to expose or hide a device on the internal Matter bridge (Phase 3)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:hubspot"
    _attr_translation_key = "expose_to_matter"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        super().__init__(coordinator, device_guid)
        self._attr_unique_id = f"{device_guid}_expose_to_matter"
        self._attr_name = "Expose to Matter"

    @property
    def is_on(self) -> bool:
        """Return True if the device is currently exposed on the Matter bridge."""
        return self.coordinator.data.get_matter_device(self._device_guid) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Matter bridge endpoint metadata."""
        m_dev = self.coordinator.data.get_matter_device(self._device_guid)
        if not m_dev:
            return {"exposed": False}
        return {
            "exposed": True,
            "service_device_guid": m_dev.service_device_guid,
            "endpoint_id": m_dev.endpoint_id,
            "channels": m_dev.config.get("channels", []),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Expose this device to the Matter fabric."""
        device = self._device
        if not device:
            return
        if self.coordinator.data.get_matter_device(self._device_guid) is not None:
            return
        await self._async_execute(
            self.coordinator.client.expose_matter_device(
                product_guid=device.product_guid,
                device_guid=self._device_guid,
            )
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Remove this device from the Matter fabric."""
        m_dev = self.coordinator.data.get_matter_device(self._device_guid)
        if not m_dev:
            return
        await self._async_execute(
            self.coordinator.client.remove_matter_device(m_dev.service_device_guid)
        )
