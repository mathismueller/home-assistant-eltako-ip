/* Eltako Automation Studio — vanilla JS, zero runtime deps.
 * Talks only to the thin Studio API (server.py), which mirrors the future
 * HA WebSocket command payloads. Run `tsc --allowJs --checkJs` for types
 * without adding a build step; full TS migration = rename to .ts later.
 */

const STRINGS = {
  en: {
    preset: "Template: Staircase + prewarning",
    presetTitle: "Short press turns the relay on, auto-off after the timer. Prewarning flickers the light 3× at increasingly shorter intervals from 30s before switch-off.",
    new: "New rule",
    reset: "Reset",
    cancel: "Cancel",
    save: "Save",
    edit: "Edit",
    delete: "Delete",
    active: "active",
    empty: "No on-device rules. Create one from a template.",
    infoTitle: "What do these settings mean?",
    infoStaircase: "Staircase + prewarning (Treppenlicht): a short press switches the relay on and it turns off automatically after the off-timer. With prewarning the relay flickers 3× starting 30s before expiry so you can press again. Runs entirely on-device — works even if Wi-Fi / Home Assistant is down.",
    infoTarget: "Target logic: moves the output to a fixed targetValue (0–100) instead of toggling. Without a target the device toggles between min/max. Use it for scenes, e.g. always switch on to 100%.",
    footer: "Standalone dev harness. Same JSON contract as the future HA WebSocket API.",
    pickerTitle: "Choose a template",
    pickerTarget: "Target device",
    pickerTemplate: "Template",
    fInput: "Input device",
    fInputChar: "Input characteristic",
    fOutput: "Output actuator",
    fOutputChar: "Output characteristic",
    fLogic: "Logic",
    fOff: "Off-timer (s, 0 = off)",
    fLong: "Long-press off-timer (s, 0 = off)",
    fPre: "Prewarning flicker (30s before off)",
    fTarget: "Target value (for target logic)",
    fActive: "Rule active",
    hintLogic: "Impulse = pushbutton (Taster), Switch = rocker (Kippschalter), NO/NC = momentary contact, Target = fixed value.",
    hintOff: "Auto-off delay after a short press. 0 disables it.",
    hintLong: "Separate auto-off timer armed by a long press.",
    hintPre: "Flickers the relay 3× before the off-timer expires. Needs an off-timer > 30s to be useful.",
    hintTarget: "Relay: 0 = off, 1 = on. Blind/shutter: position 0–100.",
    inWired: "input (wired dry contact)",
    inContact: "contact (FTK window)",
    inA0: "buttonA0 (EnOcean rocker)",
    inA1: "buttonA1 (EnOcean rocker)",
    logicImpulse: "Impulse switch (Taster)",
    logicSwitch: "Switch (Kippschalter)",
    logicNO: "Momentary NO",
    logicNC: "Momentary NC",
    logicTarget: "Target value",
    titleNew: "New rule",
    titleEdit: "Edit rule",
    fixBeforeSave: "Please fix before saving:",
    liveState: "Live device state",
    rulesTitle: "On-device rules",
    fDesc: "Name",
    hintDesc: "Stored on the device and shown in rule lists.",
    descPlaceholder: "e.g. Staircase hallway",
    settingDefault: "Product default; live value not reported.",
    hintInputChar: "Only characteristics this input actually reports.",
    eudNote: "Dimmer rules are read-only in this studio version — saving would wipe the dimmer ramp configuration.",
    confirmDelete: "Delete this on-device rule?",
    confirmReset: "Reset all on-device automations to factory defaults?",
    noDevices: "No devices available",
    logicImpulseShort: "Impulse Switch",
    logicSwitchShort: "Switch",
    logicNOShort: "Momentary NO",
    logicNCShort: "Momentary NC",
    logicTargetShort: "Target",
    kindWired: "Wired input",
    kindWindow: "FTK window",
    kindRocker: "EnOcean rocker",
    kindSensor: "Sensor",
    pillOff: (s) => `Off-Timer: ${s}s`,
    pillLong: (s) => `Long-press: ${s}s`,
    pillPre: "Prewarning flicker",
    pillTarget: (v) => `Target ${v}`,
    count: (n) => `${n} rule${n === 1 ? "" : "s"}`,
    tmpl: "Template",
    tipInput: "Which physical input triggers the rule: wired dry contact, FTK window contact, or EnOcean rocker half.",
    tipOutput: "Which actuator output this rule drives (ESR relay channel).",
    tipLogic: "Impulse = action on button press. Switch = action on press AND release. NO = output normally open: press closes, release reopens. NC = the reverse. Target = fixed value; without one it toggles min/max.",
    tipOff: "A short press turns the device off after the given time. 0 disables it. Not supported with Switch logic.",
    tipLong: "A long press turns the device off after the given time.",
    tipPre: "Relay flickers 3× at increasingly shorter intervals from 30s before switch-off. Combine with offTimer or longPressOffTimer.",
    tipTarget: "Only used with Target logic: the output moves to this value (0–100). If omitted, each impulse toggles between min and max.",
  },
  de: {
    preset: "Vorlage: Treppenlicht + Vorwarnung",
    presetTitle: "Kurzer Druck schaltet ein, automatisches Ausschalten nach Zeit. Vorwarnung: 3× Flackern in immer kürzeren Abständen ab 30s vorher.",
    new: "Neue Regel",
    reset: "Zurücksetzen",
    cancel: "Abbrechen",
    save: "Speichern",
    edit: "Bearbeiten",
    delete: "Löschen",
    active: "aktiv",
    empty: "Keine Geräteregeln. Lege eine aus einer Vorlage an.",
    infoTitle: "Was bedeuten diese Einstellungen?",
    infoStaircase: "Treppenlicht + Vorwarnung: Kurzer Druck schaltet das Relais ein, nach der Ausschaltverzögerung geht es automatisch aus. Mit Vorwarnung flackert das Relais 30s vor Ablauf 3×, damit man erneut drücken kann. Läuft komplett im Gerät – auch ohne WLAN / Home Assistant.",
    infoTarget: "Target-Logik: fährt den Ausgang auf einen festen Zielwert (targetValue 0–100) statt umzuschalten. Ohne Zielwert schaltet das Gerät zwischen Min/Max um. Z. B. für Szenen: immer auf 100% einschalten.",
    footer: "Eigenständige Dev-Oberfläche. Gleiches JSON-Format wie die spätere HA-WebSocket-API.",
    pickerTitle: "Vorlage wählen",
    pickerTarget: "Zielgerät",
    pickerTemplate: "Vorlage",
    fInput: "Eingang (Taster/Kontakt)",
    fInputChar: "Eingangsmerkmal",
    fOutput: "Aktor (Ausgang)",
    fOutputChar: "Ausgangsmerkmal",
    fLogic: "Logik",
    fOff: "Ausschaltverzögerung (s, 0 = aus)",
    fLong: "Ausschaltverzögerung bei Langdruck (s, 0 = aus)",
    fPre: "Vorwarn-Flackern (30s vor Aus)",
    fTarget: "Zielwert (für Target-Logik)",
    fActive: "Regel aktiv",
    hintLogic: "Impuls = Taster, Schalter = Kippschalter, NO/NC = Tastkontakt, Target = Festwert.",
    hintOff: "Automatische Abschaltung nach Kurzdruck. 0 = deaktiviert.",
    hintLong: "Eigener Timer, der per Langdruck gestartet wird.",
    hintPre: "Lässt das Relais vor Ablauf 3× flackern. Sinnvoll erst ab Timer > 30s.",
    hintTarget: "Relais: 0 = aus, 1 = ein. Beschattung: Position 0–100.",
    inWired: "input (verdrahteter Kontakt)",
    inContact: "contact (FTK-Fenster)",
    inA0: "buttonA0 (EnOcean-Wippe)",
    inA1: "buttonA1 (EnOcean-Wippe)",
    logicImpulse: "Impulsschalter (Taster)",
    logicSwitch: "Schalter (Kippschalter)",
    logicNO: "Schließer (NO)",
    logicNC: "Öffner (NC)",
    logicTarget: "Zielwert",
    titleNew: "Neue Regel",
    titleEdit: "Regel bearbeiten",
    liveState: "Live-Zustand der Geräte",
    rulesTitle: "Geräteregeln",
    fixBeforeSave: "Bitte vor dem Speichern beheben:",
    fDesc: "Name",
    hintDesc: "Wird im Gerät gespeichert und in Regellisten angezeigt.",
    descPlaceholder: "z. B. Treppenlicht Flur",
    settingDefault: "Produkt-Standard; Live-Wert wird nicht gemeldet.",
    hintInputChar: "Nur Merkmale, die dieser Eingang tatsächlich meldet.",
    eudNote: "Dimmregeln sind in dieser Version schreibgeschützt – Speichern würde die Rampen-Konfiguration löschen.",
    confirmDelete: "Diese Geräteregel löschen?",
    confirmReset: "Alle Geräteregeln auf Werkseinstellung zurücksetzen?",
    noDevices: "Keine Geräte verfügbar",
    logicImpulseShort: "Impuls",
    logicSwitchShort: "Schalter",
    logicNOShort: "Schließer",
    logicNCShort: "Öffner",
    logicTargetShort: "Zielwert",
    kindWired: "Drahteingang",
    kindWindow: "FTK-Fenster",
    kindRocker: "EnOcean-Wippe",
    kindSensor: "Sensor",
    pillOff: (s) => `Timer: ${s}s`,
    pillLong: (s) => `Langdruck: ${s}s`,
    pillPre: "Vorwarnung",
    pillTarget: (v) => `Ziel ${v}`,
    count: (n) => `${n} Regel${n === 1 ? "" : "n"}`,
    tmpl: "Vorlage",
    tipInput: "Welcher physische Eingang die Regel auslöst: Drahtkontakt, FTK-Fensterkontakt oder EnOcean-Wippenhälfte.",
    tipOutput: "Welcher Aktor-Ausgang angesteuert wird (ESR-Relaiskanal).",
    tipLogic: "Impuls = Aktion bei Tastendruck. Schalter = Aktion bei Druck UND Loslassen. NO = Ausgang normalerweise offen: Druck schließt, Loslassen öffnet. NC = umgekehrt. Target = Festwert, ohne Wert Wechsel Min/Max.",
    tipOff: "Kurzdruck schaltet nach der Zeit automatisch aus. 0 = deaktiviert. Nicht mit Schalter-Logik kombinierbar.",
    tipLong: "Langdruck schaltet nach der Zeit automatisch aus.",
    tipPre: "Relais flackert ab 30s vor dem Ausschalten 3× in immer kürzeren Abständen. Mit offTimer oder longPressOffTimer kombinieren.",
    tipTarget: "Nur für Target-Logik: Der Ausgang fährt auf diesen Wert (0–100). Ohne Wert wechselt jeder Druck zwischen Min und Max.",
  },
};

