"""Cover platform for Eltako Series 62/64 IP shading & blind actuators (ESB64NP-IPM, ESB62NP-IP, FSB61)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator
from .entity import EltakoDeviceEntity, get_coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EltakoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eltako cover entities."""
    coordinator = get_coordinator(hass, entry)
    entities: list[CoverEntity] = []

    for device in coordinator.data.devices.values():
        if device.get_function("targetPosition") is not None:
            entities.append(EltakoCover(coordinator, device.device_guid))

    async_add_entities(entities)


class EltakoCover(EltakoDeviceEntity, CoverEntity):
    """Representation of an Eltako shading/shutter/blind actuator."""

    _attr_device_class = CoverDeviceClass.BLIND
    _attr_translation_key = "cover"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        """Initialize the cover entity."""
        super().__init__(coordinator, device_guid)
        self._attr_unique_id = f"{device_guid}_cover"
        self._attr_name = "Cover"

    @property
    def _has_tilt(self) -> bool:
        dev = self._device
        if not dev:
            return False
        if dev.get_function("targetTilt") is None:
            return False
        enable_tilt = dev.get_setting_value("enableTilt")
        if enable_tilt == "disabled":
            return False
        return True

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )
        if self._has_tilt:
            features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )
        return features

    @property
    def current_cover_position(self) -> Optional[int]:
        """Return current position of cover (0 = closed, 100 = open in Home Assistant).

        Note: Eltako's currentPosition / targetPosition uses 0 = fully open (top) and 100 = fully closed (bottom).
        We invert to match Home Assistant's convention (100 = open, 0 = closed).
        """
        dev = self._device
        if not dev:
            return None
        val = dev.get_info_value("currentPosition")
        if val is None:
            val = dev.get_function_value("targetPosition")
        if val is None:
            return None
        try:
            eltako_pos = max(0, min(100, int(round(float(val)))))
            return 100 - eltako_pos
        except (TypeError, ValueError):
            return None

    @property
    def current_cover_tilt_position(self) -> Optional[int]:
        """Return current tilt position of cover (0 = closed, 100 = open)."""
        if not self._has_tilt:
            return None
        dev = self._device
        if not dev:
            return None
        val = dev.get_info_value("currentTilt")
        if val is None:
            val = dev.get_function_value("targetTilt")
        if val is None:
            return None
        try:
            eltako_tilt = max(0, min(100, int(round(float(val)))))
            return 100 - eltako_tilt
        except (TypeError, ValueError):
            return None

    @property
    def is_closed(self) -> Optional[bool]:
        """Return true if the cover is closed."""
        pos = self.current_cover_position
        if pos is None:
            return None
        return pos == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (Eltako targetPosition = 0)."""
        await self._async_execute(
            self.coordinator.client.set_cover_position(self._device_guid, 0)
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (Eltako targetPosition = 100)."""
        await self._async_execute(
            self.coordinator.client.set_cover_position(self._device_guid, 100)
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        ha_position = int(kwargs[ATTR_POSITION])
        eltako_pos = max(0, min(100, 100 - ha_position))
        await self._async_execute(
            self.coordinator.client.set_cover_position(self._device_guid, eltako_pos)
        )

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt (Eltako targetTilt = 0)."""
        await self._async_execute(
            self.coordinator.client.set_cover_tilt(self._device_guid, 0)
        )

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt (Eltako targetTilt = 100)."""
        await self._async_execute(
            self.coordinator.client.set_cover_tilt(self._device_guid, 100)
        )

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        ha_tilt = int(kwargs[ATTR_TILT_POSITION])
        eltako_tilt = max(0, min(100, 100 - ha_tilt))
        await self._async_execute(
            self.coordinator.client.set_cover_tilt(self._device_guid, eltako_tilt)
        )
