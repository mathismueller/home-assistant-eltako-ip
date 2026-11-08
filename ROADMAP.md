# Eltako Series 62/64 IP Integration Roadmap

This roadmap outlines the plan to achieve **100% feature parity** with the official **Eltako Connect** mobile app directly within Home Assistant, while unlocking advanced capabilities exposed by the on-device REST API.

---

## Current Status (v1.0.0)

| Feature | Supported | Description |
| :--- | :---: | :--- |
| **Relay Switch** | ✅ | Turn potential-free relay contact on/off (`ESR64PF-IPM`). |
| **Sensors & Inputs** | ✅ | Wired wall switch input, FTK window contact, RSSI signal strength, EnOcean memory slot capacity. |
| **Repeater Control** | ✅ | EnOcean repeater level selector (`off`, `level_1`, `level_2`). |
| **Teach-In Scan** | ✅ | Button & service to initiate EnOcean pairing scan. |
| **Diagnostics & Health** | ✅ | Redacted diagnostics dump and `async_step_reconfigure` flow. |
| **Local Deployment** | ✅ | Automated self-contained deploy script (`scripts/deploy.py`). |

---

## Planned Phases to Full App Parity

### Phase 1: Device Identification & Configuration Settings
> **Goal:** Match the app's hardware setup screen to customize input behaviors and physically identify devices.

- [ ] **Physical Device Identification (`POST /identify`):**
  - Add `button.<device>_identify` entity in Home Assistant.
  - When pressed, the physical device flashes its status LED / pulses the relay, enabling rapid identification inside electrical cabinets or gang boxes.
- [ ] **On-Device Renaming (`PUT /devices/{deviceGuid}`):**
  - Add service `eltako_ip.rename_device` to update the device’s internal `displayName` stored in on-device flash memory.
  - Keep Home Assistant device registry names synchronized with on-device hardware labels.
- [ ] **Hardware Settings (`/devices/{deviceGuid}/settings`):**
  - Surface persistent hardware settings under `EntityCategory.CONFIG`:
    - **Wired Input Mode:** Select between *Pushbutton / Impulse* (Taster) vs. *Bistable Switch* (Kippschalter).
    - **Debounce / Offset Times:** Configurable timing parameters for inputs.

---

### Phase 2: Complete EnOcean Provisioning & Lifecycle Management
> **Goal:** Match the app's pairing wizard without requiring manual REST calls or raw EURIDs.

- [ ] **Interactive Pairing Flow (UI Wizard):**
  - Create a Home Assistant Config Flow / Action handler that guides users through pairing:
    1. Click "Add EnOcean Device".
    2. Start scan (`POST /services/enocean/scan`).
    3. Continuously poll `GET /services/enocean/scan` for received teach-in telegrams.
    4. Surface discovered devices in a select list with RSSI and suggested device profiles.
    5. Confirm and link into `GET /devices`.
- [ ] **Device Unpairing & Deletion (`DELETE /services/enocean/devices/{serviceDeviceGuid}`):**
  - Add service and button to safely unpair/delete EnOcean sensors directly from the device's NVRAM.
- [ ] **Legacy Pairing Flow (`/services/enocean/legacypair`):**
  - Support pairing older EnOcean devices that lack teach-in buttons by entering EURID and EnOcean Equipment Profile (EEP) manually.
- [ ] **Per-Device EnOcean Configuration:**
  - View and customize per-sensor configuration via `GET/PUT /services/enocean/devices/{serviceDeviceGuid}/config`.

---

### Phase 3: Matter Bridge Management & Exposure
> **Goal:** Control the device’s embedded Matter bridge to selectively expose actuators and sensors to Matter fabrics.

- [ ] **Matter Exposure Entities (`/services/matter/devices`):**
  - Add switch entities (e.g. `switch.<device>_expose_to_matter`) for each local channel and paired EnOcean sensor.
  - Toggling the switch calls `POST` or `DELETE /services/matter/devices` to dynamically expose or hide devices from the Matter fabric.
- [ ] **Matter Commissioning Status & Diagnostics (`GET /services/matter`):**
  - Diagnostic sensors showing Matter bridge state, active fabrics count, and commissioning status.
- [ ] **Matter Factory Reset Service (`DELETE /services/matter`):**
  - Service to unpair the device from all Matter controllers and reset its Matter fabric credentials.

---

### Phase 4: Firmware Lifecycle & Update Management
> **Goal:** Full visibility and control over device updates without the mobile app.

- [ ] **Home Assistant Update Entity (`update.py`):**
  - Implement the native Home Assistant `UpdateEntity` platform:
    - Displays current installed version (e.g. `2.5.0`) vs. available upstream version.
    - Notifies the user when a new release is published on `update.eltako.com`.
- [ ] **Auto-Update Toggle (`switch.<device>_auto_update`):**
  - Expose a configuration switch for `autoUpdate` (`PUT /update/config`), allowing users to toggle background updates directly from Home Assistant dashboards.
- [ ] **Update Schedule / Server Configuration:**
  - Expose select entity for `updateSchedule` (`6h`, `12h`, `24h`) and custom update server URIs.
- [ ] **Offline / Local Firmware Upload Tool:**
  - CLI script and service to flash local `.bin` files via `POST /update/prepare` and `POST /update/firmware`.

---

### Phase 5: Autonomous On-Device Automations
> **Goal:** Configure fail-safe direct bindings that execute on the chip without network dependency.

- [ ] **On-Device Automation Engine (`/services/eltako/automations`):**
  - Expose capabilities to create direct hardware bindings on the ESR64 chip:
    - Bind wired input or EnOcean sensor directly to relay output.
    - Set internal logic profiles: `buttonImpulseSwitch` (toggle), staircase timer (Treppenlichtzeitschalter), or window-contact cut-off.
  - **Fail-safe Guarantee:** Even if Home Assistant, the Wi-Fi router, or local network are offline, the physical switch and EnOcean contacts continue to trigger the relay in hardware with zero latency.

---

### Phase 6: Expanded Device Family Support
> **Goal:** Broaden integration beyond ESR64PF-IPM to all Series 62-IP and Series 64-IPM models.

- [ ] **Universal Dimmers (`light` platform):**
  - **Models:** `EUD64NPN-IPM`, `EUD62NPN-IP`, `EUD62NPN-IPM`.
  - Brightness control, dimming curves, minimum/maximum brightness levels, memory function.
- [ ] **Roller Shutter & Blind Actuators (`cover` platform):**
  - **Models:** `ESB64NP-IPM`, `ESB62NP-IP`.
  - Position control (0–100%), slat tilt angle, calibration runtime measurements.
- [ ] **Standard Relays:**
  - **Models:** `ESR64NP-IPM`, `ESR62NP-IP`.

---

## Suggested Priority Order

```
[Phase 1: Identify & Settings] ──► [Phase 4: Update Entity & Auto-Update]
             │                                     │
             ▼                                     ▼
[Phase 2: EnOcean Pairing Wizard] ──► [Phase 3: Matter Bridge Controls]
             │
             ▼
[Phase 5: On-Device Automations]  ──► [Phase 6: Dimmers & Covers]
```