const LOGIC_LABEL_I18N = {
  buttonImpulseSwitch: { en: "Impulse switch (Taster)", de: "Impulsschalter (Taster)" },
  buttonSwitch: { en: "Switch (Kippschalter)", de: "Schalter (Kippschalter)" },
  buttonNormallyOpened: { en: "Momentary NO", de: "Schließer (NO)" },
  buttonNormallyClosed: { en: "Momentary NC", de: "Öffner (NC)" },
  target: { en: "Target value", de: "Zielwert" },
  buttonTargetValue: { en: "Target value", de: "Zielwert" },
  universalButtonDimmer: { en: "Universal dimmer", de: "Universal-Dimmer" },
  directionalUpButtonDimmer: { en: "Up / dim up", de: "Hoch / hochdimmen" },
  directionalDownButtonDimmer: { en: "Down / dim down", de: "Runter / runterdimmen" },
  centralUpButtonDimmer: { en: "Central on", de: "Zentral ein" },
  centralDownButtonDimmer: { en: "Central off", de: "Zentral aus" },
  sceneButtonDimmer: { en: "Scene dimmer", de: "Szenen-Dimmer" },
};

const logicLabel = (value) => LOGIC_LABEL_I18N[value]?.[lang] || value;

// Manufacturer alias -> spec-canonical logic name (same behavior).
const LOGIC_ALIASES = { buttonTargetValue: "target" };
const canonicalLogic = (value) => LOGIC_ALIASES[value] || value;

