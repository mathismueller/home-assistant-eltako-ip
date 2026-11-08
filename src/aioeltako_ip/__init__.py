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
    ProductCharacteristicSpec,
    ProductSpec,
    SystemInfo,
    UpdateConfig,
)

__all__ = [
    "EltakoClient",
    "EltakoError",
    "AuthenticationError",
    "EltakoConnectionError",
    "DeviceNotFoundError",
    "UnsupportedCommandError",
    "AutomationAddOn",
    "AutomationRule",
    "Characteristic",
    "Device",
    "EnOceanDevice",
    "EnOceanLegacyPairStatus",
    "EnOceanScanResultItem",
    "EnOceanStatus",
    "FirmwareUpdateInfo",
    "MatterDevice",
    "MatterServiceInfo",
    "ProductCharacteristicSpec",
    "ProductSpec",
    "SystemInfo",
    "UpdateConfig",
]
