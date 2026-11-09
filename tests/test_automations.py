"""Spec-based automation validation (src/aioeltako_ip/automations.py)."""

import json
from pathlib import Path
from typing import Any

import pytest
from aioresponses import aioresponses

from aioeltako_ip import (
    AutomationAddOn,
    AutomationRule,
    EltakoClient,
    UnsupportedCommandError,
    build_capabilities,
    device_settings,
    validate_rule,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURES_DIR / f"{name}.json") as f:
        return json.load(f)


def make_rule(**kwargs: Any) -> AutomationRule:
    base: dict[str, Any] = {
        "automation_guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "input_device_guid": "11111111-1111-1111-1111-111111111111",
        "input_characteristic_identifier": "input",
        "output_device_guid": "22222222-2222-2222-2222-222222222222",
        "output_characteristic_identifier": "relay",
        "logic": "buttonImpulseSwitch",
    }
    base.update(kwargs)
    return AutomationRule(**base)


def test_valid_esr_relay_rule():
    rule = make_rule(
        add_ons=[
            AutomationAddOn(type="offTimer", time=10000),
            AutomationAddOn(type="prewarning"),
        ]
    )
    assert validate_rule(rule) == []


def test_off_timer_with_button_switch_rejected():
    rule = make_rule(
        logic="buttonSwitch",
        add_ons=[AutomationAddOn(type="offTimer", time=5000)],
    )
    problems = validate_rule(rule)
    assert any("offTimer" in p and "buttonSwitch" in p for p in problems)


def test_long_press_timer_with_button_switch_rejected():
    rule = make_rule(
        logic="buttonSwitch",
        add_ons=[AutomationAddOn(type="longPressOffTimer", time=60000)],
    )
    problems = validate_rule(rule)
    assert any("longPressOffTimer" in p for p in problems)


def test_long_press_timer_with_level_logics_rejected():
    for logic in ("buttonNormallyOpened", "buttonNormallyClosed"):
        rule = make_rule(
            logic=logic,
            add_ons=[AutomationAddOn(type="longPressOffTimer", time=60000)],
        )
        problems = validate_rule(rule)
        assert any("longPressOffTimer" in p for p in problems), logic


def test_long_press_timer_with_impulse_and_target_accepted():
    impulse = make_rule(
        add_ons=[AutomationAddOn(type="longPressOffTimer", time=60000)],
    )
    assert validate_rule(impulse) == []
    target = make_rule(
        logic="buttonTargetValue",
        add_ons=[
            AutomationAddOn(type="targetValue", data=1),
            AutomationAddOn(type="longPressOffTimer", time=60000),
        ],
    )
    assert validate_rule(target) == []


def test_prewarning_without_timer_rejected():
    rule = make_rule(add_ons=[AutomationAddOn(type="prewarning")])
    problems = validate_rule(rule)
    assert any("prewarning" in p for p in problems)


def test_prewarning_with_long_press_timer_accepted():
    rule = make_rule(
        add_ons=[
            AutomationAddOn(type="longPressOffTimer", time=60000),
            AutomationAddOn(type="prewarning"),
        ]
    )
    assert validate_rule(rule) == []


def test_unknown_logic_for_known_class_rejected():
    rule = make_rule(logic="universalButtonDimmer")
    problems = validate_rule(rule)
    assert any("universalButtonDimmer" in p for p in problems)


def test_unknown_addon_for_known_class_rejected():
    rule = make_rule(add_ons=[AutomationAddOn(type="automaticSlat", data=45)])
    problems = validate_rule(rule)
    assert any("automaticSlat" in p for p in problems)


def test_unknown_output_class_skipped_for_forward_compat():
    rule = make_rule(
        output_characteristic_identifier="someFutureChannel",
        logic="whateverLogic",
        add_ons=[AutomationAddOn(type="whateverAddon")],
    )
    assert validate_rule(rule) == []


def test_missing_guids_reported():
    rule = make_rule(input_device_guid="", output_device_guid="")
    problems = validate_rule(rule)
    assert any("inputDeviceGuid" in p for p in problems)
    assert any("outputDeviceGuid" in p for p in problems)


