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

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import AutomationRule

SPEC_VERSION = "series64ipm/1.3.0"

# Output characteristic -> actuator class, per spec examples
# (relay: ESR, targetPosition: ESB, targetBrightness: EUD).
OUTPUT_CLASS_BY_CHARACTERISTIC = {
    "relay": "ESR",
    "targetPosition": "ESB",
    "targetBrightness": "EUD",
}

# Logics per actuator class, per spec ("Logic" section for ESR/ESB,
# "EUD Automation Logic" table for EUD).
LOGICS_BY_CLASS: dict[str, frozenset[str]] = {
    "ESR": frozenset(
        {
            "buttonImpulseSwitch",
            "buttonSwitch",
            "buttonNormallyOpened",
            "buttonNormallyClosed",
            "target",
        }
    ),
    "ESB": frozenset(
        {
            "buttonImpulseSwitch",
            "buttonSwitch",
            "buttonNormallyOpened",
            "buttonNormallyClosed",
            "target",
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
