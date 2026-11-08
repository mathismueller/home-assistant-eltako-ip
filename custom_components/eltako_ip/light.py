"""Light platform for Eltako Series 62/64 IP dimmers (EUD64NPN-IPM, EUD62NPN-IP, FUD61)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
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
    """Set up Eltako dimmer lights."""
    coordinator = get_coordinator(hass, entry)
    entities: list[LightEntity] = []

    for device in coordinator.data.devices.values():
        if device.get_function("targetBrightness") is not None:
            entities.append(EltakoDimmerLight(coordinator, device.device_guid))

    async_add_entities(entities)


class EltakoDimmerLight(EltakoDeviceEntity, LightEntity):
    """Representation of an Eltako dimmer actuator (EUD64NPN-IPM / EUD62NPN-IP / FUD61)."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_translation_key = "dimmer"

    def __init__(
        self,
        coordinator: EltakoDataUpdateCoordinator,
        device_guid: str,
    ) -> None:
        """Initialize the dimmer light."""
        super().__init__(coordinator, device_guid)
        self._attr_unique_id = f"{device_guid}_light"
        self._attr_name = "Dimmer"

    @property
    def _current_pct(self) -> int:
        dev = self._device
        if not dev:
            return 0
        val = dev.get_info_value("currentBrightness")
        if val is None:
            val = dev.get_function_value("targetBrightness")
        if val is None:
            return 0
        try:
            return max(0, min(100, int(round(float(val)))))
        except (TypeError, ValueError):
            return 0

    @property
    def is_on(self) -> bool:
        """Return true if the dimmer is on (brightness > 0)."""
        return self._current_pct > 0

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        pct = self._current_pct
        return int(round(pct * 255 / 100))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional dimmer status attributes."""
        dev = self._device
        if not dev:
            return {}
        attrs: dict[str, Any] = {}
        last_br = dev.get_function_value("lastBrightness")
        if last_br is not None:
            attrs["last_brightness_pct"] = last_br
        target_br = dev.get_function_value("targetBrightness")
        if target_br is not None:
            attrs["target_brightness_pct"] = target_br
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the dimmer on to the specified brightness or restore lastBrightness."""
        if ATTR_BRIGHTNESS in kwargs:
            ha_brightness = int(kwargs[ATTR_BRIGHTNESS])
            pct = max(1, min(100, int(round(ha_brightness * 100 / 255))))
        else:
            dev = self._device
            last_br = dev.get_function_value("lastBrightness") if dev else None
            try:
                pct = int(round(float(last_br))) if last_br and float(last_br) > 0 else 100
            except (TypeError, ValueError):
                pct = 100
        await self._async_execute(
            self.coordinator.client.set_brightness(self._device_guid, pct)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the dimmer off (0% brightness)."""
        await self._async_execute(
            self.coordinator.client.set_brightness(self._device_guid, 0)
        )
