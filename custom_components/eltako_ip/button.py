"""Button platform for Eltako Series 62/64 IP actions."""

from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoDeviceEntity, EltakoGatewayEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako button entities."""
    coordinator = get_coordinator(hass, entry)

    entities: list[ButtonEntity] = [
        EltakoIdentifyButton(coordinator),
        EltakoStartEnOceanScanButton(coordinator),
    ]

    for eo_dev in coordinator.data.enocean_devices.values():
        entities.append(
            EltakoUnpairEnOceanDeviceButton(
                coordinator,
                device_guid=eo_dev.device_guid or eo_dev.service_device_guid,
                service_device_guid=eo_dev.service_device_guid,
            )
        )

    async_add_entities(entities)


class EltakoIdentifyButton(EltakoGatewayEntity, ButtonEntity):
    """Button to physically identify the device (flashes LED / pulses actuator)."""

    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "identify"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_identify"
        self._attr_name = "Identify"

    async def async_press(self) -> None:
        """Trigger physical identification on the device."""
        await self._async_execute(self.coordinator.client.identify(), refresh=False)
        _LOGGER.info(
            "Physical device identification triggered on %s",
            self.coordinator.client.host,
        )


class EltakoStartEnOceanScanButton(EltakoGatewayEntity, ButtonEntity):
    """Button to start EnOcean teach-in scanning."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:antenna"
    _attr_translation_key = "start_enocean_scan"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.system_info.serial_number}_start_enocean_scan"
        )
        self._attr_name = "Start EnOcean Pairing Scan"

    async def async_press(self) -> None:
        """Trigger EnOcean scan mode on the device."""
        await self._async_execute(
            self.coordinator.client.start_enocean_scan(), refresh=False
        )
        _LOGGER.info("EnOcean pairing scan mode initiated via button")


class EltakoUnpairEnOceanDeviceButton(EltakoDeviceEntity, ButtonEntity):
    """Button to unpair and delete a paired EnOcean sensor from on-device NVRAM."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:link-off"
    _attr_translation_key = "unpair_enocean_device"

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
        self._attr_unique_id = f"{device_guid}_unpair_enocean"
        self._attr_name = "Unpair EnOcean Device"

    async def async_press(self) -> None:
        """Delete the EnOcean device from the gateway."""
        await self._async_execute(
            self.coordinator.client.delete_enocean_device(
                self._service_device_guid,
            ),
            refresh=True,
        )
        _LOGGER.info(
            "Unpaired EnOcean device %s (service %s)",
            self._device_guid,
            self._service_device_guid,
        )
