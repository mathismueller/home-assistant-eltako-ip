"""Button platform for Eltako Series 62/64 IP actions."""

from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
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

    # Clean up legacy standalone scan button if present in the Entity Registry
    ent_reg = er.async_get(hass)
    legacy_scan_uid = f"{coordinator.system_info.serial_number}_start_enocean_scan"
    legacy_ent_id = ent_reg.async_get_entity_id("button", DOMAIN, legacy_scan_uid)
    if legacy_ent_id:
        ent_reg.async_remove(legacy_ent_id)

    entities: list[ButtonEntity] = [
        EltakoIdentifyButton(coordinator),
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
        """Delete the EnOcean device across EnOcean service, Matter bridge, /devices, and HA Device Registry."""
        try:
            await self.coordinator.client.delete_enocean_device(
                self._service_device_guid,
            )
        except DeviceNotFoundError:
            _LOGGER.debug(
                "EnOcean device %s (service %s) was already removed from EnOcean service",
                self._device_guid,
                self._service_device_guid,
            )
        except Exception as err:
            await self._async_execute(self._raise_err(err), refresh=False)

        if self._device_guid and getattr(self.coordinator, "data", None) is not None:
            for m_dev in self.coordinator.data.matter_devices:
                if (
                    m_dev.device_guid == self._device_guid
                    and m_dev.service_device_guid
                ):
                    try:
                        await self.coordinator.client.remove_matter_device(
                            m_dev.service_device_guid,
                        )
                    except DeviceNotFoundError:
                        pass

        if self._device_guid and hasattr(self.coordinator.client, "delete_device"):
            try:
                await self.coordinator.client.delete_device(self._device_guid)
            except DeviceNotFoundError:
                pass

        if self.hass is not None:
            dev_reg = dr.async_get(self.hass)
            cfg_entry = getattr(self.coordinator, "config_entry", None)
            entry_id = getattr(cfg_entry, "entry_id", None)
            for ident in (self._device_guid, self._service_device_guid):
                if ident:
                    if isinstance(entry_id, str) and hasattr(
                        dev_reg, "async_get_device_by_identifier"
                    ):
                        ha_dev = dev_reg.async_get_device_by_identifier(
                            (DOMAIN, ident), entry_id
                        )
                    else:
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
