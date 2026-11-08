"""Update platform for Eltako Series 62/64 IP firmware status."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoGatewayEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Eltako firmware update entity."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities([EltakoFirmwareUpdateEntity(coordinator)])


class EltakoFirmwareUpdateEntity(EltakoGatewayEntity, UpdateEntity):
    """Firmware update status entity for the Eltako IP gateway."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_translation_key = "firmware"

    def __init__(self, coordinator: EltakoDataUpdateCoordinator) -> None:
        """Initialize the firmware update entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.system_info.serial_number}_firmware"
        self._attr_name = "Firmware"

    @property
    def installed_version(self) -> Optional[str]:
        """Return currently installed firmware version."""
        fw = self.coordinator.data.firmware_info
        if fw and fw.current_version and fw.current_version != "0.0.0":
            return fw.current_version
        return self.coordinator.system_info.software_version

    @property
    def latest_version(self) -> Optional[str]:
        """Return latest known firmware version."""
        fw = self.coordinator.data.firmware_info
        if fw and fw.latest_version and fw.latest_version != "0.0.0":
            return fw.latest_version
        return self.installed_version

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return OTA server and update schedule metadata."""
        fw = self.coordinator.data.firmware_info
        cfg = self.coordinator.data.update_config
        return {
            "desired_version": fw.desired_version if fw else "0.0.0",
            "location": fw.location if fw else "",
            "update_server_uri": cfg.update_server_uri if cfg else "",
            "auto_update": cfg.auto_update if cfg else False,
            "update_schedule": cfg.update_schedule if cfg else "12h",
        }
