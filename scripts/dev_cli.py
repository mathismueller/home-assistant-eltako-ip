import asyncio
import json
import os
import sys
import aiohttp
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("ELTAKO_HOST")
PORT = os.getenv("ELTAKO_PORT", "443")
POP = os.getenv("ELTAKO_POP")
if not HOST or not POP:
    print("Error: ELTAKO_HOST and ELTAKO_POP must be set in your .env file.")
    sys.exit(1)

BASE_URL = f"https://{HOST}:{PORT}/api/v0"
FIXTURES_DIR = "tests/fixtures/local"

os.makedirs(FIXTURES_DIR, exist_ok=True)


async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=10.0)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print(f"1. Attempting login to {BASE_URL}/login...")
        login_payload = {
            "user": "admin",
            "password": POP,
        }

        async with session.post(f"{BASE_URL}/login", json=login_payload) as resp:
            print(f"Login HTTP status: {resp.status}")
            if resp.status != 200:
                text = await resp.text()
                print(f"Login failed! Response: {text}")
                sys.exit(1)

            data = await resp.json()

        api_key = data.get("apiKey")
        print(f"Login successful! API Key received (length {len(api_key)})")

        with open(f"{FIXTURES_DIR}/login.json", "w") as f:
            json.dump(data, f, indent=2)

        headers = {"Authorization": api_key}
        endpoints = [
            ("system", "/system"),
            ("products", "/products"),
            ("devices", "/devices"),
            ("enocean_devices", "/enocean/devices"),
            ("enocean_status", "/enocean/status"),
            ("matter_devices", "/matter/devices"),
        ]

        for name, path in endpoints:
            print(f"Fetching {path}...")
            async with session.get(f"{BASE_URL}{path}", headers=headers) as r:
                if r.status == 200:
                    try:
                        content = await r.json()
                        with open(f"{FIXTURES_DIR}/{name}.json", "w") as f:
                            json.dump(content, f, indent=2)
                        print(f"  -> Saved {name}.json ({len(str(content))} chars)")
                    except Exception as e:
                        print(f"  -> Failed to parse JSON for {name}: {e}")
                else:
                    text = await r.text()
                    print(f"  -> Status {r.status}: {text}")


if __name__ == "__main__":
    asyncio.run(main())