const CONDITION_TEXT = {
  tilt: { en: "Applies only when tilt is enabled (enableTilt).", de: "Wirkt nur bei aktivierter Neigung (enableTilt)." },
  runtime: { en: "Applies only when runtime mode is manual.", de: "Wirkt nur im manuellen Laufzeitmodus." },
};

const state = { rules: [], devices: [], enocean: [], caps: null, devSettings: {}, editing: null };
let lang = localStorage.getItem("studio-lang") || "en";
if (!STRINGS[lang]) lang = "en";

const t = (key) => STRINGS[lang][key] ?? STRINGS.en[key] ?? key;

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

/* --- Capability-driven editor -------------------------------------------
 * Dropdowns and addon rows are built from GET /api/capabilities so only
 * identifiers, logics and addOns the paired hardware actually supports
 * are offered. Unknown classes render read-only. */

const caps = () => state.caps || { triggers: [], targets: [], logicsByClass: {}, addonsByClass: {} };

function triggerDevices() {
  const seen = new Map();
  for (const trg of caps().triggers) {
    if (!seen.has(trg.deviceGuid)) seen.set(trg.deviceGuid, trg.displayName);
  }
  return [...seen.entries()].map(([deviceGuid, displayName]) => ({ deviceGuid, displayName }));
}

function inputChars(guid) {
  return caps().triggers.filter((trg) => trg.deviceGuid === guid).map((trg) => trg.identifier);
}

function targetDevices() {
  const seen = new Map();
  for (const tgt of caps().targets) {
    if (!seen.has(tgt.deviceGuid)) seen.set(tgt.deviceGuid, tgt.displayName);
  }
  return [...seen.entries()].map(([deviceGuid, displayName]) => ({ deviceGuid, displayName }));
}

function outputChars(guid) {
  return caps().targets.filter((tgt) => tgt.deviceGuid === guid);
}

function targetClass(guid, ident) {
  return caps().targets.find((tgt) => tgt.deviceGuid === guid && tgt.identifier === ident)?.deviceClass || "unknown";
}

function selectedTargetClass() {
  return targetClass($("fOutput").value, $("fOutputChar").value);
}

function setSelect(sel, value) {
  const opts = [...sel.options].map((o) => o.value);
  sel.value = opts.includes(value) ? value : (opts[0] || "");
}

function syncInputChars(keep) {
  const sel = $("fInputChar");
  const cur = keep || sel.value;
  sel.innerHTML = inputChars($("fInput").value).map((c) => `<option value="${c}">${c}</option>`).join("");
  setSelect(sel, cur);
}

function syncOutput(keepChar, keepLogic) {
  const co = $("fOutputChar");
  const curChar = keepChar || co.value;
  co.innerHTML = outputChars($("fOutput").value).map((tgt) => `<option value="${tgt.identifier}">${tgt.identifier} (${tgt.deviceClass})</option>`).join("");
  setSelect(co, curChar);
  syncLogics(keepLogic);
}

function syncLogics(keep) {
  const sel = $("fLogic");
  const cur = canonicalLogic(keep || sel.value);
  const seen = new Set();
  const logics = (caps().logicsByClass[selectedTargetClass()] || []).map(canonicalLogic).filter((l) => !seen.has(l) && seen.add(l));
  sel.innerHTML = logics.map((l) => `<option value="${l}">${logicLabel(l)}</option>`).join("");
  if (!logics.length) sel.innerHTML = `<option value="${cur}">${logicLabel(cur)}</option>`;
  setSelect(sel, cur);
  updateAddonVisibility();
}

function updateAddonVisibility() {
  const addons = new Set(caps().addonsByClass[selectedTargetClass()] || []);
  $("rOff").hidden = !addons.has("offTimer");
  $("rLong").hidden = !addons.has("longPressOffTimer");
  $("rPre").hidden = !addons.has("prewarning");
  $("rTarget").hidden = !addons.has("targetValue");
  const eud = selectedTargetClass() === "EUD";
  $("eudNote").hidden = !eud;
  if (eud) $("eudNote").textContent = t("eudNote");
}

function deviceName(guid) {
  const d = state.devices.find((x) => x.deviceGuid === guid);
  if (d) return d.displayName || guid.slice(0, 8);
  const eo = state.enocean.find((x) => x.deviceGuid === guid);
  if (eo) return `EnOcean ${String(eo.eurId || "")}`;
  return guid.slice(0, 8);
}

