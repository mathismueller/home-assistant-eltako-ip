"""Async HTTP client for Eltako Series 62/64 REST API using aiohttp."""

from __future__ import annotations

import logging
from typing import Any, Optional
import aiohttp

from .exceptions import (
    AuthenticationError,
    DeviceNotFoundError,
    EltakoConnectionError,
    EltakoError,
)
from .models import (
    Device,
    EnOceanDevice,
    EnOceanScanResultItem,
    EnOceanStatus,
    MatterDevice,
    SystemInfo,
)

_LOGGER = logging.getLogger(__name__)


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
        self.host = host
        self.port = port
        self.pop = pop
        self.api_key = api_key
        self.base_url = f"https://{host}:{port}/api/v0"
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
            raise AuthenticationError("Cannot login: Proof of Possession (PoP) code not provided.")

        session = await self._get_session()
        url = f"{self.base_url}/login"
        payload = {"user": "admin", "password": self.pop}

        try:
            async with session.post(url, json=payload, ssl=self._ssl) as resp:
                if resp.status == 401:
                    raise AuthenticationError("Invalid Proof of Possession code.")
                if resp.status != 200:
                    text = await resp.text()
                    raise EltakoError(f"Login failed with status {resp.status}: {text}")

                data = await resp.json()
        except aiohttp.ClientError as err:
            raise EltakoConnectionError(f"Failed to connect to device during login: {err}") from err

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
        **kwargs: Any,
    ) -> Any:
        """Execute authenticated HTTP request with automatic token refresh."""
        if not self.api_key:
            await self.login()

        session = await self._get_session()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = self.api_key

        url = f"{self.base_url}{path}"

        try:
            async with session.request(method, url, headers=headers, ssl=self._ssl, **kwargs) as resp:
                if resp.status == 401 and retry_auth and self.pop:
                    _LOGGER.info("API key expired or invalid; re-authenticating with PoP...")
                    await self.login()
                    headers["Authorization"] = self.api_key
                    async with session.request(method, url, headers=headers, ssl=self._ssl, **kwargs) as retry_resp:
                        return await self._handle_response(retry_resp, path)

                return await self._handle_response(resp, path)
        except aiohttp.ClientError as err:
            raise EltakoConnectionError(f"Connection error requesting {path}: {err}") from err

    async def _handle_response(self, resp: aiohttp.ClientResponse, path: str) -> Any:
        if resp.status == 401:
            raise AuthenticationError("Request unauthorized (401).")
        if resp.status == 404:
            raise DeviceNotFoundError(f"Endpoint or resource not found (404): {path}")
        if resp.status >= 400:
            text = await resp.text()
            raise EltakoError(f"HTTP {resp.status} error from {path}: {text}")

        if resp.status in (200, 201):
            return await resp.json()
        return True

    async def get_system(self) -> SystemInfo:
        """Fetch system and hardware information."""
        data = await self._request("GET", "/system")
        return SystemInfo.from_dict(data)

    async def get_devices(self) -> list[Device]:
        """Fetch all devices managed by the gateway."""
        data = await self._request("GET", "/devices")
        return [Device.from_dict(item) for item in data]

    async def get_device(self, device_guid: str) -> Device:
        """Fetch single device by its GUID."""
        data = await self._request("GET", f"/devices/{device_guid}")
        return Device.from_dict(data)

    async def set_function(
        self,
        device_guid: str,
        identifier: str,
        value: Any,
        char_type: str = "enumeration",
    ) -> bool:
        """Update a device function (e.g., relay on/off)."""
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
        return bool(res)

    async def set_relay(self, device_guid: str, state: bool) -> bool:
        """Turn relay switch on or off."""
        val = "on" if state else "off"
        return await self.set_function(device_guid, "relay", val, char_type="enumeration")

    async def get_enocean_status(self) -> EnOceanStatus:
        """Fetch EnOcean transceiver health and radio ID status."""
        data = await self._request("GET", "/services/enocean/status")
        return EnOceanStatus.from_dict(data)

    async def get_enocean_devices(self) -> list[EnOceanDevice]:
        """Fetch all paired EnOcean devices."""
        data = await self._request("GET", "/services/enocean/devices")
        return [EnOceanDevice.from_dict(item) for item in data]

    async def start_enocean_scan(self) -> None:
        """Initiate teach-in scanning procedure for new EnOcean sensors."""
        await self._request("POST", "/services/enocean/scan")

    async def get_enocean_scan_results(self) -> list[EnOceanScanResultItem]:
        """Get discovered devices from active or last scan."""
        data = await self._request("GET", "/services/enocean/scan")
        if isinstance(data, list):
            return [EnOceanScanResultItem.from_dict(item) for item in data]
        return []

    async def pair_enocean_device(
        self,
        eur_id: int,
        product_guid: str,
        bridge_direction: str = "ingress",
    ) -> EnOceanDevice:
        """Pair an EnOcean sensor to the device registry."""
        payload = {
            "eurId": eur_id,
            "productGuid": product_guid,
            "bridgeDirection": bridge_direction,
            "deviceGuid": "",
        }
        data = await self._request("POST", "/services/enocean/devices", json=payload)
        return EnOceanDevice.from_dict(data)

    async def delete_enocean_device(self, service_device_guid: str) -> None:
        """Unpair and delete an EnOcean device."""
        await self._request("DELETE", f"/services/enocean/devices/{service_device_guid}")

    async def get_enocean_configuration(self) -> dict[str, Any]:
        """Get EnOcean configuration (repeater mode, level, base ID)."""
        return await self._request("GET", "/services/enocean/configuration")

    async def set_enocean_repeater(
        self,
        repeater_level: str,
        repeater_mode: str = "on",
    ) -> None:
        """Configure on-device EnOcean repeater (off, oneLevel, twoLevel)."""
        payload = {
            "repeaterLevel": repeater_level,
            "repeaterMode": repeater_mode,
        }
        await self._request("PATCH", "/services/enocean/configuration", json=payload)

    async def get_matter_devices(self) -> list[MatterDevice]:
        """Get all devices exposed on the Matter bridge."""
        data = await self._request("GET", "/services/matter/devices")
        return [MatterDevice.from_dict(item) for item in data]

    async def expose_matter_device(
        self,
        product_guid: str,
        device_guid: str,
    ) -> MatterDevice:
        """Expose a device to the Matter bridge."""
        payload = {
            "productGuid": product_guid,
            "deviceGuid": device_guid,
        }
        data = await self._request("POST", "/services/matter/devices", json=payload)
        return MatterDevice.from_dict(data)

    async def remove_matter_device(self, service_device_guid: str) -> None:
        """Remove a device from being bridged to Matter."""
        await self._request("DELETE", f"/services/matter/devices/{service_device_guid}")
