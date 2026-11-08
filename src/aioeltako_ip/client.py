"""Async HTTP client for Eltako Series 62/64 REST API using aiohttp."""

from __future__ import annotations

import ipaddress
import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse
import aiohttp

from .exceptions import (
    AuthenticationError,
    DeviceNotFoundError,
    EltakoConnectionError,
    EltakoError,
)
from .models import (
    AutomationAddOn,
    AutomationRule,
    Characteristic,
    Device,
    EnOceanDevice,
    EnOceanLegacyPairStatus,
    EnOceanScanResultItem,
    EnOceanStatus,
    FirmwareUpdateInfo,
    MatterDevice,
    MatterServiceInfo,
    ProductSpec,
    SystemInfo,
    UpdateConfig,
)

_LOGGER = logging.getLogger(__name__)


def normalize_host(host: str) -> str:
    """Normalize a hostname, IP address, or pasted URL into a clean host string."""
    cleaned = host.strip()
    if "://" in cleaned:
        parsed = urlparse(cleaned)
        if parsed.hostname:
            cleaned = parsed.hostname
    else:
        cleaned = cleaned.split("/", 1)[0]
        # Strip ":port" if not an IPv6 address
        if cleaned.count(":") == 1 and not cleaned.startswith("["):
            cleaned = cleaned.split(":", 1)[0]
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    cleaned = cleaned.rstrip(".")
    return cleaned


