"""Diagnostics support for Eltako Series 62/64 IP."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_POP
from .coordinator import EltakoConfigEntry
from .entity import get_coordinator

TO_REDACT = {
    CONF_POP,
    CONF_HOST,
    "apiKey",
    "serial_number",
    "eur_id",
    "eurId",
    "certificate",
    "thumbprint",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EltakoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = get_coordinator(hass, entry)

    data = {
        "entry_data": dict(entry.data),
        "entry_options": dict(entry.options),
        "system": {
            "software_version": coordinator.system_info.software_version,
            "hardware_version": coordinator.system_info.hardware_version,
            "product_name": coordinator.system_info.product_name,
            "product_type": coordinator.system_info.product_type,
            "product_guid": coordinator.system_info.product_guid,
            "serial_number": coordinator.system_info.serial_number,
        },
        "devices": [
            {
                "product_guid": d.product_guid,
                "display_name": d.display_name,
                "functions": [
                    {"identifier": f.identifier, "type": f.type, "value": f.value}
                    for f in d.functions
                ],
                "info": [
                    {"identifier": i.identifier, "type": i.type, "value": i.value}
                    for i in d.infos
                ],
                "settings": [
                    {"identifier": s.identifier, "type": s.type, "value": s.value}
                    for s in d.settings
                ],
            }
            for d in coordinator.data.devices.values()
        ],
        "enocean_status": (
            {
                "health": coordinator.data.enocean_status.health,
                "max_eur_ids": coordinator.data.enocean_status.max_eur_ids,
                "free_eur_ids": coordinator.data.enocean_status.free_eur_ids,
                "hardware_filter_state": coordinator.data.enocean_status.hardware_filter_state,
            }
            if coordinator.data.enocean_status
            else None
        ),
        "enocean_devices": [
            {
                "service_device_guid": d.service_device_guid,
                "device_guid": d.device_guid,
                "product_guid": d.product_guid,
                "eur_id": d.eur_id,
                "signal_strength": d.signal_strength,
                "bridge_direction": d.bridge_direction,
                "orientation": d.orientation,
                "last_seen": d.last_seen,
            }
            for d in coordinator.data.enocean_devices.values()
        ],
        "matter_devices": [
            {
                "service_device_guid": d.service_device_guid,
                "device_guid": d.device_guid,
                "product_guid": d.product_guid,
            }
            for d in coordinator.data.matter_devices
        ],
        "update_config": {
            "update_server_uri": coordinator.data.update_config.update_server_uri,
            "auto_update": coordinator.data.update_config.auto_update,
            "update_schedule": coordinator.data.update_config.update_schedule,
        },
        "firmware_info": {
            "current_version": coordinator.data.firmware_info.current_version,
            "desired_version": coordinator.data.firmware_info.desired_version,
            "location": coordinator.data.firmware_info.location,
            "certificate": coordinator.data.firmware_info.certificate,
            "thumbprint": coordinator.data.firmware_info.thumbprint,
        },
        "automations": [r.to_dict() for r in coordinator.data.automations],
    }

    return async_redact_data(data, TO_REDACT)