def test_eud_missing_logic_configuration_rejected():
    rule = make_rule(
        output_characteristic_identifier="targetBrightness",
        logic="universalButtonDimmer",
        logic_configuration={},
    )
    problems = validate_rule(rule)
    assert any("turnOnDuration" in p for p in problems)


def test_eud_valid_configuration_accepted():
    rule = make_rule(
        output_characteristic_identifier="targetBrightness",
        logic="universalButtonDimmer",
        logic_configuration={
            "turnOnDuration": 2000,
            "turnOffDuration": 2000,
            "dimDuration": 7000,
        },
    )
    assert validate_rule(rule) == []


def test_eud_unsupported_extension_rejected():
    rule = make_rule(
        output_characteristic_identifier="targetBrightness",
        logic="centralDownButtonDimmer",
        logic_configuration={
            "turnOffDuration": 2000,
            "slumberExtension": {"enabled": True, "dimDuration": 1000},
        },
    )
    problems = validate_rule(rule)
    assert any("slumberExtension" in p for p in problems)


def _cap_devices():
    return [
        {
            "deviceGuid": "out-1",
            "productGuid": "prod-esr",
            "displayName": "Relay",
            "functions": [{"identifier": "relay", "value": "on"}],
            "infos": [],
        },
        {
            "deviceGuid": "in-1",
            "productGuid": "prod-wired64",
            "displayName": "Wired input",
            "functions": [{"identifier": "inputChannel1", "value": "x"}],
            "infos": [{"identifier": "connectionStatus", "value": "online"}],
        },
    ]


def _cap_products():
    return {
        "products": [
            {
                "productGuid": "prod-wired64",
                "name": "Wired input 64",
                "features": [
                    {
                        "characteristics": [
                            {"identifier": "inputChannel1"},
                            {"identifier": "inputChannel2"},
                            {"identifier": "inputBridged"},
                        ]
                    }
                ],
            }
        ]
    }


def test_build_capabilities_offers_only_valid_options():
    caps = build_capabilities(_cap_devices(), _cap_products())
    trigger_ids = {(t["deviceGuid"], t["identifier"]) for t in caps["triggers"]}
    # live + product-spec union for the 64-style wired input
    assert ("in-1", "inputChannel1") in trigger_ids
    assert ("in-1", "inputChannel2") in trigger_ids
    assert ("in-1", "inputBridged") in trigger_ids
    # meta and outputs are never triggers
    assert not any(t["identifier"] == "connectionStatus" for t in caps["triggers"])
    assert not any(t["identifier"] == "relay" for t in caps["triggers"])
    # targets carry their actuator class
    assert caps["targets"] == [
        {
            "deviceGuid": "out-1",
            "displayName": "Relay",
            "identifier": "relay",
            "deviceClass": "ESR",
        }
    ]
    assert "buttonImpulseSwitch" in caps["logicsByClass"]["ESR"]
    assert "offTimer" in caps["addonsByClass"]["ESR"]
    assert caps["specVersion"]


def test_build_capabilities_accepts_all_product_shapes():
    devices = _cap_devices()
    by_guid = {p["productGuid"]: p for p in _cap_products()["products"]}
    assert build_capabilities(devices, by_guid)["triggers"] == build_capabilities(
        devices, _cap_products()
    )["triggers"]
    assert (
        build_capabilities(devices, _cap_products()["products"])["triggers"]
        == build_capabilities(devices, _cap_products())["triggers"]
    )


def test_button_target_value_alias_accepted():
    # Manufacturer Workflows use "buttonTargetValue" where the spec says
    # "target"; both name the same ESR behavior.
    rule = make_rule(
        logic="buttonTargetValue",
        add_ons=[AutomationAddOn(type="targetValue", data=1)],
    )
    assert validate_rule(rule) == []


