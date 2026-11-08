# Eltako Series 62/64 IP Integration Roadmap

This roadmap tracks our **100% feature parity** with the official **Eltako Connect** mobile app directly within Home Assistant, while unlocking advanced capabilities exposed by the on-device REST API.

---

## Current Status (v0.2.0 — Full Roadmap Implemented)

| Feature | Supported | Description |
| :--- | :---: | :--- |
| **Relay Switches (1ch & 2ch)** | ✅ | Turn potential-free and standard relay contacts on/off (`ESR64PF-IPM`, `ESR64NP-IPM`, `ESR62NP-IP`, `E2SR64NP-IPM`, `FSR61`). |
| **Universal Dimmers (`light`)** | ✅ | Brightness control (0–100%), restore last brightness, dimming curves, edge mode, min/max brightness (`EUD64NPN-IPM`, `EUD62NPN-IP`, `FUD61`). |
| **Roller Shutters & Blinds (`cover`)** | ✅ | Position control (0–100%), slat tilt angle, runtime & tilt calibration settings (`ESB64NP-IPM`, `ESB62NP-IP`, `FSB61`). |
| **Sensors & Inputs** | ✅ | Wired wall switch inputs (1ch/2ch), FTK window contact, RSSI signal strength, EnOcean memory slots, power/energy/climate telemetry. |
| **Physical Identification** | ✅ | `button.<device>_identify` & `eltako_ip.identify_device` service (`POST /identify`). |
| **On-Device Renaming** | ✅ | `eltako_ip.rename_device` service (`PUT /devices/{deviceGuid}`) synced with Home Assistant's Device Registry. |
| **EnOcean Provisioning & Lifecycle** | ✅ | Interactive Options Flow Pairing Wizard, Legacy Actuator Pairing (`FSR61`/`FUD61`/`FSB61`/`FHK14`), Unpair button & service, orientation select. |
| **Matter Bridge Management** | ✅ | Per-device `Expose to Matter` switch, `Matter Bridged Devices` count sensor, and `reset_matter_bridge` service. |
| **Firmware & OTA Lifecycle** | ✅ | Native `UpdateEntity` (`update.<device>_firmware`), `Auto Update` switch, `Update Check Schedule` select, and offline `.bin` upload CLI/service. |
| **Autonomous On-Device Automations** | ✅ | Wired Input Mode select (`buttonImpulseSwitch` vs `buttonSwitch`), Off-Timer number (`offTimer`), and full CRUD services. |
| **Diagnostics & Health** | ✅ | Redacted diagnostics dump, `async_step_reconfigure`, and `async_step_reauth` flow. |

---

## Completed Phases to Full App Parity

### Phase 1: Device Identification & Configuration Settings
> **Goal:** Match the app's hardware setup screen to customize input behaviors and physically identify devices.

- [x] **Physical Device Identification (`POST /identify`):**
  - Added `button.<device>_identify` entity (`EltakoIdentifyButton`) and `eltako_ip.identify_device` service.
  - When pressed, the physical device flashes its status LED / pulses the actuator, enabling rapid identification inside electrical cabinets or gang boxes.
- [x] **On-Device Renaming (`PUT /devices/{deviceGuid}`):**
  - Added service `eltako_ip.rename_device` to update the device’s internal `displayName` stored in on-device flash memory.
  - Synchronizes Home Assistant Device Registry names with on-device hardware labels.
- [x] **Hardware Settings (`/devices/{deviceGuid}/settings` & `/services/eltako/automations`):**
  - Surfaced persistent hardware settings under `EntityCategory.CONFIG`:
    - **Wired Input Mode (`EltakoWiredInputModeSelect`):** Select between *Pushbutton / Impulse* (`buttonImpulseSwitch`) vs. *Bistable Switch* (`buttonSwitch`, `buttonNormallyOpened`, `buttonNormallyClosed`).
    - **Wired Input Off-Timer (`EltakoAutomationOffTimerNumber`):** Configurable staircase / auto-off timer in seconds (`offTimer` addon).

---

### Phase 2: Complete EnOcean Provisioning & Lifecycle Management
> **Goal:** Match the app's pairing wizard without requiring manual REST calls or raw EURIDs.

- [x] **Interactive Pairing Flow (UI Wizard):**
  - Implemented `async_step_pair_enocean` in `EltakoOptionsFlowHandler`:
    1. Select "Pair EnOcean Sensor (Interactive Scan Wizard)" in gateway options.
    2. Automatically starts scan (`POST /services/enocean/scan`).
    3. Polls `GET /services/enocean/scan` for received teach-in telegrams.
    4. Surfaces discovered devices in a select list with EURID, RSSI (dBm), and product profiles.
    5. Pairs and optionally renames the sensor in one step.
