/* Eltako Automation Studio — vanilla JS, zero runtime deps.
 * Talks only to the thin Studio API (server.py), which mirrors the future
 * HA WebSocket command payloads. Run `tsc --allowJs --checkJs` for types
 * without adding a build step; full TS migration = rename to .ts later.
 */

const STRINGS = {
  en: {
    preset: "Template: Staircase + prewarning",
    presetTitle: "Short press turns the relay on, auto-off after the timer. Prewarning flickers the light 3× starting 30s before switch-off.",
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
    pickerTitle: "Choose a template",    fInput: "Input device",
    fInputChar: "Input characteristic",
    fOutput: "Output actuator",
    fOutputChar: "Output characteristic",
    fLogic: "Logic",
    fOff: "Off-timer (s, 0 = off)",
    fLong: "Long-press off-timer (s, 0 = off)",
    fPre: "Prewarning flicker (30s before off)",
    fTarget: "Target value 0–100 (for target logic)",
    fActive: "Rule active",
    hintLogic: "Impulse = pushbutton (Taster), Switch = rocker (Kippschalter), NO/NC = momentary contact, Target = fixed value.",
    hintOff: "Auto-off delay after a short press. 0 disables it.",
    hintLong: "Separate auto-off timer armed by a long press.",
    hintPre: "Flickers the relay 3× before the off-timer expires. Needs an off-timer > 30s to be useful.",
    hintTarget: "Only used with Target logic: the output moves to this value.",
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
    pillOff: (s) => `Off-Timer: ${s}s`,
    pillLong: (s) => `Long-press: ${s}s`,
    pillPre: "Prewarning flicker",
    pillTarget: (v) => `Target ${v}`,
    count: (n) => `${n} rule${n === 1 ? "" : "s"}`,
    tmpl: "Template",
    tipInput: "Which physical input triggers the rule: wired dry contact, FTK window contact, or EnOcean rocker half.",
    tipOutput: "Which actuator output this rule drives (ESR relay channel).",
    tipLogic: "Impulse = pushbutton toggles on press. Switch = rocker follows press/release. NO/NC = output active only while pressed. Target = move to a fixed value.",
    tipOff: "Auto-off delay after a short press (staircase timer). 0 disables it. Not supported with Switch logic.",
    tipLong: "Separate auto-off timer armed by a long press instead of a short one.",
    tipPre: "Flickers the relay 3× starting 30s before the off-timer expires. Needs an off-timer > 30s to be useful.",
    tipTarget: "Only used with Target logic: the output moves to this value (0–100). Without it the device toggles min/max.",
  },
  de: {
    preset: "Vorlage: Treppenlicht + Vorwarnung",
    presetTitle: "Kurzer Druck schaltet ein, automatisches Ausschalten nach Zeit. Vorwarnung lässt das Licht 30s vorher 3× flackern.",
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
    fInput: "Eingang (Taster/Kontakt)",
    fInputChar: "Eingangsmerkmal",
    fOutput: "Aktor (Ausgang)",
    fOutputChar: "Ausgangsmerkmal",
    fLogic: "Logik",
    fOff: "Ausschaltverzögerung (s, 0 = aus)",
    fLong: "Ausschaltverzögerung bei Langdruck (s, 0 = aus)",
    fPre: "Vorwarn-Flackern (30s vor Aus)",
    fTarget: "Zielwert 0–100 (für Target-Logik)",
    fActive: "Regel aktiv",
    hintLogic: "Impuls = Taster, Schalter = Kippschalter, NO/NC = Tastkontakt, Target = Festwert.",
    hintOff: "Automatische Abschaltung nach Kurzdruck. 0 = deaktiviert.",
    hintLong: "Eigener Timer, der per Langdruck gestartet wird.",
    hintPre: "Lässt das Relais vor Ablauf 3× flackern. Sinnvoll erst ab Timer > 30s.",
    hintTarget: "Nur für Target-Logik: Der Ausgang fährt auf diesen Wert.",
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
    pillOff: (s) => `Timer: ${s}s`,
    pillLong: (s) => `Langdruck: ${s}s`,
    pillPre: "Vorwarnung",
    pillTarget: (v) => `Ziel ${v}`,
    count: (n) => `${n} Regel${n === 1 ? "" : "n"}`,
    tmpl: "Vorlage",
    tipInput: "Welcher physische Eingang die Regel auslöst: Drahtkontakt, FTK-Fensterkontakt oder EnOcean-Wippenhälfte.",
    tipOutput: "Welcher Aktor-Ausgang angesteuert wird (ESR-Relaiskanal).",
    tipLogic: "Impuls = Taster schaltet um. Schalter = Wippe folgt Druck/Loslassen. NO/NC = Ausgang nur während Druck aktiv. Target = fester Zielwert.",
    tipOff: "Ausschaltverzögerung nach Kurzdruck (Treppenlicht). 0 = aus. Nicht mit Schalter-Logik kombinierbar.",
    tipLong: "Eigener Ausschalt-Timer, der per Langdruck statt Kurzdruck gestartet wird.",
    tipPre: "Lässt das Relais 30s vor Ablauf 3× flackern. Sinnvoll erst ab Timer > 30s.",
    tipTarget: "Nur für Target-Logik: Der Ausgang fährt auf diesen Wert (0–100). Ohne Wert schaltet das Gerät Min/Max um.",
  },
};

