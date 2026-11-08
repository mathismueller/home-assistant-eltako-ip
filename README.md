# Eltako Series 62/64 IP Home Assistant Integration & Client

A Home Assistant integration and typed async Python client (`aioeltako-ip`) for **Eltako Series 62-IP and Series 64-IPM** smart home devices, targeting **Home Assistant 2026.11+**. It enables 100% local setup, control, EnOcean provisioning, Matter bridge management, firmware management, and autonomous on-device automation configuration without requiring the manufacturer mobile app.

### Supported Hardware
- **Relay Actuators (`switch`)**: `ESR64PF-IPM`, `ESR64NP-IPM`, `ESR62NP-IP`, `ESR62PF-IP`, `E2SR64NP-IPM` (2-channel), `FSR61`.
- **Universal Dimmers (`light`)**: `EUD64NPN-IPM`, `EUD62NPN-IP`, `EUD62NPN-IPM`, `FUD61`.
- **Shading & Roller Shutter Actuators (`cover`)**: `ESB64NP-IPM`, `ESB62NP-IP`, `FSB61`.
- **EnOcean Gateway (`EOA64`)**: Paired EnOcean sensors and actuators (e.g. `FTK` solar window/door contacts, wall rockers, power/climate/environmental sensors).

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

A dedicated deployment tool is provided at `scripts/deploy.py` to test the integration directly with any running Home Assistant instance. Note that `src/aioeltako_ip` is maintained as a standalone library within this repository and is automatically bundled into the target Home Assistant `custom_components/eltako_ip/` folder during deployment.

### 1. Local Deployment (Copy Mode)
Copies the component into your Home Assistant `custom_components` directory and automatically bundles `src/aioeltako_ip` inside it:

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

## Home Assistant Setup & Capabilities

### Adding the Integration in Home Assistant
1. Deploy via `scripts/deploy.py` or add this repository as a custom HACS repository.
2. Restart Home Assistant.
3. Navigate to **Settings** > **Devices & Services** > **Add Integration** and search for **Eltako Series 62/64 IP**.
4. Enter:
   - **Host**: IP address of your device (e.g. `192.168.1.100`).
   - **Port**: `443` (default).
   - **Proof of Possession (PoP)**: The PIN printed on the device sticker.

### Platforms & Entities
- **Switch (`switch`)**:
  - 1-channel and 2-channel relay outputs (`Relay`, `Relay Channel 1`, `Relay Channel 2`).
  - `Auto Update` configuration toggle (`PUT /update/config`).
  - Per-device `Expose to Matter` configuration switch (`POST`/`DELETE /services/matter/devices`).
- **Light (`light`)**:
  - Universal dimmer brightness control (`0–100%`) with `lastBrightness` restore (`EUD64NPN-IPM`, `EUD62NPN-IP`, `FUD61`).
- **Cover (`cover`)**:
  - Roller shutter and blind position (`0–100%`) and slat tilt angle (`0–100%`) control (`ESB64NP-IPM`, `ESB62NP-IP`, `FSB61`).
- **Binary Sensor (`binary_sensor`)**:
  - Window/door contact (`FTK`), sensor connectivity status, 1ch/2ch physical wired inputs, and dynamic motion/smoke/moisture/vibration sensors.
- **Sensor (`sensor`)**:
  - EnOcean RSSI (`dBm`), `EnOcean Free Slots`, `Matter Bridged Devices`, `On-Device Automations`, plus dynamic telemetry (`power`, `electricEnergyMeter`, `temperature`, `humidity`, `illumination`, `co2`, `tvoc`, `batteryPercentageRemaining`, `windSpeed`).
- **Select (`select`)**:
  - `EnOcean Repeater Level` (`off`, `oneLevel`, `twoLevel`).
  - `Update Check Schedule` (`6h`, `12h`, `24h`).
  - `Wired Input Mode` (`buttonImpulseSwitch` Pushbutton vs `buttonSwitch` Kippschalter).
  - Dynamic hardware enumeration settings (`edgeMode`, `dimCurve`, `runtimeMode`, `movementDirection`, `enableTilt`).
  - Per-device EnOcean `Orientation` (`auto`, `clockwise0`, `clockwise90`, `clockwise180`, `clockwise270`).
- **Number (`number`)**:
  - `Wired Input Off-Timer` in seconds (on-device hardware staircase/auto-off timer).
  - Dynamic hardware numeric settings (`minimumBrightness`, `maximumBrightness`, `runtime`, `offset`, `tiltRuntime`, temperature/humidity offsets).
