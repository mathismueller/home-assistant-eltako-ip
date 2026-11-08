"""DataUpdateCoordinator for Eltako Series 62/64 IP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
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

from .const import DOMAIN, LOCAL_WIRED_INPUT_PRODUCTS, PRODUCT_NAMES_FALLBACK

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

            # Clean up any half-deleted/orphaned EnOcean devices still lingering in /devices or /services/matter/devices
            local_product_guids = {
                self.system_info.product_guid,
                *LOCAL_WIRED_INPUT_PRODUCTS,
            }
            orphan_guids = [
                guid
                for guid, dev in devices_map.items()
                if dev.product_guid not in local_product_guids
                and guid not in eo_devices_map
            ]
            for orphan_guid in orphan_guids:
                _LOGGER.info(
                    "Cleaning up orphaned EnOcean device %s from /devices and /services/matter/devices",
                    orphan_guid,
                )
                for m_dev in list(matter_devs):
                    if m_dev.device_guid == orphan_guid and m_dev.service_device_guid:
                        try:
                            await self.client.remove_matter_device(
                                m_dev.service_device_guid
                            )
                        except EltakoError:
                            pass
                        matter_devs.remove(m_dev)
                for rule in list(automations):
                    if orphan_guid in (
                        rule.input_device_guid,
                        rule.output_device_guid,
                    ) and rule.automation_guid:
                        try:
                            await self.client.delete_automation(rule.automation_guid)
                        except EltakoError:
                            pass
                        automations.remove(rule)
                try:
                    await self.client.delete_device(orphan_guid)
                except EltakoError:
                    pass
                devices_map.pop(orphan_guid, None)

            self._async_cleanup_removed_devices(devices_map, eo_devices_map)

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

    async def async_unpair_enocean_device(
        self,
        device_guid: Optional[str] = None,
        service_device_guid: Optional[str] = None,
    ) -> None:
        """Completely unpair an EnOcean device across EnOcean service, Matter bridge, automations, /devices, and HA Device Registry."""
        if self.data is not None:
            if not service_device_guid and device_guid:
                eo_dev = self.data.enocean_devices.get(device_guid)
                if eo_dev:
                    service_device_guid = eo_dev.service_device_guid
            elif service_device_guid and not device_guid:
                for eo_dev in self.data.enocean_devices.values():
                    if eo_dev.service_device_guid == service_device_guid:
                        device_guid = eo_dev.device_guid
                        break

        # 1. Unlink from EnOcean service (/services/enocean/devices/{serviceDeviceGuid})
        if service_device_guid:
            try:
                await self.client.delete_enocean_device(service_device_guid)
            except DeviceNotFoundError:
                _LOGGER.debug(
                    "EnOcean service device %s was already deleted",
                    service_device_guid,
                )

        # 2. Unlink from Matter service (/services/matter/devices/{serviceDeviceGuid}) if exposed
        if device_guid and self.data is not None:
            for m_dev in self.data.matter_devices:
                if m_dev.device_guid == device_guid and m_dev.service_device_guid:
                    try:
                        await self.client.remove_matter_device(
                            m_dev.service_device_guid
                        )
                    except DeviceNotFoundError:
                        pass

            # 3. Delete any on-device automations referencing this device
            for rule in self.data.automations:
                if (
                    device_guid in (rule.input_device_guid, rule.output_device_guid)
                    and rule.automation_guid
                ):
                    try:
                        await self.client.delete_automation(rule.automation_guid)
                    except DeviceNotFoundError:
                        pass

        # 4. Delete logical device (/devices/{deviceGuid})
        if device_guid:
            try:
                await self.client.delete_device(device_guid)
            except DeviceNotFoundError:
                _LOGGER.debug(
                    "Logical device %s was already deleted from /devices",
                    device_guid,
                )

        # 5. Remove from Home Assistant Device Registry
        if self.hass is not None:
            dev_reg = dr.async_get(self.hass)
            for ident in (device_guid, service_device_guid):
                if ident:
                    ha_dev = dev_reg.async_get_device(identifiers={(DOMAIN, ident)})
                    if ha_dev:
                        dev_reg.async_remove_device(ha_dev.id)

    def _async_cleanup_removed_devices(
        self,
        devices_map: dict[str, Device],
        eo_devices_map: dict[str, EnOceanDevice],
    ) -> None:
        """Remove stale child devices from the Home Assistant Device Registry."""
        if self.hass is None or self.config_entry is None:
            return

        active_ids: set[str] = {
            self.system_info.serial_number,
            *devices_map.keys(),
            *eo_devices_map.keys(),
            *(d.service_device_guid for d in eo_devices_map.values() if d.service_device_guid),
        }

        dev_reg = dr.async_get(self.hass)
        for device_entry in dr.async_entries_for_config_entry(
            dev_reg, self.config_entry.entry_id
        ):
            eltako_ids = {
                ident_val
                for domain, ident_val in device_entry.identifiers
                if domain == DOMAIN
            }
            if eltako_ids and eltako_ids.isdisjoint(active_ids):
                _LOGGER.info(
                    "Removing unpaired/stale Eltako device %s (%s) from Device Registry",
                    device_entry.name,
                    eltako_ids,
                )
                dev_reg.async_remove_device(device_entry.id)
