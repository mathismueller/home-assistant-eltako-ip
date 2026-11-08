"""Sanitizes local hardware fixture dumps into anonymized mocks for public repo."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
LOCAL_DIR = BASE_DIR / "tests" / "fixtures" / "local"
PUBLIC_DIR = BASE_DIR / "tests" / "fixtures"

REAL_IP = os.getenv("ELTAKO_HOST", "")
REAL_POP = os.getenv("ELTAKO_POP", "")
REAL_SERIAL = os.getenv("ELTAKO_SERIAL", "")
REAL_EURID = os.getenv("ELTAKO_EURID", "")

# Physical Hardware Identifiers & Instance UUIDs -> Synthetic Placeholders
REPLACEMENTS = {
    # Instance Device GUIDs (Random session UUIDs) -> Semantic Test UUIDs
    "3889bfbc-3efc-4d37-ac76-ac89e781c21f": "11111111-1111-1111-1111-111111111111",  # Relay
    "60f693b9-d58d-4a89-895f-6fbc119d5565": "22222222-2222-2222-2222-222222222222",  # Wired Input
    "36a755be-2f70-4d0c-868b-259a0573d7f9": "33333333-3333-3333-3333-333333333333",  # Window Sensor
    # Instance Service Device GUIDs
    "44f78d44-05f5-44fc-af8e-d6a265bf09c6": "44444444-4444-4444-4444-444444444444",  # EnOcean Service Dev
    "903a207f-027e-4a4d-b68e-8dc4e5cf4d8a": "55555555-5555-5555-5555-555555555550",  # Actuator Service Dev
    "d31e3708-9ad5-44af-9423-ba38f73023b6": "55555555-5555-5555-5555-555555555551",  # Matter Relay Dev
    "7bbc0af3-423b-4c61-b269-ab90abc6135a": "55555555-5555-5555-5555-555555555552",  # Matter Window Dev
    "c95b46b5-85be-47ab-abb0-55e413f3c47c": "55555555-5555-5555-5555-555555555553",  # Matter Input Dev
}

if REAL_POP:
    REPLACEMENTS[REAL_POP] = "test_proof_of_possession"
if REAL_IP:
    REPLACEMENTS[REAL_IP] = "192.0.2.1"
if REAL_SERIAL:
    REPLACEMENTS[REAL_SERIAL] = "ELTAKO-0000000000"
if REAL_EURID:
    REPLACEMENTS[REAL_EURID] = "16909060"


def sanitize_text(text: str) -> str:
    for real, synthetic in REPLACEMENTS.items():
        text = text.replace(real, synthetic)
    return text


def main():
    if not LOCAL_DIR.exists():
        print(f"Error: Local directory {LOCAL_DIR} does not exist.")
        return

    print("Sanitizing fixtures from tests/fixtures/local/ -> tests/fixtures/...")
    count = 0
    for file_path in LOCAL_DIR.glob("*.json"):
        # Skip redundant single-device dump files (devices.json holds everything)
        if file_path.name.startswith("device_"):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Specific sanitization for login.json
        if file_path.name == "login.json":
            sanitized_data = {"apiKey": "mock_jwt_api_key_test_token"}
            sanitized_content = json.dumps(sanitized_data, indent=2) + "\n"
        else:
            sanitized_content = sanitize_text(content)

        dest_path = PUBLIC_DIR / file_path.name
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(sanitized_content)
        count += 1

    print(f"Successfully sanitized {count} fixture files.")


if __name__ == "__main__":
    main()