function inputKind(rule) {
  const c = rule.configuration.inputCharacteristicIdentifier || "";
  if (c === "contact" || c === "windowDoorContact") return t("kindWindow");
  if (c.startsWith("button")) return t("kindRocker");
  if (c.startsWith("input")) return t("kindWired");
  if (/motion|smoke|water|rain|temperature|humidity|illumination|co2|tvoc/.test(c)) return t("kindSensor");
  return c;
}

function addonPills(rule) {
  const pills = [];
  for (const a of rule.configuration.addOns || []) {
    if (a.type === "offTimer") pills.push({ text: t("pillOff")(Math.round(a.time / 1000)), title: t("tipOff") });
    else if (a.type === "longPressOffTimer") pills.push({ text: t("pillLong")(Math.round(a.time / 1000)), title: t("tipLong") });
    else if (a.type === "prewarning") pills.push({ text: t("pillPre"), title: t("tipPre") });
    else if (a.type === "targetValue") pills.push({ text: t("pillTarget")(a.data), title: t("tipTarget") });
    else pills.push({ text: a.type, title: "" });
  }
  return pills;
}

function errorText(rule) {
  return (rule.errors || []).map((e) => [e.code, e.title || e.description].filter(Boolean).join(" ")).join("; ");
}

function renderDevices() {
  const box = $("devstates");
  box.innerHTML = "";
  for (const dev of state.devices) {
    const card = document.createElement("div");
    card.className = "card";
    const name = document.createElement("div");
    name.style.fontWeight = "600";
    name.textContent = dev.displayName || dev.deviceGuid.slice(0, 8);
    const flow = document.createElement("div");
    flow.className = "flow";
    const chars = [...(dev.functions || []), ...(dev.infos || [])];
    if (!chars.length) {
      const none = document.createElement("span");
      none.className = "meta";
      none.textContent = "—";
      flow.appendChild(none);
    }
    for (const ch of chars) {
      const pill = document.createElement("span");
      pill.className = "pill";
      pill.textContent = `${ch.identifier}: ${ch.value}`;
      flow.appendChild(pill);
    }
    const eo = state.enocean.find((x) => x.deviceGuid === dev.deviceGuid);
    if (eo && eo.signalStrength !== undefined && eo.signalStrength !== null) {
      const rssi = document.createElement("span");
      rssi.className = "pill";
      rssi.textContent = `RSSI ${eo.signalStrength} dBm`;
      rssi.title = eo.lastSeen ? `last seen ${eo.lastSeen}` : "";
      flow.appendChild(rssi);
    }
    for (const st of state.devSettings[dev.deviceGuid] || []) {
      const pill = document.createElement("span");
      pill.className = "pill dim" + (st.applies ? "" : " off");
      const shown = st.value ?? st.default;
      pill.textContent = `${st.identifier}: ${shown}${st.unit ? " " + st.unit : ""}`;
      const tips = [];
      if (!st.live) tips.push(t("settingDefault"));
      if (!st.applies && st.reason) tips.push((CONDITION_TEXT[st.reason] || {})[lang] || st.reason);
      if (tips.length) pill.title = tips.join(" ");
      flow.appendChild(pill);
    }
    card.append(name, flow);
    box.appendChild(card);
  }
}

function isTemplateRule(rule) {
  const desc = rule.description || "";
  if (typeof TEMPLATES !== "undefined" && TEMPLATES.some((tmpl) =>
    (tmpl.description && desc === tmpl.description)
    || (tmpl.suggest && (desc === tmpl.suggest.en || desc === tmpl.suggest.de))
  )) return true;
  return /staircase|treppen|prewarning|vorwarnung/i.test(desc);
}

function applyI18n() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const v = t(el.dataset.i18n);
    if (typeof v === "string") el.textContent = v;
  });
  $("fInput").title = t("tipInput");
  $("fInputChar").title = t("tipInput");
  $("fOutput").title = t("tipOutput");
  $("fLogic").title = t("tipLogic");
  $("fOff").title = t("tipOff");
  $("fLong").title = t("tipLong");
  $("fPre").title = t("tipPre");
  $("fTarget").title = t("tipTarget");
  $("lang").value = lang;
  localStorage.setItem("studio-lang", lang);
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
  try {
    state.caps = await api("/api/capabilities");
  } catch { state.caps = null; }
  try {
    const ds = await api("/api/device_settings");
    state.devSettings = Object.fromEntries(
      (ds.devices || []).map((d) => [d.deviceGuid, d.settings || []])
    );
  } catch { state.devSettings = {}; }
  const modeEl = $("mode");
  modeEl.textContent = status.mode || "mock";
  modeEl.classList.toggle("live", status.mode === "live");
  $("count").textContent = t("count")(rules.length);
  render();
}

