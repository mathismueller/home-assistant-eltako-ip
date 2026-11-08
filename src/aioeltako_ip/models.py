"""Data models for Eltako Series 62/64 REST API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Characteristic:
    """Device characteristic (function, info, or setting)."""

    identifier: str
    type: str
    value: Any

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Characteristic:
        return cls(
            identifier=data["identifier"],
            type=data.get("type", "string"),
            value=data.get("value"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "type": self.type,
            "value": self.value,
        }


@dataclass
class Device:
    """Logical device managed by the Eltako gateway."""

    device_guid: str
    product_guid: str
    display_name: str
    functions: list[Characteristic] = field(default_factory=list)
    infos: list[Characteristic] = field(default_factory=list)
    settings: list[Characteristic] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        if "DeviceInfo" in data and isinstance(data["DeviceInfo"], dict):
            data = data["DeviceInfo"]
        return cls(
            device_guid=data["deviceGuid"],
            product_guid=data["productGuid"],
            display_name=data.get("displayName", ""),
            functions=[Characteristic.from_dict(c) for c in data.get("functions", [])],
            infos=[Characteristic.from_dict(c) for c in data.get("infos", [])],
            settings=[Characteristic.from_dict(c) for c in data.get("settings", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "deviceGuid": self.device_guid,
            "productGuid": self.product_guid,
            "displayName": self.display_name,
            "functions": [f.to_dict() for f in self.functions],
            "infos": [i.to_dict() for i in self.infos],
            "settings": [s.to_dict() for s in self.settings],
        }

    def get_function(self, identifier: str) -> Optional[Characteristic]:
        for f in self.functions:
            if f.identifier == identifier:
                return f
        return None

    def get_function_value(self, identifier: str) -> Any:
        char = self.get_function(identifier)
        return char.value if char is not None else None

    def get_info(self, identifier: str) -> Optional[Characteristic]:
        for i in self.infos:
            if i.identifier == identifier:
                return i
        return None

    def get_info_value(self, identifier: str) -> Any:
        char = self.get_info(identifier)
        return char.value if char is not None else None

    def get_setting(self, identifier: str) -> Optional[Characteristic]:
        for s in self.settings:
            if s.identifier == identifier:
                return s
        return None

    def get_setting_value(self, identifier: str) -> Any:
        char = self.get_setting(identifier)
        return char.value if char is not None else None


@dataclass
class ProductCharacteristicSpec:
    """Metadata specification for a characteristic from /products."""

    identifier: str
    type: str
    category: str
    read_only: bool = False
    default_value: Any = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    unit: Optional[str] = None
    enumerations: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductCharacteristicSpec:
        raw_enums = data.get("enumerations") or data.get("enums") or []
        enums: list[str] = []
        for item in raw_enums:
            if isinstance(item, dict) and "key" in item:
                enums.append(str(item["key"]))
            elif isinstance(item, str):
                enums.append(item)

        read_only = data.get("readOnly", False)
        if "access" in data and data["access"] == "readOnly":
            read_only = True

        return cls(
            identifier=data["identifier"],
            type=data.get("type", "string"),
            category=data.get("category", "info"),
            read_only=bool(read_only),
            default_value=data.get("defaultValue"),
            minimum=float(data["minimum"]) if data.get("minimum") is not None else None,
            maximum=float(data["maximum"]) if data.get("maximum") is not None else None,
            step=float(data["step"]) if data.get("step") is not None else None,
            unit=data.get("unit"),
            enumerations=enums,
        )


@dataclass
class ProductSpec:
    """Product metadata entry from the on-device product database (/products)."""

    product_guid: str
    name: str
    category: str = "unknown"
    profile: str = ""
    channels: int = 1
    characteristics: dict[str, ProductCharacteristicSpec] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductSpec:
        chars: dict[str, ProductCharacteristicSpec] = {}
        for feat in data.get("features", []):
            for c_data in feat.get("characteristics", []):
                if "identifier" in c_data:
                    spec = ProductCharacteristicSpec.from_dict(c_data)
                    chars[spec.identifier] = spec
        return cls(
            product_guid=data["productGuid"],
            name=data.get("name") or data.get("productName", "Unknown Product"),
            category=data.get("category", "unknown"),
            profile=data.get("profile", ""),
            channels=int(data.get("channels", 1)),
            characteristics=chars,
        )

    def get_characteristic_spec(
        self, identifier: str
    ) -> Optional[ProductCharacteristicSpec]:
        return self.characteristics.get(identifier)

    @property
    def settings(self) -> list[ProductCharacteristicSpec]:
        """Return all setting characteristic specifications for this product."""
        return [
            c for c in self.characteristics.values() if c.category in ("setting", "settings")
        ]


@dataclass
class EnOceanDevice:
    """Paired EnOcean service device."""

    service_device_guid: str
    device_guid: str
    product_guid: str
    eur_id: int
    signal_strength: Optional[int] = None
    last_seen: Optional[str] = None
    bridge_direction: str = "ingress"
    orientation: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.orientation and "orientation" not in self.config:
            self.config["orientation"] = self.orientation
        elif not self.orientation and "orientation" in self.config:
            self.orientation = str(self.config["orientation"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnOceanDevice:
        cfg = dict(data.get("config") or {})
        orient = data.get("orientation") or cfg.get("orientation")
        return cls(
            service_device_guid=data["serviceDeviceGuid"],
            device_guid=data.get("deviceGuid") or "",
            product_guid=data.get("productGuid", ""),
            eur_id=int(data["eurId"]),
            signal_strength=data.get("signalStrength"),
            last_seen=data.get("lastSeen"),
            bridge_direction=data.get("bridgeDirection", "ingress"),
            orientation=str(orient) if orient is not None else None,
            config=cfg,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "serviceDeviceGuid": self.service_device_guid,
            "deviceGuid": self.device_guid or None,
            "productGuid": self.product_guid,
            "eurId": self.eur_id,
            "signalStrength": self.signal_strength,
            "lastSeen": self.last_seen,
            "bridgeDirection": self.bridge_direction,
            "config": self.config,
        }


@dataclass
class EnOceanStatus:
    """EnOcean transceiver status and slot capacity."""

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
    """Discovered EnOcean telegram from a teach-in scan."""

    eur_id: int
    signal_strength: Optional[int] = None
    potential_products: list[str] = field(default_factory=list)
    last_seen: Optional[str] = None
    paired: bool = False
    count: Optional[int] = None

    @property
    def product_guid(self) -> Optional[str]:
        """Return the primary candidate productGuid if available."""
        return self.potential_products[0] if self.potential_products else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnOceanScanResultItem:
        pot = list(data.get("potentialProducts") or [])
        if data.get("productGuid") and data["productGuid"] not in pot:
            pot.insert(0, str(data["productGuid"]))
        return cls(
            eur_id=int(data["eurId"]),
            signal_strength=data.get("signalStrength"),
            potential_products=pot,
            last_seen=data.get("lastSeen"),
            paired=bool(data.get("paired", False)),
            count=data.get("count"),
        )


@dataclass
class EnOceanLegacyPairStatus:
    """Status of the EnOcean legacy pairing procedure (/services/enocean/legacypair/status)."""

    status: str
    description: str
    teach_in: bool
    taught_in: bool
    service_device_guid: Optional[str] = None
    remote_peer_eur_id: Optional[str] = None
    device_sender_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnOceanLegacyPairStatus:
        return cls(
            status=data.get("status", "unknown"),
            description=data.get("description", ""),
            teach_in=bool(data.get("teachIn", False)),
            taught_in=bool(data.get("taughtIn", False)),
            service_device_guid=data.get("serviceDeviceGuid"),
            remote_peer_eur_id=data.get("remotePeerEurId"),
            device_sender_id=data.get("deviceSenderId"),
        )


@dataclass
class MatterDevice:
    """Device exposed on the internal Matter bridge."""

    service_device_guid: str
    product_guid: str
    device_guid: str
    endpoint_id: int = 0
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatterDevice:
        return cls(
            service_device_guid=data["serviceDeviceGuid"],
            product_guid=data["productGuid"],
            device_guid=data.get("deviceGuid") or "",
            endpoint_id=data.get("endpointId", 0),
            config=data.get("config") or {},
        )


@dataclass
class MatterServiceInfo:
    """Full Matter bridge service status (/services/matter)."""

    configuration: dict[str, Any] = field(default_factory=dict)
    devices: list[MatterDevice] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatterServiceInfo:
        return cls(
            configuration=data.get("configuration") or {},
            devices=[MatterDevice.from_dict(d) for d in data.get("devices", [])],
        )


@dataclass
class UpdateConfig:
    """Firmware update configuration (/update/config)."""

    auto_update: bool = False
    update_schedule: str = "12h"
    update_server_uri: str = "update.eltako.com"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UpdateConfig:
        return cls(
            auto_update=bool(data.get("autoUpdate", False)),
            update_schedule=data.get("updateSchedule", "12h"),
            update_server_uri=data.get("updateServerUri", "update.eltako.com"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "autoUpdate": self.auto_update,
            "updateSchedule": self.update_schedule,
            "updateServerUri": self.update_server_uri,
        }


@dataclass
class FirmwareUpdateInfo:
    """Firmware update status and server metadata (/update/firmware)."""

    current_version: str
    desired_version: str
    location: str = ""
    thumbprint: str = ""
    certificate: str = ""
    version_token: str = ""
    request_type: str = "custom"
    schema: str = "TBD"
    headers: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FirmwareUpdateInfo:
        inner = data.get("data") or {}
        auth = inner.get("auth") or {}
        upd = inner.get("update") or {}
        return cls(
            current_version=inner.get("currentVersion", "0.0.0"),
            desired_version=upd.get("desiredVersion", "0.0.0"),
            location=data.get("location", ""),
            thumbprint=inner.get("thumbprint", ""),
            certificate=auth.get("certificate", ""),
            version_token=upd.get("version", ""),
            request_type=data.get("requestType", "custom"),
            schema=data.get("schema", "TBD"),
            headers=data.get("headers") or [],
        )

    @property
    def update_available(self) -> bool:
        """Return True if a newer firmware version is advertised."""
        return bool(
            self.desired_version
            and self.desired_version not in ("0.0.0", "unknown", self.current_version)
        )

    @property
    def latest_version(self) -> str:
        """Return the latest available version (falls back to current_version if none)."""
        if self.update_available:
            return self.desired_version
        return self.current_version


@dataclass
class AutomationAddOn:
    """AddOn parameter for an on-device Eltako automation rule."""

    type: str
    time: Optional[int] = None
    data: Optional[Any] = None

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> AutomationAddOn:
        return cls(
            type=item["type"],
            time=item.get("time"),
            data=item.get("data"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "time": self.time,
            "data": self.data,
        }


class AutomationRule:
    """On-device autonomous automation rule (/services/eltako/automations)."""

    def __init__(
        self,
        automation_guid: str = "",
        enabled: Optional[bool] = None,
        description: str = "",
        logic: str = "buttonImpulseSwitch",
        input_device_guid: str = "",
        input_characteristic_identifier: str = "input",
        output_device_guid: str = "",
        output_characteristic_identifier: str = "relay",
        add_ons: Optional[list[AutomationAddOn]] = None,
        logic_configuration: Optional[dict[str, Any]] = None,
        operating_status: str = "success",
        errors: Optional[list[dict[str, Any]]] = None,
        *,
        active: Optional[bool] = None,
        addons: Optional[list[AutomationAddOn]] = None,
    ) -> None:
        self.automation_guid = automation_guid
        if enabled is not None:
            self.enabled = bool(enabled)
        elif active is not None:
            self.enabled = bool(active)
        else:
            self.enabled = True
        self.description = description
        self.logic = logic
        self.input_device_guid = input_device_guid
        self.input_characteristic_identifier = input_characteristic_identifier
        self.output_device_guid = output_device_guid
        self.output_characteristic_identifier = output_characteristic_identifier
        self.add_ons: list[AutomationAddOn] = list(add_ons or addons or [])
        self.logic_configuration: dict[str, Any] = dict(logic_configuration or {})
        self.operating_status = operating_status
        self.errors: list[dict[str, Any]] = list(errors or [])

    @property
    def active(self) -> bool:
        """Alias for enabled."""
        return self.enabled

    @property
    def addons(self) -> list[AutomationAddOn]:
        """Alias for add_ons."""
        return self.add_ons

    @property
    def off_timer_ms(self) -> Optional[int]:
        """Return offTimer value in milliseconds if configured."""
        return self.get_off_timer_ms()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutomationRule:
        cfg = data.get("configuration") or {}
        return cls(
            automation_guid=cfg.get("automationGuid", ""),
            enabled=bool(data.get("enabled", True)),
            description=data.get("description", ""),
            logic=cfg.get("logic", "buttonImpulseSwitch"),
            input_device_guid=cfg.get("inputDeviceGuid", ""),
            input_characteristic_identifier=cfg.get(
                "inputCharacteristicIdentifier", "input"
            ),
            output_device_guid=cfg.get("outputDeviceGuid", ""),
            output_characteristic_identifier=cfg.get(
                "outputCharacteristicIdentifier", "relay"
            ),
            add_ons=[AutomationAddOn.from_dict(a) for a in cfg.get("addOns", [])],
            logic_configuration=cfg.get("logicConfiguration") or {},
            operating_status=data.get("operatingStatus", "success"),
            errors=data.get("errors") or [],
        )

    def get_addon(self, addon_type: str) -> Optional[AutomationAddOn]:
        for addon in self.add_ons:
            if addon.type == addon_type:
                return addon
        return None

    def get_off_timer_ms(self) -> Optional[int]:
        addon = self.get_addon("offTimer")
        if addon and addon.time is not None:
            return int(addon.time)
        return None

    def to_payload(self, include_guid: bool = True) -> dict[str, Any]:
        cfg: dict[str, Any] = {
            "logic": self.logic,
            "inputDeviceGuid": self.input_device_guid,
            "inputCharacteristicIdentifier": self.input_characteristic_identifier,
            "outputDeviceGuid": self.output_device_guid,
            "outputCharacteristicIdentifier": self.output_characteristic_identifier,
            "addOns": [a.to_dict() for a in self.add_ons],
        }
        if include_guid and self.automation_guid:
            cfg["automationGuid"] = self.automation_guid
        if self.logic_configuration:
            cfg["logicConfiguration"] = self.logic_configuration
        return {
            "enabled": self.enabled,
            "description": self.description,
            "configuration": cfg,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize rule to dictionary."""
        return self.to_payload(include_guid=True)


