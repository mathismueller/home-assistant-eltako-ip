"""Live test runner demonstrating full integration against device."""

import asyncio
import os
import sys
from dotenv import load_dotenv
from aioeltako_ip import EltakoClient

load_dotenv()

HOST = os.getenv("ELTAKO_HOST")
PORT = int(os.getenv("ELTAKO_PORT", "443"))
POP = os.getenv("ELTAKO_POP")
if not HOST or not POP:
    print("Error: ELTAKO_HOST and ELTAKO_POP must be set in your .env file.")
    sys.exit(1)
assert HOST is not None and POP is not None

PRODUCT_ESR64PF_IPM = "4893e06b-448c-40d5-b426-42e2e6b73656"
PRODUCT_FTK_CONTACT = "791a7c28-22e3-4fab-8ecc-0084e15396c5"
PRODUCT_WIRED_INPUT = "6f6d379f-4c6f-45ed-b881-671ed7ea8970"


async def main():
    assert HOST is not None and POP is not None
    print(f"Connecting to Eltako device at {HOST}:{PORT}...")
    async with EltakoClient(HOST, pop=POP, port=PORT) as client:
        # 1. System info
        system = await client.get_system()
        print("\n" + "=" * 55)
        print(f"  DEVICE:   {system.product_name}")
        print(f"  SERIAL:   {system.serial_number}")
        print(f"  FIRMWARE: {system.software_version}")
        print("=" * 55)

        # 2. Devices and mapped HA entities
        devices = await client.get_devices()
        print("\n--- Mapped Home Assistant Entities ---")
        for dev in devices:
            if dev.product_guid == PRODUCT_ESR64PF_IPM:
                relay_state = dev.get_function_value("relay")
                print(f"[SWITCH] {dev.display_name} (Relay)")
                print(f"         State: {'ON' if relay_state == 'on' else 'OFF'} (raw: {relay_state})")
                print(f"         GUID:  {dev.device_guid}")

            elif dev.product_guid == PRODUCT_FTK_CONTACT:
                contact = dev.get_info_value("contact")
                conn = dev.get_info_value("connectionStatus")
                print(f"[BINARY SENSOR] {dev.display_name} (Window/Door Contact)")
                print(f"                State:  {'OPEN' if contact == 'opened' else 'CLOSED'} (raw: {contact})")
                print(f"                Status: {conn}")
                print(f"                GUID:   {dev.device_guid}")

            elif dev.product_guid == PRODUCT_WIRED_INPUT:
                inp = dev.get_function_value("input")
                print(f"[BINARY SENSOR] {dev.display_name} (Wired Input)")
                print(f"                State: {'OPEN' if inp == 'opened' else 'CLOSED'} (raw: {inp})")
                print(f"                GUID:  {dev.device_guid}")

        # 3. EnOcean Diagnostics
        eo_status = await client.get_enocean_status()
        eo_devs = await client.get_enocean_devices()
        eo_config = await client.get_enocean_configuration()

        print("\n--- EnOcean Gateway Telemetry ---")
        print(f"Radio Health:         {eo_status.health}")
        print(f"Radio Slots Used:     {eo_status.max_eur_ids - eo_status.free_eur_ids} / {eo_status.max_eur_ids}")
        print(f"Repeater Level:       {eo_config.get('repeaterLevel')}")
        print(f"Paired EnOcean Units: {len(eo_devs)}")
        for ed in eo_devs:
            print(f"  - EURID: 0x{ed.eur_id:08X} ({ed.eur_id}) | RSSI: {ed.signal_strength} dBm | Seen: {ed.last_seen}")

        # 4. Matter Bridge Exposure
        matter_devs = await client.get_matter_devices()
        print("\n--- Matter Bridge Exposed Endpoints ---")
        for md in matter_devs:
            print(f"  - Endpoint #{md.endpoint_id} | Device GUID: {md.device_guid}")

        print("\nVerification complete! All services and entities responding.")


if __name__ == "__main__":
    asyncio.run(main())