function render() {
  renderDevices();
  listEl.innerHTML = "";
  if (!state.rules.length) {
    const div = document.createElement("div");
    div.className = "card";
    const inner = document.createElement("div");
    inner.className = "meta";
    inner.textContent = t("empty");
    div.appendChild(inner);
    listEl.appendChild(div);
    return;
  }
  for (const rule of state.rules) {
    const cfg = rule.configuration;
    const card = document.createElement("div");
    card.className = "card";
    const health = rule.operatingStatus && rule.operatingStatus !== "success"
      ? `<span class="pill warn" title="${escXml(errorText(rule))}">${rule.operatingStatus}</span>` : "";
    const flow = document.createElement("div");
    flow.className = "flow";
    const title = document.createElement("div");
    title.style.fontWeight = "600";
    title.textContent = rule.description || cfg.automationGuid;
    title.title = cfg.automationGuid;
    const tmplPill = isTemplateRule(rule)
      ? `<span class="pill logic" title="${t("presetTitle")}">${t("tmpl")}</span>` : "";
    const pillsHtml = addonPills(rule).map((p) => `<span class="pill" title="${p.title}">${p.text}</span>`).join("");
    flow.innerHTML = `
      ${tmplPill}
      <span class="pill" title="${t("tipInput")}">${inputKind(rule)} · ${deviceName(cfg.inputDeviceGuid)}</span>
      <span class="arrow">──►</span>
      <span class="pill logic" title="${t("tipLogic")}">${logicLabel(cfg.logic)}</span>
      ${pillsHtml}
      <span class="arrow">──►</span>
      <span class="pill" title="${t("tipOutput")}">${deviceName(cfg.outputDeviceGuid)} · ${cfg.outputCharacteristicIdentifier}</span>
      ${health}`;
    const row = document.createElement("div");
    row.className = "row";
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = `${cfg.automationGuid} · in:${cfg.inputCharacteristicIdentifier} → out:${cfg.outputCharacteristicIdentifier}`;
    const spacer = document.createElement("span");
    spacer.className = "spacer";
    const checkLabel = document.createElement("label");
    checkLabel.className = "check";
    const toggle = document.createElement("input");
    toggle.type = "checkbox";
    toggle.checked = !!rule.enabled;
    toggle.addEventListener("change", async (e) => {
      await api(`/api/automations/${cfg.automationGuid}`, {
        method: "PUT",
        body: JSON.stringify({ ...rule, enabled: e.target.checked }),
      });
      await refresh();
    });
    checkLabel.append(toggle, document.createTextNode(" " + t("active")));
    const editBtn = document.createElement("button");
    editBtn.textContent = t("edit");
    editBtn.addEventListener("click", () => openEditor(rule));
    const delBtn = document.createElement("button");
    delBtn.textContent = t("delete");
    delBtn.className = "danger";
    delBtn.addEventListener("click", async () => {
      if (!confirm(t("confirmDelete"))) return;
      await api(`/api/automations/${cfg.automationGuid}`, { method: "DELETE" });
      await refresh();
    });
    row.append(meta, spacer, checkLabel, editBtn, delBtn);
    card.append(title, flow, row);
    listEl.appendChild(card);
  }
}

function fillDeviceSelects() {
  const fI = $("fInput"), fO = $("fOutput");
  fI.innerHTML = triggerDevices().map((d) => `<option value="${d.deviceGuid}">${d.displayName}</option>`).join("");
  fO.innerHTML = targetDevices().map((d) => `<option value="${d.deviceGuid}">${d.displayName}</option>`).join("");
  syncInputChars();
  syncOutput();
}