const state = { rules: [], devices: [], enocean: [], editing: null };
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

function logicLabels() {
  return {
    buttonImpulseSwitch: t("logicImpulseShort"),
    buttonSwitch: t("logicSwitchShort"),
    buttonNormallyOpened: t("logicNOShort"),
    buttonNormallyClosed: t("logicNCShort"),
    target: t("logicTargetShort"),
  };
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
  if (c === "contact") return t("kindWindow");
  if (c.startsWith("button")) return t("kindRocker");
  return t("kindWired");
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

function isTemplateRule(rule) {
  const desc = rule.description || "";
  if (typeof TEMPLATES !== "undefined" && TEMPLATES.some((tmpl) => tmpl.description && desc === tmpl.description)) return true;
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
  const modeEl = $("mode");
  modeEl.textContent = status.mode || "mock";
  modeEl.classList.toggle("live", status.mode === "live");
  $("count").textContent = t("count")(rules.length);
  render();
}

function render() {
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
  const labels = logicLabels();
  for (const rule of state.rules) {
    const cfg = rule.configuration;
    const card = document.createElement("div");
    card.className = "card";
    const health = rule.operatingStatus && rule.operatingStatus !== "success"
      ? `<span class="pill warn">${rule.operatingStatus}</span>` : "";
    const flow = document.createElement("div");
    flow.className = "flow";
    const tmplPill = isTemplateRule(rule)
      ? `<span class="pill logic" title="${t("presetTitle")}">${t("tmpl")}</span>` : "";
    const pillsHtml = addonPills(rule).map((p) => `<span class="pill" title="${p.title}">${p.text}</span>`).join("");
    flow.innerHTML = `
      ${tmplPill}
      <span class="pill" title="${t("tipInput")}">${inputKind(rule)} · ${deviceName(cfg.inputDeviceGuid)}</span>
      <span class="arrow">──►</span>
      <span class="pill logic" title="${t("tipLogic")}">${labels[cfg.logic] || cfg.logic}</span>
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
    card.append(flow, row);
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
  const get = (t2) => (cfg.addOns || []).find((a) => a.type === t2);
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
  const description = state.editing?.description || state.pendingDescription || "studio";
  state.pendingDescription = null;
  return {
    enabled: $("fActive").checked,
    description,
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
  $("editorTitle").textContent = rule ? t("titleEdit") : t("titleNew");
  $("fErr").textContent = "";
  if (rule) ruleToForm(rule);
  editor.showModal();
}

function prefillForm(v) {
  if (v.inputGuid) $("fInput").value = v.inputGuid;
  if (v.inputChar) $("fInputChar").value = v.inputChar;
  if (v.outputGuid) $("fOutput").value = v.outputGuid;
  if (v.logic) $("fLogic").value = v.logic;
  if (v.off !== undefined) $("fOff").value = v.off;
  if (v.long !== undefined) $("fLong").value = v.long;
  if (v.pre !== undefined) $("fPre").checked = v.pre;
  if (v.target !== undefined) $("fTarget").value = v.target;
  $("fActive").checked = v.active !== false;
}

function wiredInput() {
  return state.devices.find((d) => /wired input/i.test(d.displayName || ""))
    || state.devices[1] || state.devices[0];
}

function relayOutput() {
  return state.devices.find((d) => /ESR/i.test(d.displayName || ""))
    || state.devices[0];
}

function windowDevice() {
  return state.devices.find((d) => (d.infos || []).some((f) => f.identifier === "contact"))
    || state.devices.find((d) => /window|fenster|ftk/i.test(d.displayName || ""))
    || null;
}

function enoceanInput() {
  const eo = state.enocean[0];
  return eo ? { deviceGuid: eo.deviceGuid } : wiredInput();
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
    values: () => ({ inputGuid: wiredInput()?.deviceGuid, inputChar: "input", outputGuid: relayOutput()?.deviceGuid, logic: "buttonImpulseSwitch", off: 10, long: 0, pre: true }),
  },
  {
    id: "toggle",
    en: { name: "Template: Pushbutton toggle", desc: "Taster: each press toggles the relay, no timer." },
    de: { name: "Vorlage: Taster-Umschaltung", desc: "Jeder Tastendruck schaltet das Relais um, ohne Timer." },
    description: "pushbutton-toggle",
    values: () => ({ inputGuid: wiredInput()?.deviceGuid, inputChar: "input", outputGuid: relayOutput()?.deviceGuid, logic: "buttonImpulseSwitch", off: 0, long: 0, pre: false }),
  },
  {
    id: "rocker",
    en: { name: "Template: Rocker switch", desc: "Kippschalter: output follows press and release." },
    de: { name: "Vorlage: Kippschalter", desc: "Der Ausgang folgt Druck und Loslassen der Wippe." },
    description: "rocker-switch",
    values: () => ({ inputGuid: wiredInput()?.deviceGuid, inputChar: "input", outputGuid: relayOutput()?.deviceGuid, logic: "buttonSwitch", off: 0, long: 0, pre: false }),
  },
  {
    id: "longpress",
    en: { name: "Template: Long-press timer", desc: "Short press toggles, long press starts a 60s auto-off timer." },
    de: { name: "Vorlage: Langdruck-Timer", desc: "Kurzdruck schaltet um, Langdruck startet 60s-Timer." },
    description: "longpress-timer",
    values: () => ({ inputGuid: wiredInput()?.deviceGuid, inputChar: "input", outputGuid: relayOutput()?.deviceGuid, logic: "buttonImpulseSwitch", off: 0, long: 60, pre: false }),
  },
  {
    id: "window",
    en: { name: "Template: Window contact", desc: "FTK contact drives the relay (follows open/close)." },
    de: { name: "Vorlage: Fensterkontakt", desc: "FTK-Kontakt steuert das Relais (folgt Auf/Zu)." },
    description: "window-contact",
    values: () => ({ inputGuid: windowDevice()?.deviceGuid || wiredInput()?.deviceGuid, inputChar: "contact", outputGuid: relayOutput()?.deviceGuid, logic: "buttonSwitch", off: 0, long: 0, pre: false }),
  },
  {
    id: "enocean",
    en: { name: "Template: EnOcean rocker", desc: "Paired wireless rocker (buttonA0) toggles the relay." },
    de: { name: "Vorlage: EnOcean-Wippe", desc: "Gekoppelte Funkwippe (buttonA0) schaltet das Relais." },
    description: "enocean-rocker",
    values: () => ({ inputGuid: enoceanInput()?.deviceGuid, inputChar: "buttonA0", outputGuid: relayOutput()?.deviceGuid, logic: "buttonImpulseSwitch", off: 0, long: 0, pre: false }),
  },
];

const picker = $("picker"), tmplList = $("tmplList");

function openPicker() {
  if (!state.devices.length) { alert(t("noDevices")); return; }
  fillDeviceSelects();
  tmplList.innerHTML = "";
  for (const tmpl of TEMPLATES) {
    const txt = tmpl[lang] || tmpl.en;
    const btn = document.createElement("button");
    const name = document.createElement("strong");
    name.textContent = txt.name;
    const desc = document.createElement("small");
    desc.textContent = txt.desc;
    btn.append(name, desc);
    btn.addEventListener("click", () => {
      picker.close();
      state.editing = null;
      state.pendingDescription = tmpl.description || "studio";
      openEditor(null);
      prefillForm(tmpl.values());
    });
    tmplList.appendChild(btn);
  }
  picker.showModal();
}

$("new").addEventListener("click", () => openPicker());
$("lang").addEventListener("change", async (e) => {
  lang = e.target.value;
  applyI18n();
  $("count").textContent = t("count")(state.rules.length);
  render();
});

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
