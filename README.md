# Eltako Series 62/64 IP Home Assistant Integration & Client

A modern, local Home Assistant integration and typed async Python client (`aioeltako-ip`) for **Eltako Series 62-IP and Series 64-IPM** smart home devices, targeting **Home Assistant 2026.11+** and **Python 3.14+**.

Supported hardware:
- **Actuators**: ESR64PF-IPM (potential-free relay switch), ESR64NP-IPM, EUD64NPN-IPM, ESB64NP-IPM.
- **EnOcean Gateway**: EOA64 radio adapter with connected EnOcean sensors (e.g. FTK solar window/door contacts).
- **Matter Bridge**: Direct management of on-device Matter bridge exposure.

---

## Architecture & Design

- **Native `aiohttp` Client**: Built directly on `aiohttp` to integrate natively with Home Assistant Core's `async_get_clientsession(hass)` connection pool.
- **Home Assistant 2026.11 Native**: Fully compatible with Home Assistant 2026.11's built-in **Marketplace** (replacing legacy HACS) and Python 3.14 runtime requirements.
- **Zero Cloud / 100% Local**: Communicates directly over local HTTPS (port 443) with the device's on-device REST API using Proof-of-Possession (PoP) authentication.
- **Strict Privacy**: Hardware serial numbers, EURIDs, Proof-of-Possession PINs, and local IPs are strictly parameterized and excluded from version control.

---

## Repository Structure

```text
├── custom_components/eltako_ip/   # Home Assistant custom component
│   ├── manifest.json              # Integration metadata (min HA 2026.11)
│   ├── config_flow.py             # UI configuration & Options flow
│   ├── coordinator.py             # DataUpdateCoordinator (10s polling)
│   ├── switch.py                  # Relay switch platform
│   ├── binary_sensor.py           # Window/door contacts & wired input
│   ├── sensor.py                  # EnOcean RSSI & capacity diagnostics
│   ├── select.py                  # EnOcean repeater level control
│   ├── button.py                  # Trigger EnOcean pairing scan
│   ├── services.yaml              # Custom service definitions
│   └── translations/              # German & English translations
├── src/aioeltako_ip/              # Standalone async client library
│   ├── client.py                  # EltakoClient (aiohttp-based)
│   ├── models.py                  # Typed dataclasses
│   └── exceptions.py              # Error hierarchy
├── scripts/                       # Developer & maintenance utilities
│   ├── deploy.py                  # Deployment script for local testing & live HA
│   ├── test_live_entities.py      # End-to-end live hardware test
│   ├── dev_cli.py                 # Live API fixture capture (writes to local/)
│   ├── anonymize.py               # Sanitizes local dumps into mock fixtures
│   ├── explore.py                 # Endpoint discovery probe
│   ├── inspect_spec.py            # OpenAPI spec analyzer
│   ├── inspect_products.py        # Product catalog inspector
│   └── api.yaml                   # Device OpenAPI 3.1.0 specification
├── tests/                         # Pytest test suite
│   ├── fixtures/                  # Anonymized synthetic mock fixtures (committed)
│   ├── fixtures/local/            # Raw hardware fixture dumps (git-ignored)
│   ├── conftest.py                # Pytest configuration & --live flag
│   ├── test_client.py             # Mock unit tests (aioresponses, run in CI)
│   ├── test_ha_entities.py        # Entity tests against Home Assistant Core classes
│   └── test_live.py               # Real hardware integration tests (--live)
├── hacs.json                      # Marketplace repository configuration
├── ROADMAP.md                     # Roadmap to 100% app feature parity
└── pyproject.toml                 # uv project & packaging configuration
```

---

## Quick Start & Development

