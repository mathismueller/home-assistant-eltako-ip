"""Button platform for Eltako Series 62/64 IP actions."""

from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from aioeltako_ip import DeviceNotFoundError

from .const import DOMAIN
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
        """Delete the EnOcean device from the gateway and remove its HA device."""
        try:
            await self.coordinator.client.delete_enocean_device(
                self._service_device_guid,
            )
        except DeviceNotFoundError:
            _LOGGER.debug(
                "EnOcean device %s (service %s) was already removed from gateway",
                self._device_guid,
                self._service_device_guid,
            )
        except Exception as err:
            await self._async_execute(self._raise_err(err), refresh=False)

        if self.hass is not None:
            dev_reg = dr.async_get(self.hass)
            for ident in (self._device_guid, self._service_device_guid):
                if ident:
                    ha_dev = dev_reg.async_get_device(identifiers={(DOMAIN, ident)})
                    if ha_dev:
                        dev_reg.async_remove_device(ha_dev.id)

        await self.coordinator.async_request_refresh()
        _LOGGER.info(
            "Unpaired EnOcean device %s (service %s)",
            self._device_guid,
            self._service_device_guid,
        )

    @staticmethod
    async def _raise_err(err: Exception) -> None:
        raise err
