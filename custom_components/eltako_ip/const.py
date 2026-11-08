"""Constants for the Eltako Series 62/64 IP integration."""

from typing import Final

DOMAIN: Final = "eltako_ip"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_POP: Final = "pop"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_PORT: Final = 443
DEFAULT_SCAN_INTERVAL: Final = 10

# Product GUIDs verified from device product database
PRODUCT_ESR64PF_IPM: Final = "4893e06b-448c-40d5-b426-42e2e6b73656"
PRODUCT_ESR64NP_IPM: Final = "ade276c9-a9a2-41cd-9114-631b8d1177b4"
PRODUCT_ESR62NP_IP: Final = "f4c6539f-807c-4936-8063-1e307c7795e7"
PRODUCT_ESR62PF_IP: Final = "ab9075a6-3bcf-428a-bb83-c65cc6af63a3"
PRODUCT_E2SR64NP_IPM: Final = "489355b8-64dd-49e7-b7b8-0608bf8e67c7"
PRODUCT_FSR61: Final = "7358f66f-5d44-4781-a4eb-bd6857e8e39e"

PRODUCT_EUD64NPN_IPM: Final = "b7580625-4e9f-473b-afe4-29e0c073744a"
PRODUCT_EUD62NPN_IP: Final = "8077e5f1-5e9c-44de-83c7-fdd7f2b8e090"
PRODUCT_EUD62NPN_IPM: Final = "82f2faba-9645-4de7-9083-0df9156cb0cc"
PRODUCT_FUD61: Final = "195cd597-136e-4e0e-923c-65016a49bcab"

PRODUCT_ESB64NP_IPM: Final = "2b046bb5-6bcd-4d41-9c5c-01bac63ebc1d"
PRODUCT_ESB62NP_IP: Final = "0b898240-e820-4a06-879a-fccf35260a35"
PRODUCT_FSB61: Final = "35784df1-4372-443c-9743-b234e9af283b"

PRODUCT_WIRED_INPUT: Final = "6f6d379f-4c6f-45ed-b881-671ed7ea8970"
PRODUCT_WIRED_INPUT_2CH: Final = "52d055e8-4bf4-4583-a9d8-5672bb36dbcf"
PRODUCT_FTK_CONTACT: Final = "791a7c28-22e3-4fab-8ecc-0084e15396c5"

LOCAL_WIRED_INPUT_PRODUCTS: Final = {
    PRODUCT_WIRED_INPUT,
    PRODUCT_WIRED_INPUT_2CH,
}

# Fallback human-readable names when /products is not loaded
PRODUCT_NAMES_FALLBACK: Final[dict[str, str]] = {
    PRODUCT_ESR64PF_IPM: "ESR64PF-IPM Relay Actuator",
    PRODUCT_ESR64NP_IPM: "ESR64NP-IPM Relay Actuator",
    PRODUCT_ESR62NP_IP: "ESR62NP-IP Relay Actuator",
    PRODUCT_ESR62PF_IP: "ESR62PF-IP Relay Actuator",
    PRODUCT_E2SR64NP_IPM: "E2SR64NP-IPM 2-Channel Relay Actuator",
    PRODUCT_FSR61: "FSR61 EnOcean Relay",
    PRODUCT_EUD64NPN_IPM: "EUD64NPN-IPM Universal Dimmer",
    PRODUCT_EUD62NPN_IP: "EUD62NPN-IP Universal Dimmer",
    PRODUCT_EUD62NPN_IPM: "EUD62NPN-IPM Universal Dimmer",
    PRODUCT_FUD61: "FUD61 EnOcean Dimmer",
    PRODUCT_ESB64NP_IPM: "ESB64NP-IPM Shading & Blind Actuator",
    PRODUCT_ESB62NP_IP: "ESB62NP-IP Shading & Blind Actuator",
    PRODUCT_FSB61: "FSB61 EnOcean Blind Actuator",
    PRODUCT_WIRED_INPUT: "Wired Input",
    PRODUCT_WIRED_INPUT_2CH: "Wired Input (2-Channel)",
    PRODUCT_FTK_CONTACT: "FTK Solar Contact Sensor",
}