Manage the development environment using [`uv`](https://docs.astral.sh/uv/):

```bash
# 1. Install dependencies
uv sync

# 2. Run offline unit tests against anonymized fixtures (Safe for CI)
uv run pytest

# 3. Run live hardware tests against physical device (reads .env)
uv run pytest --live

# 4. Strict typechecking with ty
uv run ty check src/ tests/
```

### Environment Configuration (`.env`)

Create a `.env` file from `.env.example` to store credentials for live testing and deployment:

```bash
cp .env.example .env
```

```ini
# Eltako Hardware Credentials (for live tests & dev CLI)
ELTAKO_HOST=192.168.1.100
ELTAKO_PORT=443
ELTAKO_POP=your_proof_of_possession_pin

# Optional Home Assistant Local Testing Settings
HA_CONFIG_DIR=~/.homeassistant
# Or remote Home Assistant (via SSH):
# HA_REMOTE=root@homeassistant.local:/config
# HA_URL=http://homeassistant.local:8123
# HA_TOKEN=your_long_lived_access_token
```

---

## Deploying to Home Assistant for Local Testing

A dedicated deployment tool is provided at `scripts/deploy.py` to test the integration directly with any running Home Assistant instance.

### 1. Local Deployment (Copy Mode)
Copies the component into your Home Assistant `custom_components` directory and automatically bundles `aioeltako_ip` inside it (so no PyPI install is required in Home Assistant):

```bash
# Explicit path:
python3 scripts/deploy.py --target /path/to/homeassistant/config

# Or using HA_CONFIG_DIR configured in your .env:
python3 scripts/deploy.py
```

### 2. Remote Deployment (SSH / rsync)
Deploys to a remote Home Assistant instance (e.g. Home Assistant OS on a Raspberry Pi or server):

```bash
# Direct argument:
python3 scripts/deploy.py --remote root@homeassistant.local:/config

# Or configure HA_REMOTE in .env and run:
python3 scripts/deploy.py
```

### 3. Automatic Configuration Validation & Restart
If `HA_TOKEN` and `HA_URL` are set in `.env` (or passed via CLI), the deployment script will check Home Assistant's configuration for errors and trigger an automatic restart:

```bash
python3 scripts/deploy.py --restart
```

---

## Home Assistant Setup

### Adding the Integration in Home Assistant
1. Ensure the integration has been deployed via `scripts/deploy.py` or downloaded via the **Marketplace**.
2. Restart Home Assistant.
3. In Home Assistant, navigate to **Settings** > **Devices & Services** > **Add Integration**.
4. Search for **Eltako Series 62/64 IP**.
5. Enter:
   - **Host**: The IP address of your device (e.g. `192.168.1.100`).
   - **Port**: `443` (default).
   - **Proof of Possession (PoP)**: The 8-digit PIN printed on the device sticker.

### Supported Entities
Once added, the integration automatically discovers and creates:
* **Relay Switch (`switch.<device_name>`)**: Controls the potential-free relay contact on ESR64PF-IPM.
* **Window/Door Contact (`binary_sensor.<sensor_name>`)**: Real-time open/closed state of FTK EnOcean sensors.
* **Wired Input (`binary_sensor.<device_name>_wired_input`)**: On/off state of physical wall switches wired to terminal 2.
* **EnOcean RSSI (`sensor.<sensor_name>_signal_strength`)**: Signal strength diagnostics in dBm.
* **EnOcean Memory (`sensor.eltako_enocean_devices_capacity`)**: Diagnostic sensor tracking paired sensor capacity.
* **Repeater Mode (`select.eltako_enocean_repeater`)**: Controls EOA64 repeater level (`off`, `level_1`, `level_2`).
* **Pairing Scan (`button.eltako_scan_enocean_devices`)**: Puts the gateway into pairing mode to learn new EnOcean devices.

---

## Disclaimer & Trademark Notice

This is an independent open-source project and is **not** affiliated with, endorsed by, or associated with **Eltako GmbH** or any of its subsidiaries.

* **"Eltako"** and any related product names or designations (including *ESR64PF-IPM*, *ESR64NP-IPM*, *EUD64NPN-IPM*, *ESB64NP-IPM*, and *EOA64*) are registered trademarks or trade names of Eltako GmbH.
* **"EnOcean"** is a registered trademark of EnOcean GmbH.
* **"Home Assistant"** is a registered trademark of the Open Home Foundation.

All product names, trademarks, and registered trademarks are property of their respective owners and are used in this repository solely for identification, informational, and compatibility purposes.

> [!WARNING]
> This software is provided "as is", without warranty of any kind, express or implied. Controlling building electrical systems and switching actuators carries inherent risk. Always ensure electrical installations comply with local building regulations and safety standards.

---

## AI Assistance Disclosure

Parts of this project—including reverse-engineering and parsing of the on-device OpenAPI 3.1 specification, async client scaffolding, synthetic fixture anonymization, Home Assistant entity platforms, and test suites—were developed with the assistance of AI pair-programming tools (Google Antigravity / Gemini models). 

All code, models, and integration platforms have been reviewed, statically type-checked with `ty`, verified against synthetic mock suites, and tested against physical Eltako Series 64 hardware.

---

## License

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for the full license text.