function ruleToForm(rule) {
  const cfg = rule.configuration;
  const get = (t2) => (cfg.addOns || []).find((a) => a.type === t2);
  $("fDesc").value = rule.description || "";
  setSelect($("fInput"), cfg.inputDeviceGuid);
  syncInputChars(cfg.inputCharacteristicIdentifier);
  setSelect($("fOutput"), cfg.outputDeviceGuid);
  syncOutput(cfg.outputCharacteristicIdentifier, cfg.logic);
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
  const descField = $("fDesc").value.trim();
  const description = descField || state.editing?.description || "studio";
  return {
    enabled: $("fActive").checked,
    description,
    configuration: {
      automationGuid: base.automationGuid || "",
      logic: $("fLogic").value,
      inputDeviceGuid: $("fInput").value,
      inputCharacteristicIdentifier: $("fInputChar").value,
      outputDeviceGuid: $("fOutput").value,
      outputCharacteristicIdentifier: $("fOutputChar").value || "relay",
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
  $("editorTitle").textContent = rule ? t("titleEdit") : t("titleNew");
  $("fErr").textContent = "";
  $("fDesc").placeholder = t("descPlaceholder");
  if (rule) ruleToForm(rule);
  else $("fDesc").value = "";
  editor.showModal();
}

function prefillForm(v) {
  $("fDesc").value = v.suggest?.[lang] || v.suggest?.en || "";
  if (v.inputGuid) setSelect($("fInput"), v.inputGuid);
  syncInputChars(v.inputChar);
  if (v.outputGuid) setSelect($("fOutput"), v.outputGuid);
  syncOutput(v.outputChar, v.logic);
  if (v.inputChar) setSelect($("fInputChar"), v.inputChar);
  if (v.logic) setSelect($("fLogic"), v.logic);
  updateAddonVisibility();
  if (v.off !== undefined) $("fOff").value = v.off;
  if (v.long !== undefined) $("fLong").value = v.long;
  if (v.pre !== undefined) $("fPre").checked = v.pre;
  if (v.target !== undefined) $("fTarget").value = v.target;
  $("fActive").checked = v.active !== false;
}

/* Trigger resolution from capabilities (falls back to paired devices). */
function capTrigger(pred) {
  return (state.caps?.triggers || []).find(pred) || null;
}

function wiredTrigger() {
  return capTrigger((x) => /wired/i.test(x.displayName))
    || capTrigger((x) => x.identifier === "input")
    || capTrigger(() => true);
}

function relayTarget() {
  const tgts = state.caps?.targets || [];
  return tgts.find((x) => /ESR/i.test(x.displayName)) || tgts[0] || null;
}

function contactTrigger() {
  return capTrigger((x) => x.identifier === "contact")
    || capTrigger((x) => /contact/i.test(x.identifier));
}

function buttonTrigger() {
  return capTrigger((x) => /^button/i.test(x.identifier)) || wiredTrigger();
}

/* One-click templates. Each prefills the editor (nothing is saved until
 * the user confirms with Save), except blank which opens defaults. */
const TEMPLATES = [
  {
    id: "blank",
    en: { name: "Blank rule", desc: "Start from scratch with default values." },
    de: { name: "Leere Regel", desc: "Mit Standardwerten neu beginnen." },
    values: () => ({}),
  },
  {
    id: "staircase",
    en: { name: "Template: Staircase + prewarning", desc: "Treppenlicht: on with short press, auto-off after 10s, 3× flicker warning." },
    de: { name: "Vorlage: Treppenlicht + Vorwarnung", desc: "Bei Kurzdruck ein, nach 10s automatisch aus, 3× Flackern als Warnung." },
    description: "staircase+prewarning",
    classes: ["ESR"],
    suggest: { en: "Staircase + prewarning", de: "Treppenlicht + Vorwarnung" },
    values: () => {
      const w = wiredTrigger();
      return { inputGuid: w?.deviceGuid, inputChar: w?.identifier || "input", outputGuid: relayTarget()?.deviceGuid, logic: "buttonImpulseSwitch", off: 10, long: 0, pre: true };
    },
  },
  {
    id: "toggle",
    en: { name: "Template: Pushbutton toggle", desc: "Taster: each press toggles the relay, no timer." },
    de: { name: "Vorlage: Taster-Umschaltung", desc: "Jeder Tastendruck schaltet das Relais um, ohne Timer." },
    description: "pushbutton-toggle",
    classes: ["ESR"],
    suggest: { en: "Pushbutton toggle", de: "Taster-Umschaltung" },
    values: () => {
      const w = wiredTrigger();
      return { inputGuid: w?.deviceGuid, inputChar: w?.identifier || "input", outputGuid: relayTarget()?.deviceGuid, logic: "buttonImpulseSwitch", off: 0, long: 0, pre: false };
    },
  },
  {
    id: "rocker",
    en: { name: "Template: Rocker switch", desc: "Kippschalter: output follows press and release." },
    de: { name: "Vorlage: Kippschalter", desc: "Der Ausgang folgt Druck und Loslassen der Wippe." },
    description: "rocker-switch",
    classes: ["ESR"],
    suggest: { en: "Rocker switch", de: "Kippschalter" },
    values: () => {
      const w = wiredTrigger();
      return { inputGuid: w?.deviceGuid, inputChar: w?.identifier || "input", outputGuid: relayTarget()?.deviceGuid, logic: "buttonSwitch", off: 0, long: 0, pre: false };
    },
  },
  {
    id: "longpress",
    en: { name: "Template: Long-press timer", desc: "Short press toggles, long press starts a 60s auto-off timer." },
    de: { name: "Vorlage: Langdruck-Timer", desc: "Kurzdruck schaltet um, Langdruck startet 60s-Timer." },
    description: "longpress-timer",
    classes: ["ESR"],
    suggest: { en: "Long-press timer", de: "Langdruck-Timer" },
    values: () => {
      const w = wiredTrigger();
      return { inputGuid: w?.deviceGuid, inputChar: w?.identifier || "input", outputGuid: relayTarget()?.deviceGuid, logic: "buttonImpulseSwitch", off: 0, long: 60, pre: false };
    },
  },
  {
    id: "alwayson",
    en: { name: "Template: Always on", desc: "Press always switches the relay on (manufacturer pattern, targetValue 1)." },
    de: { name: "Vorlage: Immer ein", desc: "Druck schaltet das Relais immer ein (Herstellermuster, targetValue 1)." },
    description: "always-on",
    classes: ["ESR"],
    suggest: { en: "Always on", de: "Immer ein" },
    values: () => {
      const w = wiredTrigger();
      return { inputGuid: w?.deviceGuid, inputChar: w?.identifier || "input", outputGuid: relayTarget()?.deviceGuid, logic: "target", off: 0, long: 0, pre: false, target: 1 };
    },
  },
  {
    id: "alwaysoff",
    en: { name: "Template: Always off", desc: "Press always switches the relay off (manufacturer pattern, targetValue 0)." },
    de: { name: "Vorlage: Immer aus", desc: "Druck schaltet das Relais immer aus (Herstellermuster, targetValue 0)." },
    description: "always-off",
    classes: ["ESR"],
    suggest: { en: "Always off", de: "Immer aus" },
    values: () => {
      const w = wiredTrigger();
      return { inputGuid: w?.deviceGuid, inputChar: w?.identifier || "input", outputGuid: relayTarget()?.deviceGuid, logic: "target", off: 0, long: 0, pre: false, target: 0 };
    },
  },
  {
    id: "window",
    en: { name: "Template: Window contact", desc: "FTK contact drives the relay (follows open/close)." },
    de: { name: "Vorlage: Fensterkontakt", desc: "FTK-Kontakt steuert das Relais (folgt Auf/Zu)." },
    description: "window-contact",
    classes: ["ESR"],
    suggest: { en: "Window contact", de: "Fensterkontakt" },
    values: () => {
      const c = contactTrigger() || wiredTrigger();
      return { inputGuid: c?.deviceGuid, inputChar: c?.identifier || "contact", outputGuid: relayTarget()?.deviceGuid, logic: "buttonSwitch", off: 0, long: 0, pre: false };
    },
  },
  {
    id: "enocean",
    en: { name: "Template: EnOcean rocker", desc: "Paired wireless rocker toggles the relay." },
    de: { name: "Vorlage: EnOcean-Wippe", desc: "Gekoppelte Funkwippe schaltet das Relais." },
    description: "enocean-rocker",
    classes: ["ESR"],
    suggest: { en: "EnOcean rocker", de: "EnOcean-Wippe" },
    values: () => {
      const b = buttonTrigger();
      return { inputGuid: b?.deviceGuid, inputChar: b?.identifier || "input", outputGuid: relayTarget()?.deviceGuid, logic: "buttonImpulseSwitch", off: 0, long: 0, pre: false };
    },
  },
];

const picker = $("picker"), tmplList = $("tmplList"), tgtList = $("tgtList");
let pickedTarget = null;

/* --- Mini wiring diagrams (inline SVG, zero deps) -------------------------
 * Schematic-style preview per template: input symbol ──► logic box ──►
 * relay + lamp, with timer annotations. Generated from template values. */

const escXml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;",
}[c]));