@dataclass
class SystemInfo:
    """Hardware and firmware metadata from /system."""

    software_version: str
    hardware_version: str
    product_name: str
    product_type: str
    product_guid: str
    serial_number: str
    manufacturer_name: str = "Eltako GmbH"
    manufacturer_website: str = "https://www.eltako.com/"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemInfo:
        infos = data.get("infos", {})
        prod = data.get("product", {})
        mfg = prod.get("manufacturer", {})
        return cls(
            software_version=infos.get("softwareVersion", "unknown"),
            hardware_version=infos.get("hardwareVersion", "unknown"),
            product_name=prod.get("productName", "Eltako Device"),
            product_type=prod.get("productType", "unknown"),
            product_guid=prod.get("productGuid", ""),
            serial_number=prod.get("serialNumber", ""),
            manufacturer_name=mfg.get("name", "Eltako GmbH"),
            manufacturer_website=mfg.get("website", "https://www.eltako.com/"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "infos": {
                "softwareVersion": self.software_version,
                "hardwareVersion": self.hardware_version,
            },
            "product": {
                "productName": self.product_name,
                "productType": self.product_type,
                "productGuid": self.product_guid,
                "serialNumber": self.serial_number,
                "manufacturer": {
                    "name": self.manufacturer_name,
                    "website": self.manufacturer_website,
                },
            },
        }
