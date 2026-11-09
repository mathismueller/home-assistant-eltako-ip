"""Spec-based validation for ELTAKO Basic Automations.

Capability tables are transcribed from the official Eltako OpenAPI specification
(``series64ipm/1.3.0``, ``GET /services/eltako/automations`` description).
They are versioned data: when Eltako publishes a new spec revision, update the
tables and the ``SPEC_VERSION`` marker below.

Design rules:
- Unknown output classes are never rejected (forward compatibility with new
  hardware and the spec's own "prerelease, expected to change" warning).
- Known classes are validated strictly so bad rules fail locally with a clear
  message instead of as an opaque device ``400``.
- Validation is bypassable (``validate=False``) for firmware that outgrew
  these tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .models import AutomationRule

SPEC_VERSION = "series64ipm/1.3.0"

# Output characteristic -> actuator class, per spec examples
# (relay: ESR, targetPosition: ESB, targetBrightness: EUD).
# Multichannel relays expose per-channel identifiers.
OUTPUT_CLASS_BY_CHARACTERISTIC = {
    "relay": "ESR",
    "relayChannel1": "ESR",
    "relayChannel2": "ESR",
    "targetPosition": "ESB",
    "targetBrightness": "EUD",
}

# Characteristic identifiers that can never trigger a rule: connection and
# device-meta status, calibration offsets, device range metadata, power
# telemetry, actuator settings, and live values. Anything else is offered
# as a trigger: per spec, "the modification of a characteristic (e.g. motion
# detected) can trigger an automation".
NON_TRIGGER_IDENTIFIERS = frozenset(
    {
        "connectionStatus",
        "temperatureOffset",
        "humidityOffset",
        "testModeStatus",
        "faultStatus",
        "serviceLifeTime",
        "energyHarvestingActive",
        "energyBufferChargeLevel",
        "batteryChargeLevel",
        "batteryPercentageRemaining",
        "batteryVoltage",
        "supplyVoltage",
        "controlHierarchy",
        "motionDetectionMode",
        "edgeMode",
        "dimCurve",
        "runtimeMode",
        "movementDirection",
        "enableTilt",
        "maxRuntime",
        "runtime",
        "offset",
        "tiltRuntime",
        "power",
        "currentBrightness",
        "lastBrightness",
        "minimumBrightness",
        "maximumBrightness",
        "currentPosition",
        "currentTilt",
    }
)

# Prefixes of device range metadata (e.g. minimumDeviceTemperature).
NON_TRIGGER_PREFIXES = ("minimum", "maximum")

# Logics per actuator class, per spec ("Logic" section for ESR/ESB,
# "EUD Automation Logic" table for EUD).
# NOTE: Eltako's own Postman Workflows (SERIES 62-IP API collection,
# "ESR62-IP (Relay) / Input as always on|off") use "buttonTargetValue"
# where the OpenAPI spec (series64ipm/1.3.0) says "target". Both name the
# same behavior, so both validate. Prefer "target" when writing.
LOGICS_BY_CLASS: dict[str, frozenset[str]] = {
    "ESR": frozenset(
        {
            "buttonImpulseSwitch",
            "buttonSwitch",
            "buttonNormallyOpened",
            "buttonNormallyClosed",
            "target",
            "buttonTargetValue",
        }
    ),
    "ESB": frozenset(
        {
            "buttonImpulseSwitch",
            "buttonSwitch",
            "buttonNormallyOpened",
            "buttonNormallyClosed",
            "target",
            "buttonTargetValue",
        }
    ),
    "EUD": frozenset(
        {
            "universalButtonDimmer",
            "directionalUpButtonDimmer",
            "directionalDownButtonDimmer",
            "centralUpButtonDimmer",
            "centralDownButtonDimmer",
            "sceneButtonDimmer",
        }
    ),
}

# AddOns per actuator class, per spec ("AddOns" table "Supported Devices").
ADDONS_BY_CLASS: dict[str, frozenset[str]] = {
    "ESR": frozenset(
        {"targetValue", "offTimer", "longPressOffTimer", "prewarning"}
    ),
    "ESB": frozenset(
        {
            "targetValue",
            "shortPressNormallyOpened",
            "extraLongPressNormallyOpened",
            "automaticReversal",
            "automaticSlat",
            "sceneButton",
            "sceneValueOverride",
            "sceneWithReferenceMovement",
            "targetAngle",
        }
    ),
    # EUD automations carry no addOns in the spec; behavior is configured
    # entirely through logicConfiguration.
    "EUD": frozenset(),
}

# Required logicConfiguration keys per EUD logic, per spec table
# ("Required LogicConfiguration" column).
EUD_REQUIRED_CONFIG: dict[str, frozenset[str]] = {
    "universalButtonDimmer": frozenset(
        {"turnOnDuration", "turnOffDuration", "dimDuration"}
    ),
    "directionalUpButtonDimmer": frozenset({"turnOnDuration", "dimDuration"}),
    "directionalDownButtonDimmer": frozenset({"turnOffDuration", "dimDuration"}),
    "centralUpButtonDimmer": frozenset({"turnOnDuration"}),
    "centralDownButtonDimmer": frozenset({"turnOffDuration"}),
    "sceneButtonDimmer": frozenset(
        {"turnOnDuration", "turnOffDuration", "dimDuration", "targetBrightness"}
    ),
}

# logicConfiguration extensions and the EUD logics supporting them,
# per spec ("LogicConfiguration Extensions" table).
EUD_EXTENSION_LOGICS: dict[str, frozenset[str]] = {
    "childrenRoomExtension": frozenset(
        {"universalButtonDimmer", "directionalUpButtonDimmer"}
    ),
    "slumberExtension": frozenset(
        {"universalButtonDimmer", "directionalDownButtonDimmer"}
    ),
    "lightAlarmExtension": frozenset({"directionalUpButtonDimmer"}),
    "sceneValueOverrideExtension": frozenset({"sceneButtonDimmer"}),
}


def device_class_for_output(output_characteristic: str) -> Optional[str]:
    """Map an output characteristic identifier to an actuator class.

    Returns ``None`` for characteristics the spec tables do not cover, in
    which case validation is skipped (forward compatibility).
    """
    return OUTPUT_CLASS_BY_CHARACTERISTIC.get(output_characteristic)


def _is_trigger_identifier(identifier: str) -> bool:
    """Decide whether a characteristic identifier is a plausible trigger."""
    if not identifier:
        return False
    if identifier in OUTPUT_CLASS_BY_CHARACTERISTIC:
        return False
    if identifier in NON_TRIGGER_IDENTIFIERS:
        return False
    return not identifier.startswith(NON_TRIGGER_PREFIXES)


def _product_characteristics(products_raw: Any) -> dict[str, list[str]]:
    """Map productGuid -> characteristic identifiers from /products data.

    Accepts the shapes gateways return: ``{"products": [...]}``, a bare
    list, or a ``{guid: product}`` dict.
    """
    items: Any = products_raw
    if isinstance(items, dict):
        items = items.get("products", list(items.values()))
    result: dict[str, list[str]] = {}
    if not isinstance(items, list):
        return result
    for product in items:
        if not isinstance(product, dict) or "productGuid" not in product:
            continue
        identifiers: list[str] = []
        for feature in product.get("features", []):
            if not isinstance(feature, dict):
                continue
            for char in feature.get("characteristics", []):
                if isinstance(char, dict) and char.get("identifier"):
                    identifiers.append(str(char["identifier"]))
        result[str(product["productGuid"])] = identifiers
    return result


def build_capabilities(devices_raw: Any, products_raw: Any) -> dict[str, Any]:
    """Enumerate valid automation triggers and targets from gateway data.

    Takes raw ``/devices`` (list) and ``/products`` data and returns::

        {
          "triggers": [{"deviceGuid", "displayName", "identifier"}],
          "targets": [{"deviceGuid", "displayName", "identifier",
                       "deviceClass"}],
          "logicsByClass": {"ESR": [...], ...},
          "addonsByClass": {"ESR": [...], ...},
          "specVersion": ...,
        }

    Triggers union live characteristics with the device model's product-spec
    characteristics (so e.g. all ``inputChannel``/``buttonChannel`` variants
    of the paired hardware are offered), minus meta identifiers. Targets are
    live output functions with a known actuator class only.
    """
    triggers: list[dict[str, str]] = []
    targets: list[dict[str, str]] = []
    seen_triggers: set[tuple[str, str]] = set()
    spec_chars = _product_characteristics(products_raw)

    devices = devices_raw if isinstance(devices_raw, list) else []
    for device in devices:
        if not isinstance(device, dict):
            continue
        guid = str(device.get("deviceGuid", ""))
        name = str(device.get("displayName") or guid[:8])
        if not guid:
            continue
        live_ids: list[str] = []
        for section in ("functions", "infos"):
            chars = device.get(section, [])
            if isinstance(chars, list):
                live_ids.extend(
                    str(c.get("identifier"))
                    for c in chars
                    if isinstance(c, dict) and c.get("identifier")
                )
        for ident in live_ids + spec_chars.get(str(device.get("productGuid", "")), []):
            if _is_trigger_identifier(ident) and (guid, ident) not in seen_triggers:
                seen_triggers.add((guid, ident))
                triggers.append(
                    {"deviceGuid": guid, "displayName": name, "identifier": ident}
                )
        for char in device.get("functions", []):
            if not isinstance(char, dict):
                continue
            ident = str(char.get("identifier", ""))
            cls = OUTPUT_CLASS_BY_CHARACTERISTIC.get(ident)
            if cls and not any(
                t["deviceGuid"] == guid and t["identifier"] == ident for t in targets
            ):
                targets.append(
                    {
                        "deviceGuid": guid,
                        "displayName": name,
                        "identifier": ident,
                        "deviceClass": cls,
                    }
                )

    return {
        "triggers": triggers,
        "targets": targets,
        "logicsByClass": {
            cls: sorted(logics) for cls, logics in LOGICS_BY_CLASS.items()
        },
        "addonsByClass": {
            cls: sorted(addons) for cls, addons in ADDONS_BY_CLASS.items()
        },
        "specVersion": SPEC_VERSION,
    }


def validate_rule(
    rule: AutomationRule, output_class: Optional[str] = None
) -> list[str]:
    """Validate an automation rule against the spec tables.

    Returns a list of human-readable problems (empty = valid). Unknown
    output classes are accepted without checks. Pass ``output_class``
    explicitly when the characteristic identifier is ambiguous; otherwise
    it is derived from the rule's output characteristic.
    """
    errors: list[str] = []
    cls = output_class or device_class_for_output(
        rule.output_characteristic_identifier
    )
    if cls is None:
        return errors

    if not rule.input_device_guid:
        errors.append("inputDeviceGuid is missing.")
    if not rule.output_device_guid:
        errors.append("outputDeviceGuid is missing.")

    allowed_logics = LOGICS_BY_CLASS.get(cls)
    if allowed_logics is not None and rule.logic not in allowed_logics:
        errors.append(
            f"Logic {rule.logic!r} is not supported for {cls} actuators "
            f"(spec {SPEC_VERSION})."
        )

    allowed_addons = ADDONS_BY_CLASS.get(cls, frozenset())
    for addon in rule.add_ons:
        if addon.type not in allowed_addons:
            errors.append(
                f"AddOn {addon.type!r} is not supported for {cls} actuators "
                f"(spec {SPEC_VERSION})."
            )

    # buttonSwitch triggers on press AND release, so a short-press offTimer
    # has no meaning; the device rejects the combination.
    if rule.logic == "buttonSwitch" and rule.get_addon("offTimer") is not None:
        errors.append(
            "offTimer cannot be combined with buttonSwitch logic "
            "(no short press exists to arm it)."
        )

    # Spec: prewarning "is to be combined with the offTimer addon or the
    # longPressOffTimer addon".
    if rule.get_addon("prewarning") is not None and (
        rule.get_addon("offTimer") is None
        and rule.get_addon("longPressOffTimer") is None
    ):
        errors.append(
            "prewarning requires an offTimer or longPressOffTimer addOn."
        )

    # Manufacturer Workflows ("Input as always on|off") drive ESR relays
    # with targetValue 0/1; other values are meaningless on a relay.
    if cls == "ESR" and rule.logic in ("target", "buttonTargetValue"):
        target_addon = rule.get_addon("targetValue")
        if target_addon is not None and target_addon.data not in (0, 1):
            errors.append(
                "targetValue for ESR relays must be 0 (off) or 1 (on), "
                f"got {target_addon.data!r}."
            )

    if cls == "EUD":
        required = EUD_REQUIRED_CONFIG.get(rule.logic, frozenset())
        missing = [
            key
            for key in sorted(required)
            if key not in (rule.logic_configuration or {})
        ]
        if missing:
            errors.append(
                f"Logic {rule.logic!r} requires logicConfiguration keys "
                f"{', '.join(missing)} (spec {SPEC_VERSION})."
            )
        for ext, logics in EUD_EXTENSION_LOGICS.items():
            if (
                ext in (rule.logic_configuration or {})
                and rule.logic not in logics
            ):
                errors.append(
                    f"Extension {ext!r} is not supported for logic "
                    f"{rule.logic!r} (spec {SPEC_VERSION})."
                )

    return errors
