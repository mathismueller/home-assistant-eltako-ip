/* Eltako Automation Studio — vanilla JS, zero runtime deps.
 * Talks only to the thin Studio API (server.py), which mirrors the future
 * HA WebSocket command payloads. Run `tsc --allowJs --checkJs` for types
 * without adding a build step; full TS migration = rename to .ts later.
 */

const LOGIC_LABELS = {
  buttonImpulseSwitch: "Impulse Switch",
  buttonSwitch: "Switch",
  buttonNormallyOpened: "Momentary NO",
  buttonNormallyClosed: "Momentary NC",
  target: "Target",
};

const state = { rules: [], devices: [], enocean: [], editing: null };

const $ = (id) => document.getElementById(id);
const listEl = $("list"), editor = $("editor");

async function api(path, opts) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts?.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function deviceName(guid) {
  const d = state.devices.find((x) => x.deviceGuid === guid);
  if (d) return d.displayName || guid.slice(0, 8);
  const eo = state.enocean.find((x) => x.deviceGuid === guid);
  if (eo) return `EnOcean ${String(eo.eurId || "")}`;
  return guid.slice(0, 8);
}

function inputKind(rule) {
  const c = rule.configuration.inputCharacteristicIdentifier;
  if (c === "contact") return "FTK window";
  if (c.startsWith("button")) return "EnOcean rocker";
  return "Wired input";
}

function addonPills(rule) {
  const pills = [];
  for (const a of rule.configuration.addOns || []) {
    if (a.type === "offTimer") pills.push(`Off-Timer: ${Math.round(a.time / 1000)}s`);
    else if (a.type === "longPressOffTimer") pills.push(`Long-press: ${Math.round(a.time / 1000)}s`);
    else if (a.type === "prewarning") pills.push("Prewarning flicker");
    else if (a.type === "targetValue") pills.push(`Target ${a.data}`);
    else pills.push(a.type);
  }
  return pills;
}

async function refresh() {
  const [status, rules, devices, enocean] = await Promise.all([
    api("/api/status").catch(() => ({ mode: "mock", rule_count: 0 })),
    api("/api/automations"),
    api("/api/devices").catch(() => []),
    api("/api/enocean_devices").catch(() => []),
  ]);
  state.rules = rules;
  state.devices = Array.isArray(devices) ? devices : devices.devices || [];
  state.enocean = enocean;
  const modeEl = $("mode");
  modeEl.textContent = status.mode || "mock";
  modeEl.classList.toggle("live", status.mode === "live");
  $("count").textContent = `${rules.length} rule${rules.length === 1 ? "" : "s"}`;
  render();
}

function render() {
  listEl.innerHTML = "";
  if (!state.rules.length) {
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `<div class="meta">No on-device rules. Create one, or apply the staircase preset.</div>`;
    listEl.appendChild(div);
    return;
  }
  for (const rule of state.rules) {
    const cfg = rule.configuration;
    const card = document.createElement("div");
    card.className = "card";
    const health = rule.operatingStatus && rule.operatingStatus !== "success"
      ? `<span class="pill warn">${rule.operatingStatus}</span>` : "";
    card.innerHTML = `
      <div class="flow">
        <span class="pill">${inputKind(rule)} · ${deviceName(cfg.inputDeviceGuid)}</span>
        <span class="arrow">──►</span>
        <span class="pill logic">${LOGIC_LABELS[cfg.logic] || cfg.logic}</span>
        ${addonPills(rule).map((p) => `<span class="pill">${p}</span>`).join("")}
        <span class="arrow">──►</span>
        <span class="pill">${deviceName(cfg.outputDeviceGuid)} · ${cfg.outputCharacteristicIdentifier}</span>
        ${health}
      </div>
      <div class="row">
        <span class="meta">${cfg.automationGuid} · in:${cfg.inputCharacteristicIdentifier} → out:${cfg.outputCharacteristicIdentifier}</span>
        <span class="spacer"></span>
        <label class="check"><input type="checkbox" ${rule.enabled ? "checked" : ""} data-act="toggle" /> active</label>
        <button data-act="edit">Edit</button>
        <button data-act="del" class="danger">Delete</button>
      </div>`;
    card.querySelector('[data-act="toggle"]').addEventListener("change", async (e) => {
      await api(`/api/automations/${cfg.automationGuid}`, {
        method: "PUT",
        body: JSON.stringify({ ...rule, enabled: e.target.checked }),
      });
      await refresh();
    });
    card.querySelector('[data-act="edit"]').addEventListener("click", () => openEditor(rule));
    card.querySelector('[data-act="del"]').addEventListener("click", async () => {
      if (!confirm("Delete this on-device rule?")) return;
      await api(`/api/automations/${cfg.automationGuid}`, { method: "DELETE" });
      await refresh();
    });
    listEl.appendChild(card);
  }
}

