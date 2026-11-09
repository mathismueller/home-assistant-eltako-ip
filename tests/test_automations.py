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
