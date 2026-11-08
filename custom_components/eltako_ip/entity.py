"""Base entity classes for the Eltako Series 62/64 IP integration."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Optional

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from aioeltako_ip import Device, EltakoConnectionError, EltakoError

from .const import DOMAIN
from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator


def get_coordinator(hass: Any, entry: EltakoConfigEntry) -> EltakoDataUpdateCoordinator:
    """Resolve coordinator from entry.runtime_data with fallback to hass.data."""
    if hasattr(entry, "runtime_data") and entry.runtime_data is not None:
        return entry.runtime_data
    return hass.data[DOMAIN][entry.entry_id]


class EltakoBaseEntity(CoordinatorEntity[EltakoDataUpdateCoordinator]):
    """Common base entity for Eltako IP."""

    _attr_has_entity_name = True

    async def _async_execute(
        self,
        coro: Awaitable[Any],
        refresh: bool = True,
    ) -> Any:
        """Execute an API call and translate client errors to HomeAssistantError."""
        try:
            result = await coro
        except (EltakoConnectionError, EltakoError) as err:
            raise HomeAssistantError(f"Eltako communication error: {err}") from err
        if refresh:
            await self.coordinator.async_request_refresh()
        return result


class EltakoGatewayEntity(EltakoBaseEntity):
    """Entity attached directly to the Eltako IP gateway / hub device."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return gateway device metadata."""
        sys_info = self.coordinator.system_info
        # Find main actuator display name if customized
        display_name = sys_info.product_name
        for dev in self.coordinator.data.devices.values():
            if dev.product_guid == sys_info.product_guid and dev.display_name:
                display_name = dev.display_name
                break
        identifiers = {(DOMAIN, sys_info.serial_number)}
        if hasattr(self.coordinator, "get_device_identifiers"):
            custom_ids = self.coordinator.get_device_identifiers(is_gateway=True)
            if isinstance(custom_ids, set):
                identifiers = custom_ids
        return DeviceInfo(
            identifiers=identifiers,
            name=display_name,
            manufacturer="Eltako",
            model=sys_info.product_name,
            serial_number=sys_info.serial_number,
            sw_version=sys_info.software_version,
            hw_version=sys_info.hardware_version,
        )


class EltakoDeviceEntity(EltakoBaseEntity):
    """Entity attached to a logical device in /devices."""

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator)
        self._device_guid = device_guid

    @property
    def _device(self) -> Optional[Device]:
        """Return the underlying Device object from coordinator data."""
        return self.coordinator.data.devices.get(self._device_guid)

    @property
    def available(self) -> bool:
        """Return True if the coordinator is available and the device still exists."""
        return super().available and (
            self._device_guid in self.coordinator.data.devices
            or self._device_guid in self.coordinator.data.enocean_devices
        )

    @property
    def _is_gateway_local_device(self) -> bool:
        """Return True if this device is the primary local gateway/actuator."""
        if self._device_guid in self.coordinator.data.enocean_devices:
            return False
        dev = self._device
        if dev is None:
            return False
        return dev.product_guid == self.coordinator.system_info.product_guid

    @property
    def device_info(self) -> DeviceInfo:
        """Return DeviceInfo for either the local gateway or a child device."""
        sys_info = self.coordinator.system_info
        dev = self._device

        if self._is_gateway_local_device:
            # Find primary actuator display_name if present
            name = sys_info.product_name
            if dev and dev.product_guid == sys_info.product_guid and dev.display_name:
                name = dev.display_name
            else:
                for d in self.coordinator.data.devices.values():
                    if d.product_guid == sys_info.product_guid and d.display_name:
                        name = d.display_name
                        break
            identifiers = {
                (DOMAIN, sys_info.serial_number),
                (DOMAIN, self._device_guid),
            }
            if hasattr(self.coordinator, "get_device_identifiers"):
                custom_ids = self.coordinator.get_device_identifiers(
                    self._device_guid, is_gateway=True
                )
                if isinstance(custom_ids, set):
                    identifiers = custom_ids
            return DeviceInfo(
                identifiers=identifiers,
                name=name,
                manufacturer="Eltako",
                model=sys_info.product_name,
                serial_number=sys_info.serial_number,
                sw_version=sys_info.software_version,
                hw_version=sys_info.hardware_version,
            )

        name = dev.display_name if (dev and dev.display_name) else "Eltako Device"
        model = (
            self.coordinator.data.get_product_name(dev.product_guid, "Eltako Device")
            if dev
            else "Eltako Device"
        )
        identifiers = {(DOMAIN, self._device_guid)}
        if hasattr(self.coordinator, "get_device_identifiers"):
            custom_ids = self.coordinator.get_device_identifiers(
                self._device_guid, is_gateway=False
            )
            if isinstance(custom_ids, set):
                identifiers = custom_ids

        via_kwargs: dict[str, Any] = {"via_device": (DOMAIN, sys_info.serial_number)}
        cfg_entry = getattr(self.coordinator, "config_entry", None)
        entry_id = getattr(cfg_entry, "entry_id", None)
        if self.hass is not None and isinstance(entry_id, str):
            dev_reg = dr.async_get(self.hass)
            if hasattr(dev_reg, "async_get_device_by_identifier"):
                gw_entry = dev_reg.async_get_device_by_identifier(
                    (DOMAIN, sys_info.serial_number),
                    entry_id,
                )
                if gw_entry is not None and isinstance(getattr(gw_entry, "id", None), str):
                    via_kwargs = {"via_device_id": gw_entry.id}

        return DeviceInfo(
            identifiers=identifiers,
            name=name,
            manufacturer="Eltako",
            model=model,
            **via_kwargs,
        )
