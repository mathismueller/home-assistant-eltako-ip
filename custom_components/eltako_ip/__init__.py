"""The Eltako Series 62/64 IP integration."""

from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:
    from aioeltako_ip import EltakoClient
except ImportError:
    import sys
    from pathlib import Path
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from aioeltako_ip import EltakoClient  # type: ignore[no-redef]

from .const import (
    CONF_HOST,
    CONF_POP,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_EXPOSE_MATTER_DEVICE,
    SERVICE_PAIR_ENOCEAN_DEVICE,
    SERVICE_REMOVE_MATTER_DEVICE,
    SERVICE_START_ENOCEAN_SCAN,
)
from .coordinator import EltakoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eltako Series 62/64 IP from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    pop = entry.data[CONF_POP]
    scan_interval_sec = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    session = async_get_clientsession(hass, verify_ssl=False)
    client = EltakoClient(host=host, port=port, pop=pop, session=session)
    await client.login()
    system_info = await client.get_system()

    coordinator = EltakoDataUpdateCoordinator(
        hass=hass,
        client=client,
        system_info=system_info,
        update_interval=timedelta(seconds=scan_interval_sec),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload on options update (e.g. scan interval change)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services
    async def handle_start_enocean_scan(call: ServiceCall) -> None:
        """Start EnOcean teach-in scan."""
        await coordinator.client.start_enocean_scan()
        _LOGGER.info("EnOcean pairing scan initiated on %s", host)

    async def handle_pair_enocean_device(call: ServiceCall) -> None:
        """Pair an EnOcean sensor."""
        eur_id = call.data["eur_id"]
        product_guid = call.data["product_guid"]
        await coordinator.client.pair_enocean_device(eur_id=eur_id, product_guid=product_guid)
        await coordinator.async_request_refresh()
        _LOGGER.info("Paired EnOcean sensor EURID %s", eur_id)

    async def handle_expose_matter(call: ServiceCall) -> None:
        """Expose a device to the Matter bridge."""
        product_guid = call.data["product_guid"]
        device_guid = call.data["device_guid"]
        await coordinator.client.expose_matter_device(product_guid=product_guid, device_guid=device_guid)
        await coordinator.async_request_refresh()
        _LOGGER.info("Exposed device %s to Matter bridge", device_guid)

    async def handle_remove_matter(call: ServiceCall) -> None:
        """Remove a device from the Matter bridge."""
        service_device_guid = call.data["service_device_guid"]
        await coordinator.client.remove_matter_device(service_device_guid=service_device_guid)
        await coordinator.async_request_refresh()
        _LOGGER.info("Removed service device %s from Matter bridge", service_device_guid)

    if not hass.services.has_service(DOMAIN, SERVICE_START_ENOCEAN_SCAN):
        hass.services.async_register(DOMAIN, SERVICE_START_ENOCEAN_SCAN, handle_start_enocean_scan)
        hass.services.async_register(
            DOMAIN,
            SERVICE_PAIR_ENOCEAN_DEVICE,
            handle_pair_enocean_device,
            schema=vol.Schema(
                {
                    vol.Required("eur_id"): cv.positive_int,
                    vol.Required("product_guid"): cv.string,
                }
            ),
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_EXPOSE_MATTER_DEVICE,
            handle_expose_matter,
            schema=vol.Schema(
                {
                    vol.Required("product_guid"): cv.string,
                    vol.Required("device_guid"): cv.string,
                }
            ),
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_MATTER_DEVICE,
            handle_remove_matter,
            schema=vol.Schema(
                {
                    vol.Required("service_device_guid"): cv.string,
                }
            ),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: EltakoDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.client.close()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