class EltakoClient:
    """Async API Client for Eltako Series 62/64 based on aiohttp."""

    def __init__(
        self,
        host: str,
        pop: Optional[str] = None,
        api_key: Optional[str] = None,
        port: int = 443,
        ssl_verify: bool = False,
        timeout: float = 10.0,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        clean_host = normalize_host(host)
        self.host = clean_host
        self.port = port
        self.pop = pop
        self.api_key = api_key
        try:
            is_ipv6 = isinstance(ipaddress.ip_address(clean_host), ipaddress.IPv6Address)
        except ValueError:
            is_ipv6 = False
        url_host = f"[{clean_host}]" if is_ipv6 else clean_host
        self.root_url = f"https://{url_host}:{port}"
        self.base_url = f"{self.root_url}/api/v0"
        self._ssl: bool = ssl_verify
        self._timeout = timeout
        self._external_session = session is not None
        self._session = session

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._ssl)
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close client session if internally created."""
        if not self._external_session and self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> EltakoClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def login(self) -> str:
        """Authenticate using Proof of Possession (PoP) to acquire an API key."""
        if not self.pop:
            raise AuthenticationError(
                "Cannot login: Proof of Possession (PoP) code not provided."
            )

        session = await self._get_session()
        url = f"{self.base_url}/login"
        payload = {"user": "admin", "password": self.pop}

        try:
            async with session.post(url, json=payload, ssl=self._ssl) as resp:
                if resp.status == 401:
                    raise AuthenticationError("Invalid Proof of Possession code.")
                if resp.status != 200:
                    text = await resp.text()
                    raise EltakoError(
                        f"Login failed with status {resp.status}: {text}"
                    )

                data = await resp.json()
        except aiohttp.ClientError as err:
            raise EltakoConnectionError(
                f"Failed to connect to device during login: {err}"
            ) from err

        self.api_key = data.get("apiKey")
        if not self.api_key:
            raise EltakoError("Device returned OK response but no apiKey was found.")

        _LOGGER.debug("Successfully logged in to Eltako device at %s", self.host)
        return self.api_key

    async def _request(
        self,
        method: str,
        path: str,
        retry_auth: bool = True,
        use_root: bool = False,
        require_auth: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Execute authenticated HTTP request with automatic token refresh."""
        if require_auth and not self.api_key:
            await self.login()

        session = await self._get_session()
        headers = dict(kwargs.pop("headers", {}))
        if require_auth and self.api_key:
            headers["Authorization"] = self.api_key

        prefix = self.root_url if use_root else self.base_url
        url = f"{prefix}{path}"

        try:
            async with session.request(
                method, url, headers=headers, ssl=self._ssl, **kwargs
            ) as resp:
                if resp.status == 401 and retry_auth and self.pop:
                    _LOGGER.info(
                        "API key expired or invalid; re-authenticating with PoP..."
                    )
                    await self.login()
                    if self.api_key:
                        headers["Authorization"] = self.api_key
                    async with session.request(
                        method, url, headers=headers, ssl=self._ssl, **kwargs
                    ) as retry_resp:
                        return await self._handle_response(retry_resp, path)

                return await self._handle_response(resp, path)
        except aiohttp.ClientError as err:
            raise EltakoConnectionError(
                f"Connection error requesting {path}: {err}"
            ) from err

    async def _handle_response(self, resp: aiohttp.ClientResponse, path: str) -> Any:
        if resp.status == 401:
            raise AuthenticationError("Request unauthorized (401).")
        if resp.status == 404:
            raise DeviceNotFoundError(f"Endpoint or resource not found (404): {path}")
        if resp.status >= 400:
            text = await resp.text()
            raise EltakoError(f"HTTP {resp.status} error from {path}: {text}")

        if resp.status in (200, 201, 202):
            text = await resp.text()
            if not text or not text.strip():
                return True
            try:
                return json.loads(text)
            except ValueError:
                return True
        return True

    # -------------------------------------------------------------------------
    # System, Well-Known & Physical Identification (Phase 1)
    # -------------------------------------------------------------------------

    async def get_well_known(self) -> dict[str, Any]:
        """Fetch unauthenticated well-known API metadata."""
        data = await self._request(
            "GET",
            "/.well-known/eltako/devices",
            use_root=True,
            require_auth=False,
        )
        return data if isinstance(data, dict) else {}

    async def identify(self) -> bool:
        """Flash LED / pulse actuator to physically identify the device."""
        try:
            await self._request("POST", "/identify", use_root=True)
            return True
        except DeviceNotFoundError:
            await self._request("POST", "/identify", use_root=False)
            return True

    async def get_system(self) -> SystemInfo:
        """Fetch system and hardware information."""
        data = await self._request("GET", "/system")
        return SystemInfo.from_dict(data)

    async def update_system_name(
        self, product_name: str, system_info: Optional[SystemInfo] = None
    ) -> SystemInfo:
        """Update the system product name on the device."""
        current = system_info or await self.get_system()
        payload = current.to_dict()
        payload["product"]["productName"] = product_name
        data = await self._request("PUT", "/system", json=payload)
        if isinstance(data, dict) and "product" in data:
            return SystemInfo.from_dict(data)
        current.product_name = product_name
        return current

    async def get_products(self) -> dict[str, ProductSpec]:
        """Fetch the on-device product metadata database (/products)."""
        data = await self._request("GET", "/products")
        products_list = data.get("products", []) if isinstance(data, dict) else []
        result: dict[str, ProductSpec] = {}
        for item in products_list:
            if isinstance(item, dict) and "productGuid" in item:
                spec = ProductSpec.from_dict(item)
                result[spec.product_guid] = spec
        return result

    # -------------------------------------------------------------------------
    # Devices, Functions, Settings & Renaming (Phase 1 & Phase 6)
    # -------------------------------------------------------------------------

    async def get_devices(self) -> list[Device]:
        """Fetch all devices managed by the gateway."""
        data = await self._request("GET", "/devices")
        return [Device.from_dict(item) for item in data]

    async def get_device(self, device_guid: str) -> Device:
        """Fetch single device by its GUID."""
        data = await self._request("GET", f"/devices/{device_guid}")
        return Device.from_dict(data)

    async def update_device(self, device: Device) -> bool:
        """Update an entire device object (including displayName, functions, settings)."""
        res = await self._request(
            "PUT",
            f"/devices/{device.device_guid}",
            json=device.to_dict(),
        )
        return res is not None

    async def rename_device(
        self,
        device_guid: str,
        display_name: str,
        device: Optional[Device] = None,
    ) -> bool:
        """Update a device's persistent displayName in on-device flash memory."""
        target = device or await self.get_device(device_guid)
        updated = Device(
            device_guid=target.device_guid,
            product_guid=target.product_guid,
            display_name=display_name,
            functions=list(target.functions),
            infos=list(target.infos),
            settings=list(target.settings),
        )
        return await self.update_device(updated)

    async def delete_device(self, device_guid: str) -> bool:
        """Delete an unlinked logical device from /devices."""
        res = await self._request("DELETE", f"/devices/{device_guid}")
        return res is not None

    async def set_function(
        self,
        device_guid: str,
        identifier: str,
        value: Any,
        char_type: str = "enumeration",
    ) -> bool:
        """Update a device function characteristic."""
        payload = {
            "identifier": identifier,
            "type": char_type,
            "value": value,
        }
        res = await self._request(
            "PUT",
            f"/devices/{device_guid}/functions/{identifier}",
            json=payload,
        )
        return res is not None

    async def set_functions(
        self,
        device_guid: str,
        functions: list[Characteristic],
    ) -> bool:
        """Update multiple function characteristics simultaneously."""
        payload = [f.to_dict() for f in functions]
        res = await self._request(
            "PUT",
            f"/devices/{device_guid}/functions",
            json=payload,
        )
        return res is not None

    async def get_settings(self, device_guid: str) -> list[Characteristic]:
        """Get all configurable settings for a device."""
        data = await self._request("GET", f"/devices/{device_guid}/settings")
        if isinstance(data, list):
            return [Characteristic.from_dict(item) for item in data]
        return []

    async def set_setting(
        self,
        device_guid: str,
        identifier: str,
        value: Any,
        char_type: str = "enumeration",
    ) -> bool:
        """Update a single persistent hardware setting on a device."""
        payload = {
            "identifier": identifier,
            "type": char_type,
            "value": value,
        }
        res = await self._request(
            "PUT",
            f"/devices/{device_guid}/settings/{identifier}",
            json=payload,
        )
        return res is not None

    async def set_settings(
        self,
        device_guid: str,
        settings: list[Characteristic],
    ) -> bool:
        """Update all settings for a device."""
        payload = [s.to_dict() for s in settings]
        res = await self._request(
            "PUT",
            f"/devices/{device_guid}/settings",
            json=payload,
        )
        return res is not None

    async def set_relay(
        self,
        device_guid: str,
        state: bool,
        identifier: str = "relay",
    ) -> bool:
        """Turn a relay switch channel on or off."""
        val = "on" if state else "off"
        return await self.set_function(
            device_guid, identifier, val, char_type="enumeration"
        )

    async def set_brightness(self, device_guid: str, brightness: int) -> bool:
        """Set dimmer target brightness (0-100%)."""
        clamped = max(0, min(100, int(brightness)))
        return await self.set_function(
            device_guid, "targetBrightness", clamped, char_type="number"
        )

    async def set_cover_position(self, device_guid: str, position: int) -> bool:
        """Set roller shutter / blind target position (0-100%)."""
        clamped = max(0, min(100, int(position)))
        return await self.set_function(
            device_guid, "targetPosition", clamped, char_type="number"
        )

    async def set_cover_tilt(self, device_guid: str, tilt: int) -> bool:
        """Set blind slat target tilt angle (0-100%)."""
        clamped = max(0, min(100, int(tilt)))
        return await self.set_function(
            device_guid, "targetTilt", clamped, char_type="number"
        )

    # -------------------------------------------------------------------------
    # EnOcean Provisioning & Lifecycle Management (Phase 2)
    # -------------------------------------------------------------------------

    async def get_enocean_status(self) -> EnOceanStatus:
        """Fetch EnOcean transceiver health and radio ID status."""
        data = await self._request("GET", "/services/enocean/status")
        return EnOceanStatus.from_dict(data)

    async def get_enocean_devices(self) -> list[EnOceanDevice]:
        """Fetch all paired EnOcean devices."""
        data = await self._request("GET", "/services/enocean/devices")
        return [EnOceanDevice.from_dict(item) for item in data]

    async def start_enocean_scan(self, duration: int = 60) -> None:
        """Initiate teach-in scanning procedure for new EnOcean sensors."""
        scan_duration = max(15, int(duration))
        await self._request(
            "POST", "/services/enocean/scan", json={"duration": scan_duration}
        )

    async def get_enocean_scan_results(self) -> list[EnOceanScanResultItem]:
        """Get discovered devices from active or last scan."""
        data = await self._request("GET", "/services/enocean/scan")
        if isinstance(data, list):
            return [EnOceanScanResultItem.from_dict(item) for item in data]
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return [EnOceanScanResultItem.from_dict(item) for item in data["items"]]
        return []

    async def pair_enocean_device(
        self,
        eur_id: int,
        product_guid: str,
        bridge_direction: str = "ingress",
        device_guid: str = "",
    ) -> dict[str, Any]:
        """Pair an EnOcean sensor to the device registry."""
        payload = {
            "eurId": int(eur_id),
            "productGuid": product_guid,
            "bridgeDirection": bridge_direction,
            "deviceGuid": device_guid,
        }
        data = await self._request("POST", "/services/enocean/devices", json=payload)
        return data if isinstance(data, dict) else {"eurId": eur_id, "productGuid": product_guid}

    async def delete_enocean_device(
        self,
        service_device_guid: str,
        device_guid: Optional[str] = None,
    ) -> bool:
        """Unpair and delete an EnOcean device from NVRAM (and optionally its logical device)."""
        await self._request(
            "DELETE", f"/services/enocean/devices/{service_device_guid}"
        )
        if device_guid:
            try:
                await self.delete_device(device_guid)
            except EltakoError:
                _LOGGER.debug(
                    "Logical device %s already removed or still linked", device_guid
                )
        return True

    async def get_enocean_device_config(
        self, service_device_guid: str
    ) -> dict[str, Any]:
        """Get per-device EnOcean custom configuration (e.g., orientation)."""
        data = await self._request(
            "GET", f"/services/enocean/devices/{service_device_guid}/config"
        )
        return data if isinstance(data, dict) else {}

    async def set_enocean_device_config(
        self,
        service_device_guid: str,
        config: Optional[dict[str, Any]] = None,
        *,
        orientation: Optional[str] = None,
        bridge_direction: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update per-device EnOcean custom configuration (e.g., orientation)."""
        payload: dict[str, Any] = dict(config or {})
        if orientation is not None:
            payload["orientation"] = orientation
        if bridge_direction is not None:
            payload["bridgeDirection"] = bridge_direction
        data = await self._request(
            "PUT",
            f"/services/enocean/devices/{service_device_guid}/config",
            json=payload,
        )
        return data if isinstance(data, dict) else payload

    async def get_enocean_configuration(self) -> dict[str, Any]:
        """Get EnOcean configuration (repeater mode, level, base ID)."""
        data = await self._request("GET", "/services/enocean/configuration")
        return data if isinstance(data, dict) else {}

    async def set_enocean_repeater(
        self,
        repeater_level: str,
        repeater_mode: Optional[str] = None,
    ) -> None:
        """Configure on-device EnOcean repeater (off, oneLevel, twoLevel)."""
        if repeater_mode is None:
            repeater_mode = "off" if repeater_level == "off" else "on"
        payload = {
            "repeaterLevel": repeater_level,
            "repeaterMode": repeater_mode,
        }
        await self._request("PATCH", "/services/enocean/configuration", json=payload)

    async def get_enocean_legacy_pair_supported_devices(self) -> list[str]:
        """Get list of product GUIDs supported by legacy pairing (FSR61/FUD61/FSB61/FHK14)."""
        data = await self._request(
            "GET", "/services/enocean/legacypair/info/supported-devices"
        )
        if isinstance(data, list):
            return [str(item) for item in data]
        return []

    async def start_enocean_legacy_pair(
        self,
        product_guid: str | dict[str, Any] | None = None,
        teach_in: bool = True,
    ) -> bool:
        """Start a legacy pairing session (POST /services/enocean/legacypair/add)."""
        if isinstance(product_guid, dict):
            payload = dict(product_guid)
            payload.setdefault("teachIn", bool(teach_in))
        else:
            payload = {
                "productGuid": product_guid or "",
                "teachIn": bool(teach_in),
            }
        res = await self._request(
            "POST", "/services/enocean/legacypair/add", json=payload
        )
        return res is not None

    async def continue_enocean_legacy_pair(
        self,
        product_guid: str | dict[str, Any] | None = None,
        teach_in: bool = False,
        taught_in: bool = True,
    ) -> bool:
        """Continue legacy pairing (send teach-in or confirmation control sequence)."""
        if isinstance(product_guid, dict):
            payload = dict(product_guid)
            payload.setdefault("teachIn", bool(teach_in))
            payload.setdefault("taughtIn", bool(taught_in))
        else:
            payload = {
                "productGuid": product_guid or "",
                "teachIn": bool(teach_in),
                "taughtIn": bool(taught_in),
            }
        res = await self._request(
            "PUT", "/services/enocean/legacypair/add", json=payload
        )
        return res is not None

    async def get_enocean_legacy_pair_status(self) -> EnOceanLegacyPairStatus:
        """Fetch current status of the legacy pairing procedure."""
        data = await self._request("GET", "/services/enocean/legacypair/status")
        return EnOceanLegacyPairStatus.from_dict(
            data if isinstance(data, dict) else {}
        )

    # -------------------------------------------------------------------------
    # Matter Bridge Management & Exposure (Phase 3)
    # -------------------------------------------------------------------------

    async def get_matter_service(self) -> MatterServiceInfo:
        """Get full Matter bridge service info including configuration and bridged devices."""
        data = await self._request("GET", "/services/matter")
        return MatterServiceInfo.from_dict(data if isinstance(data, dict) else {})

    async def get_matter_devices(self) -> list[MatterDevice]:
        """Get all devices exposed on the Matter bridge."""
        data = await self._request("GET", "/services/matter/devices")
        return [MatterDevice.from_dict(item) for item in data]

    async def expose_matter_device(
        self,
        product_guid: str,
        device_guid: str,
        config: Optional[dict[str, Any]] = None,
    ) -> MatterDevice:
        """Expose a device to the Matter bridge."""
        payload: dict[str, Any] = {
            "productGuid": product_guid,
            "deviceGuid": device_guid,
        }
        if config is not None:
            payload["config"] = config
        data = await self._request("POST", "/services/matter/devices", json=payload)
        if isinstance(data, dict) and "serviceDeviceGuid" in data:
            return MatterDevice.from_dict(data)
        return MatterDevice(
            service_device_guid="",
            product_guid=product_guid,
            device_guid=device_guid,
        )

    async def update_matter_device_config(
        self,
        service_device_guid: str,
        config: dict[str, Any],
    ) -> bool:
        """Update channel configuration of a bridged Matter device (e.g. momentary vs latching)."""
        res = await self._request(
            "PUT",
            f"/services/matter/devices/{service_device_guid}/config",
            json=config,
        )
        return res is not None

    async def remove_matter_device(self, service_device_guid: str) -> bool:
        """Remove a device from being bridged to Matter."""
        await self._request("DELETE", f"/services/matter/devices/{service_device_guid}")
        return True

    async def reset_matter_service(self) -> bool:
        """Factory reset the internal Matter bridge and unpair all Matter fabrics."""
        try:
            res = await self._request("POST", "/services/matter/reset")
            return res is not None
        except DeviceNotFoundError:
            res = await self._request("DELETE", "/services/matter")
            return res is not None

    # -------------------------------------------------------------------------
    # Firmware Lifecycle & Update Management (Phase 4)
    # -------------------------------------------------------------------------

    async def get_update_config(self) -> UpdateConfig:
        """Retrieve firmware update configuration (/update/config)."""
        data = await self._request("GET", "/update/config")
        return UpdateConfig.from_dict(data if isinstance(data, dict) else {})

    async def set_update_config(
        self,
        auto_update: Optional[bool] = None,
        update_schedule: Optional[str] = None,
        update_server_uri: Optional[str] = None,
    ) -> bool:
        """Update firmware auto-update settings (/update/config)."""
        payload: dict[str, Any] = {}
        if auto_update is not None:
            payload["autoUpdate"] = bool(auto_update)
        if update_schedule is not None:
            payload["updateSchedule"] = update_schedule
        if update_server_uri is not None:
            payload["updateServerUri"] = update_server_uri
        res = await self._request("PUT", "/update/config", json=payload)
        return res is not None

    async def reset_update_config(self) -> bool:
        """Reset update configuration to factory defaults."""
        res = await self._request("DELETE", "/update/config")
        return res is not None

    async def get_firmware_update_info(self) -> FirmwareUpdateInfo:
        """Retrieve firmware update version and server metadata (/update/firmware)."""
        data = await self._request("GET", "/update/firmware")
        return FirmwareUpdateInfo.from_dict(data if isinstance(data, dict) else {})

    async def prepare_firmware_update(
        self, metadata: str | dict[str, Any]
    ) -> bool:
        """Prepare the device for a firmware binary upload."""
        payload = metadata if isinstance(metadata, dict) else {"metadata": metadata}
        try:
            res = await self._request("PUT", "/update/firmware", json=payload)
            return res is not None
        except DeviceNotFoundError:
            res = await self._request("POST", "/update/prepare", json=payload)
            return res is not None

    async def upload_firmware_binary(self, binary_data: bytes) -> bool:
        """Upload raw firmware binary image (/update/firmware/bin or /update/firmware)."""
        try:
            res = await self._request(
                "PUT",
                "/update/firmware/bin",
                headers={"Content-Type": "application/octet-stream"},
                data=binary_data,
            )
            return res is not None
        except DeviceNotFoundError:
            res = await self._request(
                "POST",
                "/update/firmware",
                headers={"Content-Type": "application/octet-stream"},
                data=binary_data,
            )
            return res is not None

    # -------------------------------------------------------------------------
    # Autonomous On-Device Automations (Phase 5 & Phase 1 Wired Input Mode)
    # -------------------------------------------------------------------------

    async def get_automations(self) -> list[AutomationRule]:
        """Fetch all on-device autonomous automations."""
        data = await self._request("GET", "/services/eltako/automations")
        if isinstance(data, list):
            return [AutomationRule.from_dict(item) for item in data]
        return []

    async def get_automation(self, automation_guid: str) -> AutomationRule:
        """Fetch a single on-device automation by GUID."""
        data = await self._request(
            "GET", f"/services/eltako/automations/{automation_guid}"
        )
        return AutomationRule.from_dict(data)

    async def create_automation(self, rule: AutomationRule) -> AutomationRule:
        """Create a new on-device hardware binding automation."""
        data = await self._request(
            "POST",
            "/services/eltako/automations",
            json=rule.to_payload(include_guid=False),
        )
        if isinstance(data, dict) and "configuration" in data:
            return AutomationRule.from_dict(data)
        return rule

    async def update_automation(self, rule: AutomationRule) -> bool:
        """Update an existing on-device automation rule."""
        res = await self._request(
            "PUT",
            f"/services/eltako/automations/{rule.automation_guid}",
            json=rule.to_payload(include_guid=True),
        )
        return res is not None

    async def delete_automation(self, automation_guid: str) -> bool:
        """Delete a specific on-device automation rule."""
        res = await self._request(
            "DELETE", f"/services/eltako/automations/{automation_guid}"
        )
        return res is not None

    async def reset_automations(self) -> bool:
        """Reset all on-device automations back to factory defaults."""
        res = await self._request("DELETE", "/services/eltako/automations")
        return res is not None

    async def set_automation_logic(
        self,
        rule: AutomationRule,
        logic: str,
        off_timer_ms: Optional[int] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """Update the logic (e.g. buttonImpulseSwitch vs buttonSwitch) and optional offTimer of a rule."""
        new_addons: list[AutomationAddOn] = [
            a for a in rule.add_ons if a.type != "offTimer"
        ]
        # buttonSwitch (bistable toggle on any edge) does not support offTimer on hardware
        supports_off_timer = logic != "buttonSwitch"
        if supports_off_timer:
            if off_timer_ms is not None and off_timer_ms > 0:
                new_addons.append(
                    AutomationAddOn(type="offTimer", time=int(off_timer_ms), data=None)
                )
            elif off_timer_ms is None:
                existing_timer = rule.get_addon("offTimer")
                if existing_timer is not None:
                    new_addons.append(existing_timer)

        updated = AutomationRule(
            automation_guid=rule.automation_guid,
            enabled=rule.enabled if active is None else bool(active),
            description=rule.description,
            logic=logic,
            input_device_guid=rule.input_device_guid,
            input_characteristic_identifier=rule.input_characteristic_identifier,
            output_device_guid=rule.output_device_guid,
            output_characteristic_identifier=rule.output_characteristic_identifier,
            add_ons=new_addons,
            logic_configuration=dict(rule.logic_configuration),
        )
        try:
            return await self.update_automation(updated)
        except EltakoError as err:
            if "offTimer is not supported" in str(err) and any(
                a.type == "offTimer" for a in updated.add_ons
            ):
                updated.add_ons = [
                    a for a in updated.add_ons if a.type != "offTimer"
                ]
                return await self.update_automation(updated)
            raise