function inputSymbol(char) {
  // DIN-style momentary symbols, drawn around center x=34, contacts ~y=44.
  const c = char || "";
  if (/contact|window/i.test(c)) {
    // reed tube with inner contacts + magnet bar
    return `<rect x="24" y="24" width="12" height="18" fill="none" stroke="currentColor" stroke-width="2"/>`
      + `<line x1="30" y1="24" x2="30" y2="30" stroke="currentColor" stroke-width="2"/>`
      + `<line x1="30" y1="36" x2="30" y2="42" stroke="currentColor" stroke-width="2"/>`
      + `<rect x="42" y="20" width="5" height="26" fill="currentColor"/>`
      + `<line x1="30" y1="42" x2="30" y2="48" stroke="currentColor" stroke-width="2"/>`;
  }
  if (/button/i.test(c)) {
    // rocker: housing, tilted paddle, pivot dot
    return `<rect x="20" y="22" width="28" height="22" rx="2" fill="none" stroke="currentColor" stroke-width="2"/>`
      + `<line x1="23" y1="41" x2="45" y2="25" stroke="currentColor" stroke-width="2"/>`
      + `<circle cx="34" cy="33" r="1.8" fill="currentColor"/>`;
  }
  // pushbutton (NO): base line, terminal ticks, angled bridge with contact dot
  return `<line x1="20" y1="44" x2="48" y2="44" stroke="currentColor" stroke-width="2"/>`
    + `<line x1="23" y1="44" x2="23" y2="50" stroke="currentColor" stroke-width="2"/>`
    + `<line x1="45" y1="44" x2="45" y2="50" stroke="currentColor" stroke-width="2"/>`
    + `<line x1="23" y1="32" x2="43" y2="41" stroke="currentColor" stroke-width="2"/>`
    + `<circle cx="44" cy="42" r="2" fill="currentColor"/>`;
}

function logicShort(value) {
  const map = {
    buttonImpulseSwitch: t("logicImpulseShort"),
    buttonSwitch: t("logicSwitchShort"),
    buttonNormallyOpened: t("logicNOShort"),
    buttonNormallyClosed: t("logicNCShort"),
    target: t("logicTargetShort"),
    buttonTargetValue: t("logicTargetShort"),
  };
  return map[value] || value || "?";
}

function miniDiagram(v, outIdent, outClass) {
  if (!v.logic) return "";
  const parts = [];
  if (v.off > 0) parts.push(`t=${v.off}s`);
  if (v.long > 0) parts.push(`tL=${v.long}s`);
  if (v.pre && v.off > 0) parts.push("+pre");
  if (v.logic === "target" && v.target !== undefined) parts.push(`→${v.target}`);
  const sub = escXml(parts.join("  "));
  const inChar = escXml(v.inputChar || "");
  const title = escXml(`${v.inputChar || "?"} → ${v.logic} → ${outIdent || outClass || "?"}`);
  return `<svg width="240" height="80" viewBox="0 0 240 80" role="img" aria-label="${title}">`
    + `<title>${title}</title>`
    + `<g style="color:var(--secondary-text-color)">`
    + inputSymbol(v.inputChar)
    + `<line x1="52" y1="34" x2="62" y2="34" stroke="currentColor" stroke-width="2"/>`
    + `<polygon points="62,30 70,34 62,38" fill="currentColor"/>`
    + `</g>`
    + `<rect x="70" y="12" width="92" height="42" rx="8" fill="rgba(3,169,244,0.07)" stroke="var(--primary-color)" stroke-width="1.5"/>`
    + `<text x="116" y="32" text-anchor="middle" font-size="11" font-weight="600" fill="currentColor">${escXml(logicShort(v.logic))}</text>`
    + `<text x="116" y="46" text-anchor="middle" font-size="9" fill="var(--secondary-text-color)">${sub}</text>`
    + `<g style="color:var(--secondary-text-color)"><line x1="162" y1="34" x2="172" y2="34" stroke="currentColor" stroke-width="2"/>`
    + `<polygon points="172,30 180,34 172,38" fill="currentColor"/></g>`
    + `<g><rect x="180" y="21" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2"/>`
    + `<text x="193" y="39" text-anchor="middle" font-size="11" font-weight="600" fill="currentColor">K</text></g>`
    + `<line x1="206" y1="34" x2="210" y2="34" stroke="currentColor" stroke-width="2"/>`
    + `<g stroke="currentColor" stroke-width="2"><circle cx="221" cy="34" r="10" fill="none"/>`
    + `<line x1="215" y1="28" x2="227" y2="40" stroke-width="1.6"/><line x1="227" y1="28" x2="215" y2="40" stroke-width="1.6"/>`
    + `<line x1="221" y1="19" x2="221" y2="22" stroke-width="1.6"/><line x1="221" y1="46" x2="221" y2="49" stroke-width="1.6"/>`
    + `<line x1="233" y1="34" x2="236" y2="34" stroke-width="1.6"/></g>`
    + `<text x="34" y="72" text-anchor="middle" font-size="8" fill="var(--secondary-text-color)">${inChar}</text>`
    + `<text x="200" y="72" text-anchor="middle" font-size="8" fill="var(--secondary-text-color)">${escXml(outIdent || "")}</text>`
    + `</svg>`;
}

