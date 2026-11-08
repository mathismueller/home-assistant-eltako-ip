"""DataUpdateCoordinator for Eltako Series 62/64 IP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

try:
    from aioeltako_ip import (
        Device,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
        EnOceanDevice,
        EnOceanStatus,
        MatterDevice,
        SystemInfo,
    )
except ImportError:
    import sys
    from pathlib import Path
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from aioeltako_ip import (  # type: ignore[no-redef]
        Device,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
        EnOceanDevice,
        EnOceanStatus,
        MatterDevice,
        SystemInfo,
    )

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class EltakoData:
    """Class to hold all data retrieved from Eltako gateway."""

    system: SystemInfo
    devices: dict[str, Device]
    enocean_status: EnOceanStatus
    enocean_devices: dict[str, EnOceanDevice]
    matter_devices: list[MatterDevice]
    enocean_config: dict[str, Any]


class EltakoDataUpdateCoordinator(DataUpdateCoordinator[EltakoData]):
    """Class to manage fetching Eltako data from device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EltakoClient,
        system_info: SystemInfo,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.client = client
        self.system_info = system_info

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({system_info.product_name})",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> EltakoData:
        """Fetch data from Eltako device."""
        try:
            devices_list = await self.client.get_devices()
            devices_map = {d.device_guid: d for d in devices_list}

            eo_status = await self.client.get_enocean_status()
            eo_devices_list = await self.client.get_enocean_devices()
            eo_devices_map = {d.device_guid: d for d in eo_devices_list}

            matter_devs = await self.client.get_matter_devices()
            eo_config = await self.client.get_enocean_configuration()

            return EltakoData(
                system=self.system_info,
                devices=devices_map,
                enocean_status=eo_status,
                enocean_devices=eo_devices_map,
                matter_devices=matter_devs,
                enocean_config=eo_config,
            )
        except (EltakoConnectionError, EltakoError) as err:
            raise UpdateFailed(f"Error communicating with Eltako device: {err}") from err
