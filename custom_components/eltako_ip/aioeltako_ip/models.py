"""Data models for Eltako Series 62/64 REST API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Characteristic:
    identifier: str
    type: str
    value: Any


@dataclass
class Device:
    device_guid: str
    product_guid: str
    display_name: str
    functions: list[Characteristic] = field(default_factory=list)
    infos: list[Characteristic] = field(default_factory=list)
    settings: list[Characteristic] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        return cls(
            device_guid=data["deviceGuid"],
            product_guid=data["productGuid"],
            display_name=data.get("displayName", ""),
            functions=[
                Characteristic(
                    identifier=c["identifier"],
                    type=c.get("type", "string"),
                    value=c.get("value"),
                )
                for c in data.get("functions", [])
            ],
            infos=[
                Characteristic(
                    identifier=c["identifier"],
                    type=c.get("type", "string"),
                    value=c.get("value"),
                )
                for c in data.get("infos", [])
            ],
            settings=[
                Characteristic(
                    identifier=c["identifier"],
                    type=c.get("type", "string"),
                    value=c.get("value"),
                )
                for c in data.get("settings", [])
            ],
        )

    def get_function_value(self, identifier: str) -> Any:
        for f in self.functions:
            if f.identifier == identifier:
                return f.value
        return None

    def get_info_value(self, identifier: str) -> Any:
        for i in self.infos:
            if i.identifier == identifier:
                return i.value
        return None


@dataclass
class EnOceanDevice:
    service_device_guid: str
    device_guid: str
    product_guid: str
    eur_id: int
    signal_strength: Optional[int] = None
    last_seen: Optional[str] = None
    bridge_direction: str = "ingress"
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnOceanDevice:
        return cls(
            service_device_guid=data["serviceDeviceGuid"],
            device_guid=data.get("deviceGuid", ""),
            product_guid=data.get("productGuid", ""),
            eur_id=data["eurId"],
            signal_strength=data.get("signalStrength"),
            last_seen=data.get("lastSeen"),
            bridge_direction=data.get("bridgeDirection", "ingress"),
            config=data.get("config", {}),
        )


@dataclass
class EnOceanStatus:
    health: str
    max_eur_ids: int
    free_eur_ids: int
    hardware_filter_state: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnOceanStatus:
        return cls(
            health=data.get("health", "unknown"),
            max_eur_ids=data.get("maxEurIds", 0),
            free_eur_ids=data.get("freeEurIds", 0),
            hardware_filter_state=data.get("hardwareFilterState"),
        )


@dataclass
class EnOceanScanResultItem:
    eur_id: int
    signal_strength: Optional[int] = None
    potential_products: list[str] = field(default_factory=list)
    last_seen: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnOceanScanResultItem:
        return cls(
            eur_id=data["eurId"],
            signal_strength=data.get("signalStrength"),
            potential_products=data.get("potentialProducts", []),
            last_seen=data.get("lastSeen"),
        )


@dataclass
class MatterDevice:
    service_device_guid: str
    product_guid: str
    device_guid: str
    endpoint_id: int
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatterDevice:
        return cls(
            service_device_guid=data["serviceDeviceGuid"],
            product_guid=data["productGuid"],
            device_guid=data.get("deviceGuid", ""),
            endpoint_id=data.get("endpointId", 0),
            config=data.get("config", {}),
        )


@dataclass
class SystemInfo:
    software_version: str
    hardware_version: str
    product_name: str
    product_type: str
    product_guid: str
    serial_number: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemInfo:
        infos = data.get("infos", {})
        prod = data.get("product", {})
        return cls(
            software_version=infos.get("softwareVersion", "unknown"),
            hardware_version=infos.get("hardwareVersion", "unknown"),
            product_name=prod.get("productName", "Eltako Device"),
            product_type=prod.get("productType", "unknown"),
            product_guid=prod.get("productGuid", ""),
            serial_number=prod.get("serialNumber", ""),
        )