function templateApplies(tmpl, cls) {
  return !tmpl.classes || tmpl.classes.includes(cls);
}

function renderTargets() {
  tgtList.innerHTML = "";
  const targets = state.caps?.targets || [];
  for (const tgt of targets) {
    const btn = document.createElement("button");
    btn.textContent = `${tgt.displayName} · ${tgt.identifier} (${tgt.deviceClass})`;
    btn.title = tgt.deviceGuid;
    if (pickedTarget && pickedTarget.deviceGuid === tgt.deviceGuid && pickedTarget.identifier === tgt.identifier) {
      btn.classList.add("selected");
    }
    btn.addEventListener("click", () => {
      pickedTarget = tgt;
      renderTargets();
      renderTemplates();
    });
    tgtList.appendChild(btn);
  }
}

function renderTemplates() {
  tmplList.innerHTML = "";
  const cls = pickedTarget?.deviceClass || "ESR";
  for (const tmpl of TEMPLATES.filter((x) => templateApplies(x, cls))) {
    const txt = tmpl[lang] || tmpl.en;
    const btn = document.createElement("button");
    const name = document.createElement("strong");
    name.textContent = txt.name;
    const desc = document.createElement("small");
    desc.textContent = txt.desc;
    btn.append(name, desc);
    try {
      const preview = miniDiagram(
        { ...tmpl.values(), suggest: tmpl.suggest },
        pickedTarget?.identifier, pickedTarget?.deviceClass
      );
      if (preview) {
        const holder = document.createElement("div");
        holder.className = "meta";
        holder.innerHTML = preview;
        btn.append(holder);
      }
    } catch { /* preview is best-effort; picker works without it */ }
    btn.addEventListener("click", () => {
      picker.close();
      state.editing = null;
      openEditor(null);
      const v = tmpl.values();
      if (pickedTarget) {
        v.outputGuid = pickedTarget.deviceGuid;
        v.outputChar = pickedTarget.identifier;
      }
      prefillForm({ ...v, suggest: tmpl.suggest });
    });
    tmplList.appendChild(btn);
  }
}

function openPicker() {
  const targets = state.caps?.targets || [];
  if (!triggerDevices().length || !targets.length) { alert(t("noDevices")); return; }
  fillDeviceSelects();
  if (!pickedTarget || !targets.some((x) => x.deviceGuid === pickedTarget.deviceGuid && x.identifier === pickedTarget.identifier)) {
    pickedTarget = targets[0];
  }
  renderTargets();
  renderTemplates();
  picker.showModal();
}

$("new").addEventListener("click", () => openPicker());
$("fInput").addEventListener("change", () => syncInputChars());
$("fOutput").addEventListener("change", () => syncOutput());
$("fOutputChar").addEventListener("change", () => syncLogics());

document.querySelectorAll("dialog").forEach((dlg) => {
  dlg.querySelectorAll('button[value="cancel"]').forEach((btn) =>
    btn.addEventListener("click", () => dlg.close())
  );
});
$("lang").addEventListener("change", async (e) => {
  lang = e.target.value;
  applyI18n();
  $("count").textContent = t("count")(state.rules.length);
  if (editor.open) syncLogics($("fLogic").value);
  render();
});

$("save").addEventListener("click", async (e) => {
  e.preventDefault();
  try {
    const payload = formToPayload();
    if (selectedTargetClass() === "EUD") {
      showProblems([t("eudNote")]);
      return;
    }
    const check = await api("/api/validate", { method: "POST", body: JSON.stringify(payload) }).catch(() => ({ ok: true, problems: [] }));
    if (!check.ok) {
      showProblems(check.problems || []);
      return;
    }
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

function showProblems(problems) {
  const box = $("fErr");
  box.innerHTML = "";
  const head = document.createElement("div");
  head.textContent = t("fixBeforeSave");
  const ul = document.createElement("ul");
  ul.style.margin = "4px 0 4px 18px";
  ul.style.padding = "0";
  for (const p of problems) {
    const li = document.createElement("li");
    li.textContent = p;
    ul.append(li);
  }
  box.append(head, ul);
}

/* Live pre-check while editing: surfaces spec problems as soon as the
 * conflicting field changes, without blocking. */
let _validateTimer = 0;
async function revalidateQuietly() {
  if (!editor.open) return;
  try {
    const check = await api("/api/validate", {
      method: "POST", body: JSON.stringify(formToPayload()),
    });
    if (check.ok) $("fErr").innerHTML = "";
    else showProblems(check.problems || []);
  } catch { /* dev server unreachable: save will report */ }
}
for (const id of ["fLogic", "fOff", "fLong", "fPre", "fTarget"]) {
  $(id).addEventListener("change", () => {
    clearTimeout(_validateTimer);
    _validateTimer = setTimeout(revalidateQuietly, 250);
  });
}

$("reset").addEventListener("click", async () => {
  if (!confirm(t("confirmReset"))) return;
  await api("/api/automations", { method: "DELETE" });
  await refresh();
});

applyI18n();
refresh().catch((err) => {
  listEl.innerHTML = "";
  const div = document.createElement("div");
  div.className = "card";
  const em = document.createElement("div");
  em.className = "err";
  em.textContent = `Failed to reach studio API: ${err.message}. Is python3 studio/server.py running?`;
  div.appendChild(em);
  listEl.appendChild(div);
});