# EnOcean repeater options
REPEATER_LEVEL_OFF: Final = "off"
REPEATER_LEVEL_1: Final = "oneLevel"
REPEATER_LEVEL_2: Final = "twoLevel"
REPEATER_OPTIONS: Final = [REPEATER_LEVEL_OFF, REPEATER_LEVEL_1, REPEATER_LEVEL_2]

# Update schedule options
UPDATE_SCHEDULE_6H: Final = "6h"
UPDATE_SCHEDULE_12H: Final = "12h"
UPDATE_SCHEDULE_24H: Final = "24h"
UPDATE_SCHEDULE_OPTIONS: Final = [
    UPDATE_SCHEDULE_6H,
    UPDATE_SCHEDULE_12H,
    UPDATE_SCHEDULE_24H,
]

# On-device automation logic modes (Wired Input Taster vs Kippschalter)
AUTOMATION_LOGIC_IMPULSE: Final = "buttonImpulseSwitch"
AUTOMATION_LOGIC_SWITCH: Final = "buttonSwitch"
AUTOMATION_LOGIC_NORMALLY_OPENED: Final = "buttonNormallyOpened"
AUTOMATION_LOGIC_NORMALLY_CLOSED: Final = "buttonNormallyClosed"
AUTOMATION_LOGIC_TARGET: Final = "buttonTargetValue"
AUTOMATION_LOGIC_UNIVERSAL_DIMMER: Final = "universalButtonDimmer"

WIRED_INPUT_LOGIC_OPTIONS: Final = [
    AUTOMATION_LOGIC_IMPULSE,
    AUTOMATION_LOGIC_SWITCH,
    AUTOMATION_LOGIC_NORMALLY_OPENED,
    AUTOMATION_LOGIC_NORMALLY_CLOSED,
]

# EnOcean device orientation options
ENOCEAN_ORIENTATION_OPTIONS: Final = [
    "auto",
    "clockwise0",
    "clockwise90",
    "clockwise180",
    "clockwise270",
]

# Default setting enumerations when /products spec is not present
DEFAULT_SETTING_ENUMS: Final[dict[str, list[str]]] = {
    "edgeMode": ["auto", "leadingEdge", "trailingEdge"],
    "dimCurve": ["linear", "LC1", "LC2", "LC3"],
    "runtimeMode": ["auto", "manual"],
    "movementDirection": ["asPrintedOnCase", "inverted"],
    "enableTilt": ["disabled", "enabled"],
}

# Services
SERVICE_IDENTIFY_DEVICE: Final = "identify_device"
SERVICE_RENAME_DEVICE: Final = "rename_device"
SERVICE_START_ENOCEAN_SCAN: Final = "start_enocean_scan"
SERVICE_PAIR_ENOCEAN_DEVICE: Final = "pair_enocean_device"
SERVICE_UNPAIR_ENOCEAN_DEVICE: Final = "unpair_enocean_device"
SERVICE_LEGACY_PAIR_ENOCEAN: Final = "legacy_pair_enocean_device"
SERVICE_SET_ENOCEAN_DEVICE_CONFIG: Final = "set_enocean_device_config"
SERVICE_EXPOSE_MATTER_DEVICE: Final = "expose_matter_device"
SERVICE_REMOVE_MATTER_DEVICE: Final = "remove_matter_device"
SERVICE_RESET_MATTER_BRIDGE: Final = "reset_matter_bridge"
SERVICE_CREATE_AUTOMATION: Final = "create_automation"
SERVICE_UPDATE_AUTOMATION: Final = "update_automation"
SERVICE_DELETE_AUTOMATION: Final = "delete_automation"
SERVICE_RESET_AUTOMATIONS: Final = "reset_automations"
SERVICE_UPLOAD_FIRMWARE: Final = "upload_firmware"