function fillDeviceSelects() {
  const inputs = [...state.devices, ...state.enocean.map((e) => ({
    deviceGuid: e.deviceGuid, displayName: `EnOcean ${e.eurId || e.deviceGuid.slice(0, 8)}`,
  }))];
  const outputs = state.devices.filter((d) =>
    (d.functions || []).some((f) => f.identifier === "relay") || /ESR/i.test(d.displayName || ""));
  const fI = $("fInput"), fO = $("fOutput");
  fI.innerHTML = inputs.map((d) => `<option value="${d.deviceGuid}">${d.displayName}</option>`).join("");
  const outList = outputs.length ? outputs : state.devices;
  fO.innerHTML = outList.map((d) => `<option value="${d.deviceGuid}">${d.displayName}</option>`).join("");
}

function ruleToForm(rule) {
  const cfg = rule.configuration;
  const get = (t) => (cfg.addOns || []).find((a) => a.type === t);
  $("fInput").value = cfg.inputDeviceGuid;
  $("fInputChar").value = cfg.inputCharacteristicIdentifier;
  $("fOutput").value = cfg.outputDeviceGuid;
  $("fLogic").value = cfg.logic;
  $("fOff").value = get("offTimer") ? Math.round(get("offTimer").time / 1000) : 0;
  $("fLong").value = get("longPressOffTimer") ? Math.round(get("longPressOffTimer").time / 1000) : 0;
  $("fPre").checked = !!get("prewarning");
  $("fTarget").value = get("targetValue")?.data ?? 100;
  $("fActive").checked = !!rule.enabled;
}

function formToPayload() {
  const off = Math.max(0, Number($("fOff").value || 0));
  const long = Math.max(0, Number($("fLong").value || 0));
  const addOns = [];
  if (off > 0 && $("fLogic").value !== "buttonSwitch") addOns.push({ type: "offTimer", time: off * 1000, data: null });
  if (long > 0) addOns.push({ type: "longPressOffTimer", time: long * 1000, data: null });
  if ($("fPre").checked && off > 0) addOns.push({ type: "prewarning", time: null, data: null });
  if ($("fLogic").value === "target") addOns.push({ type: "targetValue", time: null, data: Number($("fTarget").value || 100) });
  const base = state.editing?.configuration || {};
  return {
    enabled: $("fActive").checked,
    description: state.editing?.description || "studio",
    configuration: {
      automationGuid: base.automationGuid || "",
      logic: $("fLogic").value,
      inputDeviceGuid: $("fInput").value,
      inputCharacteristicIdentifier: $("fInputChar").value,
      outputDeviceGuid: $("fOutput").value,
      outputCharacteristicIdentifier: "relay",
      addOns,
      logicConfiguration: {},
    },
    operatingStatus: "success",
    errors: [],
  };
}

function openEditor(rule) {
  state.editing = rule || null;
  fillDeviceSelects();
  $("editorTitle").textContent = rule ? "Edit rule" : "New rule";
  $("fErr").textContent = "";
  if (rule) ruleToForm(rule);
  editor.showModal();
}

$("new").addEventListener("click", () => openEditor(null));

$("save").addEventListener("click", async (e) => {
  e.preventDefault();
  try {
    const payload = formToPayload();
    if (state.editing) {
      await api(`/api/automations/${state.editing.configuration.automationGuid}`, {
        method: "PUT", body: JSON.stringify(payload),
      });
    } else {
      await api("/api/automations", { method: "POST", body: JSON.stringify(payload) });
    }
    editor.close();
    await refresh();
  } catch (err) {
    $("fErr").textContent = String(err.message || err);
  }
});

$("reset").addEventListener("click", async () => {
  if (!confirm("Reset all on-device automations to factory defaults?")) return;
  await api("/api/automations", { method: "DELETE" });
  await refresh();
});

$("preset").addEventListener("click", async () => {
  // Staircase timer with prewarning: wired input -> first relay output.
  const input = state.devices.find((d) => /wired input/i.test(d.displayName || ""))
    || state.devices[1] || state.devices[0];
  const output = state.devices.find((d) => /ESR/i.test(d.displayName || ""))
    || state.devices[0];
  if (!input || !output) { alert("No devices available"); return; }
  await api("/api/automations", {
    method: "POST",
    body: JSON.stringify({
      enabled: true,
      description: "staircase+prewarning",
      configuration: {
        automationGuid: "",
        logic: "buttonImpulseSwitch",
        inputDeviceGuid: input.deviceGuid,
        inputCharacteristicIdentifier: "input",
        outputDeviceGuid: output.deviceGuid,
        outputCharacteristicIdentifier: "relay",
        addOns: [
          { type: "offTimer", time: 10000, data: null },
          { type: "prewarning", time: null, data: null },
        ],
        logicConfiguration: {},
      },
      operatingStatus: "success",
      errors: [],
    }),
  });
  await refresh();
});

refresh().catch((err) => {
  listEl.innerHTML = `<div class="card"><div class="err">Failed to reach studio API: ${err.message}. Is <code>python3 studio/server.py</code> running?</div></div>`;
});
