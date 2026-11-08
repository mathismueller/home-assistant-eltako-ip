"""aioeltako_ip - Asynchronous Python client for Eltako Series 62/64 IP REST API."""

from .client import EltakoClient
from .exceptions import (
    AuthenticationError,
    DeviceNotFoundError,
    EltakoConnectionError,
    EltakoError,
    UnsupportedCommandError,
)
from .models import (
    Characteristic,
    Device,
    EnOceanDevice,
    EnOceanScanResultItem,
    EnOceanStatus,
    MatterDevice,
    SystemInfo,
)

__all__ = [
    "EltakoClient",
    "EltakoError",
    "AuthenticationError",
    "EltakoConnectionError",
    "DeviceNotFoundError",
    "UnsupportedCommandError",
    "Characteristic",
    "Device",
    "EnOceanDevice",
    "EnOceanScanResultItem",
    "EnOceanStatus",
    "MatterDevice",
    "SystemInfo",
]