- [x] **Device Unpairing & Deletion (`DELETE /services/enocean/devices/{serviceDeviceGuid}`):**
  - Added `EltakoUnpairEnOceanDeviceButton` (`button.<sensor>_unpair_enocean_device`) and `eltako_ip.unpair_enocean_device` service to safely unpair/delete EnOcean sensors from NVRAM and clean up the Home Assistant Device Registry.
- [x] **Legacy Pairing Flow (`/services/enocean/legacypair`):**
  - Added `async_step_legacy_pair_enocean` wizard and `eltako_ip.legacy_pair_enocean_device` service for bidirectional EnOcean actuators (`FSR61`, `FUD61`, `FSB61`, `FHK14`).
- [x] **Per-Device EnOcean Configuration:**
  - Added `EltakoEnOceanOrientationSelect` (`select.<sensor>_orientation`) and `eltako_ip.set_enocean_device_config` service (`GET/PUT /services/enocean/devices/{serviceDeviceGuid}/config`).

---

### Phase 3: Matter Bridge Management & Exposure
> **Goal:** Control the device’s embedded Matter bridge to selectively expose actuators and sensors to Matter fabrics.

- [x] **Matter Exposure Entities (`/services/matter/devices`):**
  - Added `EltakoMatterExposureSwitch` (`switch.<device>_expose_to_matter`) for each local channel and paired EnOcean sensor.
  - Toggling the switch calls `POST` or `DELETE /services/matter/devices` to dynamically expose or hide devices from the Matter fabric.
- [x] **Matter Commissioning Status & Diagnostics (`GET /services/matter`):**
  - Added `EltakoMatterBridgedCountSensor` (`sensor.<device>_matter_bridged_devices`) showing bridged endpoint count and endpoint mappings.
- [x] **Matter Factory Reset Service (`/services/matter`):**
  - Added `eltako_ip.reset_matter_bridge` service to reset the internal Matter bridge.

---

### Phase 4: Firmware Lifecycle & Update Management
> **Goal:** Full visibility and control over device updates without the mobile app.

- [x] **Home Assistant Update Entity (`update.py`):**
  - Implemented `EltakoFirmwareUpdateEntity` (`update.<device>_firmware`) exposing `installed_version`, `latest_version`, and OTA metadata attributes.
- [x] **Auto-Update Toggle (`switch.<device>_auto_update`):**
  - Exposed `EltakoAutoUpdateSwitch` (`PUT /update/config`) to toggle background firmware updates from Home Assistant.
- [x] **Update Schedule / Server Configuration:**
  - Exposed `EltakoUpdateScheduleSelect` (`select.<device>_update_check_schedule`) for `6h`, `12h`, and `24h` schedules.
- [x] **Offline / Local Firmware Upload Tool:**
  - Added `eltako_ip.upload_firmware` service and `python3 scripts/dev_cli.py upload-firmware --file <path>` CLI command.

---

### Phase 5: Autonomous On-Device Automations
> **Goal:** Configure fail-safe direct bindings that execute on the chip without network dependency.

- [x] **On-Device Automation Engine (`/services/eltako/automations`):**
  - Added `EltakoWiredInputModeSelect`, `EltakoAutomationOffTimerNumber`, `EltakoAutomationsCountSensor`, and services `create_automation`, `update_automation`, `delete_automation`, and `reset_automations`.
  - **Fail-safe Guarantee:** Even if Home Assistant or Wi-Fi are offline, the physical switch and EnOcean contacts continue to trigger the actuator in hardware with zero latency.

---

### Phase 6: Expanded Device Family Support
> **Goal:** Broaden integration beyond ESR64PF-IPM to all Series 62-IP and Series 64-IPM models.

- [x] **Universal Dimmers (`light` platform):**
  - **Models:** `EUD64NPN-IPM`, `EUD62NPN-IP`, `EUD62NPN-IPM`, `FUD61`.
  - Brightness control (`EltakoDimmerLight`), dimming curves (`dimCurve`), edge mode (`edgeMode`), minimum/maximum brightness (`minimumBrightness`, `maximumBrightness`), and `lastBrightness` restore.
- [x] **Roller Shutter & Blind Actuators (`cover` platform):**
  - **Models:** `ESB64NP-IPM`, `ESB62NP-IP`, `FSB61`.
  - Position control (`0–100%`), slat tilt angle (`0–100%`), calibration runtime (`runtime`), start offset (`offset`), and tilt runtime (`tiltRuntime`).
- [x] **Standard & 2-Channel Relays (`switch` platform):**
  - **Models:** `ESR64NP-IPM`, `ESR62NP-IP`, `ESR62PF-IP`, `E2SR64NP-IPM`, `FSR61`.