- **Button (`button`)**:
  - `Identify` (`POST /identify` to flash the physical LED).
  - Per-sensor `Unpair EnOcean Device` (`DELETE /services/enocean/devices/{guid}`).
- **Update (`update`)**:
  - `Firmware` update status entity showing installed vs. latest firmware version and OTA server metadata.

### Domain Services (`eltako_ip.*`)
- `eltako_ip.identify_device`: Flash the physical LED on the actuator.
- `eltako_ip.rename_device`: Update `displayName` in on-device flash and synchronize the Home Assistant Device Registry name.
- `eltako_ip.start_enocean_scan`: Start a teach-in scan for new EnOcean sensors.
- `eltako_ip.pair_enocean_device`: Pair a discovered EnOcean EURID to a product profile (with optional immediate rename).
- `eltako_ip.unpair_enocean_device`: Delete a paired EnOcean sensor from NVRAM and remove it from the Device Registry.
- `eltako_ip.legacy_pair_enocean_device`: Start or continue bidirectional EnOcean actuator pairing (`FSR61`, `FUD61`, `FSB61`, `FHK14`).
- `eltako_ip.set_enocean_device_config`: Configure orientation or bridge direction on a paired EnOcean device.
- `eltako_ip.expose_matter_device` / `eltako_ip.remove_matter_device` / `eltako_ip.reset_matter_bridge`: Manage the embedded Matter bridge.
- `eltako_ip.create_automation` / `eltako_ip.update_automation` / `eltako_ip.delete_automation` / `eltako_ip.reset_automations`: Manage fail-safe autonomous on-device hardware automations.
- `eltako_ip.upload_firmware`: Upload a local signed `.bin` firmware image directly to the device.

---

## Repository Structure

```text
├── custom_components/eltako_ip/   # Home Assistant custom component
│   ├── manifest.json              # Integration metadata (min HA 2026.11)
│   ├── config_flow.py             # Setup, Reauth, Reconfigure & EnOcean Pairing Wizard
│   ├── coordinator.py             # DataUpdateCoordinator & EltakoData
│   ├── entity.py                  # Unified EltakoGatewayEntity & EltakoDeviceEntity
│   ├── switch.py                  # Relays (1ch/2ch), Auto-Update & Matter Exposure
│   ├── light.py                   # Universal Dimmers (EUD64NPN-IPM / EUD62NPN-IP / FUD61)
│   ├── cover.py                   # Shading & Blind Actuators (ESB64NP-IPM / ESB62NP-IP / FSB61)
│   ├── binary_sensor.py           # Contacts, Connectivity & Wired Inputs
│   ├── sensor.py                  # EnOcean RSSI, Capacity, Matter, Automations & Telemetry
│   ├── select.py                  # Repeater, Schedule, Wired Input Mode & Hardware Settings
│   ├── number.py                  # Off-Timer & Numeric Hardware Settings
│   ├── button.py                  # Identify, EnOcean Scan & Unpair
│   ├── update.py                  # Firmware Update Entity
│   ├── diagnostics.py             # Redacted Diagnostics Dump
│   ├── services.yaml              # Domain Service Definitions
│   └── translations/              # English & German UI Translations
├── src/aioeltako_ip/              # Standalone async client library (single source of truth)
│   ├── client.py                  # EltakoClient (aiohttp-based)
│   ├── models.py                  # Typed dataclasses
│   └── exceptions.py              # Error hierarchy
├── scripts/                       # Developer & deployment utilities
│   ├── deploy.py                  # Local/SSH deployment script (bundles src/aioeltako_ip)
│   └── dev_cli.py                 # Fixture dumper, identify & offline firmware uploader
├── tests/                         # Pytest test suite
│   ├── fixtures/                  # Anonymized synthetic fixtures (committed)
│   ├── fixtures/local/            # Raw hardware fixture dumps (git-ignored)
│   ├── conftest.py                # Pytest configuration & --live flag
│   ├── test_client.py             # Mock unit tests (aioresponses)
│   ├── test_ha_entities.py        # Home Assistant entity & diagnostics unit tests
│   └── test_live.py               # Real hardware integration tests (--live)
├── hacs.json                      # HACS Marketplace repository configuration
├── ROADMAP.md                     # Phased roadmap for On-Device Automations
└── pyproject.toml                 # uv project & packaging configuration
```

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
