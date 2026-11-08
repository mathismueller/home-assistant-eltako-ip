"""Developer CLI for Eltako Series 62/64 IP devices (fixture dumping, identify, and offline firmware upload)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

# Ensure src/aioeltako_ip is importable when invoked directly
_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from aioeltako_ip import EltakoClient  # noqa: E402

load_dotenv()

FIXTURES_DIR = Path("tests/fixtures/local")


async def dump_fixtures(client: EltakoClient) -> None:
    """Dump all device endpoints to tests/fixtures/local/."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    key = await client.login()
    with open(FIXTURES_DIR / "login.json", "w") as f:
        json.dump({"apiKey": key}, f, indent=2)
    print(f"Login successful! API Key received (length {len(key)})")

    endpoints = [
        ("well_known", "/.well-known/eltako/devices", True),
        ("system", "/system", False),
        ("products", "/products", False),
        ("devices", "/devices", False),
        ("enocean_devices", "/services/enocean/devices", False),
        ("enocean_status", "/services/enocean/status", False),
        ("enocean_scan", "/services/enocean/scan", False),
        ("legacypair_status", "/services/enocean/legacypair/status", False),
        (
            "legacypair_supported",
            "/services/enocean/legacypair/info/supported-devices",
            False,
        ),
        ("matter_devices", "/services/matter/devices", False),
        ("automations", "/services/eltako/automations", False),
        ("update_config", "/update/config", False),
        ("update_firmware", "/update/firmware", False),
    ]

    for name, path, use_root in endpoints:
        print(f"Fetching {path}...")
        try:
            content = await client._request("GET", path, use_root=use_root)
            with open(FIXTURES_DIR / f"{name}.json", "w") as f:
                json.dump(content, f, indent=2)
            print(f"  -> Saved {name}.json ({len(str(content))} chars)")
        except Exception as err:
            print(f"  -> Failed {name}: {err}")


async def upload_firmware(
    client: EltakoClient,
    file_path: Path,
    desired_version: str | None = None,
) -> None:
    """Upload a local firmware binary (.bin) to the Eltako device."""
    if not file_path.is_file():
        print(f"Error: Firmware file not found: {file_path}")
        sys.exit(1)

    await client.login()
    if desired_version:
        print(f"Staging firmware version {desired_version} on /update/firmware...")
        await client.prepare_firmware_update(
            {"update": {"desiredVersion": desired_version}}
        )
    data = file_path.read_bytes()
    print(f"Uploading {len(data)} bytes from {file_path} to /update/firmware/bin...")
    ok = await client.upload_firmware_binary(data)
    print(f"Firmware upload result: {ok}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Eltako Series 62/64 IP Developer CLI")
    parser.add_argument(
        "command",
        nargs="?",
        default="dump",
        choices=["dump", "identify", "upload-firmware"],
        help="Action to perform (default: dump)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Path to local firmware .bin file (for upload-firmware)",
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Optional desired firmware version string (for upload-firmware)",
    )
    args = parser.parse_args()

    host = os.getenv("ELTAKO_HOST")
    port = int(os.getenv("ELTAKO_PORT", "443"))
    pop = os.getenv("ELTAKO_POP")
    if not host or not pop:
        print("Error: ELTAKO_HOST and ELTAKO_POP must be set in your .env file.")
        sys.exit(1)

    async with EltakoClient(host=host, port=port, pop=pop) as client:
        if args.command == "dump":
            await dump_fixtures(client)
        elif args.command == "identify":
            await client.login()
            res = await client.identify()
            print(f"Identify response: {res}")
        elif args.command == "upload-firmware":
            if not args.file:
                print("Error: --file is required for upload-firmware")
                sys.exit(1)
            await upload_firmware(client, args.file, args.version)


if __name__ == "__main__":
    asyncio.run(main())
