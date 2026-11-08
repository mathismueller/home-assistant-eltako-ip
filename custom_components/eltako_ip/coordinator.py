"""DataUpdateCoordinator for Eltako Series 62/64 IP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from aioeltako_ip import (
    AuthenticationError,
    AutomationRule,
    Device,
    DeviceNotFoundError,
    EltakoClient,
    EltakoConnectionError,
    EltakoError,
    EnOceanDevice,
    EnOceanStatus,
    FirmwareUpdateInfo,
    MatterDevice,
    ProductSpec,
    SystemInfo,
    UpdateConfig,
)

from .const import DOMAIN, PRODUCT_NAMES_FALLBACK

_LOGGER = logging.getLogger(__name__)

type EltakoConfigEntry = ConfigEntry[EltakoDataUpdateCoordinator]


@dataclass
class EltakoData:
    """Class to hold all data retrieved from Eltako gateway."""

    system: SystemInfo
    devices: dict[str, Device]
    enocean_status: EnOceanStatus
    enocean_devices: dict[str, EnOceanDevice]
    matter_devices: list[MatterDevice]
    enocean_config: dict[str, Any]
    update_config: UpdateConfig = field(default_factory=UpdateConfig)
    firmware_info: FirmwareUpdateInfo = field(
        default_factory=lambda: FirmwareUpdateInfo(
            current_version="0.0.0",
            desired_version="0.0.0",
        )
    )
    automations: list[AutomationRule] = field(default_factory=list)
    products: dict[str, ProductSpec] = field(default_factory=dict)
    matter_supported: bool = True

    def get_matter_device(self, device_guid: str) -> Optional[MatterDevice]:
        """Return the MatterDevice entry if device_guid is exposed to Matter."""
        for m_dev in self.matter_devices:
            if m_dev.device_guid == device_guid:
                return m_dev
        return None

    def get_automation_for_input(
        self,
        input_device_guid: str,
        input_identifier: Optional[str] = None,
    ) -> Optional[AutomationRule]:
        """Find the primary on-device automation rule triggered by an input device."""
        for rule in self.automations:
            if rule.input_device_guid == input_device_guid:
                if (
                    input_identifier is None
                    or rule.input_characteristic_identifier == input_identifier
                ):
                    return rule
        return None

    def get_product_name(self, product_guid: str, default: str = "Eltako Device") -> str:
        """Return human-readable product model name from /products or fallback map."""
        spec = self.products.get(product_guid)
        if spec and spec.name:
            return spec.name
        return PRODUCT_NAMES_FALLBACK.get(product_guid, default)


class EltakoDataUpdateCoordinator(DataUpdateCoordinator[EltakoData]):
    """Class to manage fetching Eltako data from device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EltakoClient,
        system_info: SystemInfo,
        update_interval: timedelta,
        config_entry: Optional[ConfigEntry] = None,
    ) -> None:
        """Initialize."""
        self.client = client
        self.system_info = system_info
        self._products_cache: dict[str, ProductSpec] = {}
        self.matter_supported: bool = True

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} ({system_info.product_name})",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> EltakoData:
        """Fetch data from Eltako device."""
        try:
            if not self._products_cache:
                try:
                    self._products_cache = await self.client.get_products()
                except EltakoError as err:
                    _LOGGER.debug("Could not load /products catalog: %s", err)

            devices_list = await self.client.get_devices()
            devices_map = {d.device_guid: d for d in devices_list}

            # EnOcean endpoints (graceful fallback if no EnOcean transceiver present)
            try:
                eo_status = await self.client.get_enocean_status()
                eo_devices_list = await self.client.get_enocean_devices()
                eo_devices_map = {
                    (d.device_guid or d.service_device_guid): d for d in eo_devices_list
                }
                eo_config = await self.client.get_enocean_configuration()
            except DeviceNotFoundError:
                eo_status = EnOceanStatus(health="not_installed", max_eur_ids=0, free_eur_ids=0)
                eo_devices_map = {}
                eo_config = {}

            # Matter endpoints (cached skip for non-Matter Series 62 -IP models)
            matter_devs: list[MatterDevice] = []
            if self.matter_supported:
                try:
                    matter_devs = await self.client.get_matter_devices()
                except DeviceNotFoundError:
                    self.matter_supported = False
                    matter_devs = []

            # Update config & firmware update info
            try:
                update_cfg = await self.client.get_update_config()
            except EltakoError:
                update_cfg = UpdateConfig()

            try:
                firmware_info = await self.client.get_firmware_update_info()
            except EltakoError:
                firmware_info = FirmwareUpdateInfo(
                    current_version=self.system_info.software_version,
                    desired_version="0.0.0",
                )

            # On-device automations
            try:
                automations = await self.client.get_automations()
            except EltakoError:
                automations = []

            return EltakoData(
                system=self.system_info,
                devices=devices_map,
                enocean_status=eo_status,
                enocean_devices=eo_devices_map,
                matter_devices=matter_devs,
                enocean_config=eo_config,
                update_config=update_cfg,
                firmware_info=firmware_info,
                automations=automations,
                products=self._products_cache,
                matter_supported=self.matter_supported,
            )
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except (EltakoConnectionError, EltakoError) as err:
            raise UpdateFailed(f"Error communicating with Eltako device: {err}") from err