def test_esr_target_value_range_enforced():
    bad = make_rule(
        logic="target",
        add_ons=[AutomationAddOn(type="targetValue", data=100)],
    )
    assert any("targetValue" in p for p in validate_rule(bad))
    good = make_rule(
        logic="target",
        add_ons=[AutomationAddOn(type="targetValue", data=0)],
    )
    assert validate_rule(good) == []


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_deadlock(
    test_base_url: str, test_host: str, test_pop: str
):
    """Concurrent requests must serialize (firmware drops parallel ones)."""
    import asyncio

    login_data = load_fixture("login")
    automations_data = load_fixture("automations")
    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.get(
            f"{test_base_url}/services/eltako/automations",
            payload=automations_data,
            repeat=True,
        )
        async with EltakoClient(test_host, pop=test_pop) as client:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *[client.get_automations() for _ in range(5)]
                ),
                timeout=10,
            )
            assert all(len(r) == 1 for r in results)


def _settings_products():
    def char(identifier, **kw):
        base = {"identifier": identifier, "type": "number", "category": "setting"}
        base.update(kw)
        return base

    return {
        "products": [
            {
                "productGuid": "prod-esb",
                "name": "ESB",
                "features": [
                    {
                        "characteristics": [
                            char("runtimeMode", type="enumeration", defaultValue="manual",
                                 enumerations=[{"key": "auto"}, {"key": "manual"}]),
                            char("runtime", defaultValue="200000", unit="ms", minimum=1000, maximum=900000),
                            char("enableTilt", type="enumeration", defaultValue="disabled",
                                 enumerations=[{"key": "disabled"}, {"key": "enabled"}]),
                            char("tiltRuntime", defaultValue="2000", unit="ms"),
                            char("targetPosition", type="number", category="function"),
                        ]
                    }
                ],
            }
        ]
    }


def _settings_devices():
    return [
        {
            "deviceGuid": "shade-1",
            "productGuid": "prod-esb",
            "displayName": "Shade",
            "functions": [{"identifier": "targetPosition", "value": 100}],
            "infos": [],
            "settings": [],
        }
    ]


def test_device_settings_defaults_and_gating():
    out = device_settings(_settings_devices(), _settings_products())
    assert len(out["devices"]) == 1
    by_ident = {s["identifier"]: s for s in out["devices"][0]["settings"]}
    # functions are not settings
    assert "targetPosition" not in by_ident
    assert by_ident["runtime"]["value"] == "200000"
    assert by_ident["runtime"]["unit"] == "ms"
    assert by_ident["runtime"]["applies"] is True
    # enableTilt defaults to disabled -> tilt settings gated with reason
    assert by_ident["tiltRuntime"]["applies"] is False
    assert by_ident["tiltRuntime"]["reason"] == "tilt"


def test_device_settings_live_values_enable_gated():
    devices = _settings_devices()
    devices[0]["settings"] = [
        {"identifier": "enableTilt", "value": "enabled"},
        {"identifier": "runtimeMode", "value": "auto"},
    ]
    out = device_settings(devices, _settings_products())
    by_ident = {s["identifier"]: s for s in out["devices"][0]["settings"]}
    tilt = by_ident["tiltRuntime"]
    assert tilt["applies"] is True
    assert tilt["value"] == "2000"  # default, not reported live
    runtime = next(s for s in out["devices"][0]["settings"] if s["identifier"] == "runtime")
    assert runtime["applies"] is False
    assert runtime["reason"] == "runtime"


@pytest.mark.asyncio
async def test_create_rejects_invalid_rule_before_http(
    test_host: str, test_pop: str
):
    rule = make_rule(
        logic="buttonSwitch",
        add_ons=[AutomationAddOn(type="offTimer", time=5000)],
    )
    async with EltakoClient(test_host, pop=test_pop) as client:
        with pytest.raises(UnsupportedCommandError, match="offTimer"):
            await client.create_automation(rule)


@pytest.mark.asyncio
async def test_create_bypass_validation_with_flag(
    test_base_url: str, test_host: str, test_pop: str
):
    login_data = load_fixture("login")
    rule = make_rule(
        logic="buttonSwitch",
        add_ons=[AutomationAddOn(type="offTimer", time=5000)],
    )
    with aioresponses() as m:
        m.post(f"{test_base_url}/login", payload=login_data)
        m.post(
            f"{test_base_url}/services/eltako/automations",
            payload=rule.to_dict(),
        )
        async with EltakoClient(test_host, pop=test_pop) as client:
            created = await client.create_automation(rule, validate=False)
            assert created.logic == "buttonSwitch"
