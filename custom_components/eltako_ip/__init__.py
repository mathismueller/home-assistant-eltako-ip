"""The Eltako Series 62/64 IP integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from pathlib import Path
import sys
from typing import Any, Optional

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:
    from aioeltako_ip import (
        AuthenticationError,
        AutomationAddOn,
        AutomationRule,
        DeviceNotFoundError,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
        parse_eur_id,
    )
except ImportError:
    for _candidate in (
        Path(__file__).resolve().parent.parent.parent / "src",
        Path(__file__).resolve().parent,
    ):
        if (_candidate / "aioeltako_ip").is_dir() and str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
            break
    from aioeltako_ip import (  # type: ignore[no-redef]
        AuthenticationError,
        AutomationAddOn,
        AutomationRule,
        DeviceNotFoundError,
        EltakoClient,
        EltakoConnectionError,
        EltakoError,
        parse_eur_id,
    )

from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_POP,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_CREATE_AUTOMATION,
    SERVICE_DELETE_AUTOMATION,
    SERVICE_EXPOSE_MATTER_DEVICE,
    SERVICE_IDENTIFY_DEVICE,
    SERVICE_LEGACY_PAIR_ENOCEAN,
    SERVICE_PAIR_ENOCEAN_DEVICE,
    SERVICE_REMOVE_MATTER_DEVICE,
    SERVICE_RENAME_DEVICE,
    SERVICE_RESET_AUTOMATIONS,
    SERVICE_RESET_MATTER_BRIDGE,
    SERVICE_SET_ENOCEAN_DEVICE_CONFIG,
    SERVICE_START_ENOCEAN_SCAN,
    SERVICE_UNPAIR_ENOCEAN_DEVICE,
    SERVICE_UPDATE_AUTOMATION,
    SERVICE_UPLOAD_FIRMWARE,
)
from .coordinator import EltakoConfigEntry, EltakoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.UPDATE,
    Platform.LIGHT,
    Platform.COVER,
]


def _resolve_coordinator(
    hass: HomeAssistant,
    call: ServiceCall,
) -> EltakoDataUpdateCoordinator:
    """Resolve target EltakoDataUpdateCoordinator for a service call across single or multiple hubs."""
    coordinators: dict[str, EltakoDataUpdateCoordinator] = hass.data.get(DOMAIN, {})
    if not coordinators:
        raise HomeAssistantError("No Eltako IP gateways are currently configured.")

    entry_id = call.data.get("entry_id")
    if entry_id and entry_id in coordinators:
        return coordinators[entry_id]

    device_guid = call.data.get("device_guid")
    if device_guid:
        for coord in coordinators.values():
            if (
                device_guid in coord.data.devices
                or device_guid in coord.data.enocean_devices
            ):
                return coord

    service_device_guid = call.data.get("service_device_guid")
    if service_device_guid:
        for coord in coordinators.values():
            for eo_dev in coord.data.enocean_devices.values():
                if eo_dev.service_device_guid == service_device_guid:
                    return coord
            for m_dev in coord.data.matter_devices:
                if m_dev.service_device_guid == service_device_guid:
                    return coord

    return next(iter(coordinators.values()))


async def async_setup_entry(hass: HomeAssistant, entry: EltakoConfigEntry) -> bool:
    """Set up Eltako Series 62/64 IP from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    pop = entry.data[CONF_POP]
    scan_interval_sec = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    session = async_get_clientsession(hass, verify_ssl=False)
    client = EltakoClient(
        host=host,
        port=port,
        pop=pop,
        session=session,
        api_key=entry.data.get(CONF_API_KEY) or None,
    )
    try:
        # Reuse the stored apiKey when present; the first authenticated
        # request re-logins transparently if it expired.
        if not client.api_key:
            await client.login()
        system_info = await client.get_system()
    except AuthenticationError as err:
        await client.close()
        raise ConfigEntryAuthFailed(f"Invalid Proof of Possession (PoP): {err}") from err
    except (EltakoConnectionError, EltakoError) as err:
        await client.close()
        raise ConfigEntryNotReady(f"Cannot connect to Eltako gateway at {host}: {err}") from err

    coordinator = EltakoDataUpdateCoordinator(
        hass=hass,
        client=client,
        system_info=system_info,
        update_interval=timedelta(seconds=scan_interval_sec),
        config_entry=entry,
    )

    await coordinator.async_config_entry_first_refresh()

    # Persist a rotated/fresh apiKey so restarts reuse it instead of
    # minting a new one (the device budgets ~10 keys).
    if client.api_key and client.api_key != entry.data.get(CONF_API_KEY):
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_API_KEY: client.api_key}
        )

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Register the gateway device upfront so child entities can reference via_device_id
    dev_reg = dr.async_get(hass)
    gw_name = system_info.product_name
    for d in coordinator.data.devices.values():
        if d.product_guid == system_info.product_guid and d.display_name:
            gw_name = d.display_name
            break
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=coordinator.get_device_identifiers(is_gateway=True),
        manufacturer="Eltako",
        model=system_info.product_name,
        name=gw_name,
        serial_number=system_info.serial_number,
        sw_version=system_info.software_version,
        hw_version=system_info.hardware_version,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _async_register_services(hass)

    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Register domain services if not already registered."""
    if hass.services.has_service(DOMAIN, SERVICE_START_ENOCEAN_SCAN):
        return

    async def handle_identify_device(call: ServiceCall) -> None:
        """Flash the physical LED on the Eltako IP device."""
        coord = _resolve_coordinator(hass, call)
        await coord.client.identify()

    async def handle_rename_device(call: ServiceCall) -> None:
        """Rename a logical device on the Eltako unit and sync with Home Assistant's Device Registry."""
        coord = _resolve_coordinator(hass, call)
        device_guid: Optional[str] = call.data.get("device_guid")
        display_name: str = call.data["display_name"]

        entry_id = coord.config_entry.entry_id if coord.config_entry else None
        dev_reg = dr.async_get(hass)
        if device_guid:
            await coord.client.rename_device(device_guid, display_name)
            ha_dev = (
                dev_reg.async_get_device_by_identifier((DOMAIN, device_guid), entry_id)
                if entry_id and hasattr(dev_reg, "async_get_device_by_identifier")
                else dev_reg.async_get_device(identifiers={(DOMAIN, device_guid)})
            )
            if ha_dev:
                dev_reg.async_update_device(ha_dev.id, name=display_name)
        else:
            await coord.client.update_system_name(display_name)
            ha_dev = (
                dev_reg.async_get_device_by_identifier(
                    (DOMAIN, coord.system_info.serial_number), entry_id
                )
                if entry_id and hasattr(dev_reg, "async_get_device_by_identifier")
                else dev_reg.async_get_device(
                    identifiers={(DOMAIN, coord.system_info.serial_number)}
                )
            )
            if ha_dev:
                dev_reg.async_update_device(ha_dev.id, name=display_name)

        await coord.async_request_refresh()

    async def handle_start_enocean_scan(call: ServiceCall) -> None:
        """Start EnOcean teach-in scan."""
        coord = _resolve_coordinator(hass, call)
        duration = call.data.get("duration", 60)
        await coord.client.start_enocean_scan(duration=duration)
        _LOGGER.info("EnOcean pairing scan initiated on %s", coord.client.host)

    async def handle_pair_enocean_device(call: ServiceCall) -> None:
        """Pair an EnOcean sensor."""
        coord = _resolve_coordinator(hass, call)
        try:
            eur_id = parse_eur_id(call.data["eur_id"], prefer_hex=True)
        except ValueError as err:
            raise HomeAssistantError(f"Invalid EnOcean EURID: {err}") from err
        product_guid = str(call.data["product_guid"])
        display_name = call.data.get("display_name")
        resp = await coord.client.pair_enocean_device(
            eur_id=eur_id, product_guid=product_guid
        )
        device_guid = resp.get("deviceGuid")
        if display_name and device_guid:
            await coord.client.rename_device(device_guid, display_name)
        await coord.async_request_refresh()
        if coord.config_entry:
            await hass.config_entries.async_reload(coord.config_entry.entry_id)
        _LOGGER.info("Paired EnOcean sensor EURID %s (0x%08X)", eur_id, eur_id)

    async def handle_unpair_enocean_device(call: ServiceCall) -> None:
        """Unpair an EnOcean device and remove it from the device registry."""
        coord = _resolve_coordinator(hass, call)
        service_device_guid = call.data.get("service_device_guid")
        device_guid = call.data.get("device_guid")

        if not service_device_guid and not device_guid:
            raise HomeAssistantError(
                "Must provide either service_device_guid or a valid EnOcean device_guid."
            )

        await coord.async_unpair_enocean_device(
            device_guid=device_guid,
            service_device_guid=service_device_guid,
        )
        await coord.async_request_refresh()

    async def handle_legacy_pair_enocean(call: ServiceCall) -> None:
        """Start or continue bidirectional legacy EnOcean pairing (FSR61, FUD61, FSB61, FHK14)."""
        coord = _resolve_coordinator(hass, call)
        step = call.data.get("step", "start")
        product_guid = call.data.get("product_guid")
        payload: dict[str, Any] = {}
        if product_guid:
            payload["productGuid"] = product_guid
        if step == "continue":
            await coord.client.continue_enocean_legacy_pair(payload or None)
        else:
            await coord.client.start_enocean_legacy_pair(payload or None)
        await coord.async_request_refresh()

    async def handle_set_enocean_device_config(call: ServiceCall) -> None:
        """Configure orientation or bridge direction on a paired EnOcean device."""
        coord = _resolve_coordinator(hass, call)
        service_device_guid = call.data.get("service_device_guid")
        device_guid = call.data.get("device_guid")
        if not service_device_guid and device_guid:
            eo_dev = coord.data.enocean_devices.get(device_guid)
            if eo_dev:
                service_device_guid = eo_dev.service_device_guid
        if not service_device_guid:
            raise HomeAssistantError("Could not resolve EnOcean service_device_guid.")
        await coord.client.set_enocean_device_config(
            service_device_guid=service_device_guid,
            orientation=call.data.get("orientation"),
            bridge_direction=call.data.get("bridge_direction"),
        )
        await coord.async_request_refresh()

    async def handle_expose_matter(call: ServiceCall) -> None:
        """Expose a device to the Matter bridge."""
        coord = _resolve_coordinator(hass, call)
        product_guid = call.data["product_guid"]
        device_guid = call.data["device_guid"]
        await coord.client.expose_matter_device(
            product_guid=product_guid, device_guid=device_guid
        )
        await coord.async_request_refresh()
        _LOGGER.info("Exposed device %s to Matter bridge", device_guid)

    async def handle_remove_matter(call: ServiceCall) -> None:
        """Remove a device from the Matter bridge."""
        coord = _resolve_coordinator(hass, call)
        service_device_guid = call.data["service_device_guid"]
        await coord.client.remove_matter_device(service_device_guid=service_device_guid)
        await coord.async_request_refresh()
        _LOGGER.info("Removed service device %s from Matter bridge", service_device_guid)

    async def handle_reset_matter_bridge(call: ServiceCall) -> None:
        """Reset all bridged devices on the Matter service."""
        coord = _resolve_coordinator(hass, call)
        await coord.client.reset_matter_service()
        await coord.async_request_refresh()

    async def handle_create_automation(call: ServiceCall) -> None:
        """Create an on-device automation rule."""
        coord = _resolve_coordinator(hass, call)
        off_timer_sec = call.data.get("off_timer_seconds", 0)
        addons = (
            [AutomationAddOn(type="offTimer", time=int(float(off_timer_sec) * 1000))]
            if off_timer_sec and float(off_timer_sec) > 0
            else []
        )
        rule = AutomationRule(
            automation_guid="",
            active=call.data.get("active", True),
            description=call.data.get("description", ""),
            input_device_guid=call.data["input_device_guid"],
            input_characteristic_identifier=call.data.get(
                "input_characteristic", "input"
            ),
            output_device_guid=call.data["output_device_guid"],
            output_characteristic_identifier=call.data.get(
                "output_characteristic", "relay"
            ),
            logic=call.data.get("logic", "buttonImpulseSwitch"),
            addons=addons,
        )
        await coord.client.create_automation(rule)
        await coord.async_request_refresh()

    async def handle_update_automation(call: ServiceCall) -> None:
        """Update an existing on-device automation rule."""
        coord = _resolve_coordinator(hass, call)
        automation_guid = call.data["automation_guid"]
        existing = next(
            (
                r
                for r in coord.data.automations
                if r.automation_guid == automation_guid
            ),
            None,
        )
        if not existing:
            existing = await coord.client.get_automation(automation_guid)

        logic = call.data.get("logic", existing.logic)
        active = call.data.get("active", existing.active)
        description = call.data.get("description", existing.description)
        off_timer_sec = call.data.get("off_timer_seconds")
        off_timer_ms = (
            int(float(off_timer_sec) * 1000)
            if off_timer_sec is not None
            else existing.off_timer_ms
        )
        await coord.client.set_automation_logic(
            existing,
            logic=logic,
            off_timer_ms=off_timer_ms,
            active=active,
            description=description,
        )
        await coord.async_request_refresh()

    async def handle_delete_automation(call: ServiceCall) -> None:
        """Delete an on-device automation rule."""
        coord = _resolve_coordinator(hass, call)
        await coord.client.delete_automation(call.data["automation_guid"])
        await coord.async_request_refresh()

    async def handle_reset_automations(call: ServiceCall) -> None:
        """Reset all on-device automations to factory default."""
        coord = _resolve_coordinator(hass, call)
        await coord.client.reset_automations()
        await coord.async_request_refresh()

    async def handle_upload_firmware(call: ServiceCall) -> None:
        """Upload a local firmware image (.bin) to the Eltako device."""
        coord = _resolve_coordinator(hass, call)
        file_path = Path(call.data["file_path"])
        if not file_path.is_file():
            raise HomeAssistantError(f"Firmware file not found: {file_path}")
        desired_version = call.data.get("desired_version")
        if desired_version:
            await coord.client.prepare_firmware_update(
                {"update": {"desiredVersion": desired_version}}
            )
        firmware_bytes = await hass.async_add_executor_job(file_path.read_bytes)
        await coord.client.upload_firmware_binary(firmware_bytes)
        await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_IDENTIFY_DEVICE, handle_identify_device
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RENAME_DEVICE,
        handle_rename_device,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Optional("device_guid"): cv.string,
                vol.Required("display_name"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_ENOCEAN_SCAN,
        handle_start_enocean_scan,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Optional("duration", default=60): cv.positive_int,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PAIR_ENOCEAN_DEVICE,
        handle_pair_enocean_device,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Required("eur_id"): vol.Any(cv.positive_int, cv.string),
                vol.Required("product_guid"): cv.string,
                vol.Optional("display_name"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UNPAIR_ENOCEAN_DEVICE,
        handle_unpair_enocean_device,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Optional("service_device_guid"): cv.string,
                vol.Optional("device_guid"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LEGACY_PAIR_ENOCEAN,
        handle_legacy_pair_enocean,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Optional("step", default="start"): vol.In(["start", "continue"]),
                vol.Optional("product_guid"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ENOCEAN_DEVICE_CONFIG,
        handle_set_enocean_device_config,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Optional("service_device_guid"): cv.string,
                vol.Optional("device_guid"): cv.string,
                vol.Optional("orientation"): cv.string,
                vol.Optional("bridge_direction"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPOSE_MATTER_DEVICE,
        handle_expose_matter,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
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
                vol.Optional("entry_id"): cv.string,
                vol.Required("service_device_guid"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_MATTER_BRIDGE,
        handle_reset_matter_bridge,
        schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_AUTOMATION,
        handle_create_automation,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Required("input_device_guid"): cv.string,
                vol.Optional("description", default=""): cv.string,
                vol.Optional("input_characteristic", default="input"): cv.string,
                vol.Required("output_device_guid"): cv.string,
                vol.Optional("output_characteristic", default="relay"): cv.string,
                vol.Optional("logic", default="buttonImpulseSwitch"): cv.string,
                vol.Optional("off_timer_seconds", default=0): vol.Coerce(float),
                vol.Optional("active", default=True): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_AUTOMATION,
        handle_update_automation,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Required("automation_guid"): cv.string,
                vol.Optional("description"): cv.string,
                vol.Optional("logic"): cv.string,
                vol.Optional("off_timer_seconds"): vol.Coerce(float),
                vol.Optional("active"): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_AUTOMATION,
        handle_delete_automation,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Required("automation_guid"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_AUTOMATIONS,
        handle_reset_automations,
        schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPLOAD_FIRMWARE,
        handle_upload_firmware,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Required("file_path"): cv.string,
                vol.Optional("desired_version"): cv.string,
            }
        ),
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: EltakoConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow deleting paired EnOcean or stale child devices from Home Assistant UI."""
    coordinator: Optional[EltakoDataUpdateCoordinator] = hass.data.get(
        DOMAIN, {}
    ).get(config_entry.entry_id) or getattr(config_entry, "runtime_data", None)
    if coordinator is None:
        return True

    eltako_ids = {
        ident_val
        for domain, ident_val in device_entry.identifiers
        if domain == DOMAIN
    }

    # Never allow deleting the primary gateway device
    if coordinator.system_info.serial_number in eltako_ids:
        return False

    for ident in eltako_ids:
        eo_dev = coordinator.data.enocean_devices.get(ident)
        if eo_dev is None:
            eo_dev = next(
                (
                    d
                    for d in coordinator.data.enocean_devices.values()
                    if d.service_device_guid == ident
                ),
                None,
            )
        if eo_dev is not None:
            await coordinator.async_unpair_enocean_device(
                device_guid=eo_dev.device_guid,
                service_device_guid=eo_dev.service_device_guid,
            )
            await coordinator.async_request_refresh()
            return True

        # Prevent deleting active built-in hardware devices (like Wired Input)
        if ident in coordinator.data.devices:
            return False

    # Allow deleting stale/orphaned devices no longer on the gateway
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: Optional[EltakoDataUpdateCoordinator] = hass.data.get(
            DOMAIN, {}
        ).pop(entry.entry_id, None)
        if coordinator is None and hasattr(entry, "runtime_data"):
            coordinator = entry.runtime_data
        if coordinator:
            await coordinator.client.close()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
