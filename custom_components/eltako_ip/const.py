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
PRODUCT_WIRED_INPUT: Final = "6f6d379f-4c6f-45ed-b881-671ed7ea8970"
PRODUCT_FTK_CONTACT: Final = "791a7c28-22e3-4fab-8ecc-0084e15396c5"

# EnOcean repeater options
REPEATER_LEVEL_OFF: Final = "off"
REPEATER_LEVEL_1: Final = "oneLevel"
REPEATER_LEVEL_2: Final = "twoLevel"
REPEATER_OPTIONS: Final = [REPEATER_LEVEL_OFF, REPEATER_LEVEL_1, REPEATER_LEVEL_2]

# Services
SERVICE_START_ENOCEAN_SCAN: Final = "start_enocean_scan"
SERVICE_PAIR_ENOCEAN_DEVICE: Final = "pair_enocean_device"
SERVICE_EXPOSE_MATTER_DEVICE: Final = "expose_matter_device"
SERVICE_REMOVE_MATTER_DEVICE: Final = "remove_matter_device"
